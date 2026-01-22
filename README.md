🧾 FiscalIA Pro: Análise Inteligente de NF-e com IA
Este projeto apresenta uma API robusta desenvolvida em Python com FastAPI para automatizar o processamento e a análise de Notas Fiscais Eletrônicas (NF-e) a partir de arquivos XML. O objetivo é fornecer uma ferramenta eficiente para extração de dados fiscais, geração de relatórios detalhados e resumos inteligentes via inteligência artificial, focando na otimização de processos contábeis e fiscais.
​

🚀 Visão Geral do Projeto
A gestão fiscal, especialmente o processamento de NF-e, pode ser um processo manual e demorado. O FiscalIA Pro surge como uma solução para este problema, permitindo que usuários façam upload de múltiplos arquivos XML de NF-e, que são então processados, seus dados armazenados em um banco de dados local e relatórios consolidados gerados em formatos acessíveis.

O diferencial do projeto está na integração com serviços de Inteligência Artificial para fornecer resumos e insights sobre os dados fiscais, transformando dados brutos em informações acionáveis.

✨ Funcionalidades Principais
📂 Upload de múltiplos XMLs: Recebe e processa um lote de arquivos XML de NF-e simultaneamente via interface web ou diretamente pela API.

🧮 Processamento detalhado de NF-e: Extração de emitente, destinatário, valores totais, itens e impostos (incluindo ICMS) com validações robustas.

💾 Armazenamento em banco de dados: Persistência de dados de NF-e e empresas em SQLite, permitindo rastreabilidade e consultas futuras.

📊 Geração de relatórios em Excel: Consolidação dos dados em relatórios .xlsx organizados.

📑 Geração de relatórios em PDF: Conversão dos relatórios Excel em PDF para compartilhamento e arquivamento.

🤖 Resumos analíticos com IA: Uso de LLMs via API Groq para gerar resumos e análises sobre faturamento, principais emissores e ICMS.

🛠️ Stack Técnica
Backend

🐍 Python 3.11

⚙️ FastAPI (API REST, tipagem e docs automáticas)

🧮 Pandas (manipulação e análise de dados)

🗄️ SQLite (persistência local das NF-e e empresas)

🤖 Groq SDK (integração com modelos de linguagem)

📄 xmltodict (parsing de XML de NF-e)

🚀 uvicorn (servidor ASGI)

📑 reportlab (geração de PDF)

📊 openpyxl (manipulação de Excel)

Infraestrutura / DevOps

🐳 Docker (containerização)

🧩 Docker Compose (orquestração do serviço)

Frontend (interface de exemplo)

🌐 HTML, CSS, JavaScript: interface estática para upload de XML, exibição de totais (incluindo ICMS), download de relatórios e uso da IA.

⚙️ Como Rodar Localmente (sem Docker)
Clonar o repositório

bash
git clone https://github.com/seu-usuario/fiscal_nf_ai.git
cd fiscal_nf_ai
Criar e ativar ambiente virtual

bash
python -m venv fiscalia_env

# Windows
.\fiscalia_env\Scripts\activate

# macOS/Linux
source fiscalia_env/bin/activate
Instalar dependências

bash
pip install -r requirements.txt
Configurar chave da API Groq

Crie um arquivo .env na raiz:

text
GROQ_API_KEY="sua_chave_api_groq_aqui"
(Chave obtida em: https://console.groq.com/keys).[2]

Executar a aplicação

bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Aplicação: http://localhost:8000

Docs (Swagger): http://localhost:8000/docs
​

🐳 Como Rodar com Docker e Docker Compose
Pré-requisitos

Docker e Docker Compose instalados e rodando.
​

Clonar o repositório

bash
git clone https://github.com/seu-usuario/fiscal_nf_ai.git
cd fiscal_nf_ai
Configurar .env com a API Groq

Mesmo conteúdo do modo local (chave na raiz do projeto).

Subir os serviços

bash
docker-compose up --build -d
--build: garante rebuild da imagem após alterações.

-d: roda em background.

Ver logs (opcional)

bash
docker-compose logs -f fiscalia
Parar os serviços

bash
docker-compose down
Aplicação: http://localhost:8000

Docs: http://localhost:8000/docs

🚶 Fluxo de Uso da Aplicação
Acessar a interface

Navegador em http://localhost:8000.

Carregar arquivos XML

Arraste/solte ou selecione arquivos .xml de NF-e.

A lista de arquivos aparecerá na interface.

Gerar relatório

Clique em “Gerar Relatório”.

A API processa os XMLs, salva no banco e gera um Excel consolidado com totais e ICMS.

Baixar relatórios

Baixar Excel: download do .xlsx gerado.

Gerar e Baixar PDF: conversão do Excel para PDF e download imediato.

Análise com IA

Clique em “Análise com IA” para gerar um resumo analítico do relatório (faturamento, emissores, ICMS, etc.).

🏛️ Decisões de Arquitetura e Aprendizados
⚙️ FastAPI como backend principal

Alta performance, suporte assíncrono e documentação automática.
​

💽 Relatórios em disco (MVP)

Relatórios Excel/PDF são salvos em ./relatorios, simplificando o MVP e facilitando testes locais antes de integrar storage em cloud.

📦 Uso de Docker e volumes

Containerização garante ambiente consistente.

Volumes para banco e relatórios mantêm dados entre recriações de container.
​

🧠 Debug do ICMS no frontend

Problema: backend retornava total_icms, mas o front não exibia esse valor.

Solução: ajustar o HTML/JS para incluir um card específico de Total ICMS e garantir formatação com toFixed(2).

📈 Aprendizado contínuo

Implementação de limpeza automática de relatórios antigos.

Melhor entendimento de docker-compose, volumes e fluxo de build/rebuild.

📚 Documentação Extra
📓 Diário de Desenvolvimento e Docker
Detalhes do processo de desenvolvimento, erros, decisões e correções estão documentados em:
👉 docs/diario_docker.md

👨‍💻 Sobre o Desenvolvedor
Olá! Meu nome é Augusto, desenvolvedor do FiscalIA Pro. Este projeto marca uma etapa importante na minha jornada, com menos de um ano de estudos em programação.

Alguns pontos sobre como o projeto foi construído:

Foi desenvolvido em um estilo próximo de pair programming com IA, usando modelos de linguagem como parceiro técnico para discutir arquitetura, depurar erros e refinar o código.
​

Não foi baseado em vídeos ou tutoriais prontos; o foco foi resolver problemas reais e aprender construindo um sistema completo do zero.

Os principais objetivos foram:

Consolidar fundamentos de backend com FastAPI.

Aprender Docker e Docker Compose na prática.

Aplicar boas práticas de organização e documentação.

Estou aberto a oportunidades como desenvolvedor backend júnior/estágio, especialmente em projetos que envolvam APIs, automação e uso de IA.
