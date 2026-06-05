from datetime import datetime
from pathlib import Path
import re
import unicodedata

from core.database import DOC_DIR, consultar_df, executar
from core.helpers import agora


def _normalizar_nome(txt):
    txt = str(txt or "").strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def detectar_nome_paciente_texto(texto):
    texto = str(texto or "")
    if not texto.strip():
        return ""

    padroes = [
        r"paciente\s*[:\-]\s*([A-Za-zÀ-ÿ'´`^~çÇ ]{3,90})",
        r"nome\s*[:\-]\s*([A-Za-zÀ-ÿ'´`^~çÇ ]{3,90})",
        r"cliente\s*[:\-]\s*([A-Za-zÀ-ÿ'´`^~çÇ ]{3,90})",
        r"benefici[aá]rio\s*[:\-]\s*([A-Za-zÀ-ÿ'´`^~çÇ ]{3,90})",
    ]

    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE)
        if m:
            nome = m.group(1).strip()
            nome = re.split(
                r"\n|data|idade|sexo|cpf|rg|nascimento|conv[eê]nio|pedido|material|coleta",
                nome,
                flags=re.IGNORECASE,
            )[0].strip(" :-")
            if len(nome) >= 3:
                return nome[:90]

    return ""


def validar_paciente_documento(usuario_id, texto):
    usuario = consultar_df("SELECT id, nome FROM usuarios WHERE id = ?", (usuario_id,))
    if usuario.empty:
        return "", "Usuario ativo nao encontrado."

    nome_ativo = usuario.iloc[0]["nome"]
    detectado = detectar_nome_paciente_texto(texto)

    if not detectado:
        return "", "Nao foi possivel identificar nome do paciente no documento."

    n_ativo = _normalizar_nome(nome_ativo)
    n_detectado = _normalizar_nome(detectado)

    tokens_ativo = [t for t in n_ativo.split() if len(t) >= 3]
    tokens_detectado = [t for t in n_detectado.split() if len(t) >= 3]
    comuns = set(tokens_ativo).intersection(tokens_detectado)

    if n_detectado in n_ativo or n_ativo in n_detectado or len(comuns) >= 2:
        return detectado, "OK: nome do documento parece compativel com o usuario ativo."

    return detectado, f"ALERTA: o documento parece estar em nome de '{detectado}', mas o usuario ativo e '{nome_ativo}'."


def salvar_documento(usuario_id, tipo, data_doc, titulo, profissional, instituicao,
                     arquivo, relacionado_a, observacao, paciente_detectado=None,
                     validacao_paciente=None, marco_id=None):
    caminho = None

    if arquivo is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_seguro = arquivo.name.replace(" ", "_")
        destino = DOC_DIR / f"{usuario_id}_{timestamp}_{nome_seguro}"
        with open(destino, "wb") as f:
            f.write(arquivo.getbuffer())
        caminho = str(destino)

    return executar(
        """
        INSERT INTO documentos_saude (
            usuario_id, tipo_documento, data_documento, titulo, profissional,
            instituicao, caminho_arquivo, relacionado_a, observacao,
            paciente_detectado, validacao_paciente, marco_id, excluido, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            usuario_id,
            tipo,
            data_doc.isoformat(),
            titulo,
            profissional,
            instituicao,
            caminho,
            relacionado_a,
            observacao,
            paciente_detectado or "",
            validacao_paciente or "",
            marco_id,
            agora(),
        ),
    )


def listar_documentos(usuario_id, limite=None, incluir_excluidos=False):
    sql = """
        SELECT d.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM documentos_saude d
        LEFT JOIN marcos_jornada m ON m.id = d.marco_id
        WHERE d.usuario_id = ?
    """
    if not incluir_excluidos:
        sql += " AND COALESCE(d.excluido, 0) = 0 "

    sql += " ORDER BY d.data_documento DESC, d.id DESC "

    if limite:
        sql += f" LIMIT {int(limite)}"

    return consultar_df(sql, (usuario_id,))


def obter_documento(usuario_id, documento_id):
    return consultar_df(
        """
        SELECT *
        FROM documentos_saude
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, documento_id),
    )


def excluir_documento(usuario_id, documento_id, apagar_arquivo=True):
    doc = obter_documento(usuario_id, documento_id)

    if doc.empty:
        return False, "Documento nao encontrado."

    caminho = doc.iloc[0].get("caminho_arquivo")
    msg_arquivo = ""

    if apagar_arquivo and caminho:
        try:
            p = Path(caminho)
            if p.exists():
                p.unlink()
                msg_arquivo = " Arquivo fisico apagado."
            else:
                msg_arquivo = " Arquivo fisico nao encontrado na pasta."
        except Exception as e:
            msg_arquivo = f" Nao consegui apagar o arquivo fisico: {e}"

    executar(
        """
        UPDATE documentos_saude
        SET excluido = 1,
            excluido_em = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (agora(), usuario_id, documento_id),
    )

    return True, "Documento removido do repositorio." + msg_arquivo
