import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import recarregar
from services.privacidade_service import (
    status_privacidade_usuario,
    salvar_consentimento,
    criar_zip_exportacao_usuario,
    ler_bytes,
    desativar_usuario,
    reativar_usuario,
    excluir_dados_usuario,
    gerar_texto_termo_local,
)


def _nome_usuario(usuario):
    try:
        return usuario.get("nome", "")
    except Exception:
        try:
            return usuario["nome"]
        except Exception:
            return ""


def render_privacidade(usuario_id, usuario=None):
    nome = _nome_usuario(usuario)

    open_panel("Privacidade e dados", "Controle local dos dados, exportação, consentimento e exclusão segura.")

    st.warning(
        "Esta área lida com dados pessoais e de saúde. Exporte ou exclua com cuidado. "
        "A exclusão definitiva não deve ser feita sem backup."
    )

    status = status_privacidade_usuario(usuario_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{status['total_registros']} registros", "purple")
    with c2:
        status_pill(f"{status['tabelas']} tabelas", "lilac")
    with c3:
        status_pill(f"{status['documentos_fisicos']} arquivos físicos", "aqua" if status["documentos_fisicos"] else "warn")
    with c4:
        status_pill(f"{status['tamanho_docs_mb']} MB docs", "turq")

    st.caption(f"Banco local: {status['db_path']}")
    st.caption(f"Pasta de dados: {status['data_dir']}")
    st.caption(f"Pasta de documentos: {status['doc_dir']}")

    consent = status.get("consentimento")
    if consent:
        st.success(f"Último consentimento registrado em {consent.get('data_consentimento')} | versão {consent.get('versao_termo')}")
    else:
        st.info("Ainda não há consentimento local registrado para este cadastro.")

    tabs = st.tabs(["Termo e consentimento", "Mapa de dados", "Exportar", "Desativar", "Excluir definitivamente"])

    with tabs[0]:
        st.subheader("Termo local")
        termo = gerar_texto_termo_local()
        st.text_area("Texto do termo", value=termo, height=300)

        with st.form("form_consentimento_privacidade"):
            aceita_uso_local = st.checkbox("Entendo que os dados ficam salvos localmente neste computador.")
            aceita_documentos = st.checkbox("Entendo que documentos enviados podem conter dados sensíveis de saúde.")
            aceita_relatorios = st.checkbox("Entendo que relatórios/exportações podem conter dados sensíveis e devem ser protegidos.")
            observacao = st.text_area("Observação", placeholder="Opcional")

            if st.form_submit_button("Registrar consentimento local"):
                if not (aceita_uso_local and aceita_documentos and aceita_relatorios):
                    st.warning("Marque as três confirmações para registrar o consentimento.")
                else:
                    salvar_consentimento(
                        usuario_id=usuario_id,
                        aceita_uso_local=aceita_uso_local,
                        aceita_documentos=aceita_documentos,
                        aceita_relatorios=aceita_relatorios,
                        observacao=observacao,
                    )
                    st.success("Consentimento registrado.")
                    recarregar()

    with tabs[1]:
        st.subheader("Mapa de dados do cadastro")

        contagens = pd.DataFrame(status["contagens"])
        if contagens.empty:
            st.info("Nenhuma tabela encontrada.")
        else:
            st.dataframe(contagens, width="stretch", hide_index=True)

        st.subheader("Documentos físicos vinculados")
        docs = pd.DataFrame(status["documentos"])
        if docs.empty:
            st.info("Nenhum arquivo físico vinculado encontrado.")
        else:
            st.dataframe(docs, width="stretch", hide_index=True)

    with tabs[2]:
        st.subheader("Exportar dados do cadastro")

        st.info(
            "A exportação gera um ZIP com dados em JSON e documentos físicos vinculados, quando encontrados. "
            "Proteja esse arquivo, pois ele pode conter dados pessoais e de saúde."
        )

        if st.button("Gerar ZIP de exportação"):
            zip_path = criar_zip_exportacao_usuario(usuario_id)
            st.session_state["zip_export_privacidade"] = str(zip_path)
            st.success(f"Exportação criada: {zip_path}")

        zip_path = st.session_state.get("zip_export_privacidade")
        if zip_path:
            st.download_button(
                "Baixar exportação",
                data=ler_bytes(zip_path),
                file_name=zip_path.split("\\")[-1].split("/")[-1],
                mime="application/zip",
            )

    with tabs[3]:
        st.subheader("Desativar cadastro")

        st.info(
            "Desativar apenas remove o cadastro da lista principal de usuários ativos. "
            "Os dados continuam salvos e podem ser reativados."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Desativar cadastro atual"):
                ok, msg = desativar_usuario(usuario_id)
                if ok:
                    st.success(msg)
                    recarregar()
                else:
                    st.error(msg)

        with col2:
            if st.button("Reativar cadastro atual"):
                ok, msg = reativar_usuario(usuario_id)
                if ok:
                    st.success(msg)
                    recarregar()
                else:
                    st.error(msg)

    with tabs[4]:
        st.subheader("Excluir definitivamente")

        st.error(
            "A exclusão definitiva apaga registros do banco relacionados a este cadastro. "
            "Se você marcar a opção de excluir arquivos físicos, documentos vinculados também podem ser apagados da pasta."
        )

        st.markdown("Antes de excluir, gere uma exportação ou backup.")

        frase = f"EXCLUIR {nome}".strip()
        st.caption(f"Para confirmar, digite exatamente: {frase}")

        confirmacao = st.text_input("Confirmação")
        excluir_arquivos = st.checkbox("Também excluir arquivos físicos vinculados")
        confirmo_backup = st.checkbox("Confirmo que já gerei backup/exportação ou aceito seguir sem backup")

        if st.button("Excluir definitivamente este cadastro"):
            if confirmacao.strip() != frase:
                st.warning("A frase de confirmação não confere.")
            elif not confirmo_backup:
                st.warning("Confirme que fez backup/exportação ou que aceita seguir sem backup.")
            else:
                resultado = excluir_dados_usuario(usuario_id, excluir_arquivos=excluir_arquivos)
                if resultado["ok"]:
                    st.success(
                        f"Cadastro excluído. Arquivos físicos removidos: {resultado['arquivos_removidos']}."
                    )
                    if resultado["erros_arquivos"]:
                        st.warning(f"Alguns arquivos não puderam ser removidos: {resultado['erros_arquivos']}")
                    recarregar()
                else:
                    st.error("Não foi possível excluir.")

    close_panel()
