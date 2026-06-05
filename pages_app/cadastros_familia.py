from datetime import date
import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill
from core.helpers import data_input_br, br_date, recarregar
from services.familia_service import (
    listar_usuarios_todos,
    obter_usuario,
    atualizar_usuario,
    desativar_usuario,
    reativar_usuario,
    resumo_usuario,
    resumo_todos_usuarios,
    chave_confirmacao_exclusao,
    excluir_usuario_definitivo,
)


def _parse_data(valor):
    try:
        if not valor:
            return date(1990, 1, 1)
        return pd.to_datetime(valor).date()
    except Exception:
        return date(1990, 1, 1)


def render_cadastros_familia(usuario_id_atual=None):
    open_panel("Cadastros da família", "Administre usuários, armazenamento e exclusões com segurança.")

    resumo = resumo_todos_usuarios()

    if resumo.empty:
        st.info("Nenhum cadastro encontrado.")
        close_panel()
        return

    st.subheader("Visão geral dos cadastros")
    st.dataframe(
        resumo,
        width="stretch",
        hide_index=True,
    )

    total_docs = int(resumo["documentos"].sum()) if "documentos" in resumo.columns else 0
    total_exames = int(resumo["exames"].sum()) if "exames" in resumo.columns else 0
    total_meds = int(resumo["medicamentos"].sum()) if "medicamentos" in resumo.columns else 0
    total_mb = round(float(resumo["armazenamento_mb"].sum()), 2) if "armazenamento_mb" in resumo.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{len(resumo)} cadastro(s)", "purple")
    with c2:
        status_pill(f"{total_docs} documento(s)", "turq")
    with c3:
        status_pill(f"{total_exames} exame(s)", "aqua")
    with c4:
        status_pill(f"{total_mb} MB", "lilac")

    close_panel()

    usuarios = listar_usuarios_todos()
    opcoes = {
        f"{u['nome']} | ID {u['id']} | {'Ativo' if int(u.get('ativo') or 1) == 1 else 'Inativo'}": int(u["id"])
        for _, u in usuarios.iterrows()
    }

    tabs = st.tabs(["Editar cadastro", "Ativar / desativar", "Excluir definitivamente", "Resumo detalhado"])

    with tabs[0]:
        open_panel("Editar cadastro", "Altere nome, nascimento, sexo, altura e objetivo.")

        label = st.selectbox("Cadastro para editar", list(opcoes.keys()), key="editar_usuario_select")
        uid = opcoes[label]
        u_df = obter_usuario(uid)

        if u_df.empty:
            st.error("Usuário não encontrado.")
        else:
            u = u_df.iloc[0]

            with st.form("form_editar_usuario"):
                nome = st.text_input("Nome completo", value=u.get("nome") or "")
                data_nasc = data_input_br("Data de nascimento", _parse_data(u.get("data_nascimento")), key="edit_user_nasc")
                sexo_atual = u.get("sexo") or "Nao informado"
                sexos = ["Nao informado", "Feminino", "Masculino"]
                if sexo_atual not in sexos:
                    sexos.append(sexo_atual)

                sexo = st.selectbox("Sexo para referências laboratoriais", sexos, index=sexos.index(sexo_atual))
                altura = st.number_input("Altura em cm", min_value=0.0, max_value=250.0, value=float(u.get("altura_cm") or 0))
                objetivo = st.text_area("Objetivo de acompanhamento", value=u.get("objetivo") or "")

                if st.form_submit_button("Salvar alterações"):
                    if not nome.strip():
                        st.warning("Informe o nome.")
                    else:
                        atualizar_usuario(uid, nome, data_nasc, sexo, altura, objetivo)
                        st.success("Cadastro atualizado.")
                        recarregar()

        close_panel()

    with tabs[1]:
        open_panel("Ativar / desativar cadastro", "Desativar esconde da seleção principal, mas preserva todos os dados.")

        label = st.selectbox("Cadastro", list(opcoes.keys()), key="ativar_desativar_select")
        uid = opcoes[label]
        u_df = obter_usuario(uid)

        if u_df.empty:
            st.error("Usuário não encontrado.")
        else:
            u = u_df.iloc[0]
            ativo = int(u.get("ativo") or 1) == 1

            st.write(f"**Cadastro:** {u['nome']}")
            st.write(f"**Status:** {'Ativo' if ativo else 'Inativo'}")

            if ativo:
                confirmar = st.checkbox("Confirmo que quero desativar este cadastro")
                if st.button("Desativar cadastro"):
                    if not confirmar:
                        st.warning("Marque a confirmação.")
                    else:
                        desativar_usuario(uid)
                        st.success("Cadastro desativado. Os dados foram preservados.")
                        recarregar()
            else:
                if st.button("Reativar cadastro"):
                    reativar_usuario(uid)
                    st.success("Cadastro reativado.")
                    recarregar()

        close_panel()

    with tabs[2]:
        open_panel("Excluir cadastro definitivamente", "Ação irreversível. Apaga dados e, se escolhido, arquivos físicos.")

        label = st.selectbox("Cadastro para excluir", list(opcoes.keys()), key="excluir_usuario_select")
        uid = opcoes[label]
        u_df = obter_usuario(uid)

        if u_df.empty:
            st.error("Usuário não encontrado.")
        else:
            u = u_df.iloc[0]
            r = resumo_usuario(uid)

            st.error(
                "Atenção: esta ação é definitiva. Ela pode apagar exames, medicamentos, sintomas, documentos, marcos, atividades, doses e arquivos físicos deste cadastro."
            )

            st.write(f"**Cadastro:** {u['nome']}")
            st.write(
                f"Dados: {r['documentos']} documento(s), {r['exames']} exame(s), {r['medicamentos']} medicamento(s), "
                f"{r['sintomas']} sintoma(s), {r['marcos']} marco(s), {r['atividades']} atividade(s)."
            )
            st.write(f"Arquivos físicos encontrados: {r['arquivos_existentes']} | Espaço usado: {r['armazenamento_mb']} MB")

            apagar_arquivos = st.checkbox("Apagar também os arquivos físicos deste cadastro", value=True)

            chave = chave_confirmacao_exclusao(u["nome"])
            st.warning(f"Para confirmar, digite exatamente: {chave}")
            digitado = st.text_input("Confirmação de exclusão")

            if st.button("Excluir cadastro definitivamente"):
                if digitado.strip().upper() != chave:
                    st.warning("Texto de confirmação incorreto. Nada foi excluído.")
                else:
                    ok, msg = excluir_usuario_definitivo(uid, apagar_arquivos=apagar_arquivos)
                    if ok:
                        st.success(msg)
                        recarregar()
                    else:
                        st.error(msg)

        close_panel()

    with tabs[3]:
        open_panel("Resumo detalhado por cadastro")

        label = st.selectbox("Cadastro para ver resumo", list(opcoes.keys()), key="resumo_usuario_select")
        uid = opcoes[label]
        u_df = obter_usuario(uid)

        if not u_df.empty:
            u = u_df.iloc[0]
            r = resumo_usuario(uid)

            st.subheader(u["nome"])
            cols = st.columns(4)
            with cols[0]:
                status_pill(f"{r['documentos']} documentos", "turq")
                status_pill(f"{r['arquivos_existentes']} arquivos físicos", "aqua")
            with cols[1]:
                status_pill(f"{r['exames']} exames", "purple")
                status_pill(f"{r['medicamentos']} medicamentos", "lilac")
            with cols[2]:
                status_pill(f"{r['sintomas']} sintomas", "warn" if r["sintomas"] else "aqua")
                status_pill(f"{r['eventos']} eventos", "warn" if r["eventos"] else "aqua")
            with cols[3]:
                status_pill(f"{r['armazenamento_mb']} MB", "purple")
                status_pill(f"{r['arquivos_nao_encontrados']} arquivos não encontrados", "danger" if r["arquivos_nao_encontrados"] else "aqua")

            st.json(r)

        close_panel()
