import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from components.gauges import classificar_exame
from core.helpers import br_date, fmt_num
from services.medicamentos_service import listar_medicamentos_ativos, listar_eventos_adversos
from services.exames_service import exames_mais_recentes
from services.documentos_service import listar_documentos
from services.sintomas_service import sintomas_ultimos_dias, gerar_leitura_sintomas
from services.relatorios_service import gerar_relatorio_consulta


def render_consulta(usuario_id, usuario=None):
    open_panel("Resumo para consulta medica", "Leve este painel para a consulta")

    meds_ativos = listar_medicamentos_ativos(usuario_id)
    eventos_adversos = listar_eventos_adversos(usuario_id)
    exames_rec = exames_mais_recentes(usuario_id)
    docs_recentes = listar_documentos(usuario_id, limite=8)
    sintomas_30 = sintomas_ultimos_dias(usuario_id, dias=30)

    if usuario is not None:
        relatorio = gerar_relatorio_consulta(usuario_id, usuario)
        st.download_button(
            label="Baixar resumo da consulta em TXT",
            data=relatorio,
            file_name="resumo_consulta_saude360.txt",
            mime="text/plain",
        )

        with st.expander("Ver texto do relatorio"):
            st.text_area("Resumo gerado", value=relatorio, height=420)

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Medicamentos ativos")
        if meds_ativos.empty:
            st.info("Nenhum medicamento ativo.")
        else:
            for _, m in meds_ativos.iterrows():
                status_pill(m["nome"], "aqua")
                st.write(f"**{m['nome']}** | {m['dose'] or ''}")
                st.caption(f"Inicio: {br_date(m['data_inicio'])} | Profissional: {m['medico'] or ''}")

    with c2:
        st.subheader("Medicamentos que nao deram certo")
        if eventos_adversos.empty:
            st.success("Nenhum evento adverso registrado.")
        else:
            for _, e in eventos_adversos.head(8).iterrows():
                st.markdown(
                    f"""
                    <div class="alert-box alert-danger">
                        <b>{e['medicamento'] if e['medicamento'] else 'Medicamento nao informado'}</b> - {e['tipo_evento']}<br>
                        <span class="muted">{br_date(e['data_evento'])} | {e['motivo'] or ''}</span><br>
                        <span>{e['sintomas'] or e['observacao'] or ''}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    st.subheader("Sintomas recentes")
    st.info(gerar_leitura_sintomas(usuario_id, dias=30))

    if sintomas_30.empty:
        st.caption("Nenhum sintoma recente para levar a consulta.")
    else:
        sintomas_fortes = sintomas_30[sintomas_30["intensidade"].fillna(0) >= 7]
        if not sintomas_fortes.empty:
            st.warning(f"{len(sintomas_fortes)} sintoma(s) com intensidade 7 ou mais nos ultimos 30 dias.")

        for _, s in sintomas_30.head(8).iterrows():
            med = f" | Medicamento: {s['medicamento']}" if s.get("medicamento") else ""
            mini_row(
                f"{br_date(s['data_sintoma'])} {s['horario'] or ''} | {s['sintoma']} | {int(s['intensidade'] or 0)}/10",
                f"{s.get('gatilho') or ''}{med} | {s.get('acao_tomada') or ''} {s.get('observacao') or ''}",
            )

    st.divider()

    st.subheader("Exames em atencao")
    if exames_rec.empty:
        st.info("Sem exames.")
    else:
        encontrou = False
        for _, r in exames_rec.iterrows():
            status, _, leitura = classificar_exame(r["resultado"], r["referencia_min"], r["referencia_max"])
            if status in ["Abaixo da faixa", "Acima da faixa", "Na faixa, perto do minimo", "Na faixa, perto do maximo", "Abaixo", "Acima", "Limite inferior", "Limite superior"]:
                encontrou = True
                st.write(f"**{r['nome_exame']}**: {fmt_num(r['resultado'])} {r['unidade'] or ''} - {status}")
                st.caption(leitura)
        if not encontrou:
            st.success("Nenhum exame em alerta pelos parametros cadastrados.")

    st.divider()

    st.subheader("Documentos recentes")
    if docs_recentes.empty:
        st.info("Nenhum documento recente.")
    else:
        view = docs_recentes.copy()
        view["data_documento"] = view["data_documento"].apply(br_date)
        st.dataframe(
            view[["data_documento", "tipo_documento", "titulo", "profissional", "relacionado_a", "caminho_arquivo"]],
            width="stretch",
            hide_index=True
        )

    close_panel()
