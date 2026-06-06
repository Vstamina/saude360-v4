import streamlit as st
from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import br_date, recarregar
from services.pendencias_service import listar_pendencias, resolver_pendencia, reabrir_pendencia

def render_pendencias(usuario_id):
    open_panel('Pendências de cuidado', 'Ações que nasceram de doses não tomadas, reações, falta de medicação ou necessidade de falar com o profissional.')
    abertas=listar_pendencias(usuario_id, status='Aberta'); resolvidas=listar_pendencias(usuario_id, status='Resolvida')
    c1,c2=st.columns(2)
    with c1: status_pill(f'{len(abertas)} abertas', 'warn' if len(abertas) else 'aqua')
    with c2: status_pill(f'{len(resolvidas)} resolvidas', 'aqua')
    st.subheader('Abertas')
    if abertas.empty: st.success('Nenhuma pendência aberta.')
    else:
        for _,p in abertas.iterrows():
            st.markdown('---'); prioridade=p.get('prioridade') or ''; cor='danger' if prioridade=='Alta' else ('warn' if prioridade=='Média' else 'aqua')
            status_pill(prioridade, cor); st.write(f"**{p['titulo']}**"); st.caption(f"{br_date(p['data_criacao'])} | {p['tipo']} | origem: {p.get('origem') or ''}"); st.write(p.get('descricao') or '')
            with st.expander('Resolver pendência'):
                resolucao=st.text_area('Como foi resolvido?', key=f"resolucao_{p['id']}")
                if st.button('Marcar como resolvida', key=f"resolver_{p['id']}"):
                    resolver_pendencia(usuario_id, int(p['id']), resolucao); st.success('Pendência resolvida.'); recarregar()
    st.divider(); st.subheader('Resolvidas')
    if resolvidas.empty: st.caption('Nenhuma pendência resolvida ainda.')
    else:
        for _,p in resolvidas.head(10).iterrows():
            mini_row(f"{br_date(p['data_resolucao'])} | {p['titulo']}", p.get('resolucao') or '')
            if st.button('Reabrir', key=f"reabrir_{p['id']}"):
                reabrir_pendencia(usuario_id, int(p['id'])); st.success('Pendência reaberta.'); recarregar()
    close_panel()
