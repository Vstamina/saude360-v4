from datetime import date

import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, br_date, recarregar
from services.documentos_service import salvar_documento, listar_documentos, excluir_documento
from services.marcos_service import listar_marcos_opcoes


def render_documentos(usuario_id):
    open_panel("Repositorio de documentos de saude", "Receitas, exames, notas de consulta, notas de farmacia e relatorios")

    with st.form("form_docs_v4"):
        c1, c2 = st.columns(2)
        with c1:
            tipo_doc = st.selectbox(
                "Tipo de documento",
                ["Receita medica", "Exame", "Nota de consulta", "Nota de farmacia", "Atestado", "Relatorio medico", "Imagem", "Outro"],
            )
            data_doc = data_input_br("Data do documento", date.today(), key="doc_data")
            titulo = st.text_input("Titulo", placeholder="Ex.: Receita Dra. Melissa - Neural")
        with c2:
            profissional = st.text_input("Profissional")
            instituicao = st.text_input("Instituicao / farmacia / laboratorio")
            relacionado_a = st.text_input("Relacionado a", placeholder="Ex.: Neural, Ferritina, consulta endocrino")

        opcoes_marcos = listar_marcos_opcoes(usuario_id)
        marco_label = st.selectbox("Relacionado a qual consulta/marco?", list(opcoes_marcos.keys()))
        marco_id = opcoes_marcos[marco_label]

        arquivo = st.file_uploader("Arquivo", type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "docx"])
        obs_doc = st.text_area("Observacao")

        if st.form_submit_button("Salvar documento"):
            if not titulo.strip():
                st.warning("Informe um titulo.")
            else:
                salvar_documento(usuario_id, tipo_doc, data_doc, titulo, profissional, instituicao, arquivo, relacionado_a, obs_doc, marco_id=marco_id)
                st.success("Documento salvo.")
                recarregar()

    close_panel()

    open_panel("Documentos salvos")
    docs = listar_documentos(usuario_id)

    if docs.empty:
        st.info("Nenhum documento salvo.")
    else:
        view = docs.copy()
        view["data_documento"] = view["data_documento"].apply(br_date)
        if "data_marco" in view.columns:
            view["data_marco"] = view["data_marco"].apply(br_date)
        st.dataframe(
            view[["id", "data_documento", "tipo_documento", "titulo", "profissional", "instituicao", "relacionado_a", "marco_titulo", "paciente_detectado", "validacao_paciente", "caminho_arquivo", "observacao"]],
            width="stretch",
            hide_index=True,
        )

        st.subheader("Excluir documento")
        opcoes = {f"ID {r['id']} | {r['data_documento']} | {r['titulo']}": int(r["id"]) for _, r in docs.iterrows()}
        doc_label = st.selectbox("Documento para excluir", list(opcoes.keys()))
        doc_id = opcoes[doc_label]
        apagar_arquivo = st.checkbox("Apagar também o arquivo físico salvo na pasta data/documentos", value=True)
        confirmar = st.checkbox("Confirmo que desejo excluir este documento")

        if st.button("Excluir documento selecionado"):
            if not confirmar:
                st.warning("Marque a confirmação antes de excluir.")
            else:
                ok, msg = excluir_documento(usuario_id, doc_id, apagar_arquivo=apagar_arquivo)
                if ok:
                    st.success(msg)
                    recarregar()
                else:
                    st.error(msg)

    close_panel()
