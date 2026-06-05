import plotly.graph_objects as go
import streamlit as st

from core.theme import COLORS
from core.helpers import fmt_num


def classificar_exame(resultado, ref_min, ref_max):
    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        return "Sem referencia", COLORS["muted"], "Sem faixa de referencia cadastrada."

    if ref_min == 0 and ref_max == 0:
        return "Sem referencia", COLORS["muted"], "Cadastre a faixa de referencia para gerar leitura."

    if ref_max <= ref_min:
        return "Sem referencia", COLORS["muted"], "Faixa de referencia invalida."

    if resultado < ref_min:
        return "Abaixo da faixa", COLORS["danger"], "Resultado abaixo da faixa de referencia cadastrada."

    if resultado > ref_max:
        return "Acima da faixa", COLORS["purple"], "Resultado acima da faixa de referencia cadastrada."

    pos = (resultado - ref_min) / (ref_max - ref_min)

    if pos <= 0.15:
        return "Na faixa, perto do minimo", COLORS["warning"], "Dentro da faixa, mas proximo do limite inferior."

    if pos >= 0.85:
        return "Na faixa, perto do maximo", COLORS["warning"], "Dentro da faixa, mas proximo do limite superior."

    return "Na faixa esperada", COLORS["aqua"], "Resultado dentro da faixa de referencia cadastrada."


def fig_medidor_exame(nome, resultado, ref_min, ref_max, unidade):
    """
    Medidor limpo: o texto principal fica fora do grafico.
    O grafico vira apoio visual, nao a explicacao principal.
    """
    status, cor, leitura = classificar_exame(resultado, ref_min, ref_max)

    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        resultado = 0.0
        ref_min = 0.0
        ref_max = 1.0

    if ref_max <= ref_min:
        minimo = 0
        maximo = max(1, resultado * 1.5)
        ref_min = minimo
        ref_max = maximo
    else:
        margem = (ref_max - ref_min) * 0.35
        minimo = max(0, ref_min - margem)
        maximo = ref_max + margem

    tickvals = [minimo, ref_min, ref_max, maximo]
    ticktext = ["baixo", f"{ref_min:g}", f"{ref_max:g}", "alto"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=resultado,
            gauge={
                "shape": "angular",
                "axis": {
                    "range": [minimo, maximo],
                    "tickmode": "array",
                    "tickvals": tickvals,
                    "ticktext": ticktext,
                    "tickwidth": 1,
                    "tickcolor": "rgba(96,112,134,0.45)",
                    "tickfont": {"size": 10, "color": COLORS["muted"]},
                },
                "bar": {"color": cor, "thickness": 0.20},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [minimo, ref_min], "color": "rgba(232,93,117,0.16)"},
                    {"range": [ref_min, ref_max], "color": "rgba(111,211,192,0.30)"},
                    {"range": [ref_max, maximo], "color": "rgba(110,76,207,0.18)"},
                ],
                "threshold": {
                    "line": {"color": "#223248", "width": 7},
                    "thickness": 0.98,
                    "value": resultado,
                },
            },
        )
    )

    fig.add_annotation(
        x=0.18,
        y=0.02,
        xref="paper",
        yref="paper",
        text="baixo",
        showarrow=False,
        font=dict(size=10, color=COLORS["danger"]),
    )

    fig.add_annotation(
        x=0.50,
        y=0.02,
        xref="paper",
        yref="paper",
        text="faixa esperada",
        showarrow=False,
        font=dict(size=10, color="#116B5B"),
    )

    fig.add_annotation(
        x=0.82,
        y=0.02,
        xref="paper",
        yref="paper",
        text="alto",
        showarrow=False,
        font=dict(size=10, color=COLORS["purple"]),
    )

    fig.update_layout(
        height=165,
        margin=dict(l=4, r=4, t=4, b=22),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["dark"]},
    )

    return fig, status, leitura


def render_card_exame(nome, resultado, ref_min, ref_max, unidade, key):
    """
    Card pensado para usuario leigo:
    1. Nome
    2. Resultado grande
    3. Status humano
    4. Referencia
    5. Medidor como apoio visual
    """
    status, cor, leitura = classificar_exame(resultado, ref_min, ref_max)

    try:
        resultado_float = float(resultado)
    except Exception:
        resultado_float = 0.0

    try:
        ref_min_float = float(ref_min)
        ref_max_float = float(ref_max)
    except Exception:
        ref_min_float = 0.0
        ref_max_float = 0.0

    unidade_txt = f" {unidade}" if unidade else ""
    resultado_txt = f"{fmt_num(resultado_float, 2)}{unidade_txt}"

    if ref_min_float == 0 and ref_max_float == 0:
        referencia_txt = "Referencia nao cadastrada"
    else:
        referencia_txt = f"Referencia: {fmt_num(ref_min_float, 2)} a {fmt_num(ref_max_float, 2)}{unidade_txt}"

    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.96);
            border: 1px solid rgba(233,238,242,0.95);
            border-radius: 22px;
            padding: 18px 18px 10px 18px;
            box-shadow: 0 12px 30px rgba(36,52,71,0.06);
            margin-bottom: 16px;">
            <div style="font-size: 18px; font-weight: 850; color: #243447; margin-bottom: 4px;">
                {nome}
            </div>
            <div style="font-size: 34px; font-weight: 900; color: #243447; line-height: 1.05; margin-bottom: 4px;">
                {resultado_txt}
            </div>
            <div style="font-size: 14px; font-weight: 800; color: {cor}; margin-bottom: 4px;">
                {status}
            </div>
            <div style="font-size: 12px; color: #607086; margin-bottom: 4px;">
                {referencia_txt}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig, _, _ = fig_medidor_exame(nome, resultado, ref_min, ref_max, unidade)
    st.plotly_chart(fig, width="stretch", key=key)
    st.caption(leitura)
