from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def listar_medicamentos_para_evolucao(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
        ORDER BY data_inicio DESC, nome
        """,
        (usuario_id,),
    )


def obter_medicamento(usuario_id, medicamento_id):
    return consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND id = ?
        LIMIT 1
        """,
        (usuario_id, medicamento_id),
    )


def _to_date(valor):
    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def _janela_datas(data_inicio, dias_antes=30, dias_depois=90):
    inicio = _to_date(data_inicio) or date.today()
    antes_ini = inicio - timedelta(days=int(dias_antes))
    antes_fim = inicio - timedelta(days=1)
    depois_ini = inicio
    depois_fim = inicio + timedelta(days=int(dias_depois))
    return inicio, antes_ini, antes_fim, depois_ini, depois_fim


def exames_janela(usuario_id, data_inicio, dias_antes=30, dias_depois=90):
    inicio, antes_ini, antes_fim, depois_ini, depois_fim = _janela_datas(data_inicio, dias_antes, dias_depois)

    df = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame BETWEEN ? AND ?
        ORDER BY COALESCE(NULLIF(nome_padronizado, ''), nome_exame), data_exame ASC
        """,
        (usuario_id, antes_ini.isoformat(), depois_fim.isoformat()),
    )

    if df.empty:
        return df

    df["exame_chave"] = df.apply(
        lambda r: r.get("nome_padronizado") if r.get("nome_padronizado") else r.get("nome_exame"),
        axis=1,
    )
    df["periodo"] = df["data_exame"].apply(lambda x: "Antes" if (_to_date(x) and _to_date(x) < inicio) else "Depois")
    return df


def comparar_exames(usuario_id, data_inicio, dias_antes=30, dias_depois=90):
    df = exames_janela(usuario_id, data_inicio, dias_antes, dias_depois)

    if df.empty:
        return pd.DataFrame(columns=[
            "exame", "categoria", "antes_data", "antes_resultado", "depois_data",
            "depois_resultado", "unidade", "variacao_abs", "variacao_pct", "leitura"
        ])

    linhas = []
    for exame, g in df.groupby("exame_chave"):
        antes = g[g["periodo"] == "Antes"].sort_values("data_exame")
        depois = g[g["periodo"] == "Depois"].sort_values("data_exame")

        if antes.empty and depois.empty:
            continue

        antes_row = antes.iloc[-1] if not antes.empty else None
        depois_row = depois.iloc[-1] if not depois.empty else None

        antes_val = float(antes_row["resultado"]) if antes_row is not None and pd.notna(antes_row.get("resultado")) else None
        depois_val = float(depois_row["resultado"]) if depois_row is not None and pd.notna(depois_row.get("resultado")) else None

        variacao_abs = None
        variacao_pct = None
        leitura = "Sem comparação completa"

        if antes_val is not None and depois_val is not None:
            variacao_abs = depois_val - antes_val
            if antes_val != 0:
                variacao_pct = (variacao_abs / abs(antes_val)) * 100

            if abs(variacao_pct or 0) < 5:
                leitura = "Estável"
            elif variacao_abs > 0:
                leitura = "Aumentou"
            else:
                leitura = "Reduziu"
        elif antes_val is None and depois_val is not None:
            leitura = "Só há dado depois do início"
        elif antes_val is not None and depois_val is None:
            leitura = "Só há dado antes do início"

        categoria = ""
        unidade = ""
        if depois_row is not None:
            categoria = depois_row.get("categoria_exame") or ""
            unidade = depois_row.get("unidade") or ""
        elif antes_row is not None:
            categoria = antes_row.get("categoria_exame") or ""
            unidade = antes_row.get("unidade") or ""

        linhas.append({
            "exame": exame,
            "categoria": categoria or "Não classificado",
            "antes_data": antes_row.get("data_exame") if antes_row is not None else "",
            "antes_resultado": antes_val,
            "depois_data": depois_row.get("data_exame") if depois_row is not None else "",
            "depois_resultado": depois_val,
            "unidade": unidade,
            "variacao_abs": round(variacao_abs, 2) if variacao_abs is not None else None,
            "variacao_pct": round(variacao_pct, 1) if variacao_pct is not None else None,
            "leitura": leitura,
        })

    return pd.DataFrame(linhas).sort_values(["categoria", "exame"])


def sintomas_no_tratamento(usuario_id, medicamento_id, data_inicio, dias_depois=90):
    inicio = _to_date(data_inicio) or date.today()
    fim = inicio + timedelta(days=int(dias_depois))

    return consultar_df(
        """
        SELECT s.*, m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma BETWEEN ? AND ?
          AND (
                s.medicamento_id = ?
                OR s.medicamento_id IS NULL
              )
        ORDER BY s.data_sintoma DESC, COALESCE(s.horario, '') DESC
        """,
        (usuario_id, inicio.isoformat(), fim.isoformat(), medicamento_id),
    )


def eventos_no_tratamento(usuario_id, medicamento_id, data_inicio, dias_depois=90):
    inicio = _to_date(data_inicio) or date.today()
    fim = inicio + timedelta(days=int(dias_depois))

    return consultar_df(
        """
        SELECT e.*, m.nome AS medicamento
        FROM eventos_medicacao e
        LEFT JOIN medicamentos m ON m.id = e.medicamento_id
        WHERE e.usuario_id = ?
          AND e.data_evento BETWEEN ? AND ?
          AND (
                e.medicamento_id = ?
                OR e.medicamento_id IS NULL
              )
        ORDER BY e.data_evento DESC, e.id DESC
        """,
        (usuario_id, inicio.isoformat(), fim.isoformat(), medicamento_id),
    )


def doses_no_tratamento(usuario_id, medicamento_id, data_inicio, dias_depois=90):
    inicio = _to_date(data_inicio) or date.today()
    fim = inicio + timedelta(days=int(dias_depois))

    return consultar_df(
        """
        SELECT *
        FROM doses
        WHERE usuario_id = ?
          AND medicamento_id = ?
          AND data_prevista BETWEEN ? AND ?
        ORDER BY data_prevista DESC, horario_previsto DESC
        """,
        (usuario_id, medicamento_id, inicio.isoformat(), fim.isoformat()),
    )


def aderencia_tratamento(doses):
    if doses.empty:
        return {
            "total": 0,
            "tomadas": 0,
            "nao_tomadas": 0,
            "pendentes": 0,
            "aderencia": 0,
            "leitura": "Sem doses registradas para esse tratamento no período."
        }

    validas = doses[~doses["status"].isin(["Cancelada", "Pausada"])]
    total = len(validas)
    tomadas = int((validas["status"] == "Tomado").sum())
    nao = int(validas["status"].isin(["Não tomado", "Nao tomado", "Esquecido"]).sum())
    pend = int((validas["status"] == "Pendente").sum())
    ader = round((tomadas / total) * 100, 1) if total else 0

    if total == 0:
        leitura = "Sem doses válidas para cálculo."
    elif ader >= 85:
        leitura = "Boa regularidade de uso no período."
    elif ader >= 60:
        leitura = "Aderência intermediária. Vale revisar horários, esquecimentos e estoque."
    else:
        leitura = "Aderência baixa. Isso pode limitar a interpretação de evolução."

    return {
        "total": total,
        "tomadas": tomadas,
        "nao_tomadas": nao,
        "pendentes": pend,
        "aderencia": ader,
        "leitura": leitura,
    }


def bio_no_tratamento(usuario_id, data_inicio, dias_antes=30, dias_depois=90):
    inicio, antes_ini, antes_fim, depois_ini, depois_fim = _janela_datas(data_inicio, dias_antes, dias_depois)

    df = consultar_df(
        """
        SELECT *
        FROM bioimpedancia
        WHERE usuario_id = ?
          AND data_medicao BETWEEN ? AND ?
        ORDER BY data_medicao ASC, id ASC
        """,
        (usuario_id, antes_ini.isoformat(), depois_fim.isoformat()),
    )

    if df.empty:
        return df

    df["periodo"] = df["data_medicao"].apply(lambda x: "Antes" if (_to_date(x) and _to_date(x) < inicio) else "Depois")
    return df


def comparar_bio(usuario_id, data_inicio, dias_antes=30, dias_depois=90):
    df = bio_no_tratamento(usuario_id, data_inicio, dias_antes, dias_depois)

    if df.empty:
        return pd.DataFrame(columns=["indicador", "antes", "depois", "variacao", "leitura"])

    antes = df[df["periodo"] == "Antes"].sort_values("data_medicao")
    depois = df[df["periodo"] == "Depois"].sort_values("data_medicao")

    antes_row = antes.iloc[-1] if not antes.empty else None
    depois_row = depois.iloc[-1] if not depois.empty else None

    indicadores = [
        ("peso_kg", "Peso"),
        ("gordura_percentual", "Gordura %"),
        ("massa_magra_kg", "Massa magra"),
        ("massa_muscular_kg", "Massa muscular"),
        ("gordura_visceral", "Gordura visceral"),
        ("cintura_cm", "Cintura"),
    ]

    linhas = []
    for col, label in indicadores:
        a = float(antes_row[col]) if antes_row is not None and col in antes_row and pd.notna(antes_row[col]) else None
        d = float(depois_row[col]) if depois_row is not None and col in depois_row and pd.notna(depois_row[col]) else None
        var = d - a if a is not None and d is not None else None

        if var is None:
            leitura = "Sem comparação completa"
        elif abs(var) < 0.1:
            leitura = "Estável"
        elif var > 0:
            leitura = "Aumentou"
        else:
            leitura = "Reduziu"

        linhas.append({
            "indicador": label,
            "antes": a,
            "depois": d,
            "variacao": round(var, 2) if var is not None else None,
            "leitura": leitura,
        })

    return pd.DataFrame(linhas)


def gerar_leitura_tratamento(usuario_id, medicamento_id, dias_antes=30, dias_depois=90):
    med_df = obter_medicamento(usuario_id, medicamento_id)
    if med_df.empty:
        return {
            "medicamento": None,
            "texto": "Medicamento não encontrado.",
            "exames": pd.DataFrame(),
            "sintomas": pd.DataFrame(),
            "eventos": pd.DataFrame(),
            "doses": pd.DataFrame(),
            "bio": pd.DataFrame(),
            "aderencia": {},
            "bio_comp": pd.DataFrame(),
        }

    med = med_df.iloc[0]
    exames = comparar_exames(usuario_id, med["data_inicio"], dias_antes, dias_depois)
    sintomas = sintomas_no_tratamento(usuario_id, medicamento_id, med["data_inicio"], dias_depois)
    eventos = eventos_no_tratamento(usuario_id, medicamento_id, med["data_inicio"], dias_depois)
    doses = doses_no_tratamento(usuario_id, medicamento_id, med["data_inicio"], dias_depois)
    ader = aderencia_tratamento(doses)
    bio_comp = comparar_bio(usuario_id, med["data_inicio"], dias_antes, dias_depois)

    partes = []
    partes.append(f"Tratamento analisado: {med['nome']} ({med.get('dose') or 'dose não informada'}).")
    partes.append(f"Início registrado: {br_date(med.get('data_inicio'))}.")
    partes.append(f"Aderência no período: {ader.get('aderencia', 0)}%. {ader.get('leitura', '')}")

    if not exames.empty:
        completos = exames[exames["leitura"].isin(["Aumentou", "Reduziu", "Estável"])]
        partes.append(f"Foram encontradas {len(exames)} trilha(s) de exames na janela; {len(completos)} com comparação antes/depois.")
        relevantes = exames[exames["leitura"].isin(["Aumentou", "Reduziu"])]
        if not relevantes.empty:
            nomes = ", ".join(relevantes["exame"].astype(str).head(5).tolist())
            partes.append(f"Exames com mudança observada: {nomes}.")
    else:
        partes.append("Não há exames suficientes na janela para comparação antes/depois.")

    if not sintomas.empty:
        fortes = sintomas[pd.to_numeric(sintomas["intensidade"], errors="coerce").fillna(0) >= 7]
        partes.append(f"Foram registrados {len(sintomas)} sintoma(s) após o início; {len(fortes)} com intensidade alta.")
    else:
        partes.append("Não há sintomas registrados após o início no período analisado.")

    eventos_rel = eventos[eventos["tipo_evento"].isin(["Efeito adverso", "Suspenso", "Substituido", "Pausado", "Dose não tomada"])] if not eventos.empty else eventos
    if not eventos_rel.empty:
        partes.append(f"Há {len(eventos_rel)} evento(s) relevante(s) de tolerância/continuidade. Levar para a consulta.")
    else:
        partes.append("Não há eventos relevantes de tolerância registrados no período.")

    partes.append("A leitura é temporal e organizacional: não prova causa e efeito. Use como apoio para conversa com o profissional.")

    return {
        "medicamento": med,
        "texto": "\n".join(partes),
        "exames": exames,
        "sintomas": sintomas,
        "eventos": eventos,
        "doses": doses,
        "bio_comp": bio_comp,
        "aderencia": ader,
    }


def gerar_perguntas_tratamento(resultado):
    perguntas = []
    med = resultado.get("medicamento")

    if med is not None:
        perguntas.append(f"A evolução observada é compatível com o esperado para {med['nome']}?")

    exames = resultado.get("exames")
    sintomas = resultado.get("sintomas")
    eventos = resultado.get("eventos")
    ader = resultado.get("aderencia", {})

    if exames is not None and not exames.empty:
        perguntas.append("Quais mudanças nos exames são relevantes e quais podem ser apenas variação normal?")
        perguntas.append("Preciso repetir algum exame para confirmar tendência?")

    if sintomas is not None and not sintomas.empty:
        perguntas.append("Os sintomas registrados após o início podem ter relação com o tratamento?")
        perguntas.append("Quais sintomas exigem pausa, contato ou retorno antecipado?")

    if eventos is not None and not eventos.empty:
        perguntas.append("Os eventos de tolerância indicam necessidade de ajuste, troca ou acompanhamento?")

    if ader and ader.get("aderencia", 0) < 75:
        perguntas.append("Como a baixa aderência pode afetar a interpretação da evolução?")

    perguntas.append("Qual é o próximo marco: manter, ajustar, repetir exame ou retornar?")
    return perguntas


def gerar_txt_tratamento(usuario_id, medicamento_id, dias_antes=30, dias_depois=90):
    res = gerar_leitura_tratamento(usuario_id, medicamento_id, dias_antes, dias_depois)
    perguntas = gerar_perguntas_tratamento(res)

    linhas = []
    linhas.append("EVOLUÇÃO POR TRATAMENTO - SAÚDE 360")
    linhas.append("=" * 50)
    linhas.append(date.today().strftime("Gerado em: %d/%m/%Y"))
    linhas.append("")
    linhas.append("LEITURA")
    linhas.append("-" * 20)
    linhas.append(res["texto"])
    linhas.append("")
    linhas.append("PERGUNTAS PARA O PROFISSIONAL")
    linhas.append("-" * 20)
    for i, p in enumerate(perguntas, start=1):
        linhas.append(f"{i}. {p}")
    linhas.append("")

    exames = res["exames"]
    if exames is not None and not exames.empty:
        linhas.append("EXAMES COMPARADOS")
        linhas.append("-" * 20)
        for _, r in exames.iterrows():
            linhas.append(
                f"- {r['exame']}: antes {fmt_num(r.get('antes_resultado'), 2)} em {br_date(r.get('antes_data'))}; "
                f"depois {fmt_num(r.get('depois_resultado'), 2)} em {br_date(r.get('depois_data'))}; "
                f"variação {fmt_num(r.get('variacao_abs'), 2)} {r.get('unidade') or ''}; {r.get('leitura')}"
            )
        linhas.append("")

    linhas.append("Aviso: leitura temporal e organizacional; não prova causa e efeito, não diagnostica e não prescreve.")
    return "\n".join(linhas)
