import json
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

from core.database import DB_PATH, DATA_DIR, DOC_DIR, conectar, consultar_df, executar
from core.helpers import agora


TABELAS_COM_USUARIO = [
    "usuarios",
    "marcos_jornada",
    "medicamentos",
    "doses",
    "eventos_medicacao",
    "exames",
    "bioimpedancia",
    "atividades",
    "documentos_saude",
    "registros_rapidos",
    "sintomas_diario",
    "pendencias_cuidado",
    "importacoes_assistidas",
    "estoque_medicamentos",
    "receitas_medicamentos",
    "cuidados_agendados",
    "consentimentos_privacidade",
]


def tabela_existe(tabela):
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def coluna_existe(tabela, coluna):
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({tabela})")
        cols = [r[1] for r in cur.fetchall()]
        return coluna in cols
    finally:
        conn.close()


def listar_tabelas_usuario_disponiveis():
    tabelas = []
    for t in TABELAS_COM_USUARIO:
        if tabela_existe(t) and coluna_existe(t, "usuario_id"):
            tabelas.append(t)
    return tabelas


def contagem_dados_usuario(usuario_id):
    linhas = []
    for tabela in listar_tabelas_usuario_disponiveis():
        try:
            df = consultar_df(f"SELECT COUNT(*) AS total FROM {tabela} WHERE usuario_id = ?", (usuario_id,))
            total = int(df.iloc[0]["total"]) if not df.empty else 0
            linhas.append({"tabela": tabela, "registros": total})
        except Exception as e:
            linhas.append({"tabela": tabela, "registros": 0, "erro": str(e)})
    return linhas


def caminhos_documentos_usuario(usuario_id):
    if not tabela_existe("documentos_saude"):
        return []

    df = consultar_df(
        """
        SELECT id, titulo, caminho_arquivo
        FROM documentos_saude
        WHERE usuario_id = ?
          AND caminho_arquivo IS NOT NULL
          AND TRIM(caminho_arquivo) <> ''
        """,
        (usuario_id,),
    )

    caminhos = []
    if df.empty:
        return caminhos

    for _, r in df.iterrows():
        caminho = str(r.get("caminho_arquivo") or "").strip()
        p = Path(caminho)
        caminhos.append({
            "id": int(r["id"]),
            "titulo": r.get("titulo") or "",
            "caminho": caminho,
            "existe": p.exists(),
            "tamanho_bytes": p.stat().st_size if p.exists() and p.is_file() else 0,
        })

    return caminhos


def status_privacidade_usuario(usuario_id):
    contagens = contagem_dados_usuario(usuario_id)
    docs = caminhos_documentos_usuario(usuario_id)

    total_registros = sum(int(x.get("registros") or 0) for x in contagens)
    docs_fisicos = sum(1 for d in docs if d.get("existe"))
    tamanho_docs = sum(int(d.get("tamanho_bytes") or 0) for d in docs)

    consent = consultar_df(
        """
        SELECT *
        FROM consentimentos_privacidade
        WHERE usuario_id = ?
        ORDER BY data_consentimento DESC, id DESC
        LIMIT 1
        """,
        (usuario_id,),
    ) if tabela_existe("consentimentos_privacidade") else consultar_df("SELECT 1 WHERE 0")

    return {
        "total_registros": total_registros,
        "tabelas": len(contagens),
        "documentos_registrados": len(docs),
        "documentos_fisicos": docs_fisicos,
        "tamanho_docs_mb": round(tamanho_docs / (1024 * 1024), 2),
        "db_path": str(DB_PATH),
        "data_dir": str(DATA_DIR),
        "doc_dir": str(DOC_DIR),
        "consentimento": consent.to_dict(orient="records")[0] if not consent.empty else None,
        "contagens": contagens,
        "documentos": docs,
    }


