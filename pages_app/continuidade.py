from datetime import date
import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import data_input_br, br_date, fmt_num, recarregar
from services.continuidade_service import (
    listar_medicamentos_ativos_para_estoque,
    listar_documentos_receita,
    salvar_estoque,
    salvar_receita,
    painel_continuidade,
    criar_pendencias_continuidade,
)


def _status_cor(status):
    if status in ["Acabou", "Crítico", "Vencida"]:
        return "danger"
    if status in ["Atenção", "Vence em breve", "Precisa revisar"]:
        return "warn"
    if status in ["OK"]:
        return "aqua"
    return "lilac"


def render_continuidade(usuario_id):
    open_panel("Continuidade do tratamento", "Controle de estoque, receita e risco de ficar sem medicação.")

    st.info(
        "Esta área estima continuidade do tratamento com base no estoque informado, frequência cadastrada e dados de receita. "
        "É uma ferramenta de organização; confirme regras de uso, validade e compra com o profissional/farmácia."
    )

    df = painel_continuidade(usuario_id)

    if df.empty:
        st.warning("Nenhum medicamento ativo encontrado.")
    else:
        criticos = len(df[df["status_estoque"].isin(["Acabou", "Crítico"])])
        atencao = len(df[df["status_estoque"].isin(["Atenção"])])
        receitas = len(df[df["status_receita"].isin(["Vencida", "Vence em breve", "Precisa revisar"])])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            status_pill(f"{len(df)} medicamentos", "purple")
        with c2:
            status_pill(f"{criticos} críticos", "danger" if criticos else "aqua")
        with c3:
            status_pill(f"{atencao} em atenção", "warn" if atencao else "aqua")
        with c4:
            status_pill(f"{receitas} receitas revisar", "warn" if receitas else "aqua")

        if st.button("Gerar pendências automáticas de continuidade"):
            criadas = criar_pendencias_continuidade(usuario_id)
            if criadas:
                st.success(f"{criadas} pendência(s) criada(s).")
            else:
                st.info("Nenhuma nova pendência necessária ou pendências já existentes.")
            recarregar()

        st.subheader("Painel de continuidade")
        for _, r in df.iterrows():
            st.markdown("---")
            col1, col2, col3 = st.columns([1.4, 1, 1])

            with col1:
                st.write(f"**{r['nome']}**")
                st.caption(f"{r.get('dose') or ''} | {r.get('frequencia') or ''}")
                st.caption(f"Consumo estimado: {r.get('consumo_diario_estimado')} dose(s)/dia")

            with col2:
                status_pill(r["status_estoque"], _status_cor(r["status_estoque"]))
                if pd.notna(r.get("dias_restantes")) and r.get("dias_restantes") is not None:
                    st.write(f"**{int(r['dias_restantes'])} dia(s) restantes**")
                    st.caption(f"Previsão de fim: {br_date(r.get('data_prevista_fim'))}")
                else:
                    st.caption("Sem estoque cadastrado.")

            with col3:
                status_pill(r["status_receita"], _status_cor(r["status_receita"]))
                if r.get("data_validade_receita"):
                    st.caption(f"Validade estimada: {br_date(r.get('data_validade_receita'))}")
                if r.get("tipo_receita"):
                    st.caption(f"Tipo: {r.get('tipo_receita')}")
                st.caption(r.get("alerta") or "")

    close_panel()

    tabs = st.tabs(["Cadastrar estoque", "Cadastrar receita", "Tabela técnica"])

    meds = listar_medicamentos_ativos_para_estoque(usuario_id)
    docs = listar_documentos_receita(usuario_id)

    opcoes_meds = {}
    if not meds.empty:
        opcoes_meds = {f"{m['nome']} | {m.get('dose') or ''} | ID {m['id']}": int(m["id"]) for _, m in meds.iterrows()}

    opcoes_docs = {"Sem documento vinculado": None}
    if not docs.empty:
        for _, d in docs.iterrows():
            opcoes_docs[f"{br_date(d['data_documento'])} | {d['titulo']} | ID {d['id']}"] = int(d["id"])

    with tabs[0]:
        open_panel("Cadastrar estoque de medicamento")

        if not opcoes_meds:
            st.warning("Nenhum medicamento ativo para controlar.")
        else:
            with st.form("form_estoque_medicamento"):
                med_label = st.selectbox("Medicamento", list(opcoes_meds.keys()))
                med_id = opcoes_meds[med_label]

                c1, c2, c3 = st.columns(3)
                with c1:
                    data_compra = data_input_br("Data da compra/início do estoque", date.today(), key="estoque_data")
                    quantidade_total = st.number_input("Quantidade total comprada", min_value=0.0, value=30.0)
                with c2:
                    unidade_estoque = st.selectbox("Unidade", ["comprimidos", "cápsulas", "canetas", "frasco", "gotas", "sachês", "aplicações", "unidades", "outro"])
                    quantidade_por_dose = st.number_input("Quantidade usada por dose", min_value=0.01, value=1.0)
                with c3:
                    farmacia = st.text_input("Farmácia/local")
                    valor_pago = st.number_input("Valor pago", min_value=0.0, value=0.0)

                doc_label = st.selectbox("Documento/nota/receita vinculada", list(opcoes_docs.keys()))
                documento_id = opcoes_docs[doc_label]
                observacao = st.text_area("Observação", placeholder="Ex.: caixa com 30 comprimidos; caneta com X aplicações; controle aproximado.")

                if st.form_submit_button("Salvar estoque"):
                    salvar_estoque(
                        usuario_id=usuario_id,
                        medicamento_id=med_id,
                        data_compra=data_compra,
                        quantidade_total=quantidade_total,
                        unidade_estoque=unidade_estoque,
                        quantidade_por_dose=quantidade_por_dose,
                        farmacia=farmacia,
                        valor_pago=valor_pago,
                        documento_id=documento_id,
                        observacao=observacao,
                    )
                    st.success("Estoque salvo.")
                    recarregar()

        close_panel()

    with tabs[1]:
        open_panel("Cadastrar controle de receita")

        if not opcoes_meds:
            st.warning("Nenhum medicamento ativo para vincular receita.")
        else:
            with st.form("form_receita_medicamento"):
                med_label = st.selectbox("Medicamento", list(opcoes_meds.keys()), key="receita_med")
                med_id = opcoes_meds[med_label]

                doc_label = st.selectbox("Documento de receita", list(opcoes_docs.keys()), key="receita_doc")
                documento_id = opcoes_docs[doc_label]

                c1, c2, c3 = st.columns(3)
                with c1:
                    data_receita = data_input_br("Data da receita", date.today(), key="receita_data")
                    precisa_receita = st.checkbox("Precisa de receita para continuidade", value=True)
                with c2:
                    tipo_receita = st.selectbox(
                        "Tipo de receita",
                        ["Comum", "Controle especial", "Retenção", "Uso contínuo", "Não informado"],
                    )
                    retencao_receita = st.checkbox("Receita fica retida na farmácia")
                with c3:
                    validade_dias = st.number_input("Validade estimada em dias", min_value=0, value=30)

                observacao = st.text_area(
                    "Observação",
                    placeholder="Ex.: confirmar validade com farmácia/médico; receita de controle especial; precisa retorno para nova prescrição.",
                )

                if st.form_submit_button("Salvar controle de receita"):
                    salvar_receita(
                        usuario_id=usuario_id,
                        medicamento_id=med_id,
                        documento_id=documento_id,
                        data_receita=data_receita,
                        tipo_receita=tipo_receita,
                        validade_dias=validade_dias,
                        precisa_receita=precisa_receita,
                        retencao_receita=retencao_receita,
                        observacao=observacao,
                    )
                    st.success("Controle de receita salvo.")
                    recarregar()

        close_panel()

    with tabs[2]:
        open_panel("Tabela técnica de continuidade")
        df = painel_continuidade(usuario_id)
        if df.empty:
            st.info("Sem dados.")
        else:
            st.dataframe(df, width="stretch", hide_index=True)
        close_panel()
