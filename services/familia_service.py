from pathlib import Path

from core.database import consultar_df, executar
from core.helpers import agora


def listar_usuarios_ativos():
    return consultar_df(
        """
        SELECT *
        FROM usuarios
        WHERE COALESCE(ativo, 1) = 1
        ORDER BY nome
        """
    )


def listar_usuarios_todos():
    return consultar_df(
        """
        SELECT *
        FROM usuarios
        ORDER BY COALESCE(ativo, 1) DESC, nome
        """
    )


def obter_usuario(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM usuarios
        WHERE id = ?
        """,
        (usuario_id,),
    )


def atualizar_usuario(usuario_id, nome, data_nascimento, sexo, altura_cm, objetivo):
    executar(
        """
        UPDATE usuarios
        SET nome = ?,
            data_nascimento = ?,
            sexo = ?,
            altura_cm = ?,
            objetivo = ?,
            atualizado_em = ?
        WHERE id = ?
        """,
        (
            nome,
            data_nascimento.isoformat() if hasattr(data_nascimento, "isoformat") else data_nascimento,
            sexo,
            float(altura_cm or 0),
            objetivo,
            agora(),
            usuario_id,
        ),
    )


def desativar_usuario(usuario_id):
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


def reativar_usuario(usuario_id):
    executar(
        """
        UPDATE usuarios
        SET ativo = 1,
            desativado_em = NULL,
            atualizado_em = ?
        WHERE id = ?
        """,
        (agora(), usuario_id),
    )


def _contar(tabela, usuario_id, filtro_extra=""):
    sql = f"SELECT COUNT(*) AS total FROM {tabela} WHERE usuario_id = ? {filtro_extra}"
    df = consultar_df(sql, (usuario_id,))
    return int(df.iloc[0]["total"]) if not df.empty else 0


def _arquivos_usuario(usuario_id, incluir_excluidos=False):
    filtro = "" if incluir_excluidos else "AND COALESCE(excluido, 0) = 0"
    return consultar_df(
        f"""
        SELECT id, caminho_arquivo
        FROM documentos_saude
        WHERE usuario_id = ?
          {filtro}
          AND caminho_arquivo IS NOT NULL
          AND TRIM(caminho_arquivo) <> ''
        """,
        (usuario_id,),
    )


def tamanho_arquivos_usuario(usuario_id, incluir_excluidos=False):
    docs = _arquivos_usuario(usuario_id, incluir_excluidos=incluir_excluidos)
    total = 0
    arquivos_existentes = 0
    arquivos_nao_encontrados = 0

    if docs.empty:
        return {
            "bytes": 0,
            "mb": 0,
            "arquivos_existentes": 0,
            "arquivos_nao_encontrados": 0,
        }

    for _, d in docs.iterrows():
        caminho = d.get("caminho_arquivo")
        if not caminho:
            continue
        p = Path(caminho)
        if p.exists():
            arquivos_existentes += 1
            total += p.stat().st_size
        else:
            arquivos_nao_encontrados += 1

    return {
        "bytes": total,
        "mb": round(total / (1024 * 1024), 2),
        "arquivos_existentes": arquivos_existentes,
        "arquivos_nao_encontrados": arquivos_nao_encontrados,
    }


def resumo_usuario(usuario_id):
    armazenamento = tamanho_arquivos_usuario(usuario_id)

    return {
        "marcos": _contar("marcos_jornada", usuario_id),
        "medicamentos": _contar("medicamentos", usuario_id),
        "doses": _contar("doses", usuario_id),
        "eventos": _contar("eventos_medicacao", usuario_id),
        "exames": _contar("exames", usuario_id),
        "bioimpedancias": _contar("bioimpedancia", usuario_id),
        "atividades": _contar("atividades", usuario_id),
        "documentos": _contar("documentos_saude", usuario_id, "AND COALESCE(excluido, 0) = 0"),
        "documentos_excluidos": _contar("documentos_saude", usuario_id, "AND COALESCE(excluido, 0) = 1"),
        "sintomas": _contar("sintomas_diario", usuario_id),
        "registros_rapidos": _contar("registros_rapidos", usuario_id),
        "armazenamento_mb": armazenamento["mb"],
        "arquivos_existentes": armazenamento["arquivos_existentes"],
        "arquivos_nao_encontrados": armazenamento["arquivos_nao_encontrados"],
    }


def resumo_todos_usuarios():
    usuarios = listar_usuarios_todos()
    linhas = []

    if usuarios.empty:
        return usuarios

    for _, u in usuarios.iterrows():
        r = resumo_usuario(int(u["id"]))
        linhas.append({
            "id": int(u["id"]),
            "nome": u["nome"],
            "ativo": "Sim" if int(u.get("ativo") or 1) == 1 else "Não",
            "data_nascimento": u.get("data_nascimento") or "",
            "sexo": u.get("sexo") or "",
            "altura_cm": u.get("altura_cm") or 0,
            "marcos": r["marcos"],
            "documentos": r["documentos"],
            "exames": r["exames"],
            "medicamentos": r["medicamentos"],
            "sintomas": r["sintomas"],
            "atividades": r["atividades"],
            "armazenamento_mb": r["armazenamento_mb"],
            "arquivos_existentes": r["arquivos_existentes"],
            "arquivos_nao_encontrados": r["arquivos_nao_encontrados"],
        })

    import pandas as pd
    return pd.DataFrame(linhas)


def chave_confirmacao_exclusao(nome):
    nome = str(nome or "").strip().upper()
    return f"EXCLUIR {nome}"


def excluir_usuario_definitivo(usuario_id, apagar_arquivos=True):
    usuario = obter_usuario(usuario_id)

    if usuario.empty:
        return False, "Usuário não encontrado."

    docs = _arquivos_usuario(usuario_id, incluir_excluidos=True)
    arquivos_apagados = 0
    arquivos_erro = 0

    if apagar_arquivos and not docs.empty:
        for _, d in docs.iterrows():
            caminho = d.get("caminho_arquivo")
            if not caminho:
                continue

            try:
                p = Path(caminho)
                if p.exists():
                    p.unlink()
                    arquivos_apagados += 1
            except Exception:
                arquivos_erro += 1

    # Apaga dados em ordem segura.
    tabelas = [
        "doses",
        "eventos_medicacao",
        "sintomas_diario",
        "registros_rapidos",
        "atividades",
        "bioimpedancia",
        "exames",
        "medicamentos",
        "documentos_saude",
        "marcos_jornada",
    ]

    for tabela in tabelas:
        executar(f"DELETE FROM {tabela} WHERE usuario_id = ?", (usuario_id,))

    executar("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

    msg = f"Cadastro excluído definitivamente. Arquivos apagados: {arquivos_apagados}."
    if arquivos_erro:
        msg += f" Arquivos com erro ao apagar: {arquivos_erro}."

    return True, msg
