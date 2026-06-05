from datetime import date, time

import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import data_input_br, br_date, recarregar
from services.sintomas_service import (
    salvar_sintoma,
    listar_sintomas,
    sintomas_ultimos_dias,
    listar_medicamentos_para_sintoma,
    gerar_leitura_sintomas,
)


def render_sintomas(usuario_id):
    open_panel("Sintomas e diario", "Registre como voce se sentiu e conecte sintomas a medicamentos, exames e consultas.")

    st.info(
        "Use esta area para registrar eventos como enjoo, tontura, dor de cabeca, cansaco, insonia, ansiedade, mal-estar, queda de cabelo ou qualquer percepcao relevante."
    )

    with st.form("form_sintoma_diario"):
        c1, c2, c3 = st.columns(3)
        with c1:
            data_sintoma = data_input_br("Data", date.today(), key="sintoma_data")
        with c2:
            horario = st.time_input("Horario aproximado", value=time(8, 0))
        with c3:
            intensidade = st.slider("Intensidade", min_value=0, max_value=10, value=5)

        sintoma = st.text_input("Sintoma principal", placeholder="Ex.: enjoo, tontura, cansaco, dor de cabeca")
        duracao = st.text_input("Duracao", placeholder="Ex.: 30 minutos, o dia todo, 2 horas")

        meds = listar_medicamentos_para_sintoma(usuario_id)
        opcoes = {"Nao associar a medicamento": None}
        for _, m in meds.iterrows():
            opcoes[f"{m['nome']} | {m['dose'] or ''} | {m['status']} | ID {m['id']}"] = int(m["id"])

        med_label = st.selectbox("Associar a medicamento", list(opcoes.keys()))
        medicamento_id = opcoes[med_label]

        gatilho = st.text_input("Possivel gatilho", placeholder="Ex.: depois do remedio, apos treino, jejum, refeicao, estresse")
        acao_tomada = st.text_input("O que foi feito?", placeholder="Ex.: repouso, agua, alimento, contato com medico, suspendeu")
        observacao = st.text_area("Observacoes")

        salvar = st.form_submit_button("Salvar sintoma")

        if salvar:
            if not sintoma.strip():
                st.warning("Informe o sintoma principal.")
            else:
                salvar_sintoma(
                    usuario_id=usuario_id,
                    data_sintoma=data_sintoma,
                    horario=horario,
                    sintoma=sintoma,
                    intensidade=intensidade,
                    duracao=duracao,
                    medicamento_id=medicamento_id,
                    gatilho=gatilho,
                    acao_tomada=acao_tomada,
                    observacao=observacao,
                )
                st.success("Sintoma salvo no diario.")
                recarregar()

    close_panel()

    open_panel("Resumo dos ultimos 30 dias", "Leitura simples para acompanhar recorrencia e intensidade")
    leitura = gerar_leitura_sintomas(usuario_id, dias=30)
    st.info(leitura)

    recentes = sintomas_ultimos_dias(usuario_id, dias=30)

    if recentes.empty:
        st.caption("Nenhum sintoma recente.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            status_pill(f"{len(recentes)} registro(s)", "aqua")
        with c2:
            media = round(float(recentes["intensidade"].fillna(0).mean()), 1)
            status_pill(f"Intensidade media {media}/10", "lilac")
        with c3:
            associados = len(recentes[recentes["medicamento_id"].notna()])
            status_pill(f"{associados} associado(s) a remedio", "turq")

        st.subheader("Sintomas mais recentes")
        for _, r in recentes.head(8).iterrows():
            med = f" | Medicamento: {r['medicamento']}" if r.get("medicamento") else ""
            mini_row(
                f"{br_date(r['data_sintoma'])} {r['horario'] or ''} | {r['sintoma']} | intensidade {int(r['intensidade'] or 0)}/10",
                f"{r.get('gatilho') or ''} {med} | {r.get('acao_tomada') or ''} {r.get('observacao') or ''}",
            )

    close_panel()

    open_panel("Historico completo de sintomas")
    historico = listar_sintomas(usuario_id)

    if historico.empty:
        st.info("Nenhum sintoma registrado.")
    else:
        view = historico.copy()
        view["data_sintoma"] = view["data_sintoma"].apply(br_date)
        st.dataframe(
            view[["data_sintoma", "horario", "sintoma", "intensidade", "duracao", "medicamento", "gatilho", "acao_tomada", "observacao"]],
            width="stretch",
            hide_index=True,
        )
    close_panel()
