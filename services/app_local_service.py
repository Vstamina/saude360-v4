import zipfile
from datetime import date, datetime
from pathlib import Path

from core.database import DATA_DIR, DOC_DIR, DB_PATH, consultar_df, executar, conectar
from core.helpers import agora


BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
RESTORE_DIR = DATA_DIR / "restore_inbox"
APP_CONFIG_VERSION = "MVP-8.0.1-local"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
RESTORE_DIR.mkdir(parents=True, exist_ok=True)


def garantir_tabelas_app_local():
    """
    Correção defensiva:
    garante que as tabelas do modo aplicativo local existam,
    mesmo se a migração do core/database.py não tiver rodado corretamente.
    """
    conn = conectar()
    try:
        cur = conn.cursor()

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
    finally:
        conn.close()


def get_config(chave, padrao=None):
    garantir_tabelas_app_local()

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT valor FROM configuracoes_app WHERE chave = ?", (chave,))
        row = cur.fetchone()
        if row is None:
            return padrao
        return row[0]
    except Exception:
        return padrao
    finally:
        conn.close()


def set_config(chave, valor):
    garantir_tabelas_app_local()

    executar(
        """
        INSERT INTO configuracoes_app (chave, valor, atualizado_em)
        VALUES (?, ?, ?)
        ON CONFLICT(chave) DO UPDATE SET
            valor = excluded.valor,
            atualizado_em = excluded.atualizado_em
        """,
        (chave, str(valor), agora()),
    )


def get_config_bool(chave, padrao=False):
    valor = get_config(chave, "1" if padrao else "0")
    return str(valor).strip() in ["1", "true", "True", "sim", "Sim"]


def get_config_int(chave, padrao=0):
    try:
        return int(get_config(chave, padrao))
    except Exception:
        return padrao


def primeira_execucao_pendente():
    return get_config("onboarding_concluido", "0") != "1"


def concluir_onboarding():
    set_config("onboarding_concluido", "1")
    set_config("versao_onboarding", APP_CONFIG_VERSION)


def status_app_local():
    garantir_tabelas_app_local()

    tamanho_db = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    total_docs = 0
    total_docs_bytes = 0

    if DOC_DIR.exists():
        for p in DOC_DIR.rglob("*"):
            if p.is_file():
                total_docs += 1
                try:
                    total_docs_bytes += p.stat().st_size
                except Exception:
                    pass

    total_backups = len(list(BACKUP_DIR.glob("backup_saude360_*.zip"))) if BACKUP_DIR.exists() else 0

    try:
        usuarios = consultar_df("SELECT COUNT(*) AS total FROM usuarios")
        total_usuarios = int(usuarios.iloc[0]["total"]) if not usuarios.empty else 0
    except Exception:
        total_usuarios = 0

    return {
        "db_path": str(DB_PATH),
        "data_dir": str(DATA_DIR),
        "doc_dir": str(DOC_DIR),
        "backup_dir": str(BACKUP_DIR),
        "export_dir": str(EXPORT_DIR),
        "restore_dir": str(RESTORE_DIR),
        "db_mb": round(tamanho_db / (1024 * 1024), 2),
        "docs_total": total_docs,
        "docs_mb": round(total_docs_bytes / (1024 * 1024), 2),
        "backups_total": total_backups,
        "usuarios_total": total_usuarios,
        "onboarding_concluido": get_config("onboarding_concluido", "0") == "1",
        "backup_automatico": get_config_bool("backup_automatico", True),
        "backup_intervalo_dias": get_config_int("backup_intervalo_dias", 3),
        "backup_manter_ultimos": get_config_int("backup_manter_ultimos", 10),
        "ultimo_backup_auto": get_config("ultimo_backup_auto", ""),
        "versao_app_local": APP_CONFIG_VERSION,
    }


def _manifesto_backup(tipo="Manual"):
    status = status_app_local()
    linhas = []
    linhas.append("SAÚDE 360 - BACKUP LOCAL")
    linhas.append("=" * 36)
    linhas.append(f"Tipo: {tipo}")
    linhas.append(f"Gerado em: {agora()}")
    linhas.append(f"Versão: {APP_CONFIG_VERSION}")
    linhas.append("")
    linhas.append("Conteúdo:")
    linhas.append("- data/saude360.db")
    linhas.append("- data/documentos, quando existir")
    linhas.append("- manifesto do backup")
    linhas.append("")
    linhas.append("Status no momento do backup:")
    for k, v in status.items():
        linhas.append(f"- {k}: {v}")
    linhas.append("")
    linhas.append("Aviso:")
    linhas.append("Este arquivo pode conter dados pessoais e de saúde. Guarde em local seguro.")
    return "\n".join(linhas)


def criar_backup_local(tipo="Manual"):
    garantir_tabelas_app_local()

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"backup_saude360_{tipo.lower()}_{timestamp}.zip".replace(" ", "_")
    destino = BACKUP_DIR / nome

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        if DB_PATH.exists():
            z.write(DB_PATH, "data/saude360.db")

        if DOC_DIR.exists():
            for p in DOC_DIR.rglob("*"):
                if p.is_file():
                    z.write(p, Path("data/documentos") / p.relative_to(DOC_DIR))

        z.writestr("MANIFESTO_BACKUP.txt", _manifesto_backup(tipo=tipo))

    if tipo.lower() == "automatico":
        set_config("ultimo_backup_auto", date.today().isoformat())

    return destino


