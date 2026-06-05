from datetime import date

import streamlit as st

from components.cards import open_panel, close_panel, mini_row, status_pill
from core.helpers import data_input_br, br_date, recarregar
from services.marcos_service import (
    salvar_marco,
    listar_marcos,
    excluir_marco,
    resumo_itens_do_marco,
)


def render_marcos(usuario_id):
    open_panel("Consultas e marcos", "Registre consultas, retornos, exames solicitados, mudanças de conduta e eventos importantes.")

    with st.form("form_marco_jornada"):
        c1, c2 = st.columns(2)
        with c1:
            data_marco = data_input_br("Data do marco", date.today(), key="marco_data")
            tipo_marco = st.selectbox(
                "Tipo de marco",
                [
                    "Consulta médica",
                    "Retorno médico",
                    "Exame solicitado",
                    "Início de tratamento",
                    "Mudança de conduta",
                    "Efeito adverso importante",
                    "Pronto atendimento",
                    "Procedimento",
                    "Outro",
                ],
            )
            titulo = st.text_input("Título do marco", placeholder="Ex.: Consulta dermatologia - controle Roacutan")
            especialidade = st.text_input("Especialidade", placeholder="Ex.: Dermatologia, Endocrinologia")
        with c2:
            profissional = st.text_input("Profissional")
            local = st.text_input("Local / clínica / laboratório")
            proximo_passo = st.text_input("Próximo passo", placeholder="Ex.: retorno em 30 dias, repetir exames")

        queixas = st.text_area("Queixas principais", placeholder="Ex.: acne, queda de cabelo, cansaço, enjoo")
        motivo = st.text_area("Motivo / hipótese / objetivo", placeholder="Ex.: controle de Roacutan, investigar ferritina baixa")
        conduta = st.text_area("Conduta", placeholder="Ex.: iniciou medicamento, solicitou exames, suspendeu tratamento")
        exames_solicitados = st.text_area("Exames solicitados", placeholder="Ex.: TGO, TGP, triglicerídeos, ferritina")
        medicamentos_relacionados = st.text_area("Medicamentos relacionados", placeholder="Ex.: Roacutan, Wegovy, suplemento de ferro")
        observacao = st.text_area("Observações")

        salvar = st.form_submit_button("Salvar marco")

        if salvar:
            if not titulo.strip():
                st.warning("Informe um título para o marco.")
            else:
                salvar_marco(
                    usuario_id,
                    data_marco,
                    tipo_marco,
                    titulo,
                    especialidade,
                    profissional,
                    local,
                    queixas,
                    motivo,
                    conduta,
                    exames_solicitados,
                    medicamentos_relacionados,
                    proximo_passo,
                    observacao,
                )
                st.success("Marco salvo.")
                recarregar()

    close_panel()

    open_panel("Linha de consultas e marcos")
    marcos = listar_marcos(usuario_id)

    if marcos.empty:
        st.info("Nenhum marco registrado ainda.")
        close_panel()
        return

    for _, m in marcos.iterrows():
        st.markdown("---")
        c1, c2 = st.columns([4, 1])
        with c1:
            st.subheader(f"{br_date(m['data_marco'])} | {m['titulo']}")
            status_pill(m["tipo_marco"], "purple")
            if m.get("especialidade"):
                status_pill(m["especialidade"], "turq")
            st.caption(f"Profissional: {m.get('profissional') or ''} | Local: {m.get('local') or ''}")

            if m.get("queixas"):
                mini_row("Queixas", m["queixas"])
            if m.get("conduta"):
                mini_row("Conduta", m["conduta"])
            if m.get("exames_solicitados"):
                mini_row("Exames solicitados", m["exames_solicitados"])
            if m.get("proximo_passo"):
                mini_row("Próximo passo", m["proximo_passo"])

            exames, medicamentos, documentos, sintomas = resumo_itens_do_marco(usuario_id, int(m["id"]))
            st.caption(
                f"Itens vinculados: {len(exames)} exame(s), {len(medicamentos)} medicamento(s), {len(documentos)} documento(s), {len(sintomas)} sintoma(s)."
            )

        with c2:
            confirmar = st.checkbox("Confirmar exclusão", key=f"conf_excluir_marco_{m['id']}")
            if st.button("Excluir marco", key=f"btn_excluir_marco_{m['id']}"):
                if confirmar:
                    excluir_marco(usuario_id, int(m["id"]))
                    st.success("Marco excluído. Itens vinculados foram mantidos, mas desvinculados do marco.")
                    recarregar()
                else:
                    st.warning("Marque confirmar exclusão primeiro.")

    close_panel()
