# FiscalIA Pro — Guia de Funcionamento do Sistema

Este documento explica, de forma objetiva, como o sistema funciona no dia a dia, do upload dos XMLs até a geração de relatórios e resumo com IA.

## 1) Objetivo do sistema

O FiscalIA Pro automatiza o processamento de NF-e (arquivos XML), com foco em:

- Extração de dados fiscais relevantes;
- Armazenamento estruturado em banco local (SQLite);
- Geração de relatório consolidado em Excel;
- Conversão do relatório para PDF;
- Resumo analítico com IA usando Groq.

---

## 2) Fluxo funcional (ponta a ponta)

1. Usuário envia um ou mais arquivos XML pela interface web.
2. A API processa cada XML individualmente.
3. Dados essenciais da NF-e são extraídos (emitente, destinatário, totais, ICMS, itens).
4. Dados são persistidos no banco SQLite.
5. Ao final do lote, é gerado um relatório Excel consolidado.
6. Opcionalmente, o Excel é convertido para PDF.
7. Opcionalmente, o Excel é lido para gerar um resumo textual com IA.

---

## 3) Componentes principais

### Backend (FastAPI)

- Arquivo principal: `main.py`
- Responsável por rotas HTTP, processamento dos XMLs e orquestração de relatórios.

### Persistência (SQLite)

- Criação de schema: `db_setup.py`
- Operações de banco: `db_repository.py`
- Arquivo de banco: `fiscal_nf_ai.db`

### IA (resumo analítico)

- Módulo: `ia_agente.py`
- Usa variável de ambiente `GROQ_API_KEY` para autenticar na API Groq.

### Relatório PDF

- Módulo: `gerar_relatorio_pdf.py`
- Converte relatório Excel em PDF com layout simples de leitura.

### Frontend

- Página única: `assets/index.html`
- Faz upload, chama API, mostra métricas e botões de download/análise.

---

## 4) Estrutura de dados que o parser usa

O parser busca `infNFe` em 3 formatos aceitos:

1. `nfeProc > NFe > infNFe` (mais comum)
2. `NFe > infNFe`
3. `infNFe` direto

Campos críticos esperados no processamento:

- `@Id` (chave de acesso)
- `ide` com `nNF`, `serie` e `dhEmi` ou `dEmi`
- `emit` com `CNPJ` e `xNome`
- `total > ICMSTot` com `vNF` (e opcional `vICMS`)
- `det` (item único ou lista de itens)

Se esses campos essenciais não existirem, o XML entra na lista de erros do lote.

---

## 5) Endpoints e finalidade

### `GET /`

Retorna a interface web.

### `GET /health`

Verificação de saúde da API.

### `POST /processar-nfes`

Recebe múltiplos arquivos XML (`files`) e:

- processa cada nota;
- salva em banco;
- gera relatório Excel consolidado;
- retorna totais e lista de erros do lote.

### `GET /download-relatorio?nome_arquivo=...`

Baixa um relatório Excel já gerado.

### `GET /gerar-relatorio-pdf?nome_arquivo=...`

Converte um Excel existente para PDF e retorna o arquivo.

### `GET /resumo-ia?nome_arquivo=...`

Lê o Excel e gera resumo textual via LLM (Groq).

---

## 6) Como os resultados são consolidados

Durante o lote de XMLs:

- cada sucesso incrementa `total_geral` e `total_icms`;
- cada falha é registrada em `detalhes_erros`;
- no fim, um arquivo `relatorio_nfes_YYYYMMDDHHMMSS.xlsx` é criado.

O Excel inclui as notas processadas e uma linha final de `TOTAL`.

---

## 7) Tratamento de erros

### Erros por arquivo (lote parcial)

Exemplo: XML malformado, campos faltando, chave duplicada.

Resultado: o lote continua para os demais arquivos, e os erros retornam em `detalhes_erros`.

### Erro total do lote

Se nenhuma nota for processada com sucesso:

- status HTTP `400`;
- mensagem indicando que nenhuma nota foi processada.

### Erros de IA

Se a chave Groq estiver inválida/ausente ou houver problema de conexão, o endpoint `/resumo-ia` pode retornar erro (normalmente `500`).

---

## 8) Uso diário recomendado

1. Subir API.
2. Acessar interface web.
3. Enviar lote de XMLs.
4. Validar resumo de sucesso/erros.
5. Baixar Excel.
6. (Opcional) Gerar PDF.
7. (Opcional) Gerar resumo com IA.

Esse fluxo reduz trabalho manual de consolidação fiscal e acelera conferência operacional.

---

## 9) Limitações atuais (importantes)

- Banco local SQLite (bom para uso local, não ideal para alta concorrência).
- Parser focado em campos essenciais (não cobre todos os grupos possíveis da NF-e).
- IA depende de internet e da validade da `GROQ_API_KEY`.
- Não há autenticação de usuário na API nesta versão.

---

## 10) Checklist rápido de validação

- API responde em `/health`.
- Upload de XML válido processa com sucesso.
- Excel é gerado e baixado.
- PDF é gerado a partir do Excel.
- Resumo IA retorna texto quando chave/configuração está correta.

---

## 11) Resumo executivo

O FiscalIA Pro é um pipeline local de processamento fiscal: **ingere XML de NF-e, estrutura dados, consolida relatórios e adiciona uma camada de análise por IA**. Na prática, ele elimina etapas manuais repetitivas e melhora a visibilidade rápida dos principais números fiscais.
