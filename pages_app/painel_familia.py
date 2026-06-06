import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from services.painel_familia_service import (
    painel_familia,
    resumo_familia,
    prioridades_familia,
    gerar_txt_painel_familia,
)


def _cor_status(status):
    if status == "Atenção alta":
        return "danger"
    if status == "Atenção":
        return "warn"
    if status == "Estável com ajustes":
        return "lilac"
    return "aqua"


def _cor_prioridade(prioridade):
    if prioridade == "Alta":
        return "danger"
    if prioridade == "Média":
        return "warn"
    return "aqua"


def render_painel_familia(usuario_id=None, usuario=None):
    open_panel("Família 360", "Visão familiar de doses, pendências, exames, continuidade e prioridades.")

    resumo = resumo_familia()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        status_pill(f"{resumo['pessoas']} pessoa(s)", "purple")
    with c2:
        status_pill(f"{resumo['atencao_alta']} atenção alta", "danger" if resumo["atencao_alta"] else "aqua")
    with c3:
        status_pill(f"{resumo['pendencias']} pendências", "warn" if resumo["pendencias"] else "aqua")
    with c4:
        status_pill(f"{resumo['doses_pendentes']} doses hoje", "warn" if resumo["doses_pendentes"] else "aqua")
    with c5:
        status_pill(f"{resumo['exames']} exames atenção", "warn" if resumo["exames"] else "aqua")
    with c6:
        status_pill(f"{resumo['continuidade']} continuidade", "warn" if resumo["continuidade"] else "aqua")

    st.info(resumo["leitura"])

    tabs = st.tabs(["Prioridades", "Resumo por pessoa", "Tabela técnica", "Exportar"])

    with tabs[0]:
        st.subheader("Prioridades familiares")
        itens = prioridades_familia()

        if not itens:
            st.success("Nenhuma prioridade familiar relevante no momento.")
        else:
            for p in itens:
                st.markdown("---")
                status_pill(p["prioridade"], _cor_prioridade(p["prioridade"]))
                mini_row(
                    f"{p['pessoa']} | {p['tipo']} | {p['titulo']}",
                    p["descricao"],
                )

    with tabs[1]:
        st.subheader("Resumo por pessoa")
        df = painel_familia()

        if df.empty:
            st.info("Nenhum cadastro ativo encontrado.")
        else:
            for _, r in df.iterrows():
                st.markdown("---")
                c1, c2, c3 = st.columns([1.4, 1.1, 2.4])

                with c1:
                    st.write(f"**{r['nome']}**")
                    status_pill(r["status"], _cor_status(r["status"]))
                    st.caption(f"Score familiar: {r['score']}/100")

                with c2:
                    status_pill(f"{r['medicamentos_ativos']} meds", "purple")
                    status_pill(f"{r['doses_pendentes_hoje']} doses pendentes", "warn" if r["doses_pendentes_hoje"] else "aqua")
                    status_pill(f"{r['pendencias_abertas']} pendências", "warn" if r["pendencias_abertas"] else "aqua")

                with c3:
                    if r["exames_atencao"]:
                        st.warning(f"Exames em atenção: {r['exames_atencao']} — {r['exames_atencao_nomes']}")
                    if r["estoque_alertas"] or r["receita_alertas"]:
                        st.warning(
                            f"Continuidade: {r['estoque_alertas']} estoque / {r['receita_alertas']} receita — {r['continuidade_nomes']}"
                        )
                    if r["documentos_revisar"]:
                        st.caption(f"Documentos para revisar: {r['documentos_revisar']}")
                    if r["sintomas_fortes"]:
                        st.caption(f"Sintomas fortes nos últimos 30 dias: {r['sintomas_fortes']}")
                    if r["eventos_relevantes"]:
                        st.caption(f"Eventos relevantes nos últimos 90 dias: {r['eventos_relevantes']}")

    with tabs[2]:
        st.subheader("Tabela técnica")
        incluir_inativos = st.checkbox("Incluir cadastros inativos")
        df = painel_familia(incluir_inativos=incluir_inativos)

        if df.empty:
            st.info("Sem dados.")
        else:
            st.dataframe(df, width="stretch", hide_index=True)

    with tabs[3]:
        st.subheader("Exportar painel familiar")

        txt = gerar_txt_painel_familia()
        st.download_button(
            "Baixar painel da família em TXT",
            data=txt.encode("utf-8"),
            file_name="painel_familia_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Painel da família", value=txt, height=520)

    close_panel()
