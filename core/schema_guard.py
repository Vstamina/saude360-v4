from core.database import conectar


def _colunas(conn, tabela):
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({tabela})")
        return [r[1] for r in cur.fetchall()]
    except Exception:
        return []


def _tabela_existe(conn, tabela):
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
        return cur.fetchone() is not None
    except Exception:
        return False


def _add_coluna(conn, tabela, definicao):
    coluna = definicao.split()[0]
    if coluna not in _colunas(conn, tabela):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {definicao}")


def garantir_schema_completo():
    """
    Correção global defensiva.
    Garante tabelas/colunas usadas pelos MVPs recentes, mesmo quando o banco antigo
    não recebeu alguma migração.
    """
    conn = conectar()
    cur = conn.cursor()

    # Usuários
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
    _add_coluna(conn, "usuarios", "ativo INTEGER DEFAULT 1")
    _add_coluna(conn, "usuarios", "atualizado_em TEXT")
    _add_coluna(conn, "usuarios", "desativado_em TEXT")

    # Marcos
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

    # Medicamentos
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
    _add_coluna(conn, "medicamentos", "marco_id INTEGER")
    _add_coluna(conn, "medicamentos", "controlar_estoque INTEGER DEFAULT 0")
    _add_coluna(conn, "medicamentos", "precisa_receita INTEGER DEFAULT 0")
    _add_coluna(conn, "medicamentos", "tipo_receita TEXT")

    # Doses
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
    _add_coluna(conn, "doses", "motivo_nao_tomou TEXT")
    _add_coluna(conn, "doses", "acao_sugerida TEXT")

    # Eventos
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
    _add_coluna(conn, "eventos_medicacao", "marco_id INTEGER")

    # Exames
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
    _add_coluna(conn, "exames", "marco_id INTEGER")
    _add_coluna(conn, "exames", "nome_padronizado TEXT")
    _add_coluna(conn, "exames", "categoria_exame TEXT")
    _add_coluna(conn, "exames", "observacao_padronizacao TEXT")

    # Bioimpedância
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

    # Atividades
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

    # Documentos
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
    _add_coluna(conn, "documentos_saude", "paciente_detectado TEXT")
    _add_coluna(conn, "documentos_saude", "validacao_paciente TEXT")
    _add_coluna(conn, "documentos_saude", "excluido INTEGER DEFAULT 0")
    _add_coluna(conn, "documentos_saude", "excluido_em TEXT")
    _add_coluna(conn, "documentos_saude", "marco_id INTEGER")

    # Registros rápidos
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

    # Sintomas
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
    _add_coluna(conn, "sintomas_diario", "marco_id INTEGER")

    # Pendências
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
    _add_coluna(conn, "pendencias_cuidado", "prioridade TEXT")
    _add_coluna(conn, "pendencias_cuidado", "descricao TEXT")
    _add_coluna(conn, "pendencias_cuidado", "origem TEXT")
    _add_coluna(conn, "pendencias_cuidado", "medicamento_id INTEGER")
    _add_coluna(conn, "pendencias_cuidado", "dose_id INTEGER")
    _add_coluna(conn, "pendencias_cuidado", "marco_id INTEGER")
    _add_coluna(conn, "pendencias_cuidado", "data_resolucao TEXT")
    _add_coluna(conn, "pendencias_cuidado", "resolucao TEXT")
    _add_coluna(conn, "pendencias_cuidado", "criado_em TEXT")

    # Importações assistidas
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
    _add_coluna(conn, "importacoes_assistidas", "tipo_documento TEXT")
    _add_coluna(conn, "importacoes_assistidas", "titulo TEXT")
    _add_coluna(conn, "importacoes_assistidas", "paciente_detectado TEXT")
    _add_coluna(conn, "importacoes_assistidas", "validacao_paciente TEXT")
    _add_coluna(conn, "importacoes_assistidas", "texto_extraido TEXT")
    _add_coluna(conn, "importacoes_assistidas", "status TEXT DEFAULT 'Rascunho'")
    _add_coluna(conn, "importacoes_assistidas", "documento_id INTEGER")
    _add_coluna(conn, "importacoes_assistidas", "criado_em TEXT")

    # Estoque
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

    # Receitas
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

    # Agenda
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

    # Privacidade
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

    # Aplicativo local
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

    conn.commit()
    conn.close()
