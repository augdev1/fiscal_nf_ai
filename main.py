# -*- coding: utf-8 -*-

# 1. Imports de bibliotecas padrão
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 2. Imports de bibliotecas de terceiros
import pandas as pd
import uvicorn
import xmltodict
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# 3. Imports de módulos locais
from db_repository import inserir_atualizar_empresa, inserir_nota_completa
from db_setup import init_db
from gerar_relatorio_pdf import gerar_relatorio_pdf
from ia_agente import gerar_resumo_nf

# --- Configuração e Constantes ---

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
RELATORIOS_DIR = BASE_DIR / "relatorios"

# Garante que os diretórios essenciais existam na inicialização
RELATORIOS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


def gerar_nome_relatorio() -> str:
    """Gera nome único para o relatório com timestamp legível."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"relatorio_nfes_{timestamp}.xlsx"


def limpar_relatorios_antigos(dias_para_manter: int = 7) -> None:
    """Remove relatórios .xlsx mais antigos que N dias na pasta de relatórios."""
    if not RELATORIOS_DIR.exists():
        return

    agora = time.time()
    limite_segundos = dias_para_manter * 24 * 60 * 60

    for arquivo in RELATORIOS_DIR.glob("relatorio_nfes_*.xlsx"):
        try:
            mtime = arquivo.stat().st_mtime
            if (agora - mtime) > limite_segundos:
                arquivo.unlink()
        except OSError:
            # Se não conseguir apagar, apenas ignora para não quebrar o startup
            pass


app = FastAPI(
    title="FiscalIA Pro",
    description="API para processamento e análise inteligente de NF-e.",
    version="1.1.0",
)

# --- Funções Auxiliares de Lógica ---


def _extrair_inf_nfe(data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extrai o dicionário 'infNFe' de forma robusta, testando os caminhos mais comuns em XMLs de NF-e.
    """
    try:
        # Caminho 1: data -> nfeProc -> NFe -> infNFe (o mais comum)
        infNFe = data.get("nfeProc", {}).get("NFe", {}).get("infNFe")
        if infNFe:
            return infNFe, None

        # Caminho 2: data -> NFe -> infNFe (quando não há o grupo 'nfeProc')
        infNFe = data.get("NFe", {}).get("infNFe")
        if infNFe:
            return infNFe, None

        # Caminho 3: data -> infNFe (estrutura mais simples, incomum)
        infNFe = data.get("infNFe")
        if infNFe:
            return infNFe, None

        return None, "A tag 'infNFe' não foi encontrada nos locais esperados dentro do XML."
    except (AttributeError, TypeError) as e:
        return None, f"Erro inesperado ao processar a estrutura do XML: {repr(e)}"


async def _processa_arquivo_nfe(file: UploadFile) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Processa um único arquivo de NF-e, desde a leitura até a persistência no banco.
    Retorna uma tupla com (dados_sucesso, dados_erro).
    """
    try:
        # 1. Leitura e Decodificação do XML
        content_bytes = await file.read()
        try:
            content_str = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content_str = content_bytes.decode('latin-1')

        data = xmltodict.parse(content_str)

        nfe, erro = _extrair_inf_nfe(data)
        if erro:
            raise ValueError(erro)

        # 2. Extração Segura dos Dados
        emitente = nfe.get("emit")
        ide = nfe.get("ide")
        total = nfe.get("total", {}).get("ICMSTot")
        chave_acesso = nfe.get("@Id", "").replace("NFe", "")

        if not all([emitente, ide, total, chave_acesso]):
            raise KeyError("XML não contém tags essenciais como 'emit', 'ide', 'total' ou '@Id'.")

        data_emissao_raw = ide.get("dhEmi") or ide.get("dEmi")
        if not data_emissao_raw:
            raise ValueError("Data de emissão ('dhEmi' ou 'dEmi') não encontrada.")

        # 3. Persistência no Banco de Dados
        empresa_id = inserir_atualizar_empresa(
            nome=emitente.get("xNome"),
            cnpj=emitente.get("CNPJ"),
        )

        detalhes_itens = nfe.get("det", [])
        if not isinstance(detalhes_itens, list):
            detalhes_itens = [detalhes_itens]

        nota_data = {
            "empresa_id": empresa_id,
            "numero": int(ide["nNF"]),
            "serie": int(ide["serie"]),
            "chave_acesso": chave_acesso,
            "data_emissao": data_emissao_raw[:10],
            "valor_total": float(total["vNF"]),
            "cfop_principal": detalhes_itens[0].get("prod", {}).get("CFOP") if detalhes_itens else None,
            "destinatario_nome": nfe.get("dest", {}).get("xNome"),
            "destinatario_cnpj": nfe.get("dest", {}).get("CNPJ"),
        }

        itens_data = [
            {
                "codigo_produto": item.get("prod", {}).get("cProd"),
                "descricao": item.get("prod", {}).get("xProd"),
                "quantidade": float(item.get("prod", {}).get("qCom", 0)),
                "valor_unitario": float(item.get("prod", {}).get("vUnCom", 0)),
                "valor_total": float(item.get("prod", {}).get("vProd", 0)),
                "cfop": item.get("prod", {}).get("CFOP"),
                "ncm": item.get("prod", {}).get("NCM"),
            }
            for item in detalhes_itens
        ]

        inserir_nota_completa(nota_data, itens_data)

        # 4. Dados para o relatório de sucesso
        dados_sucesso = {
            "arquivo": file.filename,
            "cnpj_emit": emitente.get("CNPJ"),
            "nome_emit": emitente.get("xNome"),
            "total_nf": float(total["vNF"]),
            "icms": float(total.get("vICMS", 0.0)),
        }
        return dados_sucesso, None

    except sqlite3.IntegrityError:
        return None, {"arquivo": file.filename, "erro": "Nota fiscal já cadastrada (chave duplicada)."}
    except (ValueError, KeyError, TypeError, IndexError) as e:
        return None, {"arquivo": file.filename, "erro": f"Dados inválidos ou faltando: {e}"}
    except Exception as e:
        return None, {"arquivo": file.filename, "erro": f"Erro inesperado: {repr(e)}"}


def _gera_relatorio_excel(notas: List[Dict], totais: Dict) -> str:
    """Gera um relatório em Excel a partir dos dados processados e o salva em disco."""
    df = pd.DataFrame(notas)
    df = df.sort_values(by=["nome_emit", "total_nf"], ascending=[True, False])

    # Adiciona linha de total ao DataFrame
    df_total = pd.DataFrame(
        [
            {
                "arquivo": "TOTAL",
                "total_nf": totais["geral"],
                "icms": totais["icms"],
            }
        ]
    )
    df = pd.concat([df, df_total], ignore_index=True)

    nome_arquivo = gerar_nome_relatorio()
    caminho_excel = RELATORIOS_DIR / nome_arquivo

    df.to_excel(
        caminho_excel,
        index=False,
        sheet_name="RelatorioNFes",
        engine="openpyxl",
    )

    return nome_arquivo


# --- Eventos da Aplicação ---


@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados ao iniciar a aplicação."""
    print("Executando inicialização do banco de dados...")
    init_db()
    limpar_relatorios_antigos(dias_para_manter=7)
    print("Inicialização do banco de dados concluída.")


