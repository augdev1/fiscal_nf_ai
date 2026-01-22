# FiscalIA Pro: Análise Inteligente de NF-e com IA

Este projeto apresenta uma API robusta desenvolvida em Python com FastAPI para automatizar o processamento e a análise de Notas Fiscais Eletrônicas (NF-e) a partir de arquivos XML. O objetivo é fornecer uma ferramenta eficiente para extração de dados fiscais, geração de relatórios detalhados e resumos inteligentes via inteligência artificial, focando na otimização de processos contábeis e fiscais.

## 🚀 Visão Geral do Projeto

A gestão fiscal, especialmente o processamento de NF-e, pode ser um processo manual e demorado. O FiscalIA Pro surge como uma solução para este problema, permitindo que usuários façam upload de múltiplos arquivos XML de NF-e, que são então processados, seus dados armazenados em um banco de dados local e relatórios consolidados gerados em formatos acessíveis.

O diferencial do projeto reside na integração com serviços de Inteligência Artificial para fornecer resumos e insights sobre os dados fiscais, transformando dados brutos em informações acionáveis.

## ✨ Funcionalidades Principais

*   **Upload de Múltiplos XMLs:** Capacidade de receber e processar um lote de arquivos XML de NF-e simultaneamente via uma interface web intuitiva ou diretamente pela API.
*   **Processamento Detalhado de NF-e:** Extração e validação de informações cruciais das NF-e, incluindo dados do emitente, destinatário, valores totais da nota, itens e cálculos de impostos como o ICMS.
*   **Armazenamento em Banco de Dados:** Persistência dos dados das NF-e e das empresas emitentes em um banco de dados SQLite, garantindo a rastreabilidade e a capacidade de consulta futura.
*   **Geração de Relatórios em Excel:** Consolidação dos dados processados em um relatório `.xlsx` organizado, facilitando a análise e o uso por outras ferramentas.
*   **Geração de Relatórios em PDF:** Conversão dos relatórios Excel gerados em um formato PDF, ideal para compartilhamento e arquivamento.
*   **Resumos Analíticos com IA:** Utilização de modelos de Linguagem Grandes (LLMs) via API Groq para gerar resumos concisos e análises inteligentes dos dados dos relatórios fiscais, destacando faturamento, principais emissores e insights sobre ICMS.

## 🛠️ Stack Técnica

O projeto é construído sobre uma stack moderna e performática, com foco em escalabilidade e facilidade de manutenção:

*   **Backend:**
    *   **Python 3.11:** Linguagem de programação principal.
    *   **FastAPI:** Framework web de alta performance para construção da API, com tipagem e documentação automática (Swagger/OpenAPI).
    *   **Pandas:** Biblioteca essencial para manipulação e análise de dados, utilizada na preparação para relatórios e resumos de IA.
    *   **SQLite:** Banco de dados relacional leve, ideal para a persistência local de dados das NF-e e empresas.
    *   **Groq SDK:** Integração com modelos de LLM para funcionalidade de resumo inteligente.
    *   **xmltodict:** Para parsing eficiente de arquivos XML de NF-e.
    *   **uvicorn:** Servidor ASGI de alta performance para o FastAPI.
    *   **reportlab:** Para geração programática de relatórios em PDF.
    *   **openpyxl:** Para manipulação de arquivos Excel.
*   **Infraestrutura/DevOps:**
    *   **Docker:** Conteinerização da aplicação para garantir ambientes de desenvolvimento e produção consistentes.
    *   **Docker Compose:** Orquestração de múltiplos serviços Docker (neste caso, a própria aplicação).
*   **Frontend (Interface de Exemplo):**
    *   **HTML, CSS, JavaScript:** Uma interface simples e funcional para demonstração da API, permitindo o upload de XMLs e a visualização dos resultados.

## ⚙️ Como Rodar Localmente (sem Docker)

Siga os passos abaixo para configurar e rodar o projeto em sua máquina local sem o uso de Docker.

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/fiscal_nf_ai.git
    cd fiscal_nf_ai
    ```
2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv fiscalia_env
    # No Windows:
    .\fiscalia_env\Scripts\activate
    # No macOS/Linux:
    source fiscalia_env/bin/activate
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure a chave da API Groq:**
    Crie um arquivo `.env` na raiz do projeto com sua chave da API Groq:
    ```
    GROQ_API_KEY="sua_chave_api_groq_aqui"
    ```
    Você pode obter uma chave em [Groq Console](https://console.groq.com/keys).
5.  **Execute a aplicação:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    (O `--reload` é opcional, útil para desenvolvimento).

A aplicação estará acessível em `http://localhost:8000`. A documentação interativa da API (Swagger UI) pode ser encontrada em `http://localhost:8000/docs`.

## 🐳 Como Rodar com Docker e Docker Compose

Para uma execução mais isolada e consistente, utilize Docker e Docker Compose:

