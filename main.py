import pandas as pd              # Biblioteca para trabalhar com tabelas e Excel
import time                      # Usada para gerar timestamp único no nome do arquivo
import xmltodict                # Converte XML em dicionário Python
from fastapi import FastAPI, UploadFile, File, HTTPException   # Core do FastAPI
from fastapi.middleware.cors import CORSMiddleware             # Libera acesso do front (CORS)
from fastapi.responses import FileResponse                     # Resposta de arquivo (Excel/PDF)
from fastapi.responses import HTMLResponse                     # Resposta HTML (sua página)
from fastapi.staticfiles import StaticFiles                    # Servir arquivos estáticos (logo, etc.)
from typing import List                                        # Tipagem para lista de UploadFile
from ia_agente import gerar_resumo_nf                          # Função que chama IA p/ resumo
from gerar_relatorio_pdf import gerar_relatorio_pdf            # Função que gera o PDF


def extrair_inf_nfe(data: dict) -> dict:
    """
    Função auxiliar para achar o nó 'infNFe' independente
    da estrutura raiz do XML (nfeProc, NFe, ou variações).
    """
    if "nfeProc" in data:
        # Caso padrão: nfeProc -> NFe -> infNFe
        return data["nfeProc"]["NFe"]["infNFe"]
    if "NFe" in data:
        # Caso em que o XML começa em NFe -> infNFe
        return data["NFe"]["infNFe"]
    # Varre as chaves procurando algo que termine com 'NFe'
    for k in data.keys():
        if k.endswith("NFe"):
            return data[k]["infNFe"]
    # Se nada deu certo, dispara erro
    raise KeyError("Estrutura de NF-e não reconhecida")


# Cria a aplicação FastAPI, com título exibido na documentação /docs
app = FastAPI(title="FiscalIA Pro")

# Configura o CORS para aceitar chamadas de qualquer origem (útil pro front enquanto desenvolve)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Em produção, o ideal é restringir para seu domínio
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mapeia a rota /assets para servir arquivos estáticos da pasta "assets"
# Ex.: /assets/logoai.png
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/health")
async def health():
    """
    Endpoint simples de health-check.
    Serve para ver se a API está no ar.
    """
    return {"status": "🚀 FiscalIA Pro rodando!", "ok": True}


@app.post("/processar-xml")
async def processar_xml(file: UploadFile = File(...)):
    """
    Recebe 1 XML via upload e devolve dados básicos da NF:
    CNPJ, nome do emitente, total da nota e ICMS.
    """
    try:
        # Lê o conteúdo do arquivo enviado
        content = await file.read()
        # Converte o XML em dicionário Python
        data = xmltodict.parse(content)
        print("RAIZ KEYS:", list(data.keys()))
        # Extrai o nó de interesse (infNFe), independente da estrutura
        nfe = extrair_inf_nfe(data)

        # Monta o dicionário de resposta com os campos que o front precisa
        return {
            "cnpj_emit": nfe["emit"]["CNPJ"],
            "nome_emit": nfe["emit"]["xNome"],
            "total_nf": float(nfe["total"]["ICMSTot"]["vNF"]),
            "icms": float(nfe["total"]["ICMSTot"]["vICMS"]),
        }
    except Exception as e:
        # Loga o erro no servidor
        print("ERRO AO PROCESSAR XML:", repr(e))
        # Retorna erro 500 para o cliente com mensagem
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {e}")


