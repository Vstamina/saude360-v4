import urllib.parse
from datetime import date

import streamlit as st

from core.database import init_db
from core.schema_guard import garantir_schema_completo
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
from pages_app.importacao_inteligente import render_importacao_inteligente
from pages_app.importar_documento import render_importar_documento
from pages_app.pendencias import render_pendencias
from pages_app.revisao import render_revisao
from pages_app.correcoes import render_correcoes
from pages_app.cadastros_familia import render_cadastros_familia
from pages_app.backup import render_backup
from pages_app.consulta import render_consulta
from pages_app.evolucao_tratamento import render_evolucao_tratamento
from pages_app.timeline import render_timeline
from pages_app.continuidade import render_continuidade
from pages_app.agenda import render_agenda
from pages_app.jornada_inteligente import render_jornada_inteligente
from pages_app.painel_familia import render_painel_familia
from pages_app.biblioteca_exames import render_biblioteca_exames
from pages_app.busca_inteligente import render_busca_inteligente
from pages_app.privacidade import render_privacidade
from pages_app.app_local import render_app_local
from services.app_local_service import backup_automatico_se_necessario

APP_TITLE = "Saude 360"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()
garantir_schema_completo()
aplicar_tema()

try:
    backup_automatico_se_necessario()
except Exception:
    pass

PAGES = {
    "visao": "Visão da minha saúde",
    "hoje": "Hoje",
    "importar": "Importação inteligente",
    "pendencias": "Pendências",
    "revisao": "Revisão inteligente",
    "marcos": "Consultas e marcos",
    "medicamentos": "Medicamentos",
    "eventos": "STOP e eventos",
    "tolerancia": "Histórico de tolerância",
    "exames": "Exames",
    "corpo": "Corpo e atividade",
    "sintomas": "Sintomas e diário",
    "documentos": "Documentos",
    "importar_antigo": "Importar documento antigo",
    "correcoes": "Central de correções",
    "familia": "Cadastros da família",
    "backup": "Backup e segurança",
    "consulta": "Consulta médica",
    "evolucao": "Evolução por tratamento",
    "timeline": "Linha do tempo",
    "continuidade": "Continuidade",
    "agenda": "Agenda de cuidado",
    "inteligencia": "Inteligência da jornada",
    "familia360": "Família 360",
    "biblioteca_exames": "Biblioteca de exames",
    "busca": "Busca inteligente",
    "privacidade": "Privacidade",
    "app_local": "Aplicativo local",
    "mais": "Mais áreas",
}


def get_page_slug():
    try:
        slug = st.query_params.get("page", "visao")
    except Exception:
        slug = "visao"

    if isinstance(slug, list):
        slug = slug[0] if slug else "visao"

    if slug not in PAGES:
        slug = "visao"

    return slug


def nav_href(slug):
    return f"?page={urllib.parse.quote(slug)}"


def nav_item(slug, label, active_slug):
    active = " active" if slug == active_slug else ""
    return f'<a class="bottom-nav-item{active}" href="{nav_href(slug)}" target="_self">{label}</a>'


def more_item(slug, label):
    return f'<a class="more-drawer-item" href="{nav_href(slug)}" target="_self">{label}</a>'


