# 🧾 FiscalIA Pro – Diário de Desenvolvimento com Docker

## 📌 Contexto geral

Este documento registra a evolução do uso de **Docker** no projeto **FiscalIA Pro**, focado em processamento de NF-e, geração de relatórios Excel/PDF e análise com IA.  
A ideia é documentar os primeiros passos, erros encontrados, soluções adotadas e o fluxo de comunicação usado para depuração.

---

## 1️⃣ Primeiros passos com Docker

### Objetivo inicial

- Containerizar a API **FastAPI** do FiscalIA Pro.  
- Expor a porta `8000`.  
- Conseguir testar tudo via **Swagger** e front-end HTML.

### Estrutura base do projeto

- `main.py` com endpoints:
  - `/processar-nfes`
  - `/download-relatorio`
  - `/gerar-relatorio-pdf`
  - `/resumo-ia`
  - `/health`
- `Dockerfile` para build da imagem.  
- `docker-compose.yml` com serviço `fiscalia` expondo `8000:8000`.

O foco inicial era apenas “funcionar dentro do container”, ainda sem uma estratégia pensada para persistência de dados e relatórios.

---

## 2️⃣ Problemas no front: ICMS “sumindo”

### Sintoma

- O backend calculava e retornava `total_geral` e `total_icms` corretamente no JSON.  
- No front, o card de **Total ICMS** parecia zerado ou simplesmente não aparecia.

### Exemplo de resposta da API

