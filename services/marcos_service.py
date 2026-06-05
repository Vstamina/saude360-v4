from datetime import date, timedelta

from core.database import consultar_df, executar
from core.helpers import agora


def salvar_marco(usuario_id, data_marco, tipo_marco, titulo, especialidade, profissional,
                 local, queixas, motivo, conduta, exames_solicitados,
                 medicamentos_relacionados, proximo_passo, observacao):
    return executar(
        """
        INSERT INTO marcos_jornada (
            usuario_id, data_marco, tipo_marco, titulo, especialidade, profissional,
            local, queixas, motivo, conduta, exames_solicitados,
            medicamentos_relacionados, proximo_passo, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_marco.isoformat(),
            tipo_marco,
            titulo,
            especialidade,
            profissional,
            local,
            queixas,
            motivo,
            conduta,
            exames_solicitados,
            medicamentos_relacionados,
            proximo_passo,
            observacao,
            agora(),
        ),
    )


def listar_marcos(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id,),
    )


def listar_marcos_recentes(usuario_id, limite=5):
    return consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
        ORDER BY data_marco DESC, id DESC
        LIMIT ?
        """,
        (usuario_id, int(limite)),
    )


def listar_marcos_periodo(usuario_id, data_inicio, data_fim=None, dias_padrao=365):
    import pandas as pd

    inicio = pd.to_datetime(data_inicio, errors="coerce")
    if pd.isna(inicio):
        return consultar_df("SELECT * FROM marcos_jornada WHERE 1=0")

    if data_fim:
        fim = pd.to_datetime(data_fim, errors="coerce")
        if pd.isna(fim):
            fim = inicio + pd.Timedelta(days=dias_padrao)
    else:
        fim = inicio + pd.Timedelta(days=dias_padrao)

    return consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco BETWEEN ? AND ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, inicio.date().isoformat(), fim.date().isoformat()),
    )


def listar_marcos_opcoes(usuario_id):
    df = listar_marcos(usuario_id)
    opcoes = {"Sem marco relacionado": None}

    for _, r in df.iterrows():
        label = f"{r['data_marco']} | {r['tipo_marco']} | {r['titulo']} | ID {r['id']}"
        opcoes[label] = int(r["id"])

    return opcoes


def obter_marco(usuario_id, marco_id):
    return consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, marco_id),
    )


def excluir_marco(usuario_id, marco_id):
    executar("UPDATE exames SET marco_id = NULL WHERE usuario_id = ? AND marco_id = ?", (usuario_id, marco_id))
    executar("UPDATE medicamentos SET marco_id = NULL WHERE usuario_id = ? AND marco_id = ?", (usuario_id, marco_id))
    executar("UPDATE documentos_saude SET marco_id = NULL WHERE usuario_id = ? AND marco_id = ?", (usuario_id, marco_id))
    executar("UPDATE eventos_medicacao SET marco_id = NULL WHERE usuario_id = ? AND marco_id = ?", (usuario_id, marco_id))
    executar("UPDATE sintomas_diario SET marco_id = NULL WHERE usuario_id = ? AND marco_id = ?", (usuario_id, marco_id))
    executar("DELETE FROM marcos_jornada WHERE usuario_id = ? AND id = ?", (usuario_id, marco_id))


def resumo_itens_do_marco(usuario_id, marco_id):
    exames = consultar_df(
        """
        SELECT id, data_exame, nome_exame, resultado, unidade
        FROM exames
        WHERE usuario_id = ? AND marco_id = ?
        ORDER BY data_exame DESC
        """,
        (usuario_id, marco_id),
    )

    medicamentos = consultar_df(
        """
        SELECT id, data_inicio, nome, dose, COALESCE(status, 'Ativo') AS status
        FROM medicamentos
        WHERE usuario_id = ? AND marco_id = ?
        ORDER BY data_inicio DESC
        """,
        (usuario_id, marco_id),
    )

    documentos = consultar_df(
        """
        SELECT id, data_documento, tipo_documento, titulo, caminho_arquivo
        FROM documentos_saude
        WHERE usuario_id = ? AND marco_id = ? AND COALESCE(excluido, 0) = 0
        ORDER BY data_documento DESC
        """,
        (usuario_id, marco_id),
    )

    sintomas = consultar_df(
        """
        SELECT id, data_sintoma, sintoma, intensidade
        FROM sintomas_diario
        WHERE usuario_id = ? AND marco_id = ?
        ORDER BY data_sintoma DESC
        """,
        (usuario_id, marco_id),
    )

    return exames, medicamentos, documentos, sintomas


def gerar_leitura_marcos(usuario_id, limite=8):
    df = listar_marcos_recentes(usuario_id, limite=limite)

    if df.empty:
        return "Ainda não há consultas ou marcos registrados na jornada."

    consultas = len(df[df["tipo_marco"].astype(str).str.contains("Consulta|Retorno", case=False, na=False)])
    mudancas = len(df[df["tipo_marco"].astype(str).str.contains("Mudança|Início|Efeito|Pronto|Procedimento", case=False, na=False)])

    partes = [
        f"Há {len(df)} marco(s) recente(s) registrados na jornada."
    ]

    if consultas:
        partes.append(f"{consultas} deles são consultas ou retornos.")
    if mudancas:
        partes.append(f"{mudancas} deles envolvem mudança de conduta, início de tratamento, efeito importante ou procedimento.")

    partes.append("Esses marcos ajudam a explicar por que exames, medicamentos e sintomas aparecem em determinados momentos.")

    return " ".join(partes)