st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        display: none !important;
    }

    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    .block-container {
        padding-bottom: 8.7rem !important;
    }

    .right-panel-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(245,250,252,0.94));
        border: 1px solid rgba(15,31,51,0.10);
        border-radius: 26px;
        padding: 1.2rem 1.1rem;
        box-shadow: 0 18px 42px rgba(15,31,51,0.08);
        position: sticky;
        top: 1rem;
    }

    .right-panel-card h2 {
        margin: 0 0 .35rem 0;
        font-size: 1.35rem;
        color: #0B1F33;
    }

    .right-panel-card p {
        color: #7A8CA3;
        margin-top: 0;
        font-size: .92rem;
    }

    .side-hint {
        color: #7A8CA3;
        font-size: .86rem;
        line-height: 1.45;
        margin-top: 1rem;
    }

    .active-nav-hint {
        display: inline-block;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(204,245,241,0.98), rgba(230,224,255,0.98));
        color: #312E81;
        padding: .45rem .9rem;
        font-weight: 850;
        margin: 1rem 0 .7rem 0;
        box-shadow: 0 8px 22px rgba(15,31,51,0.08);
    }

    /* Chão fixo real */
    .bottom-floor {
        position: fixed;
        left: 50%;
        bottom: 0;
        transform: translateX(-50%);
        width: min(1040px, calc(100vw - 24px));
        z-index: 999999;
        padding: 0.72rem 0.82rem 0.92rem 0.82rem;
        border-radius: 30px 30px 0 0;
        background:
            radial-gradient(circle at 15% 0%, rgba(204,245,241,0.95), transparent 35%),
            radial-gradient(circle at 85% 0%, rgba(230,224,255,0.98), transparent 38%),
            rgba(255,255,255,0.94);
        border: 1px solid rgba(15,31,51,0.10);
        border-bottom: none;
        box-shadow: 0 -20px 55px rgba(15,31,51,0.18);
        backdrop-filter: blur(18px);
    }

    .bottom-floor-label {
        position: absolute;
        left: 50%;
        top: -1.35rem;
        transform: translateX(-50%);
        background: rgba(11,31,51,0.94);
        color: #FFFFFF;
        border-radius: 999px;
        padding: .26rem .9rem;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .06em;
        text-transform: uppercase;
        box-shadow: 0 8px 22px rgba(15,31,51,0.22);
    }

    .bottom-nav-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: .55rem;
        align-items: center;
    }

    .bottom-nav-item {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 2.8rem;
        border-radius: 999px;
        text-decoration: none !important;
        color: #0B1F33 !important;
        font-weight: 850;
        font-size: .92rem;
        border: 1px solid rgba(15,31,51,0.10);
        background: rgba(255,255,255,0.90);
        box-shadow: 0 8px 20px rgba(15,31,51,0.06);
        cursor: pointer;
        user-select: none;
    }

    .bottom-nav-item:hover {
        background: linear-gradient(135deg, rgba(204,245,241,0.98), rgba(230,224,255,0.98));
        color: #312E81 !important;
        border-color: rgba(82,204,196,0.45);
    }

    .bottom-nav-item.active {
        background: linear-gradient(135deg, #BFF4EC, #E3DAFF);
        color: #312E81 !important;
        border-color: rgba(124,58,237,0.28);
        box-shadow: 0 10px 24px rgba(49,46,129,0.15);
    }

    /* Gaveta que sobe a partir do chão */
    .more-drawer {
        position: fixed;
        left: 50%;
        bottom: 5.35rem;
        transform: translateX(-50%);
        width: min(1040px, calc(100vw - 24px));
        z-index: 999998;
        padding: 1rem;
        border-radius: 30px;
        background: rgba(255,255,255,0.96);
        border: 1px solid rgba(15,31,51,0.10);
        box-shadow: 0 -18px 55px rgba(15,31,51,0.18);
        backdrop-filter: blur(18px);
        max-height: 52vh;
        overflow-y: auto;
    }

    .more-drawer h3 {
        margin: .1rem 0 .8rem 0;
        color: #0B1F33;
        font-size: 1.05rem;
    }

    .more-drawer-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .55rem;
    }

    .more-drawer-item {
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-height: 2.6rem;
        border-radius: 999px;
        text-decoration: none !important;
        color: #0B1F33 !important;
        font-size: .86rem;
        font-weight: 760;
        border: 1px solid rgba(15,31,51,0.10);
        background: rgba(255,255,255,0.96);
    }

    .more-drawer-item:hover {
        background: linear-gradient(135deg, rgba(204,245,241,0.98), rgba(230,224,255,0.98));
        color: #312E81 !important;
    }

    .more-drawer-close {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-top: .8rem;
        padding: .45rem .9rem;
        border-radius: 999px;
        background: rgba(11,31,51,0.92);
        color: #FFFFFF !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: .85rem;
    }

    @media (max-width: 1100px) {
        .right-panel-card {
            position: relative;
            top: 0;
        }

        .bottom-floor {
            width: calc(100vw - 10px);
            border-radius: 24px 24px 0 0;
        }

        .bottom-nav-grid {
            grid-template-columns: repeat(5, 1fr);
            gap: .32rem;
        }

        .bottom-nav-item {
            font-size: .75rem;
            min-height: 2.55rem;
        }

        .more-drawer {
            width: calc(100vw - 10px);
            bottom: 5.1rem;
        }

        .more-drawer-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_bottom_floor(active_slug):
    html = f"""
    <div class="bottom-floor">
        <div class="bottom-floor-label">Navegação</div>
        <div class="bottom-nav-grid">
            {nav_item("visao", "Visão", active_slug)}
            {nav_item("hoje", "Hoje", active_slug)}
            {nav_item("importar", "Importar", active_slug)}
            {nav_item("pendencias", "Pendências", active_slug)}
            {nav_item("mais", "Mais", active_slug)}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_more_drawer(active_slug):
    if active_slug != "mais":
        return

    items = [
        ("revisao", "Revisão inteligente"),
        ("marcos", "Consultas e marcos"),
        ("medicamentos", "Medicamentos"),
        ("eventos", "STOP e eventos"),
        ("tolerancia", "Histórico de tolerância"),
        ("exames", "Exames"),
        ("corpo", "Corpo e atividade"),
        ("sintomas", "Sintomas e diário"),
        ("documentos", "Documentos"),
        ("importar_antigo", "Importar documento antigo"),
        ("correcoes", "Central de correções"),
        ("familia", "Cadastros da família"),
        ("backup", "Backup e segurança"),
        ("consulta", "Consulta médica"),
        ("evolucao", "Evolução por tratamento"),
        ("timeline", "Linha do tempo"),
        ("continuidade", "Continuidade"),
        ("agenda", "Agenda de cuidado"),
        ("inteligencia", "Inteligência da jornada"),
        ("familia360", "Família 360"),
        ("biblioteca_exames", "Biblioteca de exames"),
        ("busca", "Busca inteligente"),
        ("privacidade", "Privacidade"),
        ("app_local", "Aplicativo local"),
    ]

    links = "\n".join(more_item(slug, label) for slug, label in items)

    html = f"""
    <div class="more-drawer">
        <h3>Mais áreas do Saúde 360</h3>
        <div class="more-drawer-grid">
            {links}
        </div>
        <a class="more-drawer-close" href="{nav_href("visao")}" target="_self">Fechar</a>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


usuarios_todos = listar_usuarios_todos()
usuarios_ativos = listar_usuarios_ativos()
active_slug = get_page_slug()

main_col, right_col = st.columns([4.15, 1.25], gap="large")

with right_col:
    st.markdown(
        """
        <div class="right-panel-card">
            <h2>Saude 360</h2>
            <p>Dashboard pessoal de saúde</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    with st.expander("Cadastrar usuário", expanded=usuarios_todos.empty):
        nome_user = st.text_input("Nome completo")
        data_nasc = data_input_br("Data de nascimento", date(1990, 1, 1), key="user_nasc")
        sexo = st.selectbox("Sexo para referências laboratoriais", ["Nao informado", "Feminino", "Masculino"])
        altura = st.number_input("Altura em cm", min_value=0.0, max_value=250.0, value=170.0)
        objetivo = st.text_area("Objetivo de acompanhamento", placeholder="Ex.: metabolismo, ferritina, emagrecimento, treino...")

        if st.button("Salvar usuário"):
            if not nome_user.strip():
                st.warning("Informe o nome.")
            else:
                salvar_usuario(nome_user, data_nasc, sexo, altura, objetivo)
                st.success("Usuário salvo.")
                recarregar()

    usuarios_todos = listar_usuarios_todos()
    usuarios_ativos = listar_usuarios_ativos()

    usuario_id = None
    usuario = None

    if usuarios_todos.empty:
        st.info("Cadastre um usuário para iniciar.")
    else:
        if usuarios_ativos.empty:
            st.warning("Todos os cadastros estão desativados. Reative um cadastro na aba Cadastros da família.")
            usuarios_selecao = usuarios_todos
        else:
            usuarios_selecao = usuarios_ativos

        opcoes = {f"{row['nome']} - ID {row['id']}": int(row["id"]) for _, row in usuarios_selecao.iterrows()}
        usuario_label = st.selectbox("Usuário ativo", list(opcoes.keys()))
        usuario_id = opcoes[usuario_label]
        usuario = usuarios_selecao[usuarios_selecao["id"] == usuario_id].iloc[0]

    st.divider()
    st.markdown(
        """
        <div class="side-hint">
        A barra inferior é o chão do app.
        O botão <b>Mais</b> abre as demais áreas de baixo para cima.
        </div>
        """,
        unsafe_allow_html=True,
    )

with main_col:
    if usuarios_todos.empty or usuario_id is None:
        st.markdown(
            """
            <div class="hero">
                <h1>Saude 360</h1>
                <p>Cadastre um usuário no painel à direita para iniciar o acompanhamento.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_bottom_floor(active_slug)
        render_more_drawer(active_slug)
        st.stop()

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
        "Uso informativo. O sistema organiza dados e gera leituras de acompanhamento; não realiza diagnóstico, não prescreve tratamento e não substitui avaliação médica."
    )

    render_bottom_floor(active_slug)
    render_more_drawer(active_slug)

    pagina_nome = PAGES.get(active_slug, "Visão da minha saúde")
    if active_slug == "mais":
        st.markdown('<span class="active-nav-hint">Escolha uma área no menu inferior</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="active-nav-hint">{pagina_nome}</span>', unsafe_allow_html=True)

    if active_slug == "visao" or active_slug == "mais":
        render_dashboard(usuario_id, usuario)
    elif active_slug == "hoje":
        render_hoje(usuario_id)
    elif active_slug == "importar":
        render_importacao_inteligente(usuario_id, usuario)
    elif active_slug == "pendencias":
        render_pendencias(usuario_id)
    elif active_slug == "revisao":
        render_revisao(usuario_id, usuario)
    elif active_slug == "marcos":
        render_marcos(usuario_id)
    elif active_slug == "medicamentos":
        render_medicamentos(usuario_id)
    elif active_slug == "eventos":
        render_eventos(usuario_id)
    elif active_slug == "tolerancia":
        render_historico_tolerancia(usuario_id, usuario)
    elif active_slug == "exames":
        render_exames(usuario_id)
    elif active_slug == "corpo":
        render_corpo_atividade(usuario_id)
    elif active_slug == "sintomas":
        render_sintomas(usuario_id)
    elif active_slug == "documentos":
        render_documentos(usuario_id)
    elif active_slug == "importar_antigo":
        render_importar_documento(usuario_id, usuario)
    elif active_slug == "correcoes":
        render_correcoes(usuario_id, usuario)
    elif active_slug == "familia":
        render_cadastros_familia(usuario_id)
    elif active_slug == "backup":
        render_backup()
    elif active_slug == "consulta":
        render_consulta(usuario_id, usuario)
    elif active_slug == "evolucao":
        render_evolucao_tratamento(usuario_id)
    elif active_slug == "timeline":
        render_timeline(usuario_id)
    elif active_slug == "continuidade":
        render_continuidade(usuario_id)
    elif active_slug == "agenda":
        render_agenda(usuario_id)
    elif active_slug == "inteligencia":
        render_jornada_inteligente(usuario_id, usuario)
    elif active_slug == "familia360":
        render_painel_familia(usuario_id, usuario)
    elif active_slug == "biblioteca_exames":
        render_biblioteca_exames(usuario_id)
    elif active_slug == "busca":
        render_busca_inteligente(usuario_id)
    elif active_slug == "privacidade":
        render_privacidade(usuario_id, usuario)
    elif active_slug == "app_local":
        render_app_local(usuario_id, usuario)
    else:
        render_dashboard(usuario_id, usuario)
