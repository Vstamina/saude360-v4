from datetime import date

import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, br_date, recarregar
from core.database import consultar_df
from services.medicamentos_service import atualizar_status_medicamento, listar_eventos_adversos


def render_eventos(usuario_id):
    open_panel("STOP, pausa, suspensao e substituicao", "Medicamento suspenso nao desaparece: vira evidencia clinica.")

    meds_all = consultar_df(
        """
        SELECT id, nome, dose, COALESCE(status, 'Ativo') AS status
        FROM medicamentos
        WHERE usuario_id = ?
        ORDER BY nome
        """,
        (usuario_id,),
    )

    if meds_all.empty:
        st.info("Cadastre um medicamento primeiro.")
    else:
        opcoes_med = {f"{r['nome']} | {r['dose'] or ''} | {r['status']} | ID {r['id']}": int(r["id"]) for _, r in meds_all.iterrows()}

        with st.form("form_stop"):
            med_label = st.selectbox("Medicamento", list(opcoes_med.keys()))
            med_id = opcoes_med[med_label]

            c1, c2, c3 = st.columns(3)
            with c1:
                novo_status = st.selectbox("Acao", ["Pausado", "Suspenso", "Substituido", "Concluido"])
            with c2:
                data_evento = data_input_br("Data do evento", date.today(), key="stop_data")
            with c3:
                gravidade = st.selectbox("Gravidade", ["Leve", "Moderada", "Alta", "A avaliar"])

            motivo = st.selectbox(
                "Motivo principal",
                [
                    "Efeito adverso",
                    "Alergia ou suspeita de alergia",
                    "Ineficacia percebida",
                    "Orientacao medica",
                    "Interacao medicamentosa",
                    "Fim de tratamento",
                    "Outro",
                ],
            )

            sintomas = st.text_area("Sintomas ou contexto", placeholder="Ex.: enjoo, tontura, mal-estar, dor abdominal...")
            orientado_por = st.text_input("Quem orientou?", placeholder="Ex.: Dra. Melissa")
            conduta = st.text_area("Conduta", placeholder="Ex.: suspender, substituir, observar, retornar em consulta...")
            substituto = st.text_input("Substituido por qual medicamento?", placeholder="Se houver")
            observacao = st.text_area("Observacoes adicionais")

            salvar_evento = st.form_submit_button("Registrar evento e atualizar tratamento")

            if salvar_evento:
                atualizar_status_medicamento(
                    med_id=med_id,
                    usuario_id=usuario_id,
                    novo_status=novo_status,
                    data_evento=data_evento,
                    motivo=motivo,
                    sintomas=sintomas,
                    gravidade=gravidade,
                    orientado_por=orientado_por,
                    conduta=conduta,
                    substituto=substituto,
                    observacao=observacao,
                )
                st.success("Evento registrado. Doses futuras foram pausadas/canceladas conforme a acao.")
                recarregar()

    close_panel()

    open_panel("Historico de eventos adversos e alteracoes")
    eventos_adversos = listar_eventos_adversos(usuario_id)

    if eventos_adversos.empty:
        st.info("Nenhum evento adverso ou STOP registrado.")
    else:
        view = eventos_adversos.copy()
        view["data_evento"] = view["data_evento"].apply(br_date)
        st.dataframe(
            view[["data_evento", "tipo_evento", "medicamento", "motivo", "sintomas", "gravidade", "orientado_por", "conduta", "substituto", "observacao"]],
            width="stretch",
            hide_index=True,
        )
    close_panel()