1.  **Certifique-se de ter Docker e Docker Compose instalados e em execução.**
2.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/fiscal_nf_ai.git
    cd fiscal_nf_ai
    ```
3.  **Configure a chave da API Groq:**
    Crie um arquivo `.env` na raiz do projeto com sua chave da API Groq (conforme o passo 4 da seção anterior).
4.  **Inicie os serviços com Docker Compose:**
    ```bash
    docker-compose up --build -d
    ```
    O `--build` garante que a imagem seja construída (ou reconstruída, se houver mudanças no Dockerfile) e o `-d` executa em segundo plano.
5.  **Verifique os logs (opcional):**
    ```bash
    docker-compose logs -f fiscalia
    ```
6.  **Para parar os serviços:**
    ```bash
    docker-compose down
    ```

A aplicação estará acessível em `http://localhost:8000`. A documentação interativa da API (Swagger UI) pode ser encontrada em `http://localhost:8000/docs`.

## 🚶 Como Usar a Aplicação

A interface web em `http://localhost:8000` oferece uma forma interativa de usar a API:

1.  **Acesse a Interface:** Abra seu navegador e navegue para `http://localhost:8000`.
2.  **Carregar Arquivos XML:** Na área de "Carregar Arquivos XML", clique ou arraste e solte um ou mais arquivos `.xml` de NF-e. Os arquivos selecionados aparecerão em uma lista.
3.  **Gerar Relatório:** Clique no botão "Gerar Relatório". A aplicação processará os XMLs, armazenará os dados e gerará um arquivo Excel consolidado.
4.  **Baixar Relatórios:** Após o processamento, serão exibidas opções para:
    *   **Baixar Excel:** Faça o download direto do relatório `.xlsx` gerado.
    *   **Gerar e Baixar PDF:** Converta o relatório Excel para PDF e faça o download.
5.  **Análise com IA:** Clique em "Análise com IA" para que o modelo de linguagem gere um resumo analítico dos dados do relatório.

## 🏛️ Decisões de Arquitetura e Aprendizados

Durante o desenvolvimento do FiscalIA Pro, diversas decisões arquiteturais foram tomadas visando otimização, manutenibilidade e aprendizado:

*   **Escolha do FastAPI:**
    *   **Performance:** FastAPI é conhecido por sua alta performance, crucial para uma API que pode lidar com processamento de múltiplos arquivos.
    *   **Assincronicidade:** Suporte nativo a `async/await` permite que operações de I/O (leitura de arquivos, interação com API externa como Groq) sejam não bloqueantes, melhorando a responsividade.
    *   **Documentação Automática:** A geração automática de documentação OpenAPI (Swagger UI e ReDoc) economiza tempo e facilita o consumo da API.
    *   **Validação de Dados:** Pydantic integrado oferece validação robusta de requisições e respostas.
*   **Armazenamento de Relatórios em Disco (MVP):**
    *   Para a versão inicial (MVP), optou-se por salvar os relatórios Excel e PDF diretamente em um diretório local (`./relatorios`). Esta decisão simplifica a arquitetura, evitando a complexidade de integração com serviços de armazenamento em nuvem (S3, Google Cloud Storage) e reduzindo custos operacionais para uma prova de conceito. Para uma versão de produção, a integração com armazenamento em nuvem seria o próximo passo lógico para escalabilidade e durabilidade.
*   **Aprendizados com Docker e Volumes:**
    *   **Isolamento de Ambiente:** Docker proporcionou um ambiente de execução consistente, eliminando problemas de "funciona na minha máquina".
    *   **Persistência de Dados:** O uso de volumes Docker (`db_data` para o SQLite e o mount do diretório `./relatorios`) foi fundamental para garantir que os dados do banco e os relatórios gerados persistissem entre as reinicializações dos contêineres, simulando um ambiente de produção onde os dados são valiosos.
    *   **Entendimento de `docker-compose`:** A orquestração com `docker-compose` facilitou a definição e execução do serviço da aplicação com suas dependências e configurações de rede.
*   **Depuração do Problema de ICMS no Frontend:**
    *   Um desafio notado durante o desenvolvimento da interface foi a correta exibição dos valores de ICMS e total. Inicialmente, o frontend poderia apresentar imprecisões devido a problemas de arredondamento de ponto flutuante em JavaScript ou formatação inconsistente com os valores retornados pelo backend. A depuração envolveu a verificação das payloads da API, a aplicação de `toFixed(2)` e formatação de moeda no JavaScript para garantir que os valores fossem exibidos com duas casas decimais, conforme esperado para dados financeiros, alinhando a representação visual com a precisão dos dados do backend.

## 📚 Documentação Extra

- 📓 [Diário de Desenvolvimento e Docker](docs/diario_docker.md)

O FiscalIA Pro foi concebido e desenvolvido em um estilo de **pair programming intensivo com Inteligência Artificial**, explorando as capacidades de LLMs como um parceiro de codificação. Este projeto foi uma experiência de aprendizado autodidata, **sem o uso de vídeos tutoriais ou cursos pré-estruturados**, focando na resolução de problemas reais e na construção de um sistema funcional do zero.

Meu principal objetivo com este projeto foi aprofundar meus conhecimentos em:
*   **Arquitetura Backend:** Desenvolver uma API RESTful completa e bem estruturada.
*   **Contenierização com Docker:** Dominar o uso de Docker e Docker Compose para deploy e gerenciamento de aplicações.
*   **Boas Práticas de Código:** Aplicar princípios de código limpo, modularidade e testabilidade.
