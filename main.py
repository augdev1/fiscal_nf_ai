import pandas as pd
import time
import xmltodict
import sqlite3
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List

# Funções do projeto
from ia_agente import gerar_resumo_nf
from gerar_relatorio_pdf import gerar_relatorio_pdf
from db_repository import (
    inserir_atualizar_empresa, 
    inserir_nota_completa, 
    registrar_log
)


def extrair_inf_nfe(data: dict) -> dict:
    """
    Aceita tanto:
    - nfeProc -> NFe -> infNFe
    - NFe -> infNFe
    Retorna sempre o dict de infNFe.
    """
    if "nfeProc" in data:
        return data["nfeProc"]["NFe"]["infNFe"]
    if "NFe" in data:
        return data["NFe"]["infNFe"]
    for k in data.keys():
        if k.endswith("NFe"):
            return data[k]["infNFe"]
    raise KeyError("Estrutura de NF-e não reconhecida")


app = FastAPI(title="FiscalIA Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Servir arquivos estáticos da pasta assets
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/health")
async def health():
    return {"status": "🚀 FiscalIA Pro rodando!", "ok": True}


@app.post("/processar-xml")
async def processar_xml(file: UploadFile = File(...)):
    """Upload 1 XML → extrai CNPJ/total"""
    try:
        content = await file.read()
        data = xmltodict.parse(content)
        print("RAIZ KEYS:", list(data.keys()))
        nfe = extrair_inf_nfe(data)

        return {
            "cnpj_emit": nfe["emit"]["CNPJ"],
            "nome_emit": nfe["emit"]["xNome"],
            "total_nf": float(nfe["total"]["ICMSTot"]["vNF"]),
            "icms": float(nfe["total"]["ICMSTot"]["vICMS"]),
        }
    except Exception as e:
        print("ERRO AO PROCESSAR XML:", repr(e))
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {e}")


@app.post("/processar-nfes")
async def processar_nfes(files: List[UploadFile] = File(...)):
    """
    Recebe vários XMLs, extrai dados, salva no banco de dados,
    soma totais e gera um relatório Excel.
    """
    resultados = []
    total_geral = 0.0
    total_icms = 0.0
    notas_processadas_com_sucesso = 0
    erros_processamento = []
    
    # Guarda o momento de início para usar em ambos os logs
    inicio_processo = datetime.now()

    # Inicia o log do processo de lote
    log_id = registrar_log(
        tipo_processo="processamento_nfe_lote",
        status="iniciado",
        iniciado_em=inicio_processo
    )

    for file in files:
        try:
            content = await file.read()
            data = xmltodict.parse(content)
            nfe = extrair_inf_nfe(data)

            # --- Persistência no Banco de Dados ---
            
            # 1. Salvar a empresa
            emitente = nfe["emit"]
            empresa_id = inserir_atualizar_empresa(nome=emitente["xNome"], cnpj=emitente["CNPJ"])

            # 2. Preparar dados da nota
            ide = nfe["ide"]
            total = nfe["total"]["ICMSTot"]
            
            # A chave de acesso pode ter o prefixo "NFe", removemos ele
            chave_acesso = nfe["@Id"].replace("NFe", "")
            
            # A data de emissão pode ser um datetime, pegamos apenas a parte da data
            data_emissao = ide["dhEmi"][:10]

            nota_data = {
                "empresa_id": empresa_id,
                "numero": int(ide["nNF"]),
                "serie": int(ide["serie"]),
                "chave_acesso": chave_acesso,
                "data_emissao": data_emissao,
                "valor_total": float(total["vNF"]),
                "cfop_principal": nfe["det"][0]["prod"]["CFOP"] if isinstance(nfe["det"], list) else nfe["det"]["prod"]["CFOP"],
                "destinatario_nome": nfe.get("dest", {}).get("xNome"),
                "destinatario_cnpj": nfe.get("dest", {}).get("CNPJ")
            }

            # 3. Preparar dados dos itens
            # Garante que 'det' seja sempre uma lista
            detalhes_itens = nfe["det"]
            if not isinstance(detalhes_itens, list):
                detalhes_itens = [detalhes_itens]

            itens_data = []
            for item in detalhes_itens:
                prod = item["prod"]
                itens_data.append({
                    "codigo_produto": prod["cProd"],
                    "descricao": prod["xProd"],
                    "quantidade": float(prod["qCom"]),
                    "valor_unitario": float(prod["vUnCom"]),
                    "valor_total": float(prod["vProd"]),
                    "cfop": prod["CFOP"],
                    "ncm": prod.get("NCM")
                })
            
            # 4. Inserir nota e itens de forma transacional
            inserir_nota_completa(nota_data, itens_data)
            
            # --- Fim da Persistência ---

            # Mantém a lógica original para o relatório
            valor_nf = float(total["vNF"])
            valor_icms = float(total.get("vICMS", 0.0))

            total_geral += valor_nf
            total_icms += valor_icms
            
            resultados.append({
                "arquivo": file.filename,
                "cnpj_emit": emitente["CNPJ"],
                "nome_emit": emitente["xNome"],
                "total_nf": valor_nf,
                "icms": valor_icms,
            })
            notas_processadas_com_sucesso += 1

        except sqlite3.IntegrityError as e:
            # Erro comum se a chave de acesso já existir
            erro_msg = f"Nota já existe no banco de dados (chave duplicada)."
            print(f"AVISO NO ARQUIVO {file.filename}: {erro_msg}")
            erros_processamento.append(f"{file.filename}: {erro_msg}")
        except Exception as e:
            # Captura outros erros durante o processamento do arquivo
            erro_msg = f"Erro inesperado: {repr(e)}"
            print(f"ERRO NO ARQUIVO {file.filename}: {erro_msg}")
            erros_processamento.append(f"{file.filename}: {erro_msg}")
            # Decide se um erro em um arquivo deve parar todo o lote.
            # Aqui, vamos apenas registrar e continuar.
    
    # Atualiza o log do processo de lote com o resultado final
    status_final = "sucesso_parcial" if erros_processamento else "sucesso"
    mensagem_log = f"{notas_processadas_com_sucesso} de {len(files)} notas processadas e salvas."
    
    registrar_log(
        tipo_processo="processamento_nfe_lote_finalizado",
        status=status_final,
        mensagem=mensagem_log,
        detalhes_erro=" | ".join(erros_processamento) if erros_processamento else None,
        iniciado_em=inicio_processo,  # Adicionado para corrigir o erro
        finalizado_em=datetime.now()
    )

    # Se nenhum resultado foi gerado, retorna um erro
    if not resultados:
        raise HTTPException(
            status_code=400,
            detail=f"Nenhuma nota pôde ser processada. Erros: {' | '.join(erros_processamento)}"
        )

    # Geração do DataFrame e do arquivo Excel (lógica original)
    df = pd.DataFrame(resultados)
    df = df.sort_values(by=["nome_emit", "total_nf"], ascending=[True, False])

    linha_total = {
        "arquivo": "TOTAL",
        "cnpj_emit": "",
        "nome_emit": "",
        "total_nf": total_geral,
        "icms": total_icms,
    }

    df = pd.concat([df, pd.DataFrame([linha_total])], ignore_index=True)
    nome_arquivo = f"relatorio_nfes_{int(time.time())}.xlsx"

    with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatorio")
        # (O restante da formatação do Excel é omitido para brevidade, mas funcionaria aqui)

    return {
        "qtd": len(resultados),
        "total_geral": total_geral,
        "total_icms": total_icms,
        "relatorio_excel": nome_arquivo,
        "notas": resultados,
        "erros": erros_processamento
    }


@app.get("/download-relatorio")
async def download_relatorio(nome_arquivo: str):
    """
    Faz o download do arquivo Excel gerado.
    """
    try:
        return FileResponse(
            path=nome_arquivo,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=nome_arquivo,
            headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
        )
    except Exception as e:
        print("ERRO AO ENVIAR EXCEL:", repr(e))
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {nome_arquivo}")


@app.get("/resumo-ia")
async def resumo_ia(nome_arquivo: str):
    df = pd.read_excel(nome_arquivo)
    texto = gerar_resumo_nf(df)
    return {"resumo": texto}


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" type="image/x-icon" href="/assets/logoai.ico">
        <title>FiscalIA Pro</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }

          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #000;
            color: #fff;
            overflow-x: hidden;
          }

          nav {
            position: fixed;
            top: 0;
            height: 80px;
            width: 100%;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(10px);
            z-index: 1000;
            border-bottom: 1px solid rgba(198,255,0,0.2);
          }
          
          .logo img {
            height: 80px;              /* normaliza o tamanho */
            width: auto;
            }

          .logo:hover {
            opacity: 0.8;
          }

          .nav-info {
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
          }

          .hero {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 100px 40px 60px;
            background: linear-gradient(135deg, #000 0%, #1a1a1a 100%);
            position: relative;
            overflow: hidden;
          }

          .hero-bg {
            position: absolute;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 50%, rgba(198,255,0,0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(198,255,0,0.05) 0%, transparent 50%);
          }

          .hero-content {
            position: relative;
            z-index: 1;
            text-align: center;
            max-width: 1200px;
            width: 100%;
          }

          .hero h1 {
            font-size: 80px;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #fff 0%, #c6ff00 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeInUp 1s ease;
          }

          .hero .subtitle {
            font-size: 18px;
            color: #888;
            margin-bottom: 60px;
            text-transform: uppercase;
            letter-spacing: 3px;
            animation: fadeInUp 1.2s ease;
          }

          .upload-container {
            width: 100%;
            max-width: 900px;
            margin: 40px auto;
            animation: fadeInUp 1.4s ease;
          }

          .upload-area {
            border: 3px solid rgba(198,255,0,0.3);
            padding: 80px 40px;
            text-align: center;
            background: rgba(198,255,0,0.02);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
          }

          .upload-area:hover {
            border-color: #c6ff00;
            background: rgba(198,255,0,0.05);
          }

          .upload-area.dragover {
            border-color: #c6ff00;
            background: rgba(198,255,0,0.1);
            transform: scale(1.01);
          }

          .upload-icon {
            font-size: 80px;
            margin-bottom: 20px;
            filter: grayscale(100%);
            opacity: 0.6;
            transition: all 0.3s;
          }

          .upload-area:hover .upload-icon {
            filter: grayscale(0%);
            opacity: 1;
          }

          .upload-text {
            font-size: 24px;
            color: #fff;
            margin-bottom: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
          }

          .upload-subtext {
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
          }

          input[type="file"] {
            display: none;
          }

          .file-list {
            margin-top: 30px;
            padding: 0;
          }

          .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(198,255,0,0.2);
            margin-bottom: 10px;
            transition: all 0.3s;
          }

          .file-item:hover {
            background: rgba(198,255,0,0.05);
            border-color: #c6ff00;
          }

          .file-name {
            color: #fff;
            font-size: 14px;
            flex: 1;
            text-transform: uppercase;
            letter-spacing: 1px;
          }

          .file-size {
            color: #888;
            font-size: 12px;
            margin-right: 20px;
            text-transform: uppercase;
          }

          .remove-file {
            background: transparent;
            color: #c6ff00;
            border: 1px solid #c6ff00;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s;
          }

          .remove-file:hover {
            background: #c6ff00;
            color: #000;
          }

          .btn {
            width: 100%;
            padding: 24px;
            font-size: 16px;
            font-weight: 700;
            border: 2px solid #c6ff00;
            background: transparent;
            color: #c6ff00;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 30px;
            text-transform: uppercase;
            letter-spacing: 2px;
          }

          .btn:hover:not(:disabled) {
            background: #c6ff00;
            color: #000;
            transform: translateY(-2px);
          }

          .btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
            border-color: #444;
            color: #444;
          }

          .btn-secondary {
            background: transparent;
            border: 2px solid #fff;
            color: #fff;
          }

          .btn-secondary:hover {
            background: #fff;
            color: #000;
          }

          .loading {
            display: none;
            text-align: center;
            padding: 60px 20px;
          }

          .loading.active {
            display: block;
          }

          .spinner {
            border: 3px solid rgba(198,255,0,0.1);
            border-top: 3px solid #c6ff00;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
          }

          .loading-text {
            color: #888;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 14px;
          }

          .resultado-section {
            max-width: 1200px;
            margin: 60px auto;
            padding: 0 40px;
          }

          .resultado-card {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(198,255,0,0.2);
            padding: 60px 40px;
            animation: slideIn 0.5s ease;
          }

          .resultado-title {
            font-size: 36px;
            font-weight: 900;
            color: #c6ff00;
            margin-bottom: 40px;
            text-transform: uppercase;
            letter-spacing: 2px;
          }

          .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            margin-bottom: 40px;
          }

          .stat-item {
            text-align: center;
            padding: 40px 20px;
            background: rgba(198,255,0,0.02);
            border: 1px solid rgba(198,255,0,0.2);
            transition: all 0.3s;
          }

          .stat-item:hover {
            background: rgba(198,255,0,0.05);
            border-color: #c6ff00;
            transform: translateY(-5px);
          }

          .stat-label {
            font-size: 12px;
            text-transform: uppercase;
            color: #888;
            margin-bottom: 15px;
            letter-spacing: 2px;
          }

          .stat-value {
            font-size: 42px;
            font-weight: 900;
            color: #c6ff00;
          }

          .action-buttons .btn,
          .action-buttons .btn-download {
            margin-top: 0 !important;
            margin-bottom: 5px;
            padding: 0 !important;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
          }



          .btn,
          .btn-download {
          height: 64px;
          padding: 0 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-sizing: border-box;
        }

        .btn-secondary {
          border: 2px solid #fff;
          color: #fff;
          background: transparent;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        .btn-download {
          background: transparent;
          border: 2px solid #c6ff00;
          color: #c6ff00;
          padding: 20px;
          text-decoration: none;
          display: block;
          text-align: center;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 2px;
          transition: all 0.3s;
        }

        .btn-download:hover {
          background: #c6ff00;
          color: #000;
          transform: translateY(-2px);
        }

        .resumo-ia-card {
          margin-top: 60px;
          padding: 60px 40px;
          background: rgba(255,255,255,0.02);
          border: 1px solid rgba(198,255,0,0.2);
          animation: slideIn 0.5s ease;
        }

          .resumo-ia-card h3 {
            color: #c6ff00;
            margin-bottom: 30px;
            font-size: 36px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
          }

          .resumo-ia-card pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.8;
            color: #aaa;
            font-family: inherit;
            font-size: 16px;
          }

          .hidden {
            display: none;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          @keyframes fadeInUp {
            from {
              opacity: 0;
              transform: translateY(30px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateX(-20px);
            }
            to {
              opacity: 1;
              transform: translateX(0);
            }
          }

          @media (max-width: 768px) {
            .hero h1 {
              font-size: 48px;
            }

            nav {
              padding: 15px 20px;
            }

            .logo {
              font-size: 20px;
            }

            .nav-info {
              display: none;
            }

            .upload-area {
              padding: 60px 20px;
            }

            .stats-grid {
              grid-template-columns: 1fr;
              gap: 15px;
            }

            .action-buttons {
              grid-template-columns: 1fr;
            }

            .resultado-card,
            .resumo-ia-card {
              padding: 40px 20px;
            }
          }
        </style>
      </head>
      <body>
        <nav>
            <a href="/" class="logo">
            <img src="/assets/logoai.png" alt="Fiscal IA Pro">
            </a>
          <div class="nav-info">Análise Inteligente</div>
        </nav>

        <section class="hero">
          <div class="hero-bg"></div>
          <div class="hero-content">
            <h1>FISCAL IA PRO</h1>
            <div class="subtitle">Relatório de NF-e com IA</div>

            <div class="upload-container">
              <form id="form-nfes" enctype="multipart/form-data">
                <div class="upload-area" id="upload-area" onclick="document.getElementById('file-input').click()">
                  <div class="upload-icon">📁</div>
                  <div class="upload-text">Carregar Arquivos XML</div>
                  <div class="upload-subtext">Arraste ou clique para selecionar</div>
                  <input id="file-input" name="files" type="file" multiple accept=".xml" />
                </div>

                <div id="file-list" class="file-list hidden"></div>

                <button type="button" class="btn" id="btn-processar" onclick="enviar()" disabled>
                  Gerar Relatório
                </button>
              </form>
            </div>

            <div class="loading" id="loading">
              <div class="spinner"></div>
              <div class="loading-text">Processando...</div>
            </div>
          </div>
        </section>

        <div class="resultado-section">
          <div id="resultado" class="hidden"></div>
          <div id="resumo-ia" class="hidden"></div>
        </div>

        <script>
        let selectedFiles = [];

        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const fileList = document.getElementById('file-list');
        const btnProcessar = document.getElementById('btn-processar');

        uploadArea.addEventListener('dragover', (e) => {
          e.preventDefault();
          uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
          uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
          e.preventDefault();
          uploadArea.classList.remove('dragover');
          const files = Array.from(e.dataTransfer.files);
          handleFiles(files);
        });

        fileInput.addEventListener('change', (e) => {
          const files = Array.from(e.target.files);
          handleFiles(files);
        });

        function handleFiles(files) {
          selectedFiles = files.filter(f => f.name.endsWith('.xml'));
          
          if (selectedFiles.length === 0) {
            alert('Por favor, selecione apenas arquivos XML.');
            return;
          }

          renderFileList();
          btnProcessar.disabled = false;
        }

        function renderFileList() {
          if (selectedFiles.length === 0) {
            fileList.classList.add('hidden');
            btnProcessar.disabled = true;
            return;
          }

          fileList.classList.remove('hidden');
          fileList.innerHTML = selectedFiles.map((file, index) => `
            <div class="file-item">
              <span class="file-name">📄 ${file.name}</span>
              <span class="file-size">${(file.size / 1024).toFixed(1)} KB</span>
              <button type="button" class="remove-file" onclick="removeFile(${index})">Remover</button>
            </div>
          `).join('');
        }

        function removeFile(index) {
          selectedFiles.splice(index, 1);
          renderFileList();
        }

        async function enviar() {
          const form = document.getElementById('form-nfes');
          const formData = new FormData();
          
          selectedFiles.forEach(file => {
            formData.append('files', file);
          });

          document.getElementById('loading').classList.add('active');
          document.getElementById('resultado').classList.add('hidden');
          document.getElementById('resumo-ia').classList.add('hidden');
          btnProcessar.disabled = true;

          try {
            const resp = await fetch('/processar-nfes', {
              method: 'POST',
              body: formData
            });

            const data = await resp.json();

            if (resp.ok) {
              mostrarResultado(data);
            } else {
              alert('Erro: ' + (data.detail || 'erro ao processar'));
            }
          } catch (error) {
            alert('Erro de conexão: ' + error.message);
          } finally {
            document.getElementById('loading').classList.remove('active');
            btnProcessar.disabled = false;
          }
        }

        function mostrarResultado(data) {
  const div = document.getElementById('resultado');
  div.classList.remove('hidden');

  div.innerHTML = `
    <div class="resultado-card">
      <h2 class="resultado-title">Resultado</h2>

      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-label">Notas Processadas</div>
          <div class="stat-value">${data.qtd}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Total Geral</div>
          <div class="stat-value">R$ ${data.total_geral.toFixed(2)}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Total ICMS</div>
          <div class="stat-value">R$ ${data.total_icms.toFixed(2)}</div>
        </div>
      </div>

      <div class="action-buttons">
        <a 
          href="/download-relatorio?nome_arquivo=${encodeURIComponent(data.relatorio_excel)}"
          class="btn-download"
        >
          Baixar Excel
        </a>

        <a 
          href="/gerar-relatorio-pdf?nome_arquivo=${encodeURIComponent(data.relatorio_excel)}"
          class="btn-download"
        >
          Baixar PDF
        </a>

        <button 
          type="button"
          class="btn"
          onclick="gerarResumoIA('${data.relatorio_excel}')"
        >
          Gerar Resumo IA
        </button>

      </div>
    </div>
          `;
        }

        async function gerarResumoIA(nomeArquivo) {
          document.getElementById('loading').classList.add('active');
          
          try {
            const resp = await fetch('/resumo-ia?nome_arquivo=' + encodeURIComponent(nomeArquivo));
            const data = await resp.json();

            if (resp.ok) {
              const resumoDiv = document.getElementById('resumo-ia');
              resumoDiv.classList.remove('hidden');
              resumoDiv.innerHTML = `
                <div class="resumo-ia-card">
                  <h3>Análise IA</h3>
                  <pre>${data.resumo}</pre>
                </div>
              `;
            } else {
              alert('Erro IA: ' + (data.detail || 'erro ao gerar resumo'));
            }
          } catch (error) {
            alert('Erro ao gerar resumo: ' + error.message);
          } finally {
            document.getElementById('loading').classList.remove('active');
          }
        }
        </script>
      </body>
    </html>
    """

@app.get("/gerar-relatorio-pdf")
async def relatorio_pdf(nome_arquivo: str):
    nome_arquivo = nome_arquivo.strip()
    caminho_pdf = gerar_relatorio_pdf(nome_arquivo)
    return FileResponse(
        caminho_pdf,
        media_type="application/pdf",
        filename="relatorio_nfes.pdf",
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
