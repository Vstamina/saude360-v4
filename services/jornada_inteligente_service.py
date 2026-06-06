from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def _data_min(dias):
    return (date.today() - timedelta(days=int(dias))).isoformat()


def _classificar_exame(resultado, ref_min, ref_max):
    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        return "Sem referência"

    if ref_min == 0 and ref_max == 0:
        return "Sem referência"
    if resultado < ref_min:
        return "Abaixo"
    if resultado > ref_max:
        return "Acima"

    largura = max(ref_max - ref_min, 0.0001)
    margem = largura * 0.12

    if resultado <= ref_min + margem:
        return "Limite inferior"
    if resultado >= ref_max - margem:
        return "Limite superior"
    return "Dentro"


def dados_jornada(usuario_id, dias=90):
    data_min = _data_min(dias)

    exames = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame >= ?
        ORDER BY data_exame DESC, nome_exame
        """,
        (usuario_id, data_min),
    )

    medicamentos = consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND (
                data_inicio >= ?
                OR COALESCE(status, 'Ativo') = 'Ativo'
              )
        ORDER BY data_inicio DESC, nome
        """,
        (usuario_id, data_min),
    )

    eventos = consultar_df(
        """
        SELECT e.*, m.nome AS medicamento
        FROM eventos_medicacao e
        LEFT JOIN medicamentos m ON m.id = e.medicamento_id
        WHERE e.usuario_id = ?
          AND e.data_evento >= ?
        ORDER BY e.data_evento DESC, e.id DESC
        """,
        (usuario_id, data_min),
    )

    sintomas = consultar_df(
        """
        SELECT s.*, m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma >= ?
        ORDER BY s.data_sintoma DESC, COALESCE(s.horario, '') DESC, s.id DESC
        """,
        (usuario_id, data_min),
    )

    doses = consultar_df(
        """
        SELECT d.*, m.nome AS medicamento, m.dose
        FROM doses d
        LEFT JOIN medicamentos m ON m.id = d.medicamento_id
        WHERE d.usuario_id = ?
          AND d.data_prevista >= ?
        ORDER BY d.data_prevista DESC, d.horario_previsto DESC
        """,
        (usuario_id, data_min),
    )

    pendencias = consultar_df(
        """
        SELECT p.*, m.nome AS medicamento
        FROM pendencias_cuidado p
        LEFT JOIN medicamentos m ON m.id = p.medicamento_id
        WHERE p.usuario_id = ?
          AND p.status = 'Aberta'
        ORDER BY CASE p.prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
                 p.data_criacao DESC
        """,
        (usuario_id,),
    )

    marcos = consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco >= ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    return {
        "data_min": data_min,
        "exames": exames,
        "medicamentos": medicamentos,
        "eventos": eventos,
        "sintomas": sintomas,
        "doses": doses,
        "pendencias": pendencias,
        "marcos": marcos,
    }


def exames_em_atencao(exames):
    if exames.empty:
        return exames

    df = exames.copy()
    df["leitura"] = df.apply(
        lambda r: _classificar_exame(r.get("resultado"), r.get("referencia_min"), r.get("referencia_max")),
        axis=1,
    )
    return df[df["leitura"] != "Dentro"]


def aderencia_resumo(doses):
    if doses.empty:
        return {
            "total": 0,
            "tomadas": 0,
            "nao_tomadas": 0,
            "pendentes": 0,
            "aderencia": 0,
            "leitura": "Sem doses registradas no período."
        }

    total_validas = doses[~doses["status"].isin(["Cancelada", "Pausada"])]
    total = len(total_validas)
    tomadas = len(total_validas[total_validas["status"] == "Tomado"])
    nao_tomadas = len(total_validas[total_validas["status"].isin(["Não tomado", "Nao tomado", "Esquecido"])])
    pendentes = len(total_validas[total_validas["status"] == "Pendente"])

    aderencia = round((tomadas / total) * 100, 1) if total else 0

    if total == 0:
        leitura = "Sem doses válidas para calcular aderência."
    elif aderencia >= 85:
        leitura = "Boa regularidade de tomada no período."
    elif aderencia >= 60:
        leitura = "Aderência intermediária. Vale observar esquecimentos, horários e disponibilidade da medicação."
    else:
        leitura = "Aderência baixa no período. Pode haver impacto na continuidade do tratamento."

    return {
        "total": total,
        "tomadas": tomadas,
        "nao_tomadas": nao_tomadas,
        "pendentes": pendentes,
        "aderencia": aderencia,
        "leitura": leitura,
    }


