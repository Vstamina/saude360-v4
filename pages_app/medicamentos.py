from datetime import date, time, timedelta

import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, br_date, recarregar
from services.medicamentos_service import salvar_medicamento, listar_medicamentos
from services.marcos_service import listar_marcos_opcoes


def render_medicamentos(usuario_id):
    open_panel("Cadastrar medicamento", "Com duracao, uso continuo e frequencia inteligente")

    with st.form("form_medicamento_v4"):
        nome = st.text_input("Nome do medicamento")
        dose = st.text_input("Dose", placeholder="Ex.: 1 comprimido, 200 mg, 0,25 mg")

        c1, c2 = st.columns(2)
        with c1:
            modelo = st.selectbox(
                "Frequencia",
                [
                    "1 vez ao dia",
                    "2 vezes ao dia",
                    "3 vezes ao dia",
                    "4 vezes ao dia",
                    "A cada X horas",
                    "Horarios fixos",
                    "Semanal",
                ],
            )
        with c2:
            horario_inicial = st.time_input("Horario inicial", value=time(8, 0))

        intervalo_horas = None
        horarios_fixos = ""

        if modelo == "A cada X horas":
            intervalo_horas = st.number_input("Tomar a cada quantas horas?", min_value=1, max_value=24, value=8, step=1)

        if modelo == "Horarios fixos":
            horarios_fixos = st.text_input("Horarios fixos", value="08:00, 20:00", help="Separe por virgula. Ex.: 08:00, 14:00, 22:00")

        c3, c4 = st.columns(2)
        with c3:
            data_inicio = data_input_br("Data de inicio", date.today(), key="med_inicio")
        with c4:
            duracao = st.selectbox("Duracao", ["7 dias", "14 dias", "30 dias", "Personalizado", "Uso continuo"])

        data_fim = None
        if duracao == "Personalizado":
            data_fim = data_input_br("Data de fim", date.today() + timedelta(days=13), key="med_fim")

        opcoes_marcos = listar_marcos_opcoes(usuario_id)
        marco_label = st.selectbox("Iniciado em qual consulta/marco?", list(opcoes_marcos.keys()))
        marco_id = opcoes_marcos[marco_label]

        orientacao = st.text_area("Orientacao da receita")
        medico = st.text_input("Medico ou profissional")

        salvar = st.form_submit_button("Salvar medicamento e gerar agenda")

        if salvar:
            if not nome.strip():
                st.warning("Informe o nome do medicamento.")
            else:
                salvar_medicamento(
                    usuario_id=usuario_id,
                    nome=nome,
                    dose=dose,
                    modelo=modelo,
                    intervalo_horas=intervalo_horas,
                    horarios_fixos=horarios_fixos,
                    horario_inicial=horario_inicial,
                    data_inicio=data_inicio,
                    duracao=duracao,
                    data_fim=data_fim,
                    orientacao=orientacao,
                    medico=medico,
                    marco_id=marco_id,
                )
                st.success("Medicamento salvo e agenda gerada.")
                recarregar()

    close_panel()

    open_panel("Medicamentos cadastrados")
    meds = listar_medicamentos(usuario_id)

    if meds.empty:
        st.info("Nenhum medicamento cadastrado.")
    else:
        view = meds.copy()
        view["data_inicio"] = view["data_inicio"].apply(br_date)
        view["data_fim"] = view["data_fim"].apply(br_date)
        view["uso_continuo"] = view["uso_continuo"].apply(lambda x: "Sim" if int(x or 0) == 1 else "Nao")
        if "data_marco" in view.columns:
            view["data_marco"] = view["data_marco"].apply(br_date)
        cols = ["id", "nome", "dose", "frequencia_modelo", "intervalo_horas", "horario_inicial", "data_inicio", "data_fim", "uso_continuo", "status", "medico", "marco_titulo"]
        st.dataframe(view[[c for c in cols if c in view.columns]], width="stretch", hide_index=True)
    close_panel()
