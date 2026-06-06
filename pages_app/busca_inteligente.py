import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date
from services.busca_inteligente_service import busca_global, resumo_busca, gerar_txt_busca


def render_busca_inteligente(usuario_id):
    open_panel("Busca inteligente", "Pesquise em medicamentos, exames, sintomas, documentos, marcos, eventos, pendências e corpo.")

    c1, c2 = st.columns([2, 1])
    with c1:
        termo = st.text_input(
            "O que você quer procurar?",
            placeholder="Ex.: ferritina, Wegovy, enjoo, dermato, receita, dor de cabeça..."
        )
    with c2:
        dias = st.selectbox(
            "Período",
            [30, 90, 180, 365, 9999],
            index=3,
            format_func=lambda x: "Todos os registros" if x == 9999 else f"Últimos {x} dias",
        )

    tipos = st.multiselect(
        "Filtrar por tipo",
        [
            "Medicamento",
            "Exame",
            "Sintoma",
            "Evento de medicação",
            "Marco clínico",
            "Documento",
            "Pendência",
            "Corpo",
        ],
    )

    if not termo.strip():
        st.info("Digite um termo para pesquisar.")
        st.markdown(
            """
            Exemplos úteis:

            - `ferritina`
            - `wegovy`
            - `enjoo`
            - `dermato`
            - `receita`
            - `farmácia`
            - `dor`
            - `roacutan`
            """
        )
        close_panel()
        return

    df = busca_global(usuario_id, termo, dias=dias, tipos=tipos)

    st.divider()

    status_pill(f"{len(df)} resultado(s)", "purple" if len(df) else "warn")
    st.info(resumo_busca(df, termo))

    tabs = st.tabs(["Resultados", "Tabela", "Exportar"])

    with tabs[0]:
        if df.empty:
            st.warning("Nenhum resultado encontrado. Tente outro termo ou aumente o período.")
        else:
            tipo_atual = None
            for _, r in df.iterrows():
                if r.get("tipo") != tipo_atual:
                    tipo_atual = r.get("tipo")
                    st.markdown(f"### {tipo_atual}")

                st.markdown("---")
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.write(f"**{br_date(r.get('data'))}**")
                    if r.get("status"):
                        st.caption(r.get("status"))
                with c2:
                    st.write(f"**{r.get('titulo') or ''}**")
                    if r.get("descricao"):
                        st.caption(r.get("descricao"))
                    st.caption(f"Origem: {r.get('origem')} | ID: {r.get('id')}")

    with tabs[1]:
        if df.empty:
            st.info("Sem dados.")
        else:
            st.dataframe(
                df.drop(columns=[c for c in ["data_dt"] if c in df.columns]),
                width="stretch",
                hide_index=True,
            )

    with tabs[2]:
        txt = gerar_txt_busca(df, termo)
        st.download_button(
            "Baixar resultados da busca em TXT",
            data=txt.encode("utf-8"),
            file_name="busca_inteligente_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Resultados", value=txt, height=520)

    close_panel()