# --- Middlewares e Rotas Estáticas ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


# --- Endpoints da API ---


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    """Serve a página principal da aplicação."""
    index_path = ASSETS_DIR / "index.html"
    if not index_path.is_file():
        return "<h1>FiscalIA Pro</h1><p>Arquivo index.html não encontrado.</p>", 404
    return index_path.read_text(encoding="utf-8")


@app.get("/health")
async def health():
    """Endpoint de verificação de saúde da API."""
    return {"status": "🚀 FiscalIA Pro rodando!", "ok": True}


@app.post("/processar-nfes", summary="Processa um lote de arquivos XML de NF-e")
async def processar_nfes(files: List[UploadFile] = File(...)):
    """
    Recebe um lote de arquivos XML de NF-e, processa cada um individualmente,
    salva os dados no banco e, ao final, gera um relatório consolidado em Excel.
    """
    notas_sucesso: List[Dict[str, Any]] = []
    erros_processamento: List[Dict[str, Any]] = []
    total_geral = 0.0
    total_icms = 0.0

    for file in files:
        sucesso, erro = await _processa_arquivo_nfe(file)
        if sucesso:
            notas_sucesso.append(sucesso)
            total_geral += sucesso["total_nf"]
            total_icms += sucesso["icms"]
        if erro:
            erros_processamento.append(erro)

    if not notas_sucesso:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": "Nenhuma nota fiscal pôde ser processada com sucesso.",
                "erros": erros_processamento,
            },
        )

    nome_relatorio = _gera_relatorio_excel(
        notas=notas_sucesso,
        totais={"geral": total_geral, "icms": total_icms},
    )

    return {
        "mensagem": f"Processamento concluído. {len(notas_sucesso)} de {len(files)} notas processadas com sucesso.",
        "notas_processadas": len(notas_sucesso),
        "erros": len(erros_processamento),
        "total_geral": total_geral,
        "total_icms": total_icms,
        "relatorio_excel": nome_relatorio,
        "detalhes_erros": erros_processamento,
    }


@app.get("/download-relatorio", summary="Download de relatório Excel")
async def download_relatorio(nome_arquivo: str):
    """Faz o download de um relatório Excel gerado anteriormente."""
    caminho_arquivo = RELATORIOS_DIR / nome_arquivo
    if not caminho_arquivo.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado: {nome_arquivo}",
        )

    return FileResponse(
        path=caminho_arquivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nome_arquivo,
    )


@app.get("/resumo-ia", summary="Gera resumo analítico com IA")
async def resumo_ia(nome_arquivo: str):
    """Lê um relatório Excel e gera um resumo analítico usando IA."""
    caminho_arquivo = RELATORIOS_DIR / nome_arquivo
    if not caminho_arquivo.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo de relatório não encontrado: {nome_arquivo}",
        )

    df = pd.read_excel(caminho_arquivo)
    texto = gerar_resumo_nf(df)
    return {"resumo": texto}


@app.get("/gerar-relatorio-pdf", summary="Gera e baixa relatório em PDF")
async def gerar_e_baixar_pdf(nome_arquivo: str):
    """Converte um relatório Excel existente para PDF e o retorna para download."""
    caminho_excel = RELATORIOS_DIR / nome_arquivo
    if not caminho_excel.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo Excel base não encontrado: {nome_arquivo}",
        )

    nome_pdf = caminho_excel.with_suffix(".pdf").name
    caminho_pdf = RELATORIOS_DIR / nome_pdf

    try:
        gerar_relatorio_pdf(str(caminho_excel), str(caminho_pdf))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao gerar o relatório PDF: {e}",
        )

    return FileResponse(
        path=caminho_pdf,
        media_type="application/pdf",
        filename=nome_pdf,
    )


# --- Execução Principal ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
