from pathlib import Path
from datetime import datetime
import zipfile

from core.database import DATA_DIR, DOC_DIR, DB_PATH, consultar_df


BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _bytes_para_mb(valor):
    try:
        return round(float(valor) / (1024 * 1024), 2)
    except Exception:
        return 0


def calcular_tamanho_pasta(pasta):
    pasta = Path(pasta)
    total = 0
    arquivos = 0

    if not pasta.exists():
        return {"bytes": 0, "mb": 0, "arquivos": 0}

    for p in pasta.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
                arquivos += 1
            except Exception:
                pass

    return {"bytes": total, "mb": _bytes_para_mb(total), "arquivos": arquivos}


def status_armazenamento():
    tamanho_data = calcular_tamanho_pasta(DATA_DIR)
    tamanho_docs = calcular_tamanho_pasta(DOC_DIR)
    tamanho_backups = calcular_tamanho_pasta(BACKUP_DIR)

    db_bytes = 0
    if DB_PATH.exists():
        try:
            db_bytes = DB_PATH.stat().st_size
        except Exception:
            db_bytes = 0

    docs_banco = consultar_df(
        """
        SELECT COUNT(*) AS total
        FROM documentos_saude
        WHERE COALESCE(excluido, 0) = 0
        """
    )

    docs_excluidos = consultar_df(
        """
        SELECT COUNT(*) AS total
        FROM documentos_saude
        WHERE COALESCE(excluido, 0) = 1
        """
    )

    arquivos_fisicos = consultar_df(
        """
        SELECT id, usuario_id, caminho_arquivo
        FROM documentos_saude
        WHERE caminho_arquivo IS NOT NULL
          AND TRIM(caminho_arquivo) <> ''
        """
    )

    encontrados = 0
    ausentes = 0

    if not arquivos_fisicos.empty:
        for _, r in arquivos_fisicos.iterrows():
            caminho = r.get("caminho_arquivo")
            if caminho and Path(caminho).exists():
                encontrados += 1
            else:
                ausentes += 1

    return {
        "data_mb": tamanho_data["mb"],
        "data_arquivos": tamanho_data["arquivos"],
        "documentos_mb": tamanho_docs["mb"],
        "documentos_arquivos": tamanho_docs["arquivos"],
        "backups_mb": tamanho_backups["mb"],
        "backups_arquivos": tamanho_backups["arquivos"],
        "db_mb": _bytes_para_mb(db_bytes),
        "db_existe": DB_PATH.exists(),
        "documentos_ativos_banco": int(docs_banco.iloc[0]["total"]) if not docs_banco.empty else 0,
        "documentos_excluidos_banco": int(docs_excluidos.iloc[0]["total"]) if not docs_excluidos.empty else 0,
        "arquivos_fisicos_encontrados": encontrados,
        "arquivos_fisicos_ausentes": ausentes,
    }


def gerar_manifesto_backup():
    status = status_armazenamento()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    linhas = []
    linhas.append("SAUDE 360 - MANIFESTO DO BACKUP")
    linhas.append("=" * 36)
    linhas.append("")
    linhas.append(f"Gerado em: {agora}")
    linhas.append("")
    linhas.append("Conteudo esperado:")
    linhas.append("- Banco de dados SQLite: data/saude360.db")
    linhas.append("- Documentos salvos: data/documentos")
    linhas.append("- Este manifesto")
    linhas.append("")
    linhas.append("Status no momento do backup:")
    for chave, valor in status.items():
        linhas.append(f"- {chave}: {valor}")
    linhas.append("")
    linhas.append("Observacao:")
    linhas.append("Este backup guarda os dados locais do app. Para restauracao manual, preserve a pasta data e substitua com cuidado.")
    linhas.append("")

    return "\n".join(linhas)


def criar_backup_zip():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_saude360_{timestamp}.zip"

    manifesto = gerar_manifesto_backup()

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as z:
        if DB_PATH.exists():
            z.write(DB_PATH, "data/saude360.db")

        if DOC_DIR.exists():
            for p in DOC_DIR.rglob("*"):
                if p.is_file():
                    z.write(p, Path("data/documentos") / p.relative_to(DOC_DIR))

        z.writestr("MANIFESTO_BACKUP.txt", manifesto)

    return backup_path


def ler_backup_bytes(caminho):
    caminho = Path(caminho)
    return caminho.read_bytes()


def listar_backups_locais():
    if not BACKUP_DIR.exists():
        return []

    backups = []
    for p in sorted(BACKUP_DIR.glob("backup_saude360_*.zip"), reverse=True):
        try:
            backups.append({
                "nome": p.name,
                "caminho": str(p),
                "tamanho_mb": _bytes_para_mb(p.stat().st_size),
                "modificado": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            })
        except Exception:
            pass

    return backups


def excluir_backup_local(caminho):
    p = Path(caminho)
    if not p.exists():
        return False, "Backup não encontrado."

    if p.parent != BACKUP_DIR:
        return False, "Por segurança, só é possível excluir backups da pasta data/backups."

    p.unlink()
    return True, "Backup local excluído."