def salvar_consentimento(usuario_id, aceita_uso_local, aceita_documentos, aceita_relatorios, observacao=""):
    return executar(
        """
        INSERT INTO consentimentos_privacidade (
            usuario_id, data_consentimento, versao_termo, aceita_uso_local,
            aceita_documentos, aceita_relatorios, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            date.today().isoformat(),
            "MVP-7.9-local",
            1 if aceita_uso_local else 0,
            1 if aceita_documentos else 0,
            1 if aceita_relatorios else 0,
            observacao,
            agora(),
        ),
    )


def _df_to_records_safe(df):
    if df is None or df.empty:
        return []
    df = df.copy()
    for c in df.columns:
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df.to_dict(orient="records")


def exportar_dados_usuario_json(usuario_id):
    export = {
        "metadados": {
            "app": "Saude 360",
            "versao_exportacao": "MVP-7.9",
            "gerado_em": agora(),
            "usuario_id": usuario_id,
            "observacao": "Exportação local em JSON. Uso informativo.",
        },
        "tabelas": {},
        "documentos_fisicos": caminhos_documentos_usuario(usuario_id),
    }

    for tabela in listar_tabelas_usuario_disponiveis():
        try:
            df = consultar_df(f"SELECT * FROM {tabela} WHERE usuario_id = ?", (usuario_id,))
            export["tabelas"][tabela] = _df_to_records_safe(df)
        except Exception as e:
            export["tabelas"][tabela] = {"erro": str(e)}

    return json.dumps(export, ensure_ascii=False, indent=2)


def criar_zip_exportacao_usuario(usuario_id):
    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = agora().replace(":", "").replace("-", "").replace(" ", "_")
    zip_path = export_dir / f"export_usuario_{usuario_id}_{timestamp}.zip"

    json_text = exportar_dados_usuario_json(usuario_id)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("dados_usuario.json", json_text)

        for doc in caminhos_documentos_usuario(usuario_id):
            caminho = Path(doc["caminho"])
            if caminho.exists() and caminho.is_file():
                arcname = Path("documentos") / f"{doc['id']}_{caminho.name}"
                z.write(caminho, arcname)

        z.writestr(
            "LEIA-ME.txt",
            "Exportação local do Saúde 360.\n"
            "Contém dados do usuário em JSON e, quando encontrados, documentos físicos vinculados.\n"
            "Uso informativo. Proteja este arquivo, pois pode conter dados pessoais e de saúde.\n"
        )

    return zip_path


def ler_bytes(caminho):
    return Path(caminho).read_bytes()


def desativar_usuario(usuario_id):
    if not tabela_existe("usuarios"):
        return False, "Tabela de usuários não encontrada."

    executar(
        """
        UPDATE usuarios
        SET ativo = 0,
            desativado_em = ?,
            atualizado_em = ?
        WHERE id = ?
        """,
        (agora(), agora(), usuario_id),
    )
    return True, "Cadastro desativado. Os dados permanecem preservados."


def reativar_usuario(usuario_id):
    if not tabela_existe("usuarios"):
        return False, "Tabela de usuários não encontrada."

    executar(
        """
        UPDATE usuarios
        SET ativo = 1,
            atualizado_em = ?
        WHERE id = ?
        """,
        (agora(), usuario_id),
    )
    return True, "Cadastro reativado."


def excluir_dados_usuario(usuario_id, excluir_arquivos=False):
    """
    Exclusão definitiva dos dados do usuário nas tabelas com usuario_id.
    Deve ser chamada apenas depois de confirmação forte no front.
    """
    docs = caminhos_documentos_usuario(usuario_id)
    erros_arquivos = []

    conn = conectar()
    try:
        cur = conn.cursor()

        # Exclui primeiro tabelas filhas; usuarios por último.
        tabelas = [t for t in listar_tabelas_usuario_disponiveis() if t != "usuarios"]
        for tabela in tabelas:
            cur.execute(f"DELETE FROM {tabela} WHERE usuario_id = ?", (usuario_id,))

        if tabela_existe("usuarios"):
            cur.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

        conn.commit()
    finally:
        conn.close()

    removidos = 0
    if excluir_arquivos:
        for d in docs:
            caminho = Path(d["caminho"])
            try:
                if caminho.exists() and caminho.is_file():
                    caminho.unlink()
                    removidos += 1
            except Exception as e:
                erros_arquivos.append({"caminho": str(caminho), "erro": str(e)})

    return {
        "ok": True,
        "usuario_id": usuario_id,
        "arquivos_removidos": removidos,
        "erros_arquivos": erros_arquivos,
    }


def gerar_texto_termo_local():
    return """TERMO LOCAL DE USO E PRIVACIDADE - SAÚDE 360

1. O Saúde 360 organiza dados pessoais de saúde de forma local no computador do usuário.
2. Os dados ficam no banco SQLite local e em arquivos salvos na pasta data/documentos.
3. O sistema não realiza diagnóstico, não prescreve tratamento e não substitui avaliação médica.
4. O usuário é responsável por conferir os dados importados, especialmente documentos lidos por OCR ou receitas manuscritas.
5. O sistema permite exportar os dados e documentos vinculados.
6. O sistema permite desativar ou excluir definitivamente um cadastro.
7. A exclusão definitiva pode apagar registros e, se autorizado, arquivos físicos vinculados.
8. Arquivos exportados podem conter dados sensíveis. Proteja-os adequadamente.
"""
