from datetime import date, timedelta

from core.database import consultar_df, executar
from core.helpers import agora


def salvar_sintoma(usuario_id, data_sintoma, horario, sintoma, intensidade,
                   duracao, medicamento_id, gatilho, acao_tomada, observacao):
    med_id = medicamento_id if medicamento_id not in ["", None, 0] else None

    return executar(
        """
        INSERT INTO sintomas_diario (
            usuario_id, data_sintoma, horario, sintoma, intensidade, duracao,
            medicamento_id, gatilho, acao_tomada, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_sintoma.isoformat(),
            horario.strftime("%H:%M") if horario else "",
            sintoma,
            int(intensidade or 0),
            duracao,
            med_id,
            gatilho,
            acao_tomada,
            observacao,
            agora(),
        ),
    )


def listar_sintomas(usuario_id, limite=None):
    sql = """
        SELECT s.*,
               m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
        ORDER BY s.data_sintoma DESC, s.horario DESC, s.id DESC
    """

    if limite:
        sql += f" LIMIT {int(limite)}"

    return consultar_df(sql, (usuario_id,))


def sintomas_ultimos_dias(usuario_id, dias=30):
    data_min = (date.today() - timedelta(days=dias)).isoformat()

    return consultar_df(
        """
        SELECT s.*,
               m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma >= ?
        ORDER BY s.data_sintoma DESC, s.horario DESC, s.id DESC
        """,
        (usuario_id, data_min),
    )


def resumo_sintomas(usuario_id, dias=30):
    df = sintomas_ultimos_dias(usuario_id, dias=dias)

    if df.empty:
        return {
            "total": 0,
            "media_intensidade": 0,
            "mais_frequentes": [],
            "com_medicamento": 0,
        }

    total = len(df)
    media = round(float(df["intensidade"].fillna(0).mean()), 1) if "intensidade" in df.columns else 0

    mais_frequentes = (
        df["sintoma"]
        .fillna("")
        .str.strip()
        .str.lower()
        .value_counts()
        .head(5)
        .reset_index()
        .values
        .tolist()
    )

    com_medicamento = len(df[df["medicamento_id"].notna()]) if "medicamento_id" in df.columns else 0

    return {
        "total": total,
        "media_intensidade": media,
        "mais_frequentes": mais_frequentes,
        "com_medicamento": com_medicamento,
    }


def listar_medicamentos_para_sintoma(usuario_id):
    return consultar_df(
        """
        SELECT id, nome, dose, COALESCE(status, 'Ativo') AS status
        FROM medicamentos
        WHERE usuario_id = ?
        ORDER BY status, nome
        """,
        (usuario_id,),
    )


def gerar_leitura_sintomas(usuario_id, dias=30):
    resumo = resumo_sintomas(usuario_id, dias=dias)

    if resumo["total"] == 0:
        return f"Nenhum sintoma foi registrado nos ultimos {dias} dias."

    partes = []
    partes.append(
        f"Nos ultimos {dias} dias, foram registrados {resumo['total']} sintoma(s), com intensidade media de {resumo['media_intensidade']} em uma escala de 0 a 10."
    )

    if resumo["mais_frequentes"]:
        frequentes = ", ".join([f"{nome} ({qtd}x)" for nome, qtd in resumo["mais_frequentes"] if nome])
        if frequentes:
            partes.append(f"Os sintomas mais frequentes foram: {frequentes}.")

    if resumo["com_medicamento"] > 0:
        partes.append(
            f"{resumo['com_medicamento']} registro(s) foram associados a algum medicamento, o que pode ajudar a organizar a conversa com o profissional de saude."
        )

    partes.append(
        "Essa leitura organiza relatos pessoais e nao define causa, diagnostico ou conduta clinica."
    )

    return " ".join(partes)
