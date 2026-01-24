# 🧾 FiscalIA Pro: Análise Inteligente de NF-e com IA
Este projeto apresenta uma API robusta desenvolvida em Python com FastAPI para automatizar o processamento e a análise de Notas Fiscais Eletrônicas (NF-e) a partir de arquivos XML.
​
O objetivo é fornecer uma ferramenta eficiente para extração de dados fiscais, geração de relatórios detalhados e resumos inteligentes via inteligência artificial, focando na otimização de processos contábeis e fiscais.
​

# 🚀 Visão Geral do Projeto
A gestão fiscal, especialmente o processamento de NF-e, pode ser um processo manual e demorado.
​
O FiscalIA Pro surge como uma solução para este problema, permitindo que usuários façam upload de múltiplos arquivos XML de NF-e, que são então processados, seus dados armazenados em um banco de dados local e relatórios consolidados gerados em formatos acessíveis.
​

O diferencial do projeto está na integração com serviços de Inteligência Artificial para fornecer resumos e insights sobre os dados fiscais, transformando dados brutos em informações acionáveis.
​

# ✨ Funcionalidades Principais
📂 Upload de múltiplos XMLs
Capacidade de receber e processar um lote de arquivos XML de NF-e simultaneamente via interface web ou diretamente pela API.
​



## 🧮 Processamento detalhado de NF-e
Extração e validação de informações cruciais das NF-e, incluindo dados do emitente, destinatário, valores totais da nota, itens e cálculos de impostos como o ICMS.
​



## 💾 Armazenamento em banco de dados
Persistência dos dados das NF-e e das empresas emitentes em um banco de dados SQLite, garantindo rastreabilidade e capacidade de consulta futura.
​



## 📊 Geração de relatórios em Excel
Consolidação dos dados processados em um relatório .xlsx organizado, facilitando análise e uso em outras ferramentas.
​



## 📑 Geração de relatórios em PDF
Conversão dos relatórios Excel gerados para PDF, ideal para compartilhamento e arquivamento.
​



## 🤖 Resumos analíticos com IA
Uso de modelos de linguagem (LLMs) via API Groq para gerar resumos concisos e análises inteligentes dos dados fiscais, destacando faturamento, principais emissores e insights sobre ICMS.
​



# 🛠️ Stack Técnica
O projeto é construído sobre uma stack moderna e performática, com foco em escalabilidade e facilidade de manutenção.
​






## 🔙 Backend





## 🐍 Python 3.11 – linguagem principal.


## ⚙️ FastAPI – framework web de alta performance com tipagem e documentação automática (Swagger/OpenAPI).


## 🧮 Pandas – manipulação e análise de dados para relatórios e IA.


## 🗄️ SQLite – banco de dados relacional leve para persistência local de dados das NF-e e empresas.


## 🤖 Groq SDK – integração com LLMs para resumos inteligentes.


## 📄 xmltodict – parsing eficiente de arquivos XML de NF-e.


## 🚀 uvicorn – servidor ASGI de alta performance para FastAPI.


## 📑 reportlab – geração programática de relatórios em PDF.


## 📊 openpyxl – manipulação de arquivos Excel.


​

# 🧩 Infraestrutura / DevOps
## 🐳 Docker – conteinerização da aplicação para garantir ambientes consistentes em desenvolvimento e produção.
​

## 🧱 Docker Compose – orquestração dos serviços Docker (aplicação, volumes etc.).
​

# 🌐 Frontend (interface de exemplo)
## HTML, CSS, JavaScript – interface simples e funcional para:
​

## Upload de XMLs.
​

## Visualização de totais (incluindo ICMS).
​

## Download de relatórios.
​

## Acesso à análise com IA.
​

# ⚙️ Como Rodar Localmente (sem Docker)
Siga estes passos para rodar o projeto localmente, sem Docker.
​

