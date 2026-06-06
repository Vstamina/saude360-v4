import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
DOC_DIR = DATA_DIR / "documentos"
DB_PATH = DATA_DIR / "saude360.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)


def conectar():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def executar(sql, params=()):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def consultar_df(sql, params=()):
    conn = conectar()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def coluna_existe(conn, tabela, coluna):
    try:
        cols = pd.read_sql_query(f"PRAGMA table_info({tabela})", conn)["name"].tolist()
        return coluna in cols
    except Exception:
        return False


def add_coluna(conn, tabela, definicao):
    coluna = definicao.split()[0]
    if not coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {definicao}")


def init_db():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            sexo TEXT,
            altura_cm REAL,
            objetivo TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS marcos_jornada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_marco TEXT NOT NULL,
            tipo_marco TEXT NOT NULL,
            titulo TEXT NOT NULL,
            especialidade TEXT,
            profissional TEXT,
            local TEXT,
            queixas TEXT,
            motivo TEXT,
            conduta TEXT,
            exames_solicitados TEXT,
            medicamentos_relacionados TEXT,
            proximo_passo TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            dose TEXT,
            frequencia_modelo TEXT NOT NULL,
            intervalo_horas INTEGER,
            horarios_fixos TEXT,
            horario_inicial TEXT,
            data_inicio TEXT NOT NULL,
            data_fim TEXT,
            uso_continuo INTEGER DEFAULT 0,
            orientacao TEXT,
            medico TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            data_status TEXT,
            motivo_status TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicamento_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            data_prevista TEXT NOT NULL,
            horario_previsto TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            horario_tomado TEXT,
            observacao TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS eventos_medicacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            medicamento_id INTEGER,
            data_evento TEXT NOT NULL,
            tipo_evento TEXT NOT NULL,
            motivo TEXT,
            sintomas TEXT,
            gravidade TEXT,
            orientado_por TEXT,
            conduta TEXT,
            substituto TEXT,
            documento_id INTEGER,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS exames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_exame TEXT NOT NULL,
            nome_exame TEXT NOT NULL,
            resultado REAL,
            unidade TEXT,
            referencia_min REAL,
            referencia_max REAL,
            laboratorio TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bioimpedancia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_medicao TEXT NOT NULL,
            peso_kg REAL,
            gordura_percentual REAL,
            massa_magra_kg REAL,
            massa_muscular_kg REAL,
            gordura_visceral REAL,
            cintura_cm REAL,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_atividade TEXT NOT NULL,
            tipo TEXT NOT NULL,
            duracao_min INTEGER,
            calorias REAL,
            passos INTEGER,
            frequencia_media REAL,
            origem TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS documentos_saude (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo_documento TEXT NOT NULL,
            data_documento TEXT NOT NULL,
            titulo TEXT NOT NULL,
            profissional TEXT,
            instituicao TEXT,
            caminho_arquivo TEXT,
            relacionado_a TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros_rapidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_registro TEXT NOT NULL,
            categoria TEXT NOT NULL,
            texto TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sintomas_diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_sintoma TEXT NOT NULL,
            horario TEXT,
            sintoma TEXT NOT NULL,
            intensidade INTEGER,
            duracao TEXT,
            medicamento_id INTEGER,
            gatilho TEXT,
            acao_tomada TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pendencias_cuidado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_criacao TEXT NOT NULL,
            tipo TEXT NOT NULL,
            prioridade TEXT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            origem TEXT,
            medicamento_id INTEGER,
            dose_id INTEGER,
            marco_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberta',
            data_resolucao TEXT,
            resolucao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS importacoes_assistidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_importacao TEXT NOT NULL,
            tipo_documento TEXT,
            titulo TEXT,
            paciente_detectado TEXT,
            validacao_paciente TEXT,
            texto_extraido TEXT,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            documento_id INTEGER,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque_medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            medicamento_id INTEGER NOT NULL,
            data_compra TEXT,
            quantidade_total REAL,
            unidade_estoque TEXT,
            quantidade_por_dose REAL,
            farmacia TEXT,
            valor_pago REAL,
            documento_id INTEGER,
            observacao TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS receitas_medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            medicamento_id INTEGER NOT NULL,
            documento_id INTEGER,
            data_receita TEXT,
            tipo_receita TEXT,
            validade_dias INTEGER,
            precisa_receita INTEGER DEFAULT 0,
            retencao_receita INTEGER DEFAULT 0,
            observacao TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT NOT NULL
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuidados_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_cuidado TEXT NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            prioridade TEXT,
            status TEXT NOT NULL DEFAULT 'Aberto',
            origem TEXT,
            medicamento_id INTEGER,
            exame_nome TEXT,
            marco_id INTEGER,
            pendencia_id INTEGER,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS consentimentos_privacidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data_consentimento TEXT NOT NULL,
            versao_termo TEXT,
            aceita_uso_local INTEGER DEFAULT 0,
            aceita_documentos INTEGER DEFAULT 0,
            aceita_relatorios INTEGER DEFAULT 0,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes_app (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            atualizado_em TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS restauracoes_backup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_solicitacao TEXT NOT NULL,
            caminho_backup TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
    """)

    # Migrações seguras
    add_coluna(conn, "usuarios", "ativo INTEGER DEFAULT 1")
    add_coluna(conn, "usuarios", "atualizado_em TEXT")
    add_coluna(conn, "usuarios", "desativado_em TEXT")

    add_coluna(conn, "documentos_saude", "paciente_detectado TEXT")
    add_coluna(conn, "documentos_saude", "validacao_paciente TEXT")
    add_coluna(conn, "documentos_saude", "excluido INTEGER DEFAULT 0")
    add_coluna(conn, "documentos_saude", "excluido_em TEXT")
    add_coluna(conn, "documentos_saude", "marco_id INTEGER")

    add_coluna(conn, "exames", "marco_id INTEGER")
    add_coluna(conn, "exames", "nome_padronizado TEXT")
    add_coluna(conn, "exames", "categoria_exame TEXT")
    add_coluna(conn, "exames", "observacao_padronizacao TEXT")
    add_coluna(conn, "medicamentos", "marco_id INTEGER")
    add_coluna(conn, "eventos_medicacao", "marco_id INTEGER")
    add_coluna(conn, "sintomas_diario", "marco_id INTEGER")

    add_coluna(conn, "doses", "motivo_nao_tomou TEXT")
    add_coluna(conn, "doses", "acao_sugerida TEXT")

    # Campos de continuidade diretamente no medicamento para resumo rápido
    add_coluna(conn, "medicamentos", "controlar_estoque INTEGER DEFAULT 0")
    add_coluna(conn, "medicamentos", "precisa_receita INTEGER DEFAULT 0")
    add_coluna(conn, "medicamentos", "tipo_receita TEXT")

    conn.commit()
    conn.close()
