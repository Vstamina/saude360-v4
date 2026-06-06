import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, fmt_num
from services.jornada_inteligente_service import (
    gerar_insights,
    gerar_perguntas_inteligentes,
    gerar_txt_inteligencia,
)


def _cor(prioridade):
    if prioridade == "Alta":
        return "danger"
    if prioridade == "Média":
        return "warn"
    return "aqua"


def render_jornada_inteligente(usuario_id, usuario=None):
    open_panel("Inteligência da jornada", "Leituras automáticas sobre exames, medicamentos, sintomas, pendências e contexto clínico.")

    st.info(
        "Esta área não diagnostica e não prescreve. Ela organiza sinais da jornada para ajudar você a revisar dados e preparar conversas com profissionais de saúde."
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        dias = st.selectbox("Período", [30, 60, 90, 180, 365], index=2, format_func=lambda x: f"Últimos {x} dias")
    with c2:
        foco = st.text_input("Foco da leitura", placeholder="Ex.: ferritina, pele, emagrecimento, efeitos adversos, adesão")

    resultado = gerar_insights(usuario_id, dias=dias)
    dados = resultado["dados"]
    ader = resultado["aderencia"]
    insights = resultado["insights"]
    exames_alerta = resultado["exames_alerta"]
    sint_med = resultado["sintomas_por_medicamento"]
    eventos_rel = resultado["eventos_relevantes"]

    st.divider()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        status_pill(f"{len(insights)} insights", "purple")
    with c2:
        status_pill(f"{len(exames_alerta)} exames atenção", "warn" if len(exames_alerta) else "aqua")
    with c3:
        status_pill(f"{ader['aderencia']}% aderência", "aqua" if ader["aderencia"] >= 85 else "warn" if ader["aderencia"] >= 60 else "danger")
    with c4:
        status_pill(f"{len(eventos_rel)} eventos relevantes", "danger" if len(eventos_rel) else "aqua")
    with c5:
        status_pill(f"{len(dados['pendencias'])} pendências", "warn" if len(dados["pendencias"]) else "aqua")

    st.subheader("Principais leituras")
    for i in insights:
        status_pill(i["prioridade"], _cor(i["prioridade"]))
        mini_row(f"{i['tipo']} | {i['titulo']}", i["descricao"])

    st.divider()

    tabs = st.tabs(["Perguntas", "Exames", "Sintomas x medicamentos", "Eventos", "Aderência", "Exportar"])

    with tabs[0]:
        st.subheader("Perguntas inteligentes para consulta")
        perguntas = gerar_perguntas_inteligentes(resultado, foco=foco)
        for idx, p in enumerate(perguntas, start=1):
            st.write(f"**{idx}.** {p}")

    with tabs[1]:
        st.subheader("Exames em atenção")
        if exames_alerta.empty:
            st.success("Nenhum exame em atenção no período.")
        else:
            for _, r in exames_alerta.iterrows():
                mini_row(
                    f"{br_date(r.get('data_exame'))} | {r.get('nome_exame') or ''} | {r.get('leitura') or ''}",
                    f"Resultado: {fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''} | Referência: {fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)}",
                )

    with tabs[2]:
        st.subheader("Sintomas agrupados por medicamento")
        if sint_med.empty:
            st.success("Nenhum sintoma associado a medicamento no período.")
        else:
            st.dataframe(sint_med, width="stretch", hide_index=True)

    with tabs[3]:
        st.subheader("Eventos relevantes de medicação")
        if eventos_rel.empty:
            st.success("Nenhum evento relevante no período.")
        else:
            for _, r in eventos_rel.iterrows():
                mini_row(
                    f"{br_date(r.get('data_evento'))} | {r.get('tipo_evento') or ''} | {r.get('medicamento') or ''}",
                    f"{r.get('motivo') or ''} {r.get('sintomas') or ''} {r.get('conduta') or ''}",
                )

    with tabs[4]:
        st.subheader("Aderência")
        st.write(ader["leitura"])
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status_pill(f"{ader['total']} doses", "purple")
        with c2:
            status_pill(f"{ader['tomadas']} tomadas", "aqua")
        with c3:
            status_pill(f"{ader['nao_tomadas']} não tomadas", "warn" if ader["nao_tomadas"] else "aqua")
        with c4:
            status_pill(f"{ader['pendentes']} pendentes", "warn" if ader["pendentes"] else "aqua")

    with tabs[5]:
        txt = gerar_txt_inteligencia(usuario_id, dias=dias, foco=foco)
        st.download_button(
            "Baixar inteligência da jornada em TXT",
            data=txt.encode("utf-8"),
            file_name="inteligencia_jornada_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Texto", value=txt, height=500)

    close_panel()
