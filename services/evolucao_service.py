from datetime import timedelta

import pandas as pd

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def listar_medicamentos_para_evolucao(usuario_id):
    return consultar_df(
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


def obter_medicamento(usuario_id, medicamento_id):
    return consultar_df(
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


def _to_date(valor):
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def _diff_label(antes, depois, unidade=""):
    try:
        a = float(antes)
        d = float(depois)
        diff = d - a
        sinal = "+" if diff > 0 else ""
        return f"{sinal}{fmt_num(diff, 2)} {unidade}".strip()
    except Exception:
        return ""


def buscar_exames_antes_depois(usuario_id, data_inicio, janela_antes_dias=180, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    data_min = (inicio - timedelta(days=janela_antes_dias)).isoformat()
    data_max = (inicio + timedelta(days=janela_depois_dias)).isoformat()

    exames = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame BETWEEN ? AND ?
        ORDER BY nome_exame, data_exame
        """,
        (usuario_id, data_min, data_max),
    )

    if exames.empty:
        return pd.DataFrame()

    exames["data_exame_dt"] = pd.to_datetime(exames["data_exame"], errors="coerce")
    inicio_ts = pd.to_datetime(inicio)

    linhas = []

    for nome, grupo in exames.groupby("nome_exame"):
        grupo = grupo.sort_values("data_exame_dt")
        antes = grupo[grupo["data_exame_dt"] <= inicio_ts]
        depois = grupo[grupo["data_exame_dt"] > inicio_ts]

        row_antes = antes.tail(1).iloc[0] if not antes.empty else None
        row_depois = depois.tail(1).iloc[0] if not depois.empty else None

        unidade = ""
        if row_depois is not None:
            unidade = row_depois.get("unidade", "") or ""
        elif row_antes is not None:
            unidade = row_antes.get("unidade", "") or ""

        valor_antes = row_antes["resultado"] if row_antes is not None else None
        valor_depois = row_depois["resultado"] if row_depois is not None else None

        linhas.append({
            "indicador": nome,
            "data_antes": br_date(row_antes["data_exame"]) if row_antes is not None else "",
            "antes": valor_antes,
            "data_depois": br_date(row_depois["data_exame"]) if row_depois is not None else "",
            "depois": valor_depois,
            "unidade": unidade,
            "variacao": _diff_label(valor_antes, valor_depois, unidade) if valor_antes is not None and valor_depois is not None else "",
            "referencia_min": row_depois["referencia_min"] if row_depois is not None else (row_antes["referencia_min"] if row_antes is not None else 0),
            "referencia_max": row_depois["referencia_max"] if row_depois is not None else (row_antes["referencia_max"] if row_antes is not None else 0),
        })

    return pd.DataFrame(linhas)


def buscar_corpo_antes_depois(usuario_id, data_inicio, janela_antes_dias=180, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    data_min = (inicio - timedelta(days=janela_antes_dias)).isoformat()
    data_max = (inicio + timedelta(days=janela_depois_dias)).isoformat()

    bio = consultar_df(
        """
        SELECT *
        FROM bioimpedancia
        WHERE usuario_id = ?
          AND data_medicao BETWEEN ? AND ?
        ORDER BY data_medicao
        """,
        (usuario_id, data_min, data_max),
    )

    if bio.empty:
        return pd.DataFrame()

    bio["data_dt"] = pd.to_datetime(bio["data_medicao"], errors="coerce")
    inicio_ts = pd.to_datetime(inicio)

    antes = bio[bio["data_dt"] <= inicio_ts]
    depois = bio[bio["data_dt"] > inicio_ts]

    row_antes = antes.tail(1).iloc[0] if not antes.empty else None
    row_depois = depois.tail(1).iloc[0] if not depois.empty else None

    indicadores = [
        ("Peso", "peso_kg", "kg"),
        ("Gordura corporal", "gordura_percentual", "%"),
        ("Massa magra", "massa_magra_kg", "kg"),
        ("Massa muscular", "massa_muscular_kg", "kg"),
        ("Gordura visceral", "gordura_visceral", ""),
        ("Cintura", "cintura_cm", "cm"),
    ]

    linhas = []
    for nome, coluna, unidade in indicadores:
        valor_antes = row_antes[coluna] if row_antes is not None and coluna in row_antes else None
        valor_depois = row_depois[coluna] if row_depois is not None and coluna in row_depois else None

        linhas.append({
            "indicador": nome,
            "data_antes": br_date(row_antes["data_medicao"]) if row_antes is not None else "",
            "antes": valor_antes,
            "data_depois": br_date(row_depois["data_medicao"]) if row_depois is not None else "",
            "depois": valor_depois,
            "unidade": unidade,
            "variacao": _diff_label(valor_antes, valor_depois, unidade) if valor_antes is not None and valor_depois is not None else "",
        })

    return pd.DataFrame(linhas)


def buscar_eventos_no_periodo(usuario_id, medicamento_id, data_inicio, data_fim=None, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    fim = _to_date(data_fim)
    if fim is None:
        fim = inicio + timedelta(days=janela_depois_dias)

    return consultar_df(
        """
        SELECT e.*, m.nome AS medicamento
        FROM eventos_medicacao e
        LEFT JOIN medicamentos m ON m.id = e.medicamento_id
        WHERE e.usuario_id = ?
          AND (e.medicamento_id = ? OR e.medicamento_id IS NULL)
          AND e.data_evento BETWEEN ? AND ?
        ORDER BY e.data_evento DESC, e.id DESC
        """,
        (usuario_id, medicamento_id, inicio.isoformat(), fim.isoformat()),
    )


def buscar_sintomas_no_periodo(usuario_id, medicamento_id, data_inicio, data_fim=None, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    fim = _to_date(data_fim)
    if fim is None:
        fim = inicio + timedelta(days=janela_depois_dias)

    return consultar_df(
        """
        SELECT s.*, m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma BETWEEN ? AND ?
          AND (s.medicamento_id = ? OR s.medicamento_id IS NULL)
        ORDER BY s.data_sintoma DESC, s.horario DESC, s.id DESC
        """,
        (usuario_id, inicio.isoformat(), fim.isoformat(), medicamento_id),
    )


def buscar_marcos_no_periodo(usuario_id, data_inicio, data_fim=None, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    fim = _to_date(data_fim)
    if fim is None:
        fim = inicio + timedelta(days=janela_depois_dias)

    return consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco BETWEEN ? AND ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, inicio.isoformat(), fim.isoformat()),
    )


def buscar_documentos_relacionados(usuario_id, nome_medicamento):
    termo = f"%{nome_medicamento}%"
    return consultar_df(
        """
        SELECT *
        FROM documentos_saude
        WHERE usuario_id = ?
          AND COALESCE(excluido, 0) = 0
          AND (
                titulo LIKE ?
                OR relacionado_a LIKE ?
                OR observacao LIKE ?
          )
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id, termo, termo, termo),
    )


def buscar_atividades_no_periodo(usuario_id, data_inicio, data_fim=None, janela_depois_dias=365):
    inicio = _to_date(data_inicio)
    if inicio is None:
        return pd.DataFrame()

    fim = _to_date(data_fim)
    if fim is None:
        fim = inicio + timedelta(days=janela_depois_dias)

    return consultar_df(
        """
        SELECT *
        FROM atividades
        WHERE usuario_id = ?
          AND data_atividade BETWEEN ? AND ?
        ORDER BY data_atividade DESC, id DESC
        """,
        (usuario_id, inicio.isoformat(), fim.isoformat()),
    )


def gerar_leitura_evolucao(med, exames_df, corpo_df, eventos_df, atividades_df, sintomas_df=None, marcos_df=None):
    nome = med.get("nome", "tratamento")
    status = med.get("status", "")
    data_inicio = br_date(med.get("data_inicio", ""))

    partes = []

    partes.append(
        f"O tratamento com {nome}, iniciado em {data_inicio}, esta registrado com status {status}."
    )

    if marcos_df is not None and not marcos_df.empty:
        partes.append(
            f"No mesmo periodo, ha {len(marcos_df)} marco(s) da jornada registrados, como consultas, retornos ou mudancas de conduta. Eles ajudam a interpretar por que exames, sintomas e ajustes aparecem nesse intervalo."
        )

    melhoras = 0
    pioras = 0

    if corpo_df is not None and not corpo_df.empty:
        for _, r in corpo_df.iterrows():
            antes = r.get("antes")
            depois = r.get("depois")
            indicador = str(r.get("indicador", "")).lower()

            try:
                a = float(antes)
                d = float(depois)
            except Exception:
                continue

            if indicador in ["peso", "gordura corporal", "gordura visceral", "cintura"]:
                if d < a:
                    melhoras += 1
                elif d > a:
                    pioras += 1
            elif indicador in ["massa magra", "massa muscular"]:
                if d > a:
                    melhoras += 1
                elif d < a:
                    pioras += 1

    exames_com_comparacao = 0
    if exames_df is not None and not exames_df.empty:
        for _, r in exames_df.iterrows():
            if r.get("antes") is not None and r.get("depois") is not None:
                exames_com_comparacao += 1

    if melhoras or pioras:
        partes.append(
            f"Nos dados corporais, ha {melhoras} indicador(es) com evolucao favoravel e {pioras} ponto(s) que merecem atencao, conforme os registros antes/depois."
        )

    if exames_com_comparacao:
        partes.append(
            f"Nos exames, {exames_com_comparacao} marcador(es) possuem comparacao antes/depois cadastrada. A leitura deve ser feita com o profissional de saude, considerando contexto clinico, dose, adesao e outros habitos."
        )
    else:
        partes.append(
            "Ainda nao ha exames suficientes antes e depois para uma comparacao laboratorial robusta."
        )

    if sintomas_df is not None and not sintomas_df.empty:
        fortes = len(sintomas_df[sintomas_df["intensidade"].fillna(0) >= 7]) if "intensidade" in sintomas_df.columns else 0
        partes.append(
            f"No periodo, foram registrados {len(sintomas_df)} sintoma(s), sendo {fortes} com intensidade alta. Esses relatos ajudam a contextualizar tolerancia, bem-estar e possiveis efeitos percebidos."
        )

    if eventos_df is not None and not eventos_df.empty:
        partes.append(
            f"Foram registrados {len(eventos_df)} evento(s) no periodo, incluindo alteracoes de tratamento, sintomas ou efeitos adversos. Esses pontos devem ser levados para a consulta."
        )

    if atividades_df is not None and not atividades_df.empty:
        total_min = int(atividades_df["duracao_min"].fillna(0).sum()) if "duracao_min" in atividades_df.columns else 0
        partes.append(
            f"No periodo analisado, ha {len(atividades_df)} atividade(s) fisica(s) registrada(s), somando aproximadamente {total_min} minuto(s). Isso pode influenciar peso, exames metabolicos e percepcao de bem-estar."
        )

    partes.append(
        "Esta leitura mostra associacoes temporais entre tratamento, corpo, exames, sintomas, marcos e eventos. Ela nao prova causalidade, nao substitui avaliacao medica e serve para organizar a conversa com o profissional."
    )

    return " ".join(partes)