1. Clonar o repositório
```bash
git clone https://github.com/augdev1/fiscal_nf_ai.git
cd fiscal_nf_ai
2. Criar e ativar um ambiente virtual
bash
python -m venv fiscalia_env
```
No Windows:
​

```bash
.\fiscalia_env\Scripts\activate
```
No macOS/Linux:
​

``` bash
source fiscalia_env/bin/activate
```
3. Instalar as dependências
```bash
pip install -r requirements.txt
```
4. Configurar a chave da API Groq
Crie um arquivo .env na raiz do projeto com o conteúdo:
​

```text
GROQ_API_KEY="sua_chave_api_groq_aqui"
A chave pode ser obtida em: https://console.groq.com/keys
```
​

5. Executar a aplicação
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Aplicação: http://localhost:8000
```
​

Documentação (Swagger UI): http://localhost:8000/docs
​

# 🐳 Como Rodar com Docker e Docker Compose
Para uma execução isolada e reproduzível, utilize Docker e Docker Compose.
​

Pré-requisitos
Docker e Docker Compose instalados e em execução.
​

1. Clonar o repositório
```bash
git clone https://github.com/augdev1/fiscal_nf_ai.git
cd fiscal_nf_ai
```
2. Configurar a chave da API Groq
Crie o arquivo .env na raiz do projeto (mesmo conteúdo da execução local).
​

3. Subir os serviços com Docker Compose
```bash
docker-compose up --build -d
```
--build força o rebuild da imagem ao detectar mudanças.
​

-d executa em background.
​

4. Verificar logs (opcional)
```bash
docker-compose logs -f fiscalia
```
5. Parar os serviços
```bash
docker-compose down
Aplicação: http://localhost:8000
```
​

Swagger: http://localhost:8000/docs
​

# 🚶 Como Usar a Aplicação
A interface web (http://localhost:8000) oferece uma forma interativa de usar a API.
​

1. Acessar a interface
Abra o navegador e vá para:
​

```http://localhost:8000
```
​

2. Carregar arquivos XML
Na área “Carregar Arquivos XML”, clique ou arraste/solte arquivos .xml de NF-e.
​

Os arquivos selecionados aparecerão em uma lista na tela.
​

3. Gerar relatório
Clique em “Gerar Relatório”.
​

A aplicação processa os XMLs, armazena os dados e gera um relatório Excel consolidado.
​

4. Baixar relatórios
Baixar Excel: download direto do arquivo .xlsx.
​

Gerar e Baixar PDF: conversão do Excel para PDF e download.
​

5. Análise com IA
Clique em “Análise com IA” para que o modelo de linguagem gere um resumo analítico dos dados (faturamento, principais emissores, ICMS etc.).
​

# 👨‍💻 Sobre o Desenvolvedor
Olá! Meu nome é Augusto, e sou o desenvolvedor por trás do FiscalIA Pro. Este projeto representa um marco significativo na minha jornada de aprendizado em programação, que conta com menos de um ano de estudo formal.
​

O FiscalIA Pro foi concebido e desenvolvido em um estilo de pair programming intensivo com Inteligência Artificial, explorando as capacidades de LLMs como um parceiro de codificação.
​
Este projeto foi uma experiência de aprendizado autodidata, sem o uso de vídeos tutoriais ou cursos pré-estruturados, focando na resolução de problemas reais e na construção de um sistema funcional do zero.
​

Meu principal objetivo com este projeto foi aprofundar conhecimentos em:
​

Arquitetura Backend: desenvolvimento de uma API RESTful completa e bem estruturada.
​

Conteinerização com Docker: uso de Docker e Docker Compose para deploy e gerenciamento de aplicações.
​

Boas práticas de código: aplicação de princípios de código limpo, modularidade e testabilidade.
​

Atualmente, estou buscando vagas de estágio ou júnior na área de desenvolvimento backend, onde possa aplicar e expandir minhas habilidades em um ambiente profissional.
​
Sou apaixonado por resolver problemas complexos e estou sempre buscando aprender e evoluir.
​
​
