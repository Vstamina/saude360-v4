from datetime import date

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from components.cards import open_panel, close_panel, mini_row
from components.gauges import render_card_exame
from core.helpers import data_input_br, to_float, fmt_num, br_date, recarregar
from services.exames_service import (
    salvar_exame,
    listar_exames,
    exames_mais_recentes,
    listar_nomes_exames,
    trilha_exame,
    gerar_leitura_trilha_exame,
)
from services.marcos_service import listar_marcos_opcoes


def render_exames(usuario_id):
    open_panel("Cadastrar exame", "Use unidade como mg/dL, ng/mL, U/L, uUI/mL etc.")

    with st.form("form_exame_v4"):
        c1, c2 = st.columns(2)
        with c1:
            data_exame = data_input_br("Data do exame", date.today(), key="exame_data")
            nome_exame = st.text_input("Nome do exame", placeholder="Ex.: Ferritina, Glicose, TGP, Vitamina D")
            unidade = st.text_input("Unidade", placeholder="Ex.: ng/mL, mg/dL, U/L")
        with c2:
            resultado_txt = st.text_input("Resultado", placeholder="Ex.: 32,20")
            ref_min_txt = st.text_input("Referencia minima", placeholder="Ex.: 30")
            ref_max_txt = st.text_input("Referencia maxima", placeholder="Ex.: 300")

        laboratorio = st.text_input("Laboratorio")

        opcoes_marcos = listar_marcos_opcoes(usuario_id)
        marco_label = st.selectbox("Relacionado a qual consulta/marco?", list(opcoes_marcos.keys()))
        marco_id = opcoes_marcos[marco_label]

        observacao = st.text_area("Observacao")

        salvar = st.form_submit_button("Salvar exame")

        if salvar:
            resultado = to_float(resultado_txt)
            ref_min = to_float(ref_min_txt) or 0
            ref_max = to_float(ref_max_txt) or 0

            if not nome_exame.strip():
                st.warning("Informe o nome do exame.")
            elif resultado is None:
                st.warning("Informe o resultado numerico.")
            else:
                salvar_exame(usuario_id, data_exame, nome_exame, resultado, unidade, ref_min, ref_max, laboratorio, observacao, marco_id)
                st.success("Exame salvo.")
                recarregar()

    close_panel()

    open_panel("Visao dos exames", "Resultado, status e medidor visual em uma leitura simples.")

    exames = listar_exames(usuario_id)

    if exames.empty:
        st.info("Nenhum exame cadastrado.")
    else:
        recentes = exames_mais_recentes(usuario_id).reset_index(drop=True)

        cols = st.columns(3)
        for i, r in recentes.iterrows():
            with cols[i % 3]:
                key = f"exame_card_gauge_{usuario_id}_{r.get('id', i)}_{i}_{str(r['nome_exame']).lower().replace(' ', '_')}"
                render_card_exame(
                    nome=r["nome_exame"],
                    resultado=r["resultado"],
                    ref_min=r["referencia_min"],
                    ref_max=r["referencia_max"],
                    unidade=r["unidade"],
                    key=key,
                )
                if r.get("marco_titulo"):
                    st.caption(f"Marco: {br_date(r['data_marco'])} | {r['marco_titulo']}")

        st.divider()
        st.subheader("Trilha por exame específico")

        nomes = listar_nomes_exames(usuario_id)
        if not nomes:
            st.caption("Ainda não há exames para montar trilha.")
        else:
            escolhido = st.selectbox("Escolha um exame para ver a trilha", nomes)
            trilha = trilha_exame(usuario_id, escolhido)
            st.info(gerar_leitura_trilha_exame(trilha, escolhido))

            if len(trilha) >= 2:
                chart_df = trilha.copy()
                chart_df["data_exame_dt"] = pd.to_datetime(chart_df["data_exame"], errors="coerce")

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=chart_df["data_exame_dt"],
                        y=chart_df["resultado"],
                        mode="lines+markers",
                        name=escolhido,
                    )
                )

                ref_min = chart_df["referencia_min"].dropna().iloc[-1] if not chart_df["referencia_min"].dropna().empty else None
                ref_max = chart_df["referencia_max"].dropna().iloc[-1] if not chart_df["referencia_max"].dropna().empty else None

                if ref_min is not None:
                    fig.add_hline(y=ref_min, line_dash="dot", annotation_text="mín ref")
                if ref_max is not None:
                    fig.add_hline(y=ref_max, line_dash="dot", annotation_text="máx ref")

                fig.update_layout(
                    height=320,
                    margin=dict(l=10, r=10, t=35, b=20),
                    xaxis_title="Data",
                    yaxis_title=trilha.iloc[-1].get("unidade") or "",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.88)",
                )

                st.plotly_chart(fig, width="stretch", key=f"trilha_exame_{usuario_id}_{escolhido}")

            view_trilha = trilha.copy()
            view_trilha["data_exame"] = view_trilha["data_exame"].apply(br_date)
            view_trilha["resultado"] = view_trilha["resultado"].apply(lambda x: fmt_num(x, 2))
            st.dataframe(
                view_trilha[["data_exame", "nome_exame", "resultado", "unidade", "referencia_min", "referencia_max", "laboratorio", "marco_titulo", "observacao"]],
                width="stretch",
                hide_index=True,
            )

        st.divider()
        st.subheader("Historico de exames")
        historico = exames.copy()
        historico["data_exame"] = historico["data_exame"].apply(br_date)
        historico["resultado"] = historico["resultado"].apply(lambda x: fmt_num(x, 2))
        st.dataframe(
            historico[["data_exame", "nome_exame", "resultado", "unidade", "referencia_min", "referencia_max", "laboratorio", "marco_titulo", "observacao"]],
            width="stretch",
            hide_index=True,
        )

    close_panel()
