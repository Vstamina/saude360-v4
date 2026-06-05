import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from components.gauges import render_card_exame
from core.helpers import br_date, fmt_num
from services.evolucao_service import (
    listar_medicamentos_para_evolucao,
    obter_medicamento,
    buscar_exames_antes_depois,
    buscar_corpo_antes_depois,
    buscar_eventos_no_periodo,
    buscar_sintomas_no_periodo,
    buscar_marcos_no_periodo,
    buscar_documentos_relacionados,
    buscar_atividades_no_periodo,
    gerar_leitura_evolucao,
)


def _formatar_tabela_valores(df):
    if df is None or df.empty:
        return df

    view = df.copy()
    for col in ["antes", "depois"]:
        if col in view.columns:
            view[col] = view[col].apply(lambda x: fmt_num(x, 2) if pd.notna(x) and x != "" else "")
    return view


def render_evolucao_tratamento(usuario_id):
    open_panel("Evolucao por tratamento", "Veja o que mudou no corpo, nos exames, nos sintomas, nos marcos e nos eventos depois de iniciar um medicamento.")

    meds = listar_medicamentos_para_evolucao(usuario_id)

    if meds.empty:
        st.info("Cadastre um medicamento para acompanhar evolucao por tratamento.")
        close_panel()
        return

    opcoes = {
        f"{r['nome']} | {r['dose'] or ''} | inicio {br_date(r['data_inicio'])} | {r['status']} | ID {r['id']}": int(r["id"])
        for _, r in meds.iterrows()
    }

    med_label = st.selectbox("Escolha o tratamento", list(opcoes.keys()))
    med_id = opcoes[med_label]

    med_df = obter_medicamento(usuario_id, med_id)
    if med_df.empty:
        st.warning("Medicamento nao encontrado.")
        close_panel()
        return

    med = med_df.iloc[0].to_dict()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(med.get("status", "Ativo"), "aqua" if med.get("status") == "Ativo" else "warn")
        st.write("**Status**")
    with c2:
        st.write("**Inicio**")
        st.caption(br_date(med.get("data_inicio")))
    with c3:
        st.write("**Fim/status**")
        st.caption(br_date(med.get("data_fim") or med.get("data_status")))
    with c4:
        st.write("**Profissional**")
        st.caption(med.get("medico") or "")

    if med.get("motivo_status"):
        st.warning(f"Motivo/status: {med.get('motivo_status')}")

    st.divider()

    exames_df = buscar_exames_antes_depois(usuario_id, med.get("data_inicio"))
    corpo_df = buscar_corpo_antes_depois(usuario_id, med.get("data_inicio"))
    eventos_df = buscar_eventos_no_periodo(usuario_id, med_id, med.get("data_inicio"), med.get("data_fim") or med.get("data_status"))
    sintomas_df = buscar_sintomas_no_periodo(usuario_id, med_id, med.get("data_inicio"), med.get("data_fim") or med.get("data_status"))
    marcos_df = buscar_marcos_no_periodo(usuario_id, med.get("data_inicio"), med.get("data_fim") or med.get("data_status"))
    docs_df = buscar_documentos_relacionados(usuario_id, med.get("nome"))
    atividades_df = buscar_atividades_no_periodo(usuario_id, med.get("data_inicio"), med.get("data_fim") or med.get("data_status"))

    st.subheader("Leitura inteligente")
    leitura = gerar_leitura_evolucao(med, exames_df, corpo_df, eventos_df, atividades_df, sintomas_df, marcos_df)
    st.info(leitura)

    close_panel()

    col_a, col_b = st.columns([1.15, 1])

    with col_a:
        open_panel("Marcos no periodo", "Consultas, retornos e mudanças de conduta que ajudam a explicar a evolução")
        if marcos_df.empty:
            st.info("Nenhum marco registrado no periodo do tratamento.")
        else:
            for _, m in marcos_df.head(8).iterrows():
                mini_row(
                    f"{br_date(m['data_marco'])} | {m['tipo_marco']}",
                    f"{m['titulo']} | {m.get('conduta') or m.get('queixas') or ''}"
                )
        close_panel()

        open_panel("Corpo antes e depois", "Peso, gordura, massa magra e cintura")
        if corpo_df.empty:
            st.info("Nao ha bioimpedancia/medidas suficientes no periodo.")
        else:
            view = _formatar_tabela_valores(corpo_df)
            st.dataframe(
                view[["indicador", "data_antes", "antes", "data_depois", "depois", "unidade", "variacao"]],
                width="stretch",
                hide_index=True,
            )
        close_panel()

    with col_b:
        open_panel("Sintomas no periodo", "Relatos associados ao tratamento ou ao mesmo periodo")
        if sintomas_df.empty:
            st.success("Nenhum sintoma registrado no periodo.")
        else:
            fortes = len(sintomas_df[sintomas_df["intensidade"].fillna(0) >= 7])
            status_pill(f"{len(sintomas_df)} sintoma(s)", "lilac")
            status_pill(f"{fortes} forte(s)", "danger" if fortes else "aqua")
            for _, s in sintomas_df.head(6).iterrows():
                med_nome = f" | {s['medicamento']}" if s.get("medicamento") else ""
                mini_row(
                    f"{br_date(s['data_sintoma'])} {s['horario'] or ''} | {s['sintoma']} | {int(s['intensidade'] or 0)}/10",
                    f"{s.get('gatilho') or ''}{med_nome} | {s.get('observacao') or ''}",
                )
        close_panel()

    open_panel("Exames antes e depois", "Comparacao laboratorial associada ao periodo do tratamento")
    if exames_df.empty:
        st.info("Nao ha exames suficientes no periodo para comparar.")
    else:
        view = _formatar_tabela_valores(exames_df)
        st.dataframe(
            view[["indicador", "data_antes", "antes", "data_depois", "depois", "unidade", "variacao", "referencia_min", "referencia_max"]],
            width="stretch",
            hide_index=True,
        )

        st.subheader("Resultados depois do inicio")
        cols = st.columns(3)
        medidores = exames_df[exames_df["depois"].notna()].reset_index(drop=True)
        if medidores.empty:
            st.caption("Ainda nao ha exames depois do inicio do tratamento.")
        else:
            for i, r in medidores.iterrows():
                with cols[i % 3]:
                    key = f"evolucao_card_gauge_{usuario_id}_{med_id}_{i}_{str(r['indicador']).lower().replace(' ', '_')}"
                    render_card_exame(
                        nome=r["indicador"],
                        resultado=r["depois"],
                        ref_min=r["referencia_min"],
                        ref_max=r["referencia_max"],
                        unidade=r["unidade"],
                        key=key,
                    )
    close_panel()

    col_c, col_d = st.columns(2)

    with col_c:
        open_panel("Eventos no periodo", "STOP, efeitos adversos, pausas e observacoes")
        if eventos_df.empty:
            st.success("Nenhum evento adverso/alteracao registrado no periodo.")
        else:
            for _, e in eventos_df.iterrows():
                mini_row(
                    f"{br_date(e['data_evento'])} | {e['tipo_evento']}",
                    f"{e.get('motivo') or ''} {e.get('sintomas') or ''} {e.get('observacao') or ''}",
                )
        close_panel()

    with col_d:
        open_panel("Atividade e documentos", "Movimento e arquivos relacionados ao tratamento")
        if atividades_df.empty:
            st.caption("Nenhuma atividade registrada no periodo.")
        else:
            total_min = int(atividades_df["duracao_min"].fillna(0).sum()) if "duracao_min" in atividades_df.columns else 0
            status_pill(f"{len(atividades_df)} atividade(s)", "aqua")
            status_pill(f"{total_min} min", "turq")

        st.divider()

        if docs_df.empty:
            st.info("Nenhum documento relacionado encontrado pelo nome do medicamento.")
        else:
            for _, d in docs_df.iterrows():
                mini_row(
                    f"{br_date(d['data_documento'])} | {d['tipo_documento']}",
                    f"{d['titulo']} | {d.get('relacionado_a') or ''}",
                )
        close_panel()
