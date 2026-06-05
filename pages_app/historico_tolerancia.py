import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date
from services.tolerancia_service import (
    listar_medicamentos_com_alerta,
    detalhes_tolerancia_medicamento,
    gerar_leitura_tolerancia,
    gerar_texto_historico_tolerancia,
)


def _pill_alerta(nivel):
    if nivel == "Alto":
        return "danger"
    if nivel == "Moderado":
        return "warn"
    return "aqua"


def render_historico_tolerancia(usuario_id, usuario=None):
    open_panel("Historico de tolerancia", "Medicamentos que tiveram suspensao, substituicao, eventos ou sintomas associados.")

    st.info(
        "Esta area ajuda a responder: quais medicamentos nao me fizeram bem, quando isso aconteceu e qual foi o contexto registrado."
    )

    leitura = gerar_leitura_tolerancia(usuario_id)
    st.write(leitura)

    df = listar_medicamentos_com_alerta(usuario_id)

    if usuario is not None:
        texto = gerar_texto_historico_tolerancia(usuario_id, usuario)
        st.download_button(
            label="Baixar historico de tolerancia em TXT",
            data=texto,
            file_name="historico_tolerancia_saude360.txt",
            mime="text/plain",
        )

    if df.empty:
        st.success("Nenhum medicamento com alerta de tolerancia registrado ate o momento.")
        close_panel()
        return

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{len(df)} medicamento(s)", "purple")
    with c2:
        status_pill(f"{len(df[df['nivel_alerta'] == 'Alto'])} alerta alto", "danger")
    with c3:
        status_pill(f"{len(df[df['nivel_alerta'] == 'Moderado'])} moderado", "warn")
    with c4:
        status_pill(f"{int(df['sintomas_fortes'].sum())} sintoma(s) forte(s)", "lilac")

    st.subheader("Resumo dos medicamentos")
    view = df.copy()
    st.dataframe(
        view[[
            "nivel_alerta",
            "medicamento",
            "dose",
            "status",
            "data_inicio",
            "data_status",
            "motivo_resumo",
            "eventos_total",
            "sintomas_total",
            "sintomas_fortes",
            "intensidade_media",
        ]],
        width="stretch",
        hide_index=True,
    )

    st.divider()

    opcoes = {
        f"{r['medicamento']} | alerta {r['nivel_alerta']} | ID {r['medicamento_id']}": int(r["medicamento_id"])
        for _, r in df.iterrows()
    }

    med_label = st.selectbox("Ver detalhes de um medicamento", list(opcoes.keys()))
    med_id = opcoes[med_label]

    med, eventos, sintomas, docs = detalhes_tolerancia_medicamento(usuario_id, med_id)

    if not med.empty:
        m = med.iloc[0]
        st.subheader(m["nome"])
        status_pill(m["status"], _pill_alerta(df[df["medicamento_id"] == med_id].iloc[0]["nivel_alerta"]))
        st.caption(f"Dose: {m['dose'] or ''} | Inicio: {br_date(m['data_inicio'])} | Profissional: {m['medico'] or ''}")
        if m.get("motivo_status"):
            st.warning(f"Motivo/status: {m.get('motivo_status')}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Eventos registrados")
        if eventos.empty:
            st.info("Nenhum evento de medicacao registrado.")
        else:
            for _, e in eventos.iterrows():
                mini_row(
                    f"{br_date(e['data_evento'])} | {e['tipo_evento']}",
                    f"{e.get('motivo') or ''} {e.get('sintomas') or ''} {e.get('conduta') or ''} {e.get('observacao') or ''}",
                )

    with col2:
        st.subheader("Sintomas associados")
        if sintomas.empty:
            st.info("Nenhum sintoma associado diretamente a este medicamento.")
        else:
            for _, s in sintomas.iterrows():
                mini_row(
                    f"{br_date(s['data_sintoma'])} {s.get('horario') or ''} | {s['sintoma']} | {int(s.get('intensidade') or 0)}/10",
                    f"{s.get('gatilho') or ''} | {s.get('acao_tomada') or ''} {s.get('observacao') or ''}",
                )

    st.subheader("Documentos relacionados")
    if docs.empty:
        st.info("Nenhum documento relacionado encontrado pelo nome do medicamento.")
    else:
        for _, d in docs.iterrows():
            mini_row(
                f"{br_date(d['data_documento'])} | {d['tipo_documento']}",
                f"{d['titulo']} | {d.get('relacionado_a') or ''} | {d.get('caminho_arquivo') or ''}",
            )

    close_panel()
