import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, mini_row
from core.database import consultar_df
from core.helpers import br_date


def render_timeline(usuario_id):
    open_panel("Linha do tempo de saude", "Tudo que aconteceu em ordem cronologica")

    marcos_t = consultar_df(
        """
        SELECT id, data_marco AS data, 'Marco da jornada' AS tipo,
               tipo_marco || ': ' || titulo || ' | ' || COALESCE(queixas, '') || ' ' || COALESCE(conduta, '') AS descricao
        FROM marcos_jornada WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    exames_t = consultar_df(
        """
        SELECT id, data_exame AS data, 'Exame' AS tipo,
               nome_exame || ': ' || resultado || ' ' || COALESCE(unidade, '') AS descricao
        FROM exames WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    meds_t = consultar_df(
        """
        SELECT id, data_inicio AS data, 'Medicamento' AS tipo,
               nome || ' - inicio do tratamento' AS descricao
        FROM medicamentos WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    eventos_t = consultar_df(
        """
        SELECT id, data_evento AS data, 'Evento medicacao' AS tipo,
               tipo_evento || ': ' || COALESCE(motivo, '') || ' ' || COALESCE(sintomas, '') AS descricao
        FROM eventos_medicacao WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    sintomas_t = consultar_df(
        """
        SELECT id, data_sintoma AS data, 'Sintoma' AS tipo,
               sintoma || ' | intensidade ' || intensidade || '/10 | ' || COALESCE(observacao, '') AS descricao
        FROM sintomas_diario WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    bio_t = consultar_df(
        """
        SELECT id, data_medicao AS data, 'Corpo' AS tipo,
               'Peso: ' || peso_kg || ' kg | Gordura: ' || gordura_percentual || '%' AS descricao
        FROM bioimpedancia WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    ativ_t = consultar_df(
        """
        SELECT id, data_atividade AS data, 'Atividade' AS tipo,
               tipo || ' por ' || duracao_min || ' min' AS descricao
        FROM atividades WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    docs_t = consultar_df(
        """
        SELECT id, data_documento AS data, 'Documento' AS tipo,
               tipo_documento || ': ' || titulo AS descricao
        FROM documentos_saude WHERE usuario_id = ? AND COALESCE(excluido, 0) = 0
        """,
        (usuario_id,),
    )

    rapido_t = consultar_df(
        """
        SELECT id, data_registro AS data, 'Registro rapido' AS tipo,
               categoria || ': ' || texto AS descricao
        FROM registros_rapidos WHERE usuario_id = ?
        """,
        (usuario_id,),
    )

    timeline = pd.concat(
        [marcos_t, exames_t, meds_t, eventos_t, sintomas_t, bio_t, ativ_t, docs_t, rapido_t],
        ignore_index=True
    )

    if timeline.empty:
        st.info("Linha do tempo vazia.")
    else:
        timeline["data_sort"] = pd.to_datetime(timeline["data"], errors="coerce")
        timeline = timeline.sort_values("data_sort", ascending=False)

        filtro_tipo = st.multiselect(
            "Filtrar tipos",
            sorted(timeline["tipo"].dropna().unique().tolist()),
            default=sorted(timeline["tipo"].dropna().unique().tolist()),
        )

        timeline = timeline[timeline["tipo"].isin(filtro_tipo)]

        for _, r in timeline.iterrows():
            mini_row(f"{br_date(r['data'])} | {r['tipo']}", r["descricao"])

    close_panel()
