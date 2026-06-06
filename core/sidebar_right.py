import streamlit as st


def aplicar_sidebar_direita():
    """
    Move visualmente a sidebar nativa do Streamlit para a direita.

    Observação:
    - É um ajuste visual por CSS.
    - Mantém os componentes originais da sidebar.
    - Se o Streamlit mudar muito a estrutura interna, pode precisar de ajuste futuro.
    """
    st.markdown(
        """
        <style>
        /* Move a sidebar para a direita */
        section[data-testid="stSidebar"] {
            left: auto !important;
            right: 0 !important;
            border-left: 1px solid rgba(15, 31, 51, 0.10);
            border-right: none !important;
            box-shadow: -18px 0 45px rgba(15, 31, 51, 0.08);
        }

        /* Ajusta a área principal para não ficar por baixo da sidebar */
        div[data-testid="stAppViewContainer"] > .main {
            margin-left: 0 !important;
            margin-right: 21rem !important;
        }

        /* Em telas menores, volta a se comportar melhor */
        @media (max-width: 1100px) {
            section[data-testid="stSidebar"] {
                right: 0 !important;
                left: auto !important;
            }

            div[data-testid="stAppViewContainer"] > .main {
                margin-right: 0 !important;
            }
        }

        /* Dá um acabamento mais leve ao painel lateral */
        section[data-testid="stSidebar"] > div {
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,250,252,0.96)) !important;
        }

        /* Evita que o menu pareça colado no topo */
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding-top: 3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
