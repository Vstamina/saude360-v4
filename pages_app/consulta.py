import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, fmt_num
from services.consulta_premium_service import (
    obter_dados_relatorio_consulta,
    gerar_leitura_consulta,
    gerar_perguntas_para_medico,
    gerar_html_relatorio,
    gerar_txt_relatorio,
    exames_em_atencao,
)


def _nome_usuario(usuario):
    try:
        return usuario.get("nome", "")
    except Exception:
        try:
            return usuario["nome"]
        except Exception:
            return ""


def render_consulta(usuario_id, usuario=None):
    open_panel("Consulta médica", "Prepare um resumo claro para levar ao profissional de saúde.")

    nome = _nome_usuario(usuario)
    st.info(
        "Esta tela organiza informações para a consulta. Ela não substitui avaliação médica, não diagnostica e não prescreve tratamento."
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        dias = st.selectbox("Período do relatório", [30, 60, 90, 180, 365], index=2, format_func=lambda x: f"Últimos {x} dias")
    with c2:
        motivo_consulta = st.text_input("Motivo da consulta", placeholder="Ex.: retorno dermatologia, ferritina baixa, ajuste de medicação")
    with c3:
        foco_consulta = st.text_input("Foco principal", placeholder="Ex.: pele, emagrecimento, exames, sintomas")

    observacoes = st.text_area(
        "Observações que você quer lembrar de falar",
        placeholder="Ex.: tive enjoo após iniciar medicação, esqueci doses, exame X piorou, quero revisar suplemento...",
    )

    dados = obter_dados_relatorio_consulta(usuario_id, dias=dias)
    alertas_exames = exames_em_atencao(dados["exames"])

    st.divider()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        status_pill(f"{len(dados['medicamentos_ativos'])} meds ativos", "purple")
    with c2:
        status_pill(f"{len(alertas_exames)} exames atenção", "warn" if len(alertas_exames) else "aqua")
    with c3:
        status_pill(f"{len(dados['eventos'])} eventos", "warn" if len(dados["eventos"]) else "aqua")
    with c4:
        status_pill(f"{len(dados['doses_nao_tomadas'])} doses não tomadas", "warn" if len(dados["doses_nao_tomadas"]) else "aqua")
    with c5:
        status_pill(f"{len(dados['sintomas'])} sintomas", "lilac" if len(dados["sintomas"]) else "aqua")
    with c6:
        status_pill(f"{len(dados['pendencias'])} pendências", "danger" if len(dados["pendencias"]) else "aqua")

    st.subheader("Resumo executivo para a consulta")
    leitura = gerar_leitura_consulta(dados, motivo_consulta, foco_consulta)
    st.text_area("Resumo", value=leitura, height=180)

    st.subheader("Perguntas sugeridas para o médico")
    perguntas = gerar_perguntas_para_medico(dados, motivo_consulta, foco_consulta)
    for i, p in enumerate(perguntas, start=1):
        st.write(f"**{i}.** {p}")

    st.divider()

    tabs = st.tabs(
        [
            "Medicamentos",
            "Exames",
            "Eventos e doses",
            "Sintomas",
            "Pendências",
            "Marcos",
            "Exportar",
        ]
    )

    with tabs[0]:
        st.subheader("Medicamentos ativos")
        meds = dados["medicamentos_ativos"]
        if meds.empty:
            st.success("Nenhum medicamento ativo registrado.")
        else:
            for _, r in meds.iterrows():
                mini_row(
                    f"{br_date(r.get('data_inicio'))} | {r.get('nome') or ''} | {r.get('dose') or ''}",
                    f"{r.get('frequencia_modelo') or ''} | {r.get('horario_inicial') or ''} | {r.get('orientacao') or ''}",
                )

    with tabs[1]:
        st.subheader("Exames em atenção")
        if alertas_exames.empty:
            st.success("Nenhum exame em atenção no período.")
        else:
            for _, r in alertas_exames.iterrows():
                mini_row(
                    f"{br_date(r.get('data_exame'))} | {r.get('nome_exame') or ''}",
                    f"Resultado: {fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''} | Ref.: {fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)} | {r.get('classificacao') or ''}",
                )

        with st.expander("Ver todos os exames do período"):
            exames = dados["exames"]
            if exames.empty:
                st.info("Nenhum exame no período.")
            else:
                st.dataframe(exames, width="stretch", hide_index=True)

    with tabs[2]:
        st.subheader("Eventos de medicação")
        eventos = dados["eventos"]
        if eventos.empty:
            st.success("Nenhum evento de medicação no período.")
        else:
            for _, r in eventos.head(30).iterrows():
                mini_row(
                    f"{br_date(r.get('data_evento'))} | {r.get('tipo_evento') or ''} | {r.get('medicamento') or ''}",
                    f"{r.get('motivo') or ''} {r.get('sintomas') or ''} {r.get('conduta') or ''}",
                )

        st.subheader("Doses não tomadas")
        doses = dados["doses_nao_tomadas"]
        if doses.empty:
            st.success("Nenhuma dose não tomada no período.")
        else:
            for _, r in doses.head(40).iterrows():
                mini_row(
                    f"{br_date(r.get('data_prevista'))} {r.get('horario_previsto') or ''} | {r.get('medicamento') or ''}",
                    f"Motivo: {r.get('motivo_nao_tomou') or ''} | Obs.: {r.get('observacao') or ''}",
                )

    with tabs[3]:
        st.subheader("Sintomas registrados")
        sintomas = dados["sintomas"]
        if sintomas.empty:
            st.success("Nenhum sintoma registrado no período.")
        else:
            for _, r in sintomas.head(50).iterrows():
                intensidade = r.get("intensidade") or ""
                mini_row(
                    f"{br_date(r.get('data_sintoma'))} {r.get('horario') or ''} | {r.get('sintoma') or ''} | {intensidade}/10",
                    f"Medicamento associado: {r.get('medicamento') or ''} | {r.get('observacao') or ''}",
                )

    with tabs[4]:
        st.subheader("Pendências abertas")
        pend = dados["pendencias"]
        if pend.empty:
            st.success("Nenhuma pendência aberta.")
        else:
            for _, r in pend.iterrows():
                prioridade = r.get("prioridade") or ""
                cor = "danger" if prioridade == "Alta" else "warn" if prioridade == "Média" else "aqua"
                status_pill(prioridade, cor)
                mini_row(
                    f"{br_date(r.get('data_criacao'))} | {r.get('tipo') or ''} | {r.get('titulo') or ''}",
                    r.get("descricao") or "",
                )

    with tabs[5]:
        st.subheader("Marcos recentes")
        marcos = dados["marcos"]
        if marcos.empty:
            st.info("Nenhum marco no período.")
        else:
            for _, r in marcos.head(30).iterrows():
                mini_row(
                    f"{br_date(r.get('data_marco'))} | {r.get('tipo_marco') or ''} | {r.get('titulo') or ''}",
                    f"{r.get('especialidade') or ''} | Conduta: {r.get('conduta') or ''} | Próximo passo: {r.get('proximo_passo') or ''}",
                )

    with tabs[6]:
        st.subheader("Exportar relatório")

        html = gerar_html_relatorio(usuario, dados, motivo_consulta, foco_consulta, observacoes)
        txt = gerar_txt_relatorio(usuario, dados, motivo_consulta, foco_consulta, observacoes)

        st.download_button(
            "Baixar relatório em HTML",
            data=html.encode("utf-8"),
            file_name=f"relatorio_consulta_saude360_{nome.replace(' ', '_').lower() or 'paciente'}.html",
            mime="text/html",
        )

        st.download_button(
            "Baixar relatório em TXT",
            data=txt.encode("utf-8"),
            file_name=f"relatorio_consulta_saude360_{nome.replace(' ', '_').lower() or 'paciente'}.txt",
            mime="text/plain",
        )

        with st.expander("Prévia em texto"):
            st.text_area("Texto do relatório", value=txt, height=500)

    close_panel()
