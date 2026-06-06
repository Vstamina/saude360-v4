import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, fmt_num, recarregar
from services.biblioteca_exames_service import (
    catalogo_df,
    exames_para_padronizar,
    aplicar_padronizacao_lote,
    trilhas_por_exame_padronizado,
    detalhes_trilha,
    info_catalogo,
    resumo_biblioteca,
)


def render_biblioteca_exames(usuario_id):
    open_panel("Biblioteca de exames", "Padronize nomes de exames para criar trilhas mais confiáveis ao longo do tempo.")

    resumo = resumo_biblioteca(usuario_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        status_pill(f"{resumo['total']} exames", "purple")
    with c2:
        status_pill(f"{resumo['sem_padronizar']} sem padrão", "warn" if resumo["sem_padronizar"] else "aqua")
    with c3:
        status_pill(f"{resumo['baixa_confianca']} baixa confiança", "warn" if resumo["baixa_confianca"] else "aqua")
    with c4:
        status_pill(f"{resumo['categorias']} categorias", "lilac")

    st.info(resumo["leitura"])

    tabs = st.tabs(["Padronizar", "Trilhas", "Catálogo", "Orientações"])

    with tabs[0]:
        st.subheader("Padronização assistida")

        df = exames_para_padronizar(usuario_id)

        if df.empty:
            st.success("Nenhum exame cadastrado.")
        else:
            st.caption("Revise a sugestão antes de aplicar. O sistema não altera resultados, apenas organiza nome e categoria.")

            edit = st.data_editor(
                df,
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "aplicar": st.column_config.CheckboxColumn("Aplicar"),
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "data_exame": "Data",
                    "nome_exame": st.column_config.TextColumn("Nome original", disabled=True),
                    "resultado": st.column_config.NumberColumn("Resultado", disabled=True),
                    "unidade": st.column_config.TextColumn("Unidade", disabled=True),
                    "nome_padronizado_atual": st.column_config.TextColumn("Padrão atual", disabled=True),
                    "categoria_atual": st.column_config.TextColumn("Categoria atual", disabled=True),
                    "nome_padronizado_sugerido": "Nome padronizado",
                    "categoria_sugerida": "Categoria",
                    "confianca": st.column_config.TextColumn("Confiança", disabled=True),
                    "observacao_padronizacao": "Observação",
                },
                key="editor_padronizacao_exames",
            )

            if st.button("Aplicar padronização selecionada"):
                total = aplicar_padronizacao_lote(usuario_id, edit)
                st.success(f"{total} exame(s) padronizado(s).")
                recarregar()

    with tabs[1]:
        st.subheader("Trilhas por exame padronizado")

        trilhas = trilhas_por_exame_padronizado(usuario_id)

        if trilhas.empty:
            st.info("Sem trilhas disponíveis.")
        else:
            st.dataframe(trilhas, width="stretch", hide_index=True)

            opcoes = {f"{r['exame']} | {r['registros']} registro(s)": r["exame"] for _, r in trilhas.iterrows()}
            escolha = st.selectbox("Ver detalhes da trilha", list(opcoes.keys()))
            exame = opcoes[escolha]

            info = info_catalogo(exame)
            status_pill(info["categoria"], "purple")
            st.write(f"**O que observar:** {info['o_que_observar']}")
            st.write(f"**Pergunta útil:** {info['perguntas']}")

            detalhes = detalhes_trilha(usuario_id, exame)
            if detalhes.empty:
                st.info("Sem detalhes.")
            else:
                st.subheader("Histórico da trilha")
                for _, r in detalhes.iterrows():
                    mini_row(
                        f"{br_date(r.get('data_exame'))} | {r.get('nome_exame') or ''}",
                        f"Resultado: {fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''} | Ref.: {fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)}",
                    )

    with tabs[2]:
        st.subheader("Catálogo base")
        cat = catalogo_df()
        st.dataframe(
            cat[["nome_padronizado", "categoria", "unidades_comuns", "o_que_observar", "perguntas"]],
            width="stretch",
            hide_index=True,
        )

    with tabs[3]:
        st.subheader("Como usar esta área")

        st.markdown(
            """
            A biblioteca resolve um problema prático: o mesmo exame pode aparecer escrito de formas diferentes.

            Exemplos:

            - `ferritina`
            - `Ferritina sérica`
            - `FERRITINA`
            - `Ferritina - soro`

            Depois da padronização, todos entram na mesma trilha **Ferritina**.

            Isso melhora:

            - comparação ao longo do tempo;
            - relatório para consulta;
            - inteligência da jornada;
            - leitura de exames em atenção;
            - organização por categoria.

            A padronização **não interpreta diagnóstico**. Ela apenas organiza nomes e categorias.
            """
        )

    close_panel()
