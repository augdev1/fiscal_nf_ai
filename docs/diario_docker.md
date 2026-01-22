FiscalIA Pro – Diário de Desenvolvimento com Docker
Contexto geral
Este documento registra a evolução do uso de Docker no projeto FiscalIA Pro, focado em processamento de NF-e, geração de relatórios Excel/PDF e análise com IA. A ideia é documentar os primeiros passos, erros encontrados, soluções adotadas e o fluxo de comunicação usado para depuração.

Primeiros passos com Docker

Objetivo inicial: containerizar a API FastAPI do FiscalIA Pro, expor a porta 8000 e conseguir testar tudo via Swagger e front-end HTML.

Estrutura base:

main.py com endpoints /processar-nfes, /download-relatorio, /gerar-relatorio-pdf, /resumo-ia e /health.

Dockerfile para build da imagem.

docker-compose.yml com serviço fiscalia expondo 8000:8000.

O foco inicial era apenas “funcionar dentro do container”, ainda sem uma estratégia pensada para persistência de dados e relatórios.

Problemas encontrados no front (ICMS “sumindo”)

Sintoma
O backend calculava e retornava total_geral e total_icms corretamente no JSON.

No front, o card de Total ICMS parecia “zerado” ou simplesmente não aparecia.

Exemplo de resposta da API:

json
{
  "mensagem": "Processamento concluído. 2 de 2 notas processadas com sucesso.",
  "notas_processadas": 2,
  "erros": 0,
  "total_geral": 16605.96,
  "total_icms": 2336.4,
  "relatorio_excel": "relatorio_nfes_1769062035.xlsx",
  "detalhes_erros": []
}
Causa
O HTML/JS (index.html) só exibia cards para:

Sucessos (data.notas_processadas)

Erros (data.erros)

Total Geral (data.total_geral.toFixed(2))

Não existia nenhum card no front utilizando data.total_icms, então o ICMS nunca era exibido mesmo estando correto no backend.
​

Solução
Atualizar a função mostrarResultado(data) no front para incluir o card de Total ICMS dentro da stats-grid:

js
<div class="stat-item">
  <div class="stat-label">Total ICMS</div>
  <div class="stat-value">R$ ${data.total_icms.toFixed(2)}</div>
</div>
Após alterar o HTML/JS, foi necessário:

Salvar o arquivo na pasta correta (assets/index.html).

Rebuildar a imagem Docker e recriar o container.

Fazer hard refresh no navegador (Ctrl+F5).

Resultado: o ICMS passou a aparecer normalmente no front, alinhado com o valor retornado pela API.

Questões relacionadas a Docker e atualização de arquivos

Problema: alterações no HTML não apareciam
Mesmo após editar o index.html, o front não refletia as mudanças.

Motivo: o HTML estava empacotado dentro da imagem Docker; apenas atualizar o arquivo no host não alterava o conteúdo dentro do container.
​

Solução adotada
Parar o container antigo:

docker compose down

Rebuildar a imagem com o código/HTML atualizados:

docker compose up --build -d

Hard refresh no navegador (Ctrl+F5) para evitar cache.

Após essa rotina, o front passou a servir a versão mais recente do index.html e das mudanças de JS.

Organização de armazenamento em disco (relatórios + DB)

Situação inicial
O projeto foi pensado para “apenas em disco”, sem banco em cloud no primeiro momento.

Relatórios Excel/PDF eram gerados com nomes baseados em time.time(), por exemplo relatorio_nfes_1769061799.xlsx.

As recriações de containers causavam confusão sobre onde estavam os arquivos e o DB visto pelo VS Code.

Melhorias implementadas no main.py
Pasta de relatórios e assets:

python
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
RELATORIOS_DIR = BASE_DIR / "relatorios"

RELATORIOS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
Geração de nome padronizada para relatórios:

python
from datetime import datetime

def gerar_nome_relatorio() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"relatorio_nfes_{timestamp}.xlsx"
Função para limpar relatórios antigos:

python
def limpar_relatorios_antigos(dias_para_manter: int = 7) -> None:
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
            pass