@app.post("/processar-nfes")
async def processar_nfes(files: List[UploadFile] = File(...)):
    """
    Recebe VÁRIOS XMLs de uma vez, extrai dados de cada nota,
    soma os totais e gera um relatório Excel.
    """
    resultados = []     # Lista com os dados de cada NF
    total_geral = 0.0   # Soma de vNF de todas as notas
    total_icms = 0.0    # Soma de vICMS de todas as notas

    # Percorre cada arquivo enviado
    for file in files:
        try:
            content = await file.read()        # Lê o conteúdo do XML
            data = xmltodict.parse(content)    # Converte para dicionário
            nfe = extrair_inf_nfe(data)        # Pega infNFe

            # Converte valores para float
            valor_nf = float(nfe["total"]["ICMSTot"]["vNF"])
            valor_icms = float(nfe["total"]["ICMSTot"]["vICMS"])

            # Atualiza os totais gerais
            total_geral += valor_nf
            total_icms += valor_icms

            # Guarda os dados dessa nota na lista de resultados
            resultados.append({
                "arquivo": file.filename,
                "cnpj_emit": nfe["emit"]["CNPJ"],
                "nome_emit": nfe["emit"]["xNome"],
                "total_nf": valor_nf,
                "icms": valor_icms,
            })
        except Exception as e:
            # Loga erro específico por arquivo e retorna 500
            print(f"ERRO NO ARQUIVO {file.filename}:", repr(e))
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar XML {file.filename}: {e}"
            )

    # Cria um DataFrame com todas as notas
    df = pd.DataFrame(resultados)
    # Ordena por nome do emitente e valor da NF (desc)
    df = df.sort_values(by=["nome_emit", "total_nf"], ascending=[True, False])

    # Cria uma linha "TOTAL" para resumir no final da planilha
    linha_total = {
        "arquivo": "TOTAL",
        "cnpj_emit": "",
        "nome_emit": "",
        "total_nf": total_geral,
        "icms": total_icms,
    }

    # Concatena a linha de total ao DataFrame
    df = pd.concat([df, pd.DataFrame([linha_total])], ignore_index=True)
    # Nome do arquivo Excel com timestamp para não sobrescrever
    nome_arquivo = f"relatorio_nfes_{int(time.time())}.xlsx"

    # Abre um ExcelWriter usando engine openpyxl
    with pd.ExcelWriter(nome_arquivo, engine="openpyxl") as writer:
        # Escreve o DataFrame em uma aba chamada "Relatorio"
        df.to_excel(writer, index=False, sheet_name="Relatorio")
        workbook = writer.book
        worksheet = writer.sheets["Relatorio"]
        # Número da última linha (incluindo cabeçalho e linha TOTAL)
        last_row = df.shape[0] + 1

        from openpyxl.styles import Font

        # Formata as colunas de valores (D e E) como número com 2 casas decimais
        for row in range(2, last_row + 1):  # começa em 2 para pular o cabeçalho
            worksheet[f"D{row}"].number_format = "#,##0.00"
            worksheet[f"E{row}"].number_format = "#,##0.00"

        # Deixa toda a linha TOTAL em negrito
        bold_font = Font(b=True)
        for col in range(1, 6):  # colunas A até E
            cell = worksheet.cell(row=last_row, column=col)
            cell.font = bold_font

    # Retorna resumo para o front (que ele usa para montar a tela)
    return {
        "qtd": len(resultados),
        "total_geral": total_geral,
        "total_icms": total_icms,
        "relatorio_excel": nome_arquivo,  # nome do arquivo que será usado para download e IA
        "notas": resultados,
    }


@app.get("/download-relatorio")
async def download_relatorio(nome_arquivo: str):
    """
    Endpoint para fazer download do arquivo Excel gerado em /processar-nfes.
    O front chama isso via link <a href="...">.
    """
    try:
        return FileResponse(
            path=nome_arquivo,  # caminho do arquivo no servidor
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=nome_arquivo,  # nome sugerido para salvar no cliente
            headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
        )
    except Exception as e:
        print("ERRO AO ENVIAR EXCEL:", repr(e))
        # 404 caso o arquivo não exista mais
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {nome_arquivo}")


@app.get("/resumo-ia")
async def resumo_ia(nome_arquivo: str):
    """
    Lê o Excel salvo, manda o DataFrame para a função de IA,
    e retorna o texto gerado para o front.
    """
    df = pd.read_excel(nome_arquivo)
    texto = gerar_resumo_nf(df)       # chamada para seu agente IA
    return {"resumo": texto}          # front mostra em <pre> na tela


@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Endpoint da página principal.
    Retorna um HTML completo (CSS + JS) que funciona como seu frontend.
    """
    return """
    ... (HTML/CSS/JS exatamente como você já tem) ...
    """


@app.get("/gerar-relatorio-pdf")
async def relatorio_pdf(nome_arquivo: str):
    """
    Usa o Excel já gerado para construir um PDF
    e devolve o arquivo para download.
    """
    nome_arquivo = nome_arquivo.strip()              # remove espaços/quebras de linha
    caminho_pdf = gerar_relatorio_pdf(nome_arquivo)  # gera o PDF a partir do Excel
    return FileResponse(
        caminho_pdf,
        media_type="application/pdf",
        filename="relatorio_nfes.pdf",               # nome padrão de download
    )


if __name__ == "__main__":
    # Bloco para rodar o app diretamente com `python main.py`
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)      # expõe em todas interfaces na porta 8000
