import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

def gerar_relatorio_pdf(caminho_excel_input: str, caminho_pdf_output: str) -> None:
    """
    Gera um relatório PDF a partir de um arquivo Excel de NF-es.

    Args:
        caminho_excel_input: O caminho completo para o arquivo Excel de entrada.
        caminho_pdf_output: O caminho completo onde o arquivo PDF gerado será salvo.
    """
    try:
        # Lê o Excel com os dados das notas. A coluna com nome do emissor é 'nome_emit'.
        df = pd.read_excel(caminho_excel_input)

        # Cria o canvas (a "página" do PDF)
        c = canvas.Canvas(caminho_pdf_output, pagesize=A4)
        width, height = A4

        # --- Desenho do Cabeçalho ---
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Relatório de NF-e - FiscalIA Pro")

        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Fonte: {Path(caminho_excel_input).name}")
        c.line(50, height - 75, width - 50, height - 75)

        # --- Desenho da Tabela de Dados ---
        y = height - 100
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Nome do Emitente")
        c.drawString(300, y, "Total NF (R$)")
        c.drawString(420, y, "ICMS (R$)")
        y -= 18
        c.setFont("Helvetica", 10)

        # Itera sobre as linhas do DataFrame para popular a tabela no PDF
        # O .head(40) limita a 40 registros por página para evitar overflow
        for _, row in df.head(40).iterrows():
            # Pula a linha de 'TOTAL' que pode estar no Excel
            if row.get("arquivo") == "TOTAL":
                continue
            
            # Extrai os dados da linha, com tratamento para valores ausentes
            nome_emit = str(row.get("nome_emit", "N/A"))[:40] # Limita o tamanho
            total_nf = f'{row.get("total_nf", 0.0):.2f}'
            icms = f'{row.get("icms", 0.0):.2f}'

            c.drawString(50, y, nome_emit)
            c.drawString(300, y, total_nf)
            c.drawString(420, y, icms)
            y -= 14

            # Quebra de página se o conteúdo chegar perto do rodapé
            if y < 50:
                c.showPage() # Finaliza a página atual
                y = height - 50 # Reinicia a altura para a nova página
                # (Opcional) Poderia redesenhar o cabeçalho aqui em um app mais complexo
                c.setFont("Helvetica", 10)

        # --- Finalização do PDF ---
        c.showPage() # Garante que a última página seja salva
        c.save() # Salva o arquivo PDF no disco
    
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        # Propaga a exceção para que o endpoint da API possa capturá-la
        raise e

