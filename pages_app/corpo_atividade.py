from datetime import date

import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, to_float, br_date, recarregar
from services.corpo_service import salvar_bioimpedancia, listar_bioimpedancia
from services.atividade_service import salvar_atividade, listar_atividades


def render_corpo_atividade(usuario_id):
    col_a, col_b = st.columns(2)

    with col_a:
        open_panel("Bioimpedancia e medidas")
        with st.form("form_bio_v4"):
            data_medicao = data_input_br("Data da medicao", date.today(), key="bio_data")
            peso = st.text_input("Peso kg", placeholder="Ex.: 90,5")
            gordura = st.text_input("Gordura corporal %", placeholder="Ex.: 28,4")
            massa_magra = st.text_input("Massa magra kg", placeholder="Ex.: 63,0")
            massa_muscular = st.text_input("Massa muscular kg", placeholder="Ex.: 48,0")
            gordura_visceral = st.text_input("Gordura visceral", placeholder="Ex.: 12")
            cintura = st.text_input("Cintura cm", placeholder="Ex.: 102")
            obs_bio = st.text_area("Observacoes", key="obs_bio")

            if st.form_submit_button("Salvar bioimpedancia"):
                salvar_bioimpedancia(
                    usuario_id,
                    data_medicao,
                    to_float(peso) or 0,
                    to_float(gordura) or 0,
                    to_float(massa_magra) or 0,
                    to_float(massa_muscular) or 0,
                    to_float(gordura_visceral) or 0,
                    to_float(cintura) or 0,
                    obs_bio,
                )
                st.success("Bioimpedancia salva.")
                recarregar()
        close_panel()

    with col_b:
        open_panel("Atividade fisica")
        with st.form("form_atividade_v4"):
            data_atividade = data_input_br("Data da atividade", date.today(), key="ativ_data")
            tipo = st.selectbox("Tipo", ["Musculacao", "Caminhada", "Corrida", "Bike", "Funcional", "Natacao", "Outro"])
            duracao = st.number_input("Duracao em minutos", min_value=0, value=30)
            calorias = st.text_input("Calorias", placeholder="Opcional")
            passos = st.number_input("Passos", min_value=0, value=0)
            fc = st.text_input("Frequencia cardiaca media", placeholder="Opcional")
            origem = st.selectbox("Origem", ["Manual", "Smartwatch", "Aplicativo", "Outro"])
            obs_ativ = st.text_area("Observacoes", key="obs_ativ")

            if st.form_submit_button("Salvar atividade"):
                salvar_atividade(
                    usuario_id,
                    data_atividade,
                    tipo,
                    duracao,
                    to_float(calorias) or 0,
                    passos,
                    to_float(fc) or 0,
                    origem,
                    obs_ativ,
                )
                st.success("Atividade salva.")
                recarregar()
        close_panel()

    open_panel("Historicos")
    h1, h2 = st.columns(2)

    with h1:
        bio = listar_bioimpedancia(usuario_id)
        st.subheader("Bioimpedancia")
        if bio.empty:
            st.info("Sem dados.")
        else:
            view = bio.copy()
            view["data_medicao"] = view["data_medicao"].apply(br_date)
            st.dataframe(view[["data_medicao", "peso_kg", "gordura_percentual", "massa_magra_kg", "massa_muscular_kg", "gordura_visceral", "cintura_cm", "observacao"]], width="stretch", hide_index=True)

    with h2:
        ativ = listar_atividades(usuario_id)
        st.subheader("Atividades")
        if ativ.empty:
            st.info("Sem dados.")
        else:
            view = ativ.copy()
            view["data_atividade"] = view["data_atividade"].apply(br_date)
            st.dataframe(view[["data_atividade", "tipo", "duracao_min", "calorias", "passos", "frequencia_media", "origem", "observacao"]], width="stretch", hide_index=True)

    close_panel()
