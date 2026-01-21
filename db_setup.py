import sqlite3
from pathlib import Path
from datetime import datetime

# Caminho do arquivo de banco (ficará na mesma pasta deste script)
DB_PATH = Path(__file__).parent / "fiscal_nf_ai.db"


def create_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # Tabela de empresas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT NOT NULL UNIQUE,
            inscricao_estadual TEXT,
            email TEXT,
            telefone TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        """
    )

    # Tabela de notas (cabeçalho da NF-e)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            numero TEXT NOT NULL,
            serie TEXT,
            chave_acesso TEXT NOT NULL UNIQUE,
            data_emissao TEXT NOT NULL,
            valor_total REAL NOT NULL,
            cfop_principal TEXT,
            destinatario_nome TEXT,
            destinatario_cnpj TEXT,
            uf_destinatario TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        );
        """
    )

    # Tabela de itens da nota
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS itens_nota (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER NOT NULL,
            codigo_produto TEXT,
            descricao TEXT NOT NULL,
            ncm TEXT,
            cfop TEXT,
            quantidade REAL NOT NULL,
            valor_unitario REAL NOT NULL,
            valor_total REAL NOT NULL,
            unidade TEXT,
            FOREIGN KEY (nota_id) REFERENCES notas (id)
        );
        """
    )

    # Tabela de logs de execução (para rastrear rodadas do robô/IA)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs_execucao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            tipo_processo TEXT NOT NULL, -- ex: 'processamento_nfe', 'geracao_relatorio'
            status TEXT NOT NULL,        -- ex: 'sucesso', 'erro'
            mensagem TEXT,
            detalhes_erro TEXT,
            iniciado_em TEXT NOT NULL,
            finalizado_em TEXT,
            duracao_segundos REAL,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        );
        """
    )

    # Índices úteis
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_empresas_cnpj
        ON empresas (cnpj);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notas_chave_acesso
        ON notas (chave_acesso);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notas_data_emissao
        ON notas (data_emissao);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_logs_tipo_status
        ON logs_execucao (tipo_processo, status);
        """
    )

    conn.commit()


def init_db() -> None:
    """
    Cria o arquivo de banco e as tabelas, caso ainda não existam.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)

    print(f"Banco SQLite inicializado em: {DB_PATH}")


if __name__ == "__main__":
    init_db()
# Fim do arquivo db_setup.py