def sintomas_por_medicamento(sintomas):
    if sintomas.empty:
        return pd.DataFrame(columns=["medicamento", "total", "media_intensidade", "sintomas"])

    df = sintomas.copy()
    df["medicamento"] = df["medicamento"].fillna("Sem medicamento associado")
    df["intensidade"] = pd.to_numeric(df["intensidade"], errors="coerce").fillna(0)

    agrupado = (
        df.groupby("medicamento")
        .agg(
            total=("id", "count"),
            media_intensidade=("intensidade", "mean"),
            sintomas=("sintoma", lambda x: ", ".join(sorted(set([str(v) for v in x if str(v).strip()]))[:6])),
        )
        .reset_index()
        .sort_values(["total", "media_intensidade"], ascending=[False, False])
    )
    agrupado["media_intensidade"] = agrupado["media_intensidade"].round(1)
    return agrupado


def eventos_relevantes(eventos):
    if eventos.empty:
        return eventos

    tipos = ["Efeito adverso", "Suspenso", "Substituido", "Pausado", "Dose não tomada"]
    return eventos[eventos["tipo_evento"].isin(tipos)]


def gerar_insights(usuario_id, dias=90):
    dados = dados_jornada(usuario_id, dias=dias)

    exames = dados["exames"]
    medicamentos = dados["medicamentos"]
    eventos = dados["eventos"]
    sintomas = dados["sintomas"]
    doses = dados["doses"]
    pendencias = dados["pendencias"]
    marcos = dados["marcos"]

    exames_alerta = exames_em_atencao(exames)
    ader = aderencia_resumo(doses)
    sint_med = sintomas_por_medicamento(sintomas)
    eventos_rel = eventos_relevantes(eventos)

    insights = []

    if not pendencias.empty:
        altas = len(pendencias[pendencias["prioridade"] == "Alta"])
        if altas:
            insights.append({
                "tipo": "Pendências",
                "prioridade": "Alta",
                "titulo": f"{altas} pendência(s) de alta prioridade",
                "descricao": "Comece pelas pendências de alta prioridade antes da próxima consulta ou compra de medicação.",
            })
        else:
            insights.append({
                "tipo": "Pendências",
                "prioridade": "Média",
                "titulo": f"{len(pendencias)} pendência(s) aberta(s)",
                "descricao": "Há ações pendentes que podem influenciar a continuidade do cuidado.",
            })

    if not exames_alerta.empty:
        nomes = ", ".join(exames_alerta["nome_exame"].dropna().astype(str).head(5).tolist())
        insights.append({
            "tipo": "Exames",
            "prioridade": "Alta" if len(exames_alerta) >= 3 else "Média",
            "titulo": f"{len(exames_alerta)} exame(s) em atenção",
            "descricao": f"Exames que merecem revisão: {nomes}.",
        })

    if ader["total"] > 0 and ader["aderencia"] < 75:
        insights.append({
            "tipo": "Aderência",
            "prioridade": "Média",
            "titulo": f"Aderência de {ader['aderencia']}%",
            "descricao": ader["leitura"],
        })

    if not eventos_rel.empty:
        meds = ", ".join(eventos_rel["medicamento"].fillna("não informado").astype(str).head(5).tolist())
        insights.append({
            "tipo": "Tolerância",
            "prioridade": "Alta",
            "titulo": f"{len(eventos_rel)} evento(s) relevante(s) de medicação",
            "descricao": f"Eventos ligados a: {meds}. Levar para a consulta.",
        })

    if not sint_med.empty:
        top = sint_med.iloc[0]
        if int(top["total"]) >= 2:
            insights.append({
                "tipo": "Sintomas",
                "prioridade": "Média",
                "titulo": f"Sintomas recorrentes associados a {top['medicamento']}",
                "descricao": f"{int(top['total'])} registro(s), intensidade média {top['media_intensidade']}/10. Sintomas: {top['sintomas']}.",
            })

    if marcos.empty and (not exames.empty or not medicamentos.empty):
        insights.append({
            "tipo": "Contexto",
            "prioridade": "Baixa",
            "titulo": "Dados sem contexto clínico suficiente",
            "descricao": "Há exames ou medicamentos no período, mas poucos marcos de consulta. Vincular marcos melhora a leitura da jornada.",
        })

    if not insights:
        insights.append({
            "tipo": "Geral",
            "prioridade": "Baixa",
            "titulo": "Sem alertas importantes no período",
            "descricao": "A jornada não mostra sinais organizacionais críticos com os dados registrados.",
        })

    return {
        "dados": dados,
        "insights": insights,
        "exames_alerta": exames_alerta,
        "aderencia": ader,
        "sintomas_por_medicamento": sint_med,
        "eventos_relevantes": eventos_rel,
    }


