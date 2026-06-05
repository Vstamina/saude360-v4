import streamlit as st


def kpi_card(label, value, sub=""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def open_panel(title, subtitle=None):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="panel-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="panel-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def close_panel():
    st.markdown("</div>", unsafe_allow_html=True)


def status_pill(texto, tipo="aqua"):
    st.markdown(f'<span class="pill pill-{tipo}">{texto}</span>', unsafe_allow_html=True)


def mini_row(titulo, subtitulo=""):
    st.markdown(
        f"""
        <div class="mini-row">
            <div class="mini-title">{titulo}</div>
            <div class="mini-sub">{subtitulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
