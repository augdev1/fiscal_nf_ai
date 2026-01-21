
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime

# Aponta para o arquivo do banco de dados na mesma pasta deste script
DB_PATH = Path(__file__).parent / "fiscal_nf_ai.db"

@contextmanager
def get_connection():
    """
    Context manager para gerenciar conexões com o banco de dados SQLite.
    Garante que a conexão seja fechada e que as transações sejam
    confirmadas (commit) ou revertidas (rollback) automaticamente.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        # Propaga a exceção para que o chamador possa tratá-la
        raise e
    finally:
        if conn:
            conn.close()


def inserir_atualizar_empresa(
    nome: str,
    cnpj: str,
    inscricao_estadual: Optional[str] = None,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
) -> int:
    """
    Verifica se uma empresa com o CNPJ fornecido já existe.
    Se existir, atualiza seus dados. Caso contrário, insere um novo registro.
    Retorna o ID da empresa.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verificar se a empresa já existe
        cursor.execute("SELECT id FROM empresas WHERE cnpj = ?", (cnpj,))
        empresa_existente = cursor.fetchone()
        
        now_iso = datetime.utcnow().isoformat()
        
        if empresa_existente:
            # 2. Se existir, atualizar
            empresa_id = empresa_existente["id"]
            cursor.execute(
                """
                UPDATE empresas
                SET nome = ?, inscricao_estadual = ?, email = ?, telefone = ?, updated_at = ?
                WHERE id = ?
                """,
                (nome, inscricao_estadual, email, telefone, now_iso, empresa_id),
            )
        else:
            # 3. Se não existir, inserir
            cursor.execute(
                """
                INSERT INTO empresas (nome, cnpj, inscricao_estadual, email, telefone, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (nome, cnpj, inscricao_estadual, email, telefone, now_iso, now_iso),
            )
            empresa_id = cursor.lastrowid
            
        return empresa_id

def inserir_nota_completa(
    nota_data: Dict[str, Any],
    itens_data: List[Dict[str, Any]],
) -> int:
    """
    Insere uma nota fiscal e seus itens em uma única transação.
    Retorna o ID da nota inserida.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Inserir a nota fiscal
        now_iso = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO notas (
                empresa_id, numero, serie, chave_acesso, data_emissao, valor_total,
                cfop_principal, destinatario_nome, destinatario_cnpj, uf_destinatario, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nota_data["empresa_id"],
                nota_data["numero"],
                nota_data["serie"],
                nota_data["chave_acesso"],
                nota_data["data_emissao"],
                nota_data["valor_total"],
                nota_data["cfop_principal"],
                nota_data["destinatario_nome"],
                nota_data["destinatario_cnpj"],
                nota_data.get("uf_destinatario"), # Usar .get() para campo opcional
                now_iso,
            ),
        )
        nota_id = cursor.lastrowid
        
        # 2. Inserir os itens da nota
        for item in itens_data:
            cursor.execute(
                """
                INSERT INTO itens_nota (
                    nota_id, codigo_produto, descricao, ncm, cfop,
                    quantidade, valor_unitario, valor_total, unidade
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nota_id,
                    item["codigo_produto"],
                    item["descricao"],
                    item["ncm"],
                    item["cfop"],
                    item["quantidade"],
                    item["valor_unitario"],
                    item["valor_total"],
                    item.get("unidade"), # Usar .get() para campo opcional
                ),
            )
            
        return nota_id

def registrar_log(
    tipo_processo: str,
    status: str,
    mensagem: Optional[str] = None,
    detalhes_erro: Optional[str] = None,
    empresa_id: Optional[int] = None,
    iniciado_em: Optional[datetime] = None,
    finalizado_em: Optional[datetime] = None,
) -> int:
    """
    Registra um log de execução no banco de dados.
    Calcula a duração do processo e retorna o ID do log.
    """
    now = datetime.utcnow()
    iniciado_em = iniciado_em or now
    finalizado_em = finalizado_em or now
    
    duracao = finalizado_em - iniciado_em
    duracao_segundos = duracao.total_seconds()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO logs_execucao (
                empresa_id, tipo_processo, status, mensagem, detalhes_erro,
                iniciado_em, finalizado_em, duracao_segundos
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                empresa_id,
                tipo_processo,
                status,
                mensagem,
                detalhes_erro,
                iniciado_em.isoformat(),
                finalizado_em.isoformat(),
                duracao_segundos,
            ),
        )
        log_id = cursor.lastrowid
        return log_id

# --- Funções de Consulta Analítica (Opcional) ---

def listar_notas_por_periodo(
    data_inicio: str,
    data_fim: str,
    cnpj_empresa: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Lista notas fiscais emitidas em um determinado período, com filtro opcional por CNPJ da empresa.
    Retorna uma lista de dicionários, onde cada um representa uma nota com dados da empresa.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT
                n.id AS nota_id,
                n.numero,
                n.serie,
                n.chave_acesso,
                n.data_emissao,
                n.valor_total,
                n.destinatario_nome,
                n.destinatario_cnpj,
                e.nome AS empresa_nome,
                e.cnpj AS empresa_cnpj
            FROM notas n
            JOIN empresas e ON n.empresa_id = e.id
            WHERE n.data_emissao BETWEEN ? AND ?
        """
        params = [data_inicio, data_fim]
        
        if cnpj_empresa:
            query += " AND e.cnpj = ?"
            params.append(cnpj_empresa)
            
        query += " ORDER BY n.data_emissao DESC;"
        
        cursor.execute(query, tuple(params))
        
        # Converte as linhas (sqlite3.Row) para dicionários
        return [dict(row) for row in cursor.fetchall()]

def resumo_valor_total_por_empresa(
    data_inicio: str,
    data_fim: str
) -> List[Dict[str, Any]]:
    """
    Agrupa as notas por empresa e calcula o valor total e a quantidade de notas para cada uma
    dentro de um período específico.
    Retorna uma lista de dicionários, cada um com o resumo de uma empresa.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT
                e.nome AS empresa_nome,
                e.cnpj AS empresa_cnpj,
                COUNT(n.id) AS quantidade_notas,
                SUM(n.valor_total) AS valor_total_notas
            FROM notas n
            JOIN empresas e ON n.empresa_id = e.id
            WHERE n.data_emissao BETWEEN ? AND ?
            GROUP BY e.id, e.nome, e.cnpj
            ORDER BY valor_total_notas DESC;
        """
        params = (data_inicio, data_fim)
        
        cursor.execute(query, params)
        
        # Converte as linhas (sqlite3.Row) para dicionários
        return [dict(row) for row in cursor.fetchall()]