def listar_backups():
    backups = []
    if not BACKUP_DIR.exists():
        return backups

    for p in sorted(BACKUP_DIR.glob("backup_saude360_*.zip"), reverse=True):
        try:
            backups.append({
                "nome": p.name,
                "caminho": str(p),
                "tamanho_mb": round(p.stat().st_size / (1024 * 1024), 2),
                "modificado": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            })
        except Exception:
            pass
    return backups


def limpar_backups_antigos(manter=10):
    backups = sorted(BACKUP_DIR.glob("backup_saude360_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    removidos = 0
    for p in backups[int(manter):]:
        try:
            p.unlink()
            removidos += 1
        except Exception:
            pass
    return removidos


def backup_automatico_se_necessario():
    garantir_tabelas_app_local()

    if not get_config_bool("backup_automatico", True):
        return {"feito": False, "motivo": "Backup automático desativado."}

    intervalo = get_config_int("backup_intervalo_dias", 3)
    ultimo = get_config("ultimo_backup_auto", "")

    precisa = False
    if not ultimo:
        precisa = True
    else:
        try:
            ultimo_dt = datetime.strptime(ultimo, "%Y-%m-%d").date()
            precisa = (date.today() - ultimo_dt).days >= intervalo
        except Exception:
            precisa = True

    if not precisa:
        return {"feito": False, "motivo": "Backup automático ainda não é necessário."}

    caminho = criar_backup_local(tipo="Automatico")
    removidos = limpar_backups_antigos(get_config_int("backup_manter_ultimos", 10))

    return {
        "feito": True,
        "caminho": str(caminho),
        "removidos": removidos,
    }


def salvar_config_backup(backup_automatico=True, intervalo_dias=3, manter_ultimos=10):
    set_config("backup_automatico", "1" if backup_automatico else "0")
    set_config("backup_intervalo_dias", int(intervalo_dias))
    set_config("backup_manter_ultimos", int(manter_ultimos))


def ler_bytes(caminho):
    return Path(caminho).read_bytes()


def preparar_restauracao(uploaded_file):
    garantir_tabelas_app_local()

    RESTORE_DIR.mkdir(parents=True, exist_ok=True)
    nome_seguro = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    destino = RESTORE_DIR / nome_seguro

    with open(destino, "wb") as f:
        f.write(uploaded_file.getvalue())

    rid = executar(
        """
        INSERT INTO restauracoes_backup (
            data_solicitacao, caminho_backup, status, observacao, criado_em
        )
        VALUES (?, ?, 'Pendente', ?, ?)
        """,
        (
            date.today().isoformat(),
            str(destino),
            "Backup enviado para restauração manual segura.",
            agora(),
        ),
    )

    return rid, destino


def validar_backup_zip(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        return False, "Arquivo não encontrado."

    try:
        with zipfile.ZipFile(caminho, "r") as z:
            nomes = z.namelist()
            if "data/saude360.db" not in nomes:
                return False, "O ZIP não contém data/saude360.db."
            return True, f"Backup parece válido. Itens no ZIP: {len(nomes)}."
    except Exception as e:
        return False, f"Não foi possível abrir o ZIP: {e}"


def instrucoes_restauracao_manual(caminho_backup):
    return f"""RESTAURAÇÃO MANUAL SEGURA - SAÚDE 360

O backup foi salvo em:
{caminho_backup}

Para restaurar com segurança:

1. Feche o Saúde 360.
2. Faça uma cópia da pasta atual:
   {DATA_DIR.resolve()}

3. Extraia o ZIP do backup em uma pasta temporária.
4. Substitua:
   data/saude360.db
   data/documentos

5. Abra o Saúde 360 novamente.

Por segurança, esta versão não substitui o banco enquanto o app está rodando.
Isso evita corromper dados durante o uso.
"""


def gerar_script_windows_inicio():
    return """@echo off
title Saude 360
cd /d "%~dp0"
python -m streamlit run app.py
pause
"""


def gerar_script_windows_backup():
    return """@echo off
title Saude 360 - Backup rapido
cd /d "%~dp0"
python -c "from services.app_local_service import criar_backup_local; print(criar_backup_local('Manual'))"
pause
"""


def criar_arquivos_atalho_local(base_dir="."):
    base = Path(base_dir)
    iniciar = base / "abrir_saude360.bat"
    backup = base / "backup_rapido_saude360.bat"

    iniciar.write_text(gerar_script_windows_inicio(), encoding="utf-8")
    backup.write_text(gerar_script_windows_backup(), encoding="utf-8")

    return iniciar, backup


def checklist_app_local():
    garantir_tabelas_app_local()

    return [
        {
            "item": "Dados locais",
            "status": "OK" if DATA_DIR.exists() else "Atenção",
            "descricao": f"Pasta de dados: {DATA_DIR}",
        },
        {
            "item": "Banco SQLite",
            "status": "OK" if DB_PATH.exists() else "Atenção",
            "descricao": f"Banco: {DB_PATH}",
        },
        {
            "item": "Pasta de documentos",
            "status": "OK" if DOC_DIR.exists() else "Atenção",
            "descricao": f"Documentos: {DOC_DIR}",
        },
        {
            "item": "Backup automático",
            "status": "OK" if get_config_bool("backup_automatico", True) else "Atenção",
            "descricao": "Ativo" if get_config_bool("backup_automatico", True) else "Desativado",
        },
        {
            "item": "Onboarding",
            "status": "OK" if not primeira_execucao_pendente() else "Atenção",
            "descricao": "Concluído" if not primeira_execucao_pendente() else "Pendente",
        },
    ]
