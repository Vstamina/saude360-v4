import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import recarregar
from services.app_local_service import (
    status_app_local,
    backup_automatico_se_necessario,
    criar_backup_local,
    listar_backups,
    ler_bytes,
    salvar_config_backup,
    preparar_restauracao,
    validar_backup_zip,
    instrucoes_restauracao_manual,
    criar_arquivos_atalho_local,
    checklist_app_local,
    concluir_onboarding,
)


def _cor_status(status):
    if status == "OK":
        return "aqua"
    if status == "Atenção":
        return "warn"
    return "purple"


def render_app_local(usuario_id=None, usuario=None):
    open_panel("Aplicativo local", "Configurações para usar o Saúde 360 como produto local, sem nuvem obrigatória.")

    st.info(
        "Modelo local-first: os dados ficam neste computador, dentro da pasta data. "
        "Isso reduz custo de nuvem, mas exige backup e cuidado com o computador do usuário."
    )

    status = status_app_local()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        status_pill(f"{status['usuarios_total']} usuário(s)", "purple")
    with c2:
        status_pill(f"{status['db_mb']} MB banco", "aqua")
    with c3:
        status_pill(f"{status['docs_total']} docs", "lilac")
    with c4:
        status_pill(f"{status['backups_total']} backups", "turq")
    with c5:
        status_pill("Onboarding OK" if status["onboarding_concluido"] else "Onboarding pendente", "aqua" if status["onboarding_concluido"] else "warn")

    tabs = st.tabs(["Boas-vindas", "Backup automático", "Restaurar", "Atalhos locais", "Checklist técnico"])

    with tabs[0]:
        st.subheader("Tela de boas-vindas local")

        st.markdown(
            """
            **Bem-vindo ao Saúde 360.**

            Este sistema foi pensado para funcionar como um organizador pessoal/familiar de saúde, com dados salvos localmente.

            O que isso significa:

            - seus dados ficam neste computador;
            - documentos ficam na pasta `data/documentos`;
            - o banco fica em `data/saude360.db`;
            - você pode exportar, fazer backup e apagar cadastros;
            - o sistema não substitui avaliação médica.
            """
        )

        st.caption(f"Pasta de dados: {status['data_dir']}")
        st.caption(f"Pasta de documentos: {status['doc_dir']}")
        st.caption(f"Pasta de backups: {status['backup_dir']}")

        if st.button("Marcar boas-vindas como concluídas"):
            concluir_onboarding()
            st.success("Onboarding concluído.")
            recarregar()

    with tabs[1]:
        st.subheader("Backup automático")

        auto = st.checkbox("Ativar backup automático", value=status["backup_automatico"])
        intervalo = st.number_input("Intervalo em dias", min_value=1, max_value=30, value=int(status["backup_intervalo_dias"]))
        manter = st.number_input("Manter últimos backups", min_value=3, max_value=50, value=int(status["backup_manter_ultimos"]))

        if st.button("Salvar configuração de backup"):
            salvar_config_backup(auto, intervalo, manter)
            st.success("Configuração salva.")
            recarregar()

        st.divider()

        if st.button("Rodar verificação de backup automático agora"):
            r = backup_automatico_se_necessario()
            if r["feito"]:
                st.success(f"Backup automático criado: {r['caminho']}")
                if r.get("removidos"):
                    st.caption(f"Backups antigos removidos: {r['removidos']}")
            else:
                st.info(r["motivo"])

        if st.button("Gerar backup manual agora"):
            caminho = criar_backup_local(tipo="Manual")
            st.session_state["ultimo_backup_local"] = str(caminho)
            st.success(f"Backup criado: {caminho}")

        ultimo = st.session_state.get("ultimo_backup_local")
        if ultimo:
            st.download_button(
                "Baixar último backup",
                data=ler_bytes(ultimo),
                file_name=ultimo.split("\\")[-1].split("/")[-1],
                mime="application/zip",
            )

        st.subheader("Backups existentes")
        backups = listar_backups()
        if not backups:
            st.info("Nenhum backup encontrado.")
        else:
            df = pd.DataFrame(backups)
            st.dataframe(df, width="stretch", hide_index=True)

            opcoes = {f"{b['nome']} | {b['tamanho_mb']} MB | {b['modificado']}": b["caminho"] for b in backups}
            escolhido = st.selectbox("Selecionar backup para baixar", list(opcoes.keys()))
            caminho = opcoes[escolhido]
            st.download_button(
                "Baixar backup selecionado",
                data=ler_bytes(caminho),
                file_name=caminho.split("\\")[-1].split("/")[-1],
                mime="application/zip",
            )

    with tabs[2]:
        st.subheader("Restaurar backup")

        st.warning(
            "Por segurança, esta versão não substitui o banco enquanto o app está rodando. "
            "Ela valida e salva o backup para restauração manual segura."
        )

        arquivo = st.file_uploader("Enviar ZIP de backup para restauração", type=["zip"])

        if arquivo is not None:
            if st.button("Validar e preparar restauração"):
                rid, caminho = preparar_restauracao(arquivo)
                ok, msg = validar_backup_zip(caminho)
                if ok:
                    st.success(msg)
                    st.session_state["restore_instrucoes"] = instrucoes_restauracao_manual(caminho)
                else:
                    st.error(msg)

        if st.session_state.get("restore_instrucoes"):
            st.text_area("Instruções de restauração", value=st.session_state["restore_instrucoes"], height=360)

    with tabs[3]:
        st.subheader("Atalhos locais")

        st.info(
            "Enquanto não empacotarmos como .exe, podemos criar arquivos .bat para abrir o app e gerar backup rápido."
        )

        if st.button("Criar atalhos .bat na pasta do projeto"):
            iniciar, backup = criar_arquivos_atalho_local(".")
            st.success("Atalhos criados.")
            st.caption(f"Abrir app: {iniciar}")
            st.caption(f"Backup rápido: {backup}")

        st.markdown(
            """
            Depois disso, o usuário pode criar um atalho na área de trabalho apontando para:

            - `abrir_saude360.bat`
            - `backup_rapido_saude360.bat`

            No produto final, isso vira instalador/ícone sem terminal.
            """
        )

    with tabs[4]:
        st.subheader("Checklist técnico do app local")

        checklist = checklist_app_local()
        for item in checklist:
            status_item = item["status"]
            status_pill(status_item, _cor_status(status_item))
            mini_row(item["item"], item["descricao"])

        st.divider()

        st.subheader("Caminhos locais")
        st.code(
            f"""Banco:
{status['db_path']}

Dados:
{status['data_dir']}

Documentos:
{status['doc_dir']}

Backups:
{status['backup_dir']}

Exportações:
{status['export_dir']}"""
        )

    close_panel()
