import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, fmt_num, recarregar
from services.revisao_service import (
    resumo_qualidade,
    documentos_para_revisao,
    pendencias_revisao_importacao,
    exames_incompletos,
    medicamentos_incompletos,
    documentos_sem_marco,
    sintomas_sem_marco,
    marcar_documento_revisado,
    atualizar_exame_basico,
    atualizar_medicamento_basico,
)
from services.pendencias_service import resolver_pendencia


def render_revisao(usuario_id, usuario=None):
    open_panel("Revisão inteligente", "Controle de qualidade dos dados importados, incompletos ou sem vínculo clínico.")

    resumo = resumo_qualidade(usuario_id)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        status_pill(f"Score {resumo['score']}/100", "aqua" if resumo["score"] >= 80 else "warn" if resumo["score"] >= 50 else "danger")
    with c2:
        status_pill(resumo["status"], "purple")
    with c3:
        status_pill(f"{resumo['documentos_para_revisao']} docs revisar", "warn" if resumo["documentos_para_revisao"] else "aqua")
    with c4:
        status_pill(f"{resumo['exames_incompletos']} exames incompletos", "warn" if resumo["exames_incompletos"] else "aqua")
    with c5:
        status_pill(f"{resumo['medicamentos_incompletos']} meds incompletos", "warn" if resumo["medicamentos_incompletos"] else "aqua")

    st.info(resumo["leitura"])

    close_panel()

    tabs = st.tabs(
        [
            "Documentos",
            "Pendências de importação",
            "Exames incompletos",
            "Medicamentos incompletos",
            "Itens sem marco",
            "Checklist",
        ]
    )

    with tabs[0]:
        open_panel("Documentos para revisar", "Paciente não identificado, alerta de divergência ou validação manual pendente.")

        docs = documentos_para_revisao(usuario_id)

        if docs.empty:
            st.success("Nenhum documento crítico para revisar.")
        else:
            for _, d in docs.iterrows():
                st.markdown("---")
                st.write(f"**{br_date(d['data_documento'])} | {d['tipo_documento']} | {d['titulo']}**")
                st.caption(f"Paciente detectado: {d.get('paciente_detectado') or 'não identificado'}")
                st.caption(f"Validação: {d.get('validacao_paciente') or 'sem validação'}")
                if d.get("caminho_arquivo"):
                    st.caption(f"Arquivo: {d.get('caminho_arquivo')}")
                if d.get("marco_titulo"):
                    st.caption(f"Marco: {d.get('marco_titulo')}")
                else:
                    st.warning("Documento sem marco relacionado.")

                with st.expander("Marcar documento como revisado"):
                    paciente = st.text_input("Paciente confirmado", value=d.get("paciente_detectado") if d.get("paciente_detectado") not in [None, "", "Paciente não identificado"] else "", key=f"pac_doc_{d['id']}")
                    obs = st.text_area("Observação da revisão", key=f"obs_doc_{d['id']}")
                    if st.button("Confirmar revisão do documento", key=f"rev_doc_{d['id']}"):
                        marcar_documento_revisado(usuario_id, int(d["id"]), paciente, obs)
                        st.success("Documento marcado como revisado.")
                        recarregar()

        close_panel()

    with tabs[1]:
        open_panel("Pendências de importação", "Itens que o app marcou como baixa confiança ou revisão necessária.")

        pend = pendencias_revisao_importacao(usuario_id)

        if pend.empty:
            st.success("Nenhuma pendência de importação aberta.")
        else:
            for _, p in pend.iterrows():
                st.markdown("---")
                prioridade = p.get("prioridade") or ""
                cor = "danger" if prioridade == "Alta" else "warn" if prioridade == "Média" else "aqua"
                status_pill(prioridade, cor)
                st.write(f"**{p['titulo']}**")
                st.caption(f"{br_date(p['data_criacao'])} | {p['tipo']} | origem: {p.get('origem') or ''}")
                st.write(p.get("descricao") or "")

                with st.expander("Resolver"):
                    resolucao = st.text_area("Como foi revisado?", key=f"res_pend_rev_{p['id']}")
                    if st.button("Marcar como resolvida", key=f"btn_res_pend_rev_{p['id']}"):
                        resolver_pendencia(usuario_id, int(p["id"]), resolucao)
                        st.success("Pendência resolvida.")
                        recarregar()

        close_panel()

    with tabs[2]:
        open_panel("Exames incompletos", "Exames sem unidade, referência ou marco podem prejudicar os medidores.")

        exames = exames_incompletos(usuario_id)

        if exames.empty:
            st.success("Nenhum exame incompleto encontrado.")
        else:
            for _, e in exames.iterrows():
                st.markdown("---")
                st.write(f"**{br_date(e['data_exame'])} | {e['nome_exame']} | {fmt_num(e['resultado'], 2)} {e.get('unidade') or ''}**")
                st.caption(f"Referência: {fmt_num(e.get('referencia_min'), 2)} a {fmt_num(e.get('referencia_max'), 2)}")
                if e.get("marco_titulo"):
                    st.caption(f"Marco: {e.get('marco_titulo')}")
                else:
                    st.warning("Exame sem marco. Use a Central de correções para vincular.")

                with st.expander("Corrigir dados básicos do exame"):
                    unidade = st.text_input("Unidade", value=e.get("unidade") or "", key=f"un_ex_{e['id']}")
                    ref_min = st.number_input("Referência mínima", value=float(e.get("referencia_min") or 0), key=f"refmin_ex_{e['id']}")
                    ref_max = st.number_input("Referência máxima", value=float(e.get("referencia_max") or 0), key=f"refmax_ex_{e['id']}")
                    obs = st.text_area("Observação", value=e.get("observacao") or "", key=f"obs_ex_{e['id']}")
                    if st.button("Salvar correção do exame", key=f"btn_ex_{e['id']}"):
                        atualizar_exame_basico(usuario_id, int(e["id"]), unidade, ref_min, ref_max, obs)
                        st.success("Exame atualizado.")
                        recarregar()

        close_panel()

    with tabs[3]:
        open_panel("Medicamentos incompletos", "Medicamentos sem dose, orientação ou marco precisam de revisão.")

        meds = medicamentos_incompletos(usuario_id)

        if meds.empty:
            st.success("Nenhum medicamento incompleto encontrado.")
        else:
            for _, m in meds.iterrows():
                st.markdown("---")
                st.write(f"**{br_date(m['data_inicio'])} | {m['nome']}**")
                st.caption(f"Dose: {m.get('dose') or 'não informada'} | Frequência: {m.get('frequencia_modelo') or ''} | Horário: {m.get('horario_inicial') or ''}")
                if m.get("marco_titulo"):
                    st.caption(f"Marco: {m.get('marco_titulo')}")
                else:
                    st.warning("Medicamento sem marco. Use a Central de correções para vincular.")

                with st.expander("Corrigir dados básicos do medicamento"):
                    dose = st.text_input("Dose", value=m.get("dose") or "", key=f"dose_med_{m['id']}")
                    medico = st.text_input("Médico/profissional", value=m.get("medico") or "", key=f"medico_med_{m['id']}")
                    orientacao = st.text_area("Orientação", value=m.get("orientacao") or "", key=f"ori_med_{m['id']}")
                    if st.button("Salvar correção do medicamento", key=f"btn_med_{m['id']}"):
                        atualizar_medicamento_basico(usuario_id, int(m["id"]), dose, orientacao, medico)
                        st.success("Medicamento atualizado.")
                        recarregar()

        close_panel()

    with tabs[4]:
        open_panel("Itens sem marco", "Itens sem marco ficam soltos na jornada. Vincule pela Central de correções.")

        docs_sem = documentos_sem_marco(usuario_id)
        sintomas_sem = sintomas_sem_marco(usuario_id)

        st.subheader("Documentos sem marco")
        if docs_sem.empty:
            st.success("Nenhum documento sem marco.")
        else:
            for _, d in docs_sem.head(20).iterrows():
                mini_row(f"{br_date(d['data_documento'])} | {d['tipo_documento']}", d["titulo"])

        st.subheader("Sintomas sem marco")
        if sintomas_sem.empty:
            st.success("Nenhum sintoma sem marco.")
        else:
            for _, s in sintomas_sem.head(20).iterrows():
                mini_row(f"{br_date(s['data_sintoma'])} | {s['sintoma']} | {s.get('intensidade') or 0}/10", s.get("observacao") or "")

        st.info("Para vincular itens a marcos, use a aba Central de correções → Vincular a marco.")

        close_panel()

    with tabs[5]:
        open_panel("Checklist de qualidade", "Roteiro rápido antes de gerar relatório para consulta.")

        checklist = [
            ("Documentos revisados", resumo["documentos_para_revisao"] == 0),
            ("Pendências de importação resolvidas", resumo["pendencias_revisao"] == 0),
            ("Exames com unidade e referência", resumo["exames_incompletos"] == 0),
            ("Medicamentos com dose/orientação", resumo["medicamentos_incompletos"] == 0),
            ("Documentos vinculados a marcos", resumo["documentos_sem_marco"] == 0),
            ("Sintomas vinculados quando fizer sentido", resumo["sintomas_sem_marco"] == 0),
        ]

        for label, ok in checklist:
            if ok:
                st.success(f"OK — {label}")
            else:
                st.warning(f"Revisar — {label}")

        st.caption("A base não precisa estar perfeita para usar o app, mas quanto melhor a qualidade dos dados, melhores ficam os relatórios e leituras.")

        close_panel()
