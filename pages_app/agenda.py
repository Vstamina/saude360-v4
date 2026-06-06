from datetime import date
import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import data_input_br, br_date, recarregar
from services.agenda_service import (
    montar_agenda_inteligente,
    resumo_agenda,
    criar_cuidado_manual,
    listar_cuidados_manuais,
    concluir_cuidado,
    reabrir_cuidado,
    excluir_cuidado,
    gerar_txt_agenda,
)
from services.medicamentos_service import listar_medicamentos_ativos


def _cor_prioridade(prioridade):
    if prioridade == "Alta":
        return "danger"
    if prioridade == "Média":
        return "warn"
    return "aqua"


def render_agenda(usuario_id):
    open_panel("Agenda inteligente de cuidado", "Veja o que vem pela frente: doses, retornos, receitas, estoque, pendências e cuidados manuais.")

    resumo = resumo_agenda(usuario_id)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        status_pill(f"{resumo['total']} itens", "purple")
    with c2:
        status_pill(f"{resumo['hoje']} hoje", "warn" if resumo["hoje"] else "aqua")
    with c3:
        status_pill(f"{resumo['semana']} em 7 dias", "warn" if resumo["semana"] else "aqua")
    with c4:
        status_pill(f"{resumo['alta']} alta prioridade", "danger" if resumo["alta"] else "aqua")
    with c5:
        status_pill(f"{resumo['pendencias']} pendências/continuidade", "warn" if resumo["pendencias"] else "aqua")

    st.info(resumo["leitura"])

    tabs = st.tabs(["Agenda", "Adicionar cuidado", "Cuidados manuais", "Exportar"])

    with tabs[0]:
        df = montar_agenda_inteligente(usuario_id)

        if df.empty:
            st.success("Nenhum cuidado futuro ou pendência relevante no momento.")
        else:
            filtro = st.selectbox(
                "Filtrar",
                ["Todos", "Hoje", "Próximos 7 dias", "Alta prioridade", "Medicação", "Estoque/Receita", "Pendências"],
            )

            hoje = date.today()
            if filtro != "Todos":
                df2 = df.copy()
                datas = pd.to_datetime(df2["data"], errors="coerce").dt.date

                if filtro == "Hoje":
                    df = df2[datas == hoje]
                elif filtro == "Próximos 7 dias":
                    df = df2[(datas >= hoje) & (datas <= pd.to_datetime(hoje).date().replace(day=hoje.day) + pd.Timedelta(days=7).to_pytimedelta())]
                elif filtro == "Alta prioridade":
                    df = df2[df2["prioridade"] == "Alta"]
                elif filtro == "Medicação":
                    df = df2[df2["tipo"].fillna("").str.contains("Medicação", case=False)]
                elif filtro == "Estoque/Receita":
                    df = df2[df2["tipo"].fillna("").str.contains("Estoque|Receita", case=False, regex=True)]
                elif filtro == "Pendências":
                    df = df2[df2["origem"].fillna("").str.contains("Pendência|Continuidade", case=False, regex=True)]

            if df.empty:
                st.info("Nenhum item para esse filtro.")
            else:
                for _, r in df.iterrows():
                    st.markdown("---")
                    c1, c2, c3 = st.columns([1, 1.2, 3])
                    with c1:
                        status_pill(r.get("prioridade") or "Sem prioridade", _cor_prioridade(r.get("prioridade")))
                        st.write(f"**{br_date(r.get('data'))}**")
                        if r.get("horario"):
                            st.caption(r.get("horario"))
                    with c2:
                        st.write(f"**{r.get('tipo') or ''}**")
                        st.caption(r.get("origem") or "")
                    with c3:
                        st.write(f"**{r.get('titulo') or ''}**")
                        if r.get("observacao"):
                            st.caption(r.get("observacao"))

    with tabs[1]:
        open_panel("Adicionar cuidado manual")

        meds = listar_medicamentos_ativos(usuario_id)
        opcoes_meds = {"Sem medicamento vinculado": None}
        if not meds.empty:
            for _, m in meds.iterrows():
                opcoes_meds[f"{m['nome']} | {m.get('dose') or ''} | ID {m['id']}"] = int(m["id"])

        with st.form("form_cuidado_manual"):
            c1, c2, c3 = st.columns(3)
            with c1:
                data_cuidado = data_input_br("Data do cuidado", date.today(), key="agenda_manual_data")
                tipo = st.selectbox(
                    "Tipo",
                    [
                        "Retorno médico",
                        "Repetir exame",
                        "Comprar medicamento",
                        "Pedir receita",
                        "Enviar mensagem ao médico",
                        "Levar documento",
                        "Outro",
                    ],
                )
            with c2:
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], index=1)
                med_label = st.selectbox("Medicamento vinculado", list(opcoes_meds.keys()))
                medicamento_id = opcoes_meds[med_label]
            with c3:
                exame_nome = st.text_input("Exame relacionado", placeholder="Ex.: Ferritina, Glicose, TGO/TGP")

            titulo = st.text_input("Título", placeholder="Ex.: pedir nova receita do Wegovy")
            observacao = st.text_area("Observação", placeholder="Ex.: levar último exame, perguntar sobre dose, comprar antes de acabar")

            if st.form_submit_button("Salvar cuidado na agenda"):
                if not titulo.strip():
                    st.warning("Informe um título.")
                else:
                    criar_cuidado_manual(
                        usuario_id=usuario_id,
                        data_cuidado=data_cuidado,
                        tipo=tipo,
                        titulo=titulo,
                        prioridade=prioridade,
                        origem="Manual",
                        medicamento_id=medicamento_id,
                        exame_nome=exame_nome,
                        observacao=observacao,
                    )
                    st.success("Cuidado adicionado à agenda.")
                    recarregar()

        close_panel()

    with tabs[2]:
        open_panel("Cuidados manuais cadastrados")

        incluir = st.checkbox("Mostrar concluídos")
        cuidados = listar_cuidados_manuais(usuario_id, incluir_concluidos=incluir)

        if cuidados.empty:
            st.info("Nenhum cuidado manual cadastrado.")
        else:
            for _, c in cuidados.iterrows():
                st.markdown("---")
                status_pill(c.get("prioridade") or "Sem prioridade", _cor_prioridade(c.get("prioridade")))
                st.write(f"**{br_date(c.get('data_cuidado'))} | {c.get('tipo') or ''} | {c.get('titulo') or ''}**")
                st.caption(f"Status: {c.get('status') or ''} | Origem: {c.get('origem') or ''}")
                if c.get("medicamento"):
                    st.caption(f"Medicamento: {c.get('medicamento')}")
                if c.get("exame_nome"):
                    st.caption(f"Exame: {c.get('exame_nome')}")
                if c.get("observacao"):
                    st.caption(c.get("observacao"))

                col1, col2, col3 = st.columns(3)
                with col1:
                    if c.get("status") != "Concluído":
                        if st.button("Concluir", key=f"conc_cuidado_{c['id']}"):
                            concluir_cuidado(usuario_id, int(c["id"]))
                            st.success("Cuidado concluído.")
                            recarregar()
                    else:
                        if st.button("Reabrir", key=f"reabrir_cuidado_{c['id']}"):
                            reabrir_cuidado(usuario_id, int(c["id"]))
                            st.success("Cuidado reaberto.")
                            recarregar()
                with col2:
                    if st.button("Excluir", key=f"excluir_cuidado_{c['id']}"):
                        excluir_cuidado(usuario_id, int(c["id"]))
                        st.success("Cuidado excluído.")
                        recarregar()

        close_panel()

    with tabs[3]:
        open_panel("Exportar agenda")

        txt = gerar_txt_agenda(usuario_id)
        st.download_button(
            "Baixar agenda em TXT",
            data=txt.encode("utf-8"),
            file_name="agenda_inteligente_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Prévia"):
            st.text_area("Agenda", value=txt, height=500)

        close_panel()

    close_panel()
