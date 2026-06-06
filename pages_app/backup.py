import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill
from core.helpers import recarregar
from services.backup_service import (
    status_armazenamento,
    criar_backup_zip,
    ler_backup_bytes,
    listar_backups_locais,
    excluir_backup_local,
)


def render_backup():
    open_panel("Backup e segurança", "Salve uma cópia do banco e dos documentos antes de continuar evoluindo o app.")

    st.info(
        "Antes de testar ou aplicar novos patches, gere um backup. Ele guarda o banco data/saude360.db e a pasta data/documentos em um ZIP."
    )

    status = status_armazenamento()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{status['db_mb']} MB banco", "purple")
        status_pill("Banco OK" if status["db_existe"] else "Banco ausente", "aqua" if status["db_existe"] else "danger")
    with c2:
        status_pill(f"{status['documentos_ativos_banco']} docs ativos", "turq")
        status_pill(f"{status['documentos_excluidos_banco']} docs excluídos", "warn" if status["documentos_excluidos_banco"] else "aqua")
    with c3:
        status_pill(f"{status['documentos_mb']} MB documentos", "lilac")
        status_pill(f"{status['documentos_arquivos']} arquivos", "aqua")
    with c4:
        status_pill(f"{status['arquivos_fisicos_encontrados']} encontrados", "aqua")
        status_pill(f"{status['arquivos_fisicos_ausentes']} ausentes", "danger" if status["arquivos_fisicos_ausentes"] else "aqua")

    if status["arquivos_fisicos_ausentes"] > 0:
        st.warning(
            "Há registros no banco apontando para arquivos físicos que não foram encontrados. Isso pode acontecer se um arquivo foi apagado manualmente da pasta."
        )

    st.divider()

    if st.button("Gerar backup agora"):
        caminho = criar_backup_zip()
        st.session_state["ultimo_backup_path"] = str(caminho)
        st.success(f"Backup gerado: {caminho}")

    ultimo = st.session_state.get("ultimo_backup_path")

    if ultimo:
        dados = ler_backup_bytes(ultimo)
        st.download_button(
            label="Baixar último backup gerado",
            data=dados,
            file_name=ultimo.split("\\")[-1].split("/")[-1],
            mime="application/zip",
        )

    close_panel()

    open_panel("Backups locais", "Backups já gerados dentro da pasta data/backups")

    backups = listar_backups_locais()

    if not backups:
        st.info("Nenhum backup local encontrado.")
    else:
        df = pd.DataFrame(backups)
        st.dataframe(df, width="stretch", hide_index=True)

        opcoes = {f"{b['nome']} | {b['tamanho_mb']} MB | {b['modificado']}": b["caminho"] for b in backups}
        escolha = st.selectbox("Selecionar backup local", list(opcoes.keys()))
        caminho = opcoes[escolha]

        dados = ler_backup_bytes(caminho)
        st.download_button(
            label="Baixar backup selecionado",
            data=dados,
            file_name=caminho.split("\\")[-1].split("/")[-1],
            mime="application/zip",
        )

        confirmar = st.checkbox("Confirmo que desejo excluir este backup local")
        if st.button("Excluir backup local selecionado"):
            if not confirmar:
                st.warning("Marque a confirmação antes de excluir.")
            else:
                ok, msg = excluir_backup_local(caminho)
                if ok:
                    st.success(msg)
                    recarregar()
                else:
                    st.error(msg)

    close_panel()

    open_panel("Restauração", "Orientação segura")

    st.warning(
        "Nesta versão, a restauração ainda não é automática de propósito. Restaurar banco e documentos pode sobrescrever dados atuais. Primeiro fazemos backup; depois criamos restauração com travas."
    )

    st.write(
        "Para restaurar manualmente no futuro, será necessário fechar o app, substituir a pasta data pelo conteúdo do backup e abrir novamente. Vamos automatizar isso em uma etapa posterior com confirmação forte."
    )

    close_panel()
