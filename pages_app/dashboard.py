import streamlit as st

from components.cards import kpi_card, open_panel, close_panel, mini_row, status_pill
from components.gauges import render_card_exame
from core.helpers import br_date, fmt_num
from services.medicamentos_service import (
    calcular_aderencia,
    listar_doses_hoje,
    listar_medicamentos_ativos,
    listar_eventos_adversos,
    proxima_dose,
)
from services.exames_service import exames_mais_recentes, contar_exames_alerta
from services.documentos_service import listar_documentos
from services.corpo_service import ultima_bioimpedancia
from services.atividade_service import atividades_ultimos_7_dias
from services.inteligencia_service import tentar_comando_rapido
from services.sintomas_service import sintomas_ultimos_dias, resumo_sintomas
from services.marcos_service import listar_marcos_recentes, gerar_leitura_marcos
from core.helpers import recarregar


def render_dashboard(usuario_id, usuario):
    aderencia, tomadas_30, total_30 = calcular_aderencia(usuario_id, 30)
    doses_hoje = listar_doses_hoje(usuario_id)
    meds_ativos = listar_medicamentos_ativos(usuario_id)
    eventos_adversos = listar_eventos_adversos(usuario_id)
    exames_rec = exames_mais_recentes(usuario_id)
    exames_alerta = contar_exames_alerta(exames_rec)
    prox = proxima_dose(usuario_id)
    docs_recentes = listar_documentos(usuario_id, limite=6)
    bio_rec = ultima_bioimpedancia(usuario_id)
    atividades_7 = atividades_ultimos_7_dias(usuario_id)
    sintomas_30 = sintomas_ultimos_dias(usuario_id, dias=30)
    resumo_sint = resumo_sintomas(usuario_id, dias=30)
    marcos_recentes = listar_marcos_recentes(usuario_id, limite=5)

    pendentes_hoje = len(doses_hoje[doses_hoje["status"] == "Pendente"]) if not doses_hoje.empty else 0
    tomadas_hoje = len(doses_hoje[doses_hoje["status"] == "Tomado"]) if not doses_hoje.empty else 0
    sintomas_fortes = len(sintomas_30[sintomas_30["intensidade"].fillna(0) >= 7]) if not sintomas_30.empty else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        kpi_card("Medicamentos ativos", len(meds_ativos), "tratamentos")
    with c2:
        kpi_card("Doses hoje", f"{tomadas_hoje}/{len(doses_hoje)}", f"{pendentes_hoje} pendentes")
    with c3:
        kpi_card("Aderencia 30d", f"{aderencia}%", f"{tomadas_30}/{total_30} doses")
    with c4:
        kpi_card("Exames em atencao", exames_alerta, "fora ou perto dos limites")
    with c5:
        kpi_card("Sintomas 30d", resumo_sint["total"], f"{sintomas_fortes} fortes")
    with c6:
        kpi_card("Marcos recentes", len(marcos_recentes), "consultas e eventos")

    st.write("")

    left, mid, right = st.columns([1.05, 1.25, 0.9])

    with left:
        open_panel("Agenda de hoje", "O que ja foi tomado e o que falta tomar")
        if doses_hoje.empty:
            st.success("Nenhuma dose prevista para hoje.")
        else:
            for _, r in doses_hoje.iterrows():
                if r["status"] == "Tomado":
                    pill = '<span class="pill pill-aqua">Tomado</span>'
                elif r["status"] == "Pendente":
                    pill = '<span class="pill pill-warn">Pendente</span>'
                elif r["status"] == "Esquecido":
                    pill = '<span class="pill pill-danger">Esquecido</span>'
                else:
                    pill = f'<span class="pill pill-lilac">{r["status"]}</span>'

                mini_row(
                    f"{r['horario_previsto']} | {r['medicamento']}",
                    f"{r['dose'] if r['dose'] else ''} {pill}"
                )
        close_panel()

        open_panel("Marcos recentes", "Consultas, retornos e mudanças importantes")
        if marcos_recentes.empty:
            st.info("Nenhum marco registrado ainda.")
        else:
            st.caption(gerar_leitura_marcos(usuario_id, limite=5))
            for _, m in marcos_recentes.head(4).iterrows():
                mini_row(
                    f"{br_date(m['data_marco'])} | {m['tipo_marco']}",
                    f"{m['titulo']} | {m.get('especialidade') or ''}"
                )
        close_panel()

        open_panel("Sintomas recentes", "O que voce registrou nos ultimos dias")
        if sintomas_30.empty:
            st.info("Nenhum sintoma registrado nos ultimos 30 dias.")
        else:
            for _, s in sintomas_30.head(4).iterrows():
                med = f" | {s['medicamento']}" if s.get("medicamento") else ""
                mini_row(
                    f"{br_date(s['data_sintoma'])} | {s['sintoma']} | {int(s['intensidade'] or 0)}/10",
                    f"{s.get('gatilho') or ''}{med}"
                )
        close_panel()

        open_panel("Comando rapido", "Use digitacao por voz do teclado: 'tomei Neural agora'")
        comando = st.text_input("Digite ou dite um comando", placeholder="Ex.: tomei Neural agora")
        if st.button("Executar comando rapido"):
            msg = tentar_comando_rapido(usuario_id, comando)
            st.success(msg)
            recarregar()
        close_panel()

    with mid:
        open_panel("Exames em destaque", "Leitura simples dos exames mais recentes")
        if exames_rec.empty:
            st.info("Cadastre exames para gerar medidores.")
        else:
            show = exames_rec.head(4).reset_index(drop=True)
            grid = st.columns(2)
            for i, r in show.iterrows():
                with grid[i % 2]:
                    key = f"dashboard_card_gauge_{usuario_id}_{r.get('id', i)}_{i}_{str(r['nome_exame']).lower().replace(' ', '_')}"
                    render_card_exame(
                        nome=r["nome_exame"],
                        resultado=r["resultado"],
                        ref_min=r["referencia_min"],
                        ref_max=r["referencia_max"],
                        unidade=r["unidade"],
                        key=key,
                    )
        close_panel()

    with right:
        open_panel("Proxima dose", "Proximo item pendente")
        if prox.empty:
            st.success("Nenhuma dose pendente futura.")
        else:
            r = prox.iloc[0]
            status_pill(br_date(r["data_prevista"]), "turq")
            status_pill(r["horario_previsto"], "purple")
            st.write(f"**{r['medicamento']}**")
            st.caption(r["dose"] if r["dose"] else "")
        close_panel()

        open_panel("Alertas clinicos", "Pontos para observar")
        if exames_alerta == 0 and len(eventos_adversos) == 0 and pendentes_hoje == 0 and sintomas_fortes == 0:
            st.markdown(
                '<div class="alert-box alert-ok"><b>Sem alertas importantes agora.</b><br><span class="muted">Continue acompanhando.</span></div>',
                unsafe_allow_html=True
            )
        else:
            if exames_alerta > 0:
                st.markdown(
                    f'<div class="alert-box alert-warn"><b>{exames_alerta} exame(s) em atencao</b><br><span class="muted">Confira os medidores.</span></div>',
                    unsafe_allow_html=True
                )
            if sintomas_fortes > 0:
                st.markdown(
                    f'<div class="alert-box alert-danger"><b>{sintomas_fortes} sintoma(s) forte(s)</b><br><span class="muted">Intensidade 7 ou mais nos ultimos 30 dias.</span></div>',
                    unsafe_allow_html=True
                )
            if len(eventos_adversos) > 0:
                st.markdown(
                    f'<div class="alert-box alert-danger"><b>{len(eventos_adversos)} evento(s) adverso(s)</b><br><span class="muted">Leve isso para a consulta.</span></div>',
                    unsafe_allow_html=True
                )
            if pendentes_hoje > 0:
                st.markdown(
                    f'<div class="alert-box alert-warn"><b>{pendentes_hoje} dose(s) pendente(s) hoje</b><br><span class="muted">Marque como tomada ou esquecida.</span></div>',
                    unsafe_allow_html=True
                )
        close_panel()

    bottom1, bottom2, bottom3 = st.columns(3)

    with bottom1:
        open_panel("Corpo", "Ultima bioimpedancia")
        if bio_rec.empty:
            st.info("Sem dados corporais.")
        else:
            b = bio_rec.iloc[0]
            st.markdown(
                f'<div class="big-number">{fmt_num(b["peso_kg"], 1)} kg</div>',
                unsafe_allow_html=True
            )
            status_pill(f"Gordura {fmt_num(b['gordura_percentual'], 1)}%", "lilac")
            status_pill(f"Cintura {fmt_num(b['cintura_cm'], 1)} cm", "turq")
            st.caption(f"Medicao: {br_date(b['data_medicao'])}")
        close_panel()

    with bottom2:
        open_panel("Atividade 7 dias", "Movimento registrado")
        if atividades_7.empty:
            st.info("Sem atividades nos ultimos 7 dias.")
        else:
            total_min = int(atividades_7["duracao_min"].fillna(0).sum())
            st.markdown(
                f'<div class="big-number">{total_min} min</div>',
                unsafe_allow_html=True
            )
            status_pill(f"{len(atividades_7)} atividade(s)", "aqua")
            if "passos" in atividades_7.columns:
                passos = int(atividades_7["passos"].fillna(0).sum())
                status_pill(f"{passos} passos", "turq")
        close_panel()

    with bottom3:
        open_panel("Documentos recentes", "Receitas, consultas, farmacia e exames")
        if docs_recentes.empty:
            st.info("Nenhum documento salvo.")
        else:
            for _, d in docs_recentes.head(4).iterrows():
                mini_row(
                    d["titulo"],
                    f"{d['tipo_documento']} | {br_date(d['data_documento'])}"
                )
        close_panel()
