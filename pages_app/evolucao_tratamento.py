import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, fmt_num
from services.evolucao_premium_service import (
    listar_medicamentos_para_evolucao,
    gerar_leitura_tratamento,
    gerar_perguntas_tratamento,
    gerar_txt_tratamento,
)


def _cor_aderencia(valor):
    try:
        valor = float(valor)
    except Exception:
        valor = 0

    if valor >= 85:
        return "aqua"
    if valor >= 60:
        return "warn"
    return "danger"


def render_evolucao_tratamento(usuario_id):
    open_panel("Evolução por tratamento", "Compare exames, sintomas, eventos e aderência em torno de um medicamento.")

    st.info(
        "Esta análise é temporal e organizacional. Ela mostra o que aconteceu antes e depois do início do tratamento, mas não prova causa e efeito."
    )

    meds = listar_medicamentos_para_evolucao(usuario_id)

    if meds.empty:
        st.warning("Nenhum medicamento cadastrado.")
        close_panel()
        return

    opcoes = {
        f"{m['nome']} | {m.get('dose') or ''} | início {br_date(m.get('data_inicio'))} | ID {m['id']}": int(m["id"])
        for _, m in meds.iterrows()
    }

    c1, c2, c3 = st.columns([2.2, 1, 1])
    with c1:
        med_label = st.selectbox("Tratamento", list(opcoes.keys()))
        med_id = opcoes[med_label]
    with c2:
        dias_antes = st.selectbox("Janela antes", [15, 30, 60, 90], index=1, format_func=lambda x: f"{x} dias")
    with c3:
        dias_depois = st.selectbox("Janela depois", [30, 60, 90, 180, 365], index=2, format_func=lambda x: f"{x} dias")

    resultado = gerar_leitura_tratamento(usuario_id, med_id, dias_antes, dias_depois)
    ader = resultado["aderencia"]

    st.divider()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        status_pill(f"{ader.get('aderencia', 0)}% aderência", _cor_aderencia(ader.get("aderencia", 0)))
    with c2:
        status_pill(f"{len(resultado['exames'])} exames", "purple")
    with c3:
        status_pill(f"{len(resultado['sintomas'])} sintomas", "warn" if len(resultado["sintomas"]) else "aqua")
    with c4:
        status_pill(f"{len(resultado['eventos'])} eventos", "warn" if len(resultado["eventos"]) else "aqua")
    with c5:
        status_pill(f"{ader.get('nao_tomadas', 0)} não tomadas", "warn" if ader.get("nao_tomadas", 0) else "aqua")

    st.subheader("Leitura do tratamento")
    st.text_area("Resumo", value=resultado["texto"], height=190)

    st.subheader("Perguntas para levar à consulta")
    perguntas = gerar_perguntas_tratamento(resultado)
    for i, p in enumerate(perguntas, start=1):
        st.write(f"**{i}.** {p}")

    tabs = st.tabs(["Exames antes/depois", "Sintomas", "Eventos", "Aderência", "Corpo", "Exportar"])

    with tabs[0]:
        st.subheader("Comparação de exames")
        exames = resultado["exames"]

        if exames.empty:
            st.info("Não há exames suficientes na janela para comparar.")
        else:
            st.dataframe(exames, width="stretch", hide_index=True)

            st.subheader("Leitura por exame")
            for _, r in exames.iterrows():
                mini_row(
                    f"{r['exame']} | {r['leitura']}",
                    f"Antes: {fmt_num(r.get('antes_resultado'), 2)} {r.get('unidade') or ''} em {br_date(r.get('antes_data'))} | "
                    f"Depois: {fmt_num(r.get('depois_resultado'), 2)} {r.get('unidade') or ''} em {br_date(r.get('depois_data'))} | "
                    f"Variação: {fmt_num(r.get('variacao_abs'), 2)} ({fmt_num(r.get('variacao_pct'), 1)}%)",
                )

    with tabs[1]:
        st.subheader("Sintomas após início")
        sintomas = resultado["sintomas"]

        if sintomas.empty:
            st.success("Nenhum sintoma registrado na janela após o início.")
        else:
            for _, r in sintomas.head(60).iterrows():
                mini_row(
                    f"{br_date(r.get('data_sintoma'))} {r.get('horario') or ''} | {r.get('sintoma') or ''} | {r.get('intensidade') or 0}/10",
                    f"Medicamento associado: {r.get('medicamento') or 'não informado'} | {r.get('observacao') or ''}",
                )

    with tabs[2]:
        st.subheader("Eventos de medicação")
        eventos = resultado["eventos"]

        if eventos.empty:
            st.success("Nenhum evento registrado na janela.")
        else:
            for _, r in eventos.head(60).iterrows():
                mini_row(
                    f"{br_date(r.get('data_evento'))} | {r.get('tipo_evento') or ''}",
                    f"{r.get('motivo') or ''} | Sintomas: {r.get('sintomas') or ''} | Conduta: {r.get('conduta') or ''}",
                )

    with tabs[3]:
        st.subheader("Aderência do tratamento")
        st.write(ader.get("leitura", ""))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status_pill(f"{ader.get('total', 0)} doses", "purple")
        with c2:
            status_pill(f"{ader.get('tomadas', 0)} tomadas", "aqua")
        with c3:
            status_pill(f"{ader.get('nao_tomadas', 0)} não tomadas", "warn" if ader.get("nao_tomadas", 0) else "aqua")
        with c4:
            status_pill(f"{ader.get('pendentes', 0)} pendentes", "warn" if ader.get("pendentes", 0) else "aqua")

        doses = resultado["doses"]
        if not doses.empty:
            with st.expander("Ver doses"):
                st.dataframe(doses, width="stretch", hide_index=True)

    with tabs[4]:
        st.subheader("Corpo e bioimpedância")
        bio = resultado["bio_comp"]

        if bio.empty:
            st.info("Sem bioimpedância suficiente na janela.")
        else:
            st.dataframe(bio, width="stretch", hide_index=True)

    with tabs[5]:
        txt = gerar_txt_tratamento(usuario_id, med_id, dias_antes, dias_depois)
        st.download_button(
            "Baixar evolução do tratamento em TXT",
            data=txt.encode("utf-8"),
            file_name="evolucao_tratamento_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Texto", value=txt, height=520)

    close_panel()