```json
{
  "mensagem": "Processamento concluído. 2 de 2 notas processadas com sucesso.",
  "notas_processadas": 2,
  "erros": 0,
  "total_geral": 16605.96,
  "total_icms": 2336.4,
  "relatorio_excel": "relatorio_nfes_1769062035.xlsx",
  "detalhes_erros": []
}
Causa identificada
No index.html (HTML/JS do front), a stats-grid exibia apenas:

Sucessos → data.notas_processadas

Erros → data.erros

Total Geral → data.total_geral.toFixed(2)

Não havia nenhum card utilizando data.total_icms, então o ICMS não aparecia na tela, mesmo estando correto no backend.

Solução no frontend
Adicionar um card específico de Total ICMS dentro da stats-grid:

xml
<div class="stat-item">
  <div class="stat-label">Total ICMS</div>
  <div class="stat-value">R$ ${data.total_icms.toFixed(2)}</div>
</div>
Após alterar o HTML/JS, foi necessário:

Salvar o arquivo na pasta correta: assets/index.html.

Rebuildar a imagem Docker e recriar o container.

Fazer hard refresh no navegador (Ctrl+F5) para limpar cache.

✅ Resultado: o ICMS passou a aparecer normalmente no front, alinhado com o valor retornado pela API.

3️⃣ Docker e atualização de arquivos estáticos
Problema: alterações no HTML não apareciam
Mesmo depois de editar o index.html, a interface continuava mostrando a versão antiga.

Motivo
O index.html estava empacotado dentro da imagem Docker.
Somente alterar o arquivo no host não atualiza automaticamente o conteúdo dentro do container.

Solução adotada
Passo a passo para refletir mudanças no front:

bash
# 1. Parar o container antigo
docker compose down

# 2. Rebuildar a imagem e subir novamente
docker compose up --build -d

# 3. No navegador
# Hard refresh: Ctrl + F5
Após seguir essa rotina, o front passou a servir a versão mais recente do index.html e do JavaScript.

4️⃣ Organização de armazenamento em disco (relatórios + DB)
Situação inicial
O projeto foi pensado para funcionar apenas em disco (MVP), sem banco em cloud.

Relatórios Excel/PDF eram gerados com nomes baseados em time.time(), por exemplo:

text
relatorio_nfes_1769061799.xlsx
Recriações de containers geravam confusão:

Dúvidas sobre onde estavam os arquivos de relatório.

Dificuldade em localizar o banco (.db) no VS Code após rebuilds.

Melhorias implementadas no main.py
4.1. Pastas de relatórios e assets
python
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
RELATORIOS_DIR = BASE_DIR / "relatorios"

RELATORIOS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
4.2. Geração de nome padronizado para relatórios
python
from datetime import datetime

def gerar_nome_relatorio() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"relatorio_nfes_{timestamp}.xlsx"
4.3. Função para limpar relatórios antigos
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
4.4. Chamada da limpeza no startup da API
python
@app.on_event("startup")
async def startup_event():
    print("Executando inicialização do banco de dados...")
    init_db()
    limpar_relatorios_antigos(dias_para_manter=7)
    print("Inicialização do banco de dados concluída.")
4.5. Uso do gerador de nome ao exportar Excel
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

    df.to_excel(
        caminho_excel,
        index=False,
        sheet_name="RelatorioNFes",
        engine="openpyxl"
    )

    return nome_arquivo
🔎 Isso resolve o problema de possíveis “duplicatas” conceituais e define uma estratégia clara de limpeza automática baseada na idade dos arquivos.

5️⃣ Ajustes no docker-compose e persistência
Configuração original (resumida)
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
Problema
O volume db_data:/app montava a pasta inteira /app, podendo sobrescrever arquivos da aplicação dentro do container.

Configuração ajustada para persistência mais limpa
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

Os relatórios ficam em ./relatorios no host:

Fáceis de versionar (se quiser).

Fáceis de limpar manualmente.

Simples de inspecionar diretamente pelo sistema de arquivos.

6️⃣ Estilo de perguntas e envio de erros
Durante o processo, a forma de comunicação ajudou bastante na depuração rápida. Alguns pontos fortes:

Contexto incremental
As mensagens vinham em sequência lógica:

Primeiro o sintoma: “sumiu o ICMS no front”.

Depois o JSON da API.

Depois o HTML completo (index.html).

Só então detalhes de Docker e logs.

➡️ Isso evita “tiros no escuro” e ajuda a localizar se o problema está no backend, frontend ou infra (Docker).

Exposição direta de código
Foi enviado o index.html inteiro, com a função mostrarResultado, o que permitiu identificar rapidamente que total_icms não estava sendo exibido.

Em seguida, foi enviado o main.py completo, permitindo propor mudanças sem arriscar quebrar outras partes.

Uso de logs e saídas de terminal
Foram coladas saídas do:

bash
docker compose up --build
mostrando:

Build da imagem.

Criação do container.

➡️ Isso confirmou que o problema não era “esqueceu de rebuildar”, e sim cache de navegador / front antigo.

Validação contínua
A cada mudança sugerida (por exemplo, adicionar o card de Total ICMS), o comportamento era testado e o resultado retornado (“está arrumado”, “agora o próximo passo é o deploy”).

Isso criou um ciclo rápido de feedback, parecido com uma sessão de pair programming.

🔚 Em resumo, o padrão de perguntas foi objetivo, incremental e sempre com código/log anexo, o que é ideal para suporte técnico e debugging em projetos com FastAPI + Docker + frontend estático.

7️⃣ Situação atual antes do deploy
No momento deste registro:

Endpoints funcionando (validados pelo front)
/processar-nfes com cálculo correto de total_geral e total_icms.

Download de Excel e geração de PDF funcionando.

/resumo-ia lendo o Excel e retornando análise com IA.

Front-end
Exibe corretamente:

Mensagem de processamento.

Sucessos e erros.

Total Geral.

Total ICMS em cards separados.

Docker
Preparado para:

Persistir banco de dados e relatórios em disco.

Atualizar imagem e containers via:

bash
docker compose down
docker compose up --build -d
A partir daqui, o próximo passo natural é configurar e executar o deploy em um ambiente de cloud (ex.: Railway, Render ou VPS), usando a imagem Docker já estável.
