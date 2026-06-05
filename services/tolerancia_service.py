import pandas as pd

from core.database import consultar_df
from core.helpers import br_date


def listar_medicamentos_com_alerta(usuario_id):
    """
    Lista medicamentos com algum sinal de baixa tolerancia:
    - status Suspenso/Substituido/Pausado
    - eventos de medicacao ligados ao medicamento
    - sintomas associados ao medicamento
    """
    meds = consultar_df(
        """
        SELECT id, nome, dose, data_inicio, data_fim, uso_continuo,
               COALESCE(status, 'Ativo') AS status, data_status, motivo_status,
               medico, orientacao
        FROM medicamentos
        WHERE usuario_id = ?
        ORDER BY data_inicio DESC, id DESC
        """,
        (usuario_id,),
    )

    if meds.empty:
        return pd.DataFrame()

    linhas = []

    for _, med in meds.iterrows():
        med_id = int(med["id"])

        eventos = consultar_df(
            """
            SELECT *
            FROM eventos_medicacao
            WHERE usuario_id = ?
              AND medicamento_id = ?
              AND tipo_evento IN ('Efeito adverso', 'Suspenso', 'Substituido', 'Pausado')
            ORDER BY data_evento DESC, id DESC
            """,
            (usuario_id, med_id),
        )

        sintomas = consultar_df(
            """
            SELECT *
            FROM sintomas_diario
            WHERE usuario_id = ?
              AND medicamento_id = ?
            ORDER BY data_sintoma DESC, horario DESC, id DESC
            """,
            (usuario_id, med_id),
        )

        status = med.get("status", "Ativo")
        status_alerta = status in ["Suspenso", "Substituido", "Pausado"]

        if eventos.empty and sintomas.empty and not status_alerta:
            continue

        intensidade_media = 0
        sintomas_fortes = 0
        sintomas_total = 0
        sintomas_principais = ""

        if not sintomas.empty:
            sintomas_total = len(sintomas)
            intensidade_media = round(float(sintomas["intensidade"].fillna(0).mean()), 1)
            sintomas_fortes = len(sintomas[sintomas["intensidade"].fillna(0) >= 7])
            sintomas_principais = ", ".join(
                sintomas["sintoma"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .value_counts()
                .head(4)
                .index
                .tolist()
            )

        eventos_total = len(eventos)

        nivel = "Baixo"
        if status in ["Suspenso", "Substituido"] or sintomas_fortes >= 2 or eventos_total >= 2:
            nivel = "Alto"
        elif status == "Pausado" or sintomas_fortes == 1 or eventos_total == 1 or sintomas_total >= 2:
            nivel = "Moderado"

        motivos = []
        if med.get("motivo_status"):
            motivos.append(str(med.get("motivo_status")))
        if not eventos.empty:
            for _, e in eventos.head(2).iterrows():
                trecho = e.get("motivo") or e.get("sintomas") or e.get("observacao")
                if trecho:
                    motivos.append(str(trecho))
        if sintomas_principais:
            motivos.append(f"Sintomas registrados: {sintomas_principais}")

        linhas.append({
            "medicamento_id": med_id,
            "medicamento": med.get("nome"),
            "dose": med.get("dose") or "",
            "status": status,
            "nivel_alerta": nivel,
            "data_inicio": br_date(med.get("data_inicio")),
            "data_status": br_date(med.get("data_status") or med.get("data_fim")),
            "motivo_resumo": " | ".join(motivos[:3]),
            "eventos_total": eventos_total,
            "sintomas_total": sintomas_total,
            "sintomas_fortes": sintomas_fortes,
            "intensidade_media": intensidade_media,
            "sintomas_principais": sintomas_principais,
            "medico": med.get("medico") or "",
        })

    if not linhas:
        return pd.DataFrame()

    ordem = {"Alto": 0, "Moderado": 1, "Baixo": 2}
    df = pd.DataFrame(linhas)
    df["ordem"] = df["nivel_alerta"].map(ordem).fillna(9)
    df = df.sort_values(["ordem", "medicamento"]).drop(columns=["ordem"])
    return df


def detalhes_tolerancia_medicamento(usuario_id, medicamento_id):
    med = consultar_df(
        """
        SELECT id, nome, dose, data_inicio, data_fim, uso_continuo,
               COALESCE(status, 'Ativo') AS status, data_status, motivo_status,
               medico, orientacao
        FROM medicamentos
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, medicamento_id),
    )

    eventos = consultar_df(
        """
        SELECT *
        FROM eventos_medicacao
        WHERE usuario_id = ?
          AND medicamento_id = ?
        ORDER BY data_evento DESC, id DESC
        """,
        (usuario_id, medicamento_id),
    )

    sintomas = consultar_df(
        """
        SELECT *
        FROM sintomas_diario
        WHERE usuario_id = ?
          AND medicamento_id = ?
        ORDER BY data_sintoma DESC, horario DESC, id DESC
        """,
        (usuario_id, medicamento_id),
    )

    docs = pd.DataFrame()
    if not med.empty:
        nome = med.iloc[0]["nome"]
        termo = f"%{nome}%"
        docs = consultar_df(
            """
            SELECT *
            FROM documentos_saude
            WHERE usuario_id = ?
              AND (
                    titulo LIKE ?
                    OR relacionado_a LIKE ?
                    OR observacao LIKE ?
              )
            ORDER BY data_documento DESC, id DESC
            """,
            (usuario_id, termo, termo, termo),
        )

    return med, eventos, sintomas, docs


def gerar_leitura_tolerancia(usuario_id):
    df = listar_medicamentos_com_alerta(usuario_id)

    if df.empty:
        return "Nao ha medicamentos com suspensao, substituicao, pausa, evento adverso ou sintoma associado registrados ate o momento."

    altos = len(df[df["nivel_alerta"] == "Alto"])
    moderados = len(df[df["nivel_alerta"] == "Moderado"])
    baixos = len(df[df["nivel_alerta"] == "Baixo"])

    partes = []
    partes.append(
        f"Foram identificados {len(df)} medicamento(s) com algum sinal de tolerancia a observar."
    )

    if altos:
        partes.append(
            f"{altos} medicamento(s) aparecem com alerta alto, geralmente por suspensao, substituicao, eventos repetidos ou sintomas fortes."
        )

    if moderados:
        partes.append(
            f"{moderados} medicamento(s) aparecem com alerta moderado, com registros que merecem ser revisados em consulta."
        )

    if baixos:
        partes.append(
            f"{baixos} medicamento(s) tem alerta baixo, mas ainda aparecem no historico por possuirem algum registro associado."
        )

    partes.append(
        "Essa leitura organiza eventos e relatos. Ela nao confirma alergia, intolerancia ou causalidade; serve para apoiar a conversa com o profissional de saude."
    )

    return " ".join(partes)


def gerar_texto_historico_tolerancia(usuario_id, usuario):
    nome_usuario = usuario.get("nome", "Usuario") if hasattr(usuario, "get") else str(usuario)
    df = listar_medicamentos_com_alerta(usuario_id)

    linhas = []
    linhas.append("HISTORICO DE TOLERANCIA A MEDICAMENTOS")
    linhas.append("=" * 43)
    linhas.append("")
    linhas.append(f"Paciente: {nome_usuario}")
    linhas.append("")
    linhas.append("Observacao:")
    linhas.append("Este resumo organiza medicamentos com suspensao, substituicao, pausa, eventos adversos ou sintomas associados. Nao confirma alergia, intolerancia, causalidade ou diagnostico.")
    linhas.append("")

    if df.empty:
        linhas.append("Nenhum medicamento com alerta de tolerancia foi registrado ate o momento.")
        return "\n".join(linhas)

    for _, r in df.iterrows():
        linhas.append(f"- {r['medicamento']} | {r['dose']} | alerta {r['nivel_alerta']}")
        linhas.append(f"  Status: {r['status']}")
        linhas.append(f"  Inicio: {r['data_inicio']}")
        if r["data_status"]:
            linhas.append(f"  Data status/fim: {r['data_status']}")
        if r["motivo_resumo"]:
            linhas.append(f"  Contexto: {r['motivo_resumo']}")
        linhas.append(f"  Eventos registrados: {r['eventos_total']}")
        linhas.append(f"  Sintomas associados: {r['sintomas_total']} | fortes: {r['sintomas_fortes']} | intensidade media: {r['intensidade_media']}")
        if r["sintomas_principais"]:
            linhas.append(f"  Sintomas principais: {r['sintomas_principais']}")
        if r["medico"]:
            linhas.append(f"  Profissional: {r['medico']}")
        linhas.append("")

    return "\n".join(linhas)
