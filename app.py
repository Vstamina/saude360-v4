import streamlit as st

from core.database import init_db
from core.helpers import data_input_br, recarregar
from core.theme import aplicar_tema
from services.usuarios_service import salvar_usuario
from services.familia_service import listar_usuarios_ativos, listar_usuarios_todos

from pages_app.dashboard import render_dashboard
from pages_app.hoje import render_hoje
from pages_app.marcos import render_marcos
from pages_app.medicamentos import render_medicamentos
from pages_app.eventos import render_eventos
from pages_app.historico_tolerancia import render_historico_tolerancia
from pages_app.exames import render_exames
from pages_app.corpo_atividade import render_corpo_atividade
from pages_app.sintomas import render_sintomas
from pages_app.documentos import render_documentos
from pages_app.importar_documento import render_importar_documento
from pages_app.correcoes import render_correcoes
from pages_app.cadastros_familia import render_cadastros_familia
from pages_app.consulta import render_consulta
from pages_app.evolucao_tratamento import render_evolucao_tratamento
from pages_app.timeline import render_timeline

from datetime import date

APP_TITLE = "Saude 360"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
aplicar_tema()

st.sidebar.markdown("## Saude 360")
st.sidebar.caption("Dashboard pessoal de saude")

usuarios_todos = listar_usuarios_todos()
usuarios_ativos = listar_usuarios_ativos()

with st.sidebar.expander("Cadastrar usuario", expanded=usuarios_todos.empty):
    nome_user = st.text_input("Nome completo")
    data_nasc = data_input_br("Data de nascimento", date(1990, 1, 1), key="user_nasc")
    sexo = st.selectbox("Sexo para referencias laboratoriais", ["Nao informado", "Feminino", "Masculino"])
    altura = st.number_input("Altura em cm", min_value=0.0, max_value=250.0, value=170.0)
    objetivo = st.text_area("Objetivo de acompanhamento", placeholder="Ex.: metabolismo, ferritina, emagrecimento, treino...")

    if st.button("Salvar usuario"):
        if not nome_user.strip():
            st.warning("Informe o nome.")
        else:
            salvar_usuario(nome_user, data_nasc, sexo, altura, objetivo)
            st.success("Usuario salvo.")
            recarregar()

usuarios_todos = listar_usuarios_todos()
usuarios_ativos = listar_usuarios_ativos()

if usuarios_todos.empty:
    st.markdown(
        """
        <div class="hero">
            <h1>Saude 360</h1>
            <p>Cadastre um usuario na lateral para iniciar o acompanhamento.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

if usuarios_ativos.empty:
    st.warning("Todos os cadastros estão desativados. Reative um cadastro na aba Cadastros da família.")
    usuarios_selecao = usuarios_todos
else:
    usuarios_selecao = usuarios_ativos

opcoes = {f"{row['nome']} - ID {row['id']}": int(row["id"]) for _, row in usuarios_selecao.iterrows()}
usuario_label = st.sidebar.selectbox("Usuario ativo", list(opcoes.keys()))
usuario_id = opcoes[usuario_label]
usuario = usuarios_selecao[usuarios_selecao["id"] == usuario_id].iloc[0]

st.sidebar.divider()
st.sidebar.caption("Dica: use a aba Visao da minha saude primeiro. Cadastros ficam nas abas especificas.")

st.markdown(
    f"""
    <div class="hero">
        <h1>Saude 360</h1>
        <p>{usuario['nome']} | Acompanhamento longitudinal de medicamentos, exames, corpo, sintomas, documentos e eventos adversos.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Uso informativo. O sistema organiza dados e gera leituras de acompanhamento; nao realiza diagnostico, nao prescreve tratamento e nao substitui avaliacao medica."
)

tabs = st.tabs(
    [
        "Visao da minha saude",
        "Hoje",
        "Consultas e marcos",
        "Medicamentos",
        "STOP e eventos",
        "Historico de tolerancia",
        "Exames",
        "Corpo e atividade",
        "Sintomas e diario",
        "Documentos",
        "Importar documento",
        "Central de correcoes",
        "Cadastros da familia",
        "Consulta medica",
        "Evolucao por tratamento",
        "Linha do tempo",
    ]
)

with tabs[0]:
    render_dashboard(usuario_id, usuario)

with tabs[1]:
    render_hoje(usuario_id)

with tabs[2]:
    render_marcos(usuario_id)

with tabs[3]:
    render_medicamentos(usuario_id)

with tabs[4]:
    render_eventos(usuario_id)

with tabs[5]:
    render_historico_tolerancia(usuario_id, usuario)

with tabs[6]:
    render_exames(usuario_id)

with tabs[7]:
    render_corpo_atividade(usuario_id)

with tabs[8]:
    render_sintomas(usuario_id)

with tabs[9]:
    render_documentos(usuario_id)

with tabs[10]:
    render_importar_documento(usuario_id, usuario)

with tabs[11]:
    render_correcoes(usuario_id, usuario)

with tabs[12]:
    render_cadastros_familia(usuario_id)

with tabs[13]:
    render_consulta(usuario_id, usuario)

with tabs[14]:
    render_evolucao_tratamento(usuario_id)

with tabs[15]:
    render_timeline(usuario_id)