def gerar_perguntas_inteligentes(resultado, foco=""):
    perguntas = []
    insights = resultado["insights"]
    exames_alerta = resultado["exames_alerta"]
    eventos_rel = resultado["eventos_relevantes"]
    sint_med = resultado["sintomas_por_medicamento"]
    ader = resultado["aderencia"]

    if foco:
        perguntas.append(f"Considerando meu foco em {foco}, quais dados devo acompanhar até o próximo retorno?")

    if not exames_alerta.empty:
        perguntas.append("Quais exames em atenção precisam ser repetidos, investigados ou apenas acompanhados?")
        perguntas.append("Algum resultado pode ter relação com medicamento, alimentação, peso, atividade física ou outra mudança recente?")

    if not eventos_rel.empty:
        perguntas.append("Os eventos de medicação registrados indicam necessidade de ajuste, troca, pausa ou cuidado adicional?")
        perguntas.append("Quais sinais de alerta exigem contato antes do retorno?")

    if not sint_med.empty and int(sint_med.iloc[0]["total"]) >= 2:
        perguntas.append("Os sintomas recorrentes podem estar relacionados a algum medicamento ou condição acompanhada?")

    if ader["total"] > 0 and ader["aderencia"] < 75:
        perguntas.append("Como devo proceder quando esqueço doses ou quando há falha na continuidade do tratamento?")

    perguntas.append("Quais são as prioridades até a próxima consulta?")
    perguntas.append("Quais exames, receitas ou documentos devo levar no próximo retorno?")

    return perguntas


def gerar_txt_inteligencia(usuario_id, dias=90, foco=""):
    resultado = gerar_insights(usuario_id, dias=dias)
    perguntas = gerar_perguntas_inteligentes(resultado, foco=foco)

    linhas = []
    linhas.append("INTELIGÊNCIA DA JORNADA - SAÚDE 360")
    linhas.append("=" * 48)
    linhas.append(f"Gerado em: {date.today().strftime('%d/%m/%Y')}")
    linhas.append(f"Período analisado: últimos {dias} dias")
    linhas.append("")
    linhas.append("INSIGHTS")
    linhas.append("-" * 30)

    for i in resultado["insights"]:
        linhas.append(f"- [{i['prioridade']}] {i['tipo']} | {i['titulo']}")
        linhas.append(f"  {i['descricao']}")

    linhas.append("")
    linhas.append("PERGUNTAS SUGERIDAS")
    linhas.append("-" * 30)
    for idx, p in enumerate(perguntas, start=1):
        linhas.append(f"{idx}. {p}")

    linhas.append("")
    linhas.append("Aviso: uso informativo. O sistema organiza dados e gera leituras de acompanhamento; não diagnostica, não prescreve e não substitui avaliação médica.")
    return "\n".join(linhas)
