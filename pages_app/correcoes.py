import streamlit as st

from components.cards import open_panel, close_panel, status_pill
from core.helpers import br_date, recarregar
from services.correcoes_service import (
    listar_usuarios,
    listar_documentos_para_correcao,
    listar_exames_para_correcao,
    listar_medicamentos_para_correcao,
    listar_sintomas_para_correcao,
    listar_marcos_opcoes,
    mover_documento_para_usuario,
    atualizar_marco_documento,
    atualizar_marco_exame,
    atualizar_marco_medicamento,
    atualizar_marco_sintoma,
    excluir_exame,
    excluir_sintoma,
    gerar_resumo_correcoes,
)


def _select_item(df, label_colunas, label_vazio):
    if df.empty:
        st.info(label_vazio)
        return None

    opcoes = {}
    for _, r in df.iterrows():
        partes = []
        for c in label_colunas:
            if c in r and r[c] not in [None, ""]:
                partes.append(str(r[c]))
        label = " | ".join(partes)
        label = f"ID {r['id']} | {label}"
        opcoes[label] = int(r["id"])

    escolha = st.selectbox("Selecione", list(opcoes.keys()))
    return opcoes[escolha]


def render_correcoes(usuario_id, usuario=None):
    open_panel("Central de correcoes", "Corrija documentos, exames, sintomas e vinculos sem mexer direto no banco.")

    resumo = gerar_resumo_correcoes(usuario_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{resumo['documentos']} documentos", "turq")
        status_pill(f"{resumo['docs_sem_marco']} sem marco", "warn" if resumo["docs_sem_marco"] else "aqua")
    with c2:
        status_pill(f"{resumo['exames']} exames", "purple")
        status_pill(f"{resumo['exames_sem_marco']} sem marco", "warn" if resumo["exames_sem_marco"] else "aqua")
    with c3:
        status_pill(f"{resumo['medicamentos']} medicamentos", "lilac")
        status_pill(f"{resumo['meds_sem_marco']} sem marco", "warn" if resumo["meds_sem_marco"] else "aqua")
    with c4:
        status_pill(f"{resumo['sintomas']} sintomas", "aqua")
        status_pill(f"{resumo['sintomas_sem_marco']} sem marco", "warn" if resumo["sintomas_sem_marco"] else "aqua")

    st.info(
        "Use esta area quando algo foi lançado no paciente errado, quando um exame foi digitado errado ou quando quiser ligar um item a uma consulta/marco."
    )

    close_panel()

    tabs = st.tabs(
        [
            "Mover documento",
            "Vincular a marco",
            "Excluir exame/sintoma",
            "Visao dos itens",
        ]
    )

    with tabs[0]:
        open_panel("Mover documento para outro usuario", "Ideal para corrigir arquivo salvo no cadastro errado.")

        docs = listar_documentos_para_correcao(usuario_id)
        usuarios = listar_usuarios()

        if docs.empty:
            st.info("Nenhum documento no usuario ativo.")
        elif len(usuarios) <= 1:
            st.warning("So existe um usuario cadastrado. Cadastre outro usuario para mover documentos.")
        else:
            doc_id = _select_item(
                docs,
                ["data_documento", "tipo_documento", "titulo", "paciente_detectado", "validacao_paciente"],
                "Nenhum documento.",
            )

            usuarios_destino = {}
            for _, u in usuarios.iterrows():
                if int(u["id"]) != int(usuario_id):
                    usuarios_destino[f"{u['nome']} | ID {u['id']}"] = int(u["id"])

            destino_label = st.selectbox("Mover para qual usuario?", list(usuarios_destino.keys()))
            destino_id = usuarios_destino[destino_label]

            confirmar = st.checkbox("Confirmo que quero mover este documento para outro usuario")

            if st.button("Mover documento"):
                if not confirmar:
                    st.warning("Marque a confirmacao antes de mover.")
                else:
                    ok, msg = mover_documento_para_usuario(usuario_id, doc_id, destino_id)
                    if ok:
                        st.success(msg)
                        recarregar()
                    else:
                        st.error(msg)

        close_panel()

    with tabs[1]:
        open_panel("Vincular itens a consulta/marco", "Corrige exames, medicamentos, documentos e sintomas sem marco.")

        opcoes_marcos = listar_marcos_opcoes(usuario_id)

        if len(opcoes_marcos) <= 1:
            st.warning("Crie pelo menos um marco em Consultas e marcos para vincular itens.")
        else:
            tipo_item = st.selectbox("Tipo de item", ["Exame", "Medicamento", "Documento", "Sintoma"])
            marco_label = st.selectbox("Novo marco relacionado", list(opcoes_marcos.keys()))
            marco_id = opcoes_marcos[marco_label]

            if tipo_item == "Exame":
                df = listar_exames_para_correcao(usuario_id)
                item_id = _select_item(df, ["data_exame", "nome_exame", "resultado", "unidade", "marco_titulo"], "Nenhum exame cadastrado.")
                if item_id and st.button("Atualizar marco do exame"):
                    atualizar_marco_exame(usuario_id, item_id, marco_id)
                    st.success("Marco do exame atualizado.")
                    recarregar()

            elif tipo_item == "Medicamento":
                df = listar_medicamentos_para_correcao(usuario_id)
                item_id = _select_item(df, ["data_inicio", "nome", "dose", "status", "marco_titulo"], "Nenhum medicamento cadastrado.")
                if item_id and st.button("Atualizar marco do medicamento"):
                    atualizar_marco_medicamento(usuario_id, item_id, marco_id)
                    st.success("Marco do medicamento atualizado.")
                    recarregar()

            elif tipo_item == "Documento":
                df = listar_documentos_para_correcao(usuario_id)
                item_id = _select_item(df, ["data_documento", "tipo_documento", "titulo", "marco_titulo"], "Nenhum documento cadastrado.")
                if item_id and st.button("Atualizar marco do documento"):
                    atualizar_marco_documento(usuario_id, item_id, marco_id)
                    st.success("Marco do documento atualizado.")
                    recarregar()

            elif tipo_item == "Sintoma":
                df = listar_sintomas_para_correcao(usuario_id)
                item_id = _select_item(df, ["data_sintoma", "horario", "sintoma", "intensidade", "marco_titulo"], "Nenhum sintoma cadastrado.")
                if item_id and st.button("Atualizar marco do sintoma"):
                    atualizar_marco_sintoma(usuario_id, item_id, marco_id)
                    st.success("Marco do sintoma atualizado.")
                    recarregar()

        close_panel()

    with tabs[2]:
        open_panel("Excluir exame ou sintoma", "Use somente para lançamento errado.")

        tipo_excluir = st.selectbox("O que deseja excluir?", ["Exame", "Sintoma"])

        if tipo_excluir == "Exame":
            df = listar_exames_para_correcao(usuario_id)
            item_id = _select_item(df, ["data_exame", "nome_exame", "resultado", "unidade", "laboratorio"], "Nenhum exame cadastrado.")
            confirmar = st.checkbox("Confirmo que desejo excluir este exame")
            if item_id and st.button("Excluir exame"):
                if not confirmar:
                    st.warning("Marque a confirmação.")
                else:
                    ok, msg = excluir_exame(usuario_id, item_id)
                    if ok:
                        st.success(msg)
                        recarregar()
                    else:
                        st.error(msg)

        else:
            df = listar_sintomas_para_correcao(usuario_id)
            item_id = _select_item(df, ["data_sintoma", "horario", "sintoma", "intensidade", "medicamento"], "Nenhum sintoma cadastrado.")
            confirmar = st.checkbox("Confirmo que desejo excluir este sintoma")
            if item_id and st.button("Excluir sintoma"):
                if not confirmar:
                    st.warning("Marque a confirmação.")
                else:
                    ok, msg = excluir_sintoma(usuario_id, item_id)
                    if ok:
                        st.success(msg)
                        recarregar()
                    else:
                        st.error(msg)

        close_panel()

    with tabs[3]:
        open_panel("Visao dos itens cadastrados", "Conferencia rapida dos dados do usuario ativo.")

        st.subheader("Documentos")
        docs = listar_documentos_para_correcao(usuario_id)
        if docs.empty:
            st.info("Sem documentos.")
        else:
            view = docs.copy()
            view["data_documento"] = view["data_documento"].apply(br_date)
            st.dataframe(
                view[["id", "data_documento", "tipo_documento", "titulo", "paciente_detectado", "validacao_paciente", "marco_titulo", "caminho_arquivo"]],
                width="stretch",
                hide_index=True,
            )

        st.subheader("Exames")
        exames = listar_exames_para_correcao(usuario_id)
        if exames.empty:
            st.info("Sem exames.")
        else:
            view = exames.copy()
            view["data_exame"] = view["data_exame"].apply(br_date)
            st.dataframe(
                view[["id", "data_exame", "nome_exame", "resultado", "unidade", "laboratorio", "marco_titulo", "observacao"]],
                width="stretch",
                hide_index=True,
            )

        st.subheader("Medicamentos")
        meds = listar_medicamentos_para_correcao(usuario_id)
        if meds.empty:
            st.info("Sem medicamentos.")
        else:
            view = meds.copy()
            view["data_inicio"] = view["data_inicio"].apply(br_date)
            st.dataframe(
                view[["id", "data_inicio", "nome", "dose", "status", "marco_titulo", "medico"]],
                width="stretch",
                hide_index=True,
            )

        st.subheader("Sintomas")
        sintomas = listar_sintomas_para_correcao(usuario_id)
        if sintomas.empty:
            st.info("Sem sintomas.")
        else:
            view = sintomas.copy()
            view["data_sintoma"] = view["data_sintoma"].apply(br_date)
            st.dataframe(
                view[["id", "data_sintoma", "horario", "sintoma", "intensidade", "medicamento", "marco_titulo", "observacao"]],
                width="stretch",
                hide_index=True,
            )

        close_panel()
