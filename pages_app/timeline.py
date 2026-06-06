import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date
from services.timeline_premium_service import montar_timeline, resumo_timeline, gerar_txt_timeline


def _cor_prioridade(prioridade):
    if prioridade == "Alta":
        return "danger"
    if prioridade == "Média":
        return "warn"
    return "aqua"


def render_timeline(usuario_id):
    open_panel("Linha do tempo clínica", "A história organizada da saúde: consultas, exames, medicamentos, sintomas, documentos e pendências.")

    c1, c2, c3 = st.columns([1, 1.4, 1.4])

    with c1:
        dias = st.selectbox(
            "Período",
            [30, 90, 180, 365, 9999],
            index=3,
            format_func=lambda x: "Todos os registros" if x == 9999 else f"Últimos {x} dias",
        )

    tipos_disponiveis = [
        "Marco clínico",
        "Medicamento",
        "Evento de medicação",
        "Exame",
        "Sintoma",
        "Documento",
        "Pendência",
        "Corpo",
    ]

    with c2:
        tipos = st.multiselect("Filtrar por tipo", tipos_disponiveis)

    with c3:
        prioridades = st.multiselect("Filtrar por prioridade", ["Alta", "Média", "Baixa"])

    resumo = resumo_timeline(usuario_id, dias=dias)
    df = montar_timeline(usuario_id, dias=dias, tipos=tipos, prioridades=prioridades)

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{len(df)} evento(s)", "purple")
    with c2:
        status_pill(f"{resumo['alta']} alta prioridade", "danger" if resumo["alta"] else "aqua")
    with c3:
        status_pill(f"{resumo['media']} média prioridade", "warn" if resumo["media"] else "aqua")
    with c4:
        status_pill(f"{resumo['tipos']} tipos", "lilac")

    st.info(resumo["leitura"])

    tabs = st.tabs(["Linha do tempo", "Tabela", "Exportar"])

    with tabs[0]:
        if df.empty:
            st.success("Nenhum evento encontrado para os filtros escolhidos.")
        else:
            data_atual = None
            for _, r in df.iterrows():
                data = r.get("data")
                if data != data_atual:
                    data_atual = data
                    st.markdown(f"### {br_date(data)}")

                st.markdown("---")
                c1, c2, c3 = st.columns([1, 1.2, 4])

                with c1:
                    status_pill(r.get("prioridade") or "Baixa", _cor_prioridade(r.get("prioridade")))
                    if r.get("horario"):
                        st.caption(r.get("horario"))

                with c2:
                    st.write(f"**{r.get('tipo') or ''}**")
                    st.caption(r.get("subtipo") or "")

                with c3:
                    st.write(f"**{r.get('titulo') or ''}**")
                    if r.get("descricao"):
                        st.caption(r.get("descricao"))
                    st.caption(f"Origem: {r.get('origem') or ''} | ID: {r.get('referencia_id') or ''}")

    with tabs[1]:
        if df.empty:
            st.info("Sem dados.")
        else:
            st.dataframe(
                df.drop(columns=[c for c in ["data_dt", "prioridade_ordem"] if c in df.columns]),
                width="stretch",
                hide_index=True,
            )

    with tabs[2]:
        txt = gerar_txt_timeline(usuario_id, dias=dias)
        st.download_button(
            "Baixar linha do tempo em TXT",
            data=txt.encode("utf-8"),
            file_name="linha_tempo_clinica_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Linha do tempo", value=txt, height=520)

    close_panel()