Chamada da limpeza no startup da API:

python
@app.on_event("startup")
async def startup_event():
    print("Executando inicialização do banco de dados...")
    init_db()
    limpar_relatorios_antigos(dias_para_manter=7)
    print("Inicialização do banco de dados concluída.")
Uso do gerador de nome ao exportar Excel:

python
def _gera_relatorio_excel(notas: List[Dict], totais: Dict) -> str:
    df = pd.DataFrame(notas)
    df = df.sort_values(by=["nome_emit", "total_nf"], ascending=[True, False])

    df_total = pd.DataFrame([{
        "arquivo": "TOTAL",
        "total_nf": totais["geral"],
        "icms": totais["icms"],
    }])
    df = pd.concat([df, df_total], ignore_index=True)

    nome_arquivo = gerar_nome_relatorio()
    caminho_excel = RELATORIOS_DIR / nome_arquivo

    df.to_excel(caminho_excel, index=False, sheet_name="RelatorioNFes", engine="openpyxl")

    return nome_arquivo
Isso resolve o problema de “duplicatas” conceituais e define uma estratégia clara de limpeza automática com base na idade dos arquivos.

Ajustes no docker-compose
Configuração original (resumida):

text
services:
  fiscalia:
    build: .
    image: fiscalia-pro
    container_name: fiscalia-container
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - db_data:/app

volumes:
  db_data:
Problema: o volume db_data:/app montava a pasta inteira /app, podendo sobrescrever arquivos da aplicação dentro do container.
​

Configuração ajustada para persistência mais limpa:

text
services:
  fiscalia:
    build: .
    image: fiscalia-pro
    container_name: fiscalia-container
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      # Exemplo: se o SQLite ficar em /app/db
      - db_data:/app/db
      # Relatórios Excel/PDF persistentes no host
      - ./relatorios:/app/relatorios

volumes:
  db_data:
Com isso:

O banco fica em um volume nomeado (db_data), persistindo entre recriações de container.

Os relatórios ficam em ./relatorios no host, fáceis de versionar, limpar manualmente e inspecionar.

Estilo de perguntas e envio de erros

Durante o processo, a forma de perguntar e de enviar informações ajudou bastante a depuração rápida. Alguns pontos fortes:

Contexto incremental:

As mensagens vinham em sequência lógica: primeiro o sintoma (“sumiu o ICMS no front”), depois o JSON da API, depois o HTML completo, e só então detalhes de Docker.

Isso evita “tiros no escuro” e facilita localizar se o problema está no backend, front ou Docker.

Exposição direta de trechos de código:

Foi enviado o index.html inteiro da tela, incluindo a função mostrarResultado, permitindo identificar que total_icms não estava sendo usado.

Depois, foi enviado o main.py completo, o que deu segurança para propor mudanças sem quebrar outras partes.

Uso de logs e saídas de terminal:

Foram coladas saídas do docker compose up --build mostrando que a imagem rebuildou e o container foi recriado.

Isso confirmou que o problema não era “esqueceu de rebuildar”, e sim cache de navegador ou HTML antigo.

Validação contínua:

Sempre que uma mudança era sugerida (ex.: adicionar o card de Total ICMS), você testava e respondia se o comportamento mudou.

Isso criou um ciclo rápido de feedback, igual a uma boa sessão de pair programming.
​
​

Em resumo, o padrão de perguntas foi objetivo, incremental e com código/log anexo, o que é exatamente o tipo de comunicação que facilita suporte técnico e debugging em projetos Docker + FastAPI.

Situação atual antes do deploy

No momento deste registro:

Endpoints funcionando e validados pelo front:

/processar-nfes com cálculo correto de total_geral e total_icms.

Download de Excel e geração de PDF ok.

/resumo-ia lendo o Excel e retornando análise.

Front-end exibindo corretamente:

Mensagem de processamento.

Sucessos, Erros, Total Geral e Total ICMS em cards.

Docker preparado para:

Persistir banco e relatórios em disco.

Atualizar imagem/containers via docker compose down + docker compose up --build -d.

