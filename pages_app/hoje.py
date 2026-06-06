import streamlit as st
from components.cards import open_panel, close_panel, status_pill, mini_row
from core.helpers import recarregar
from services.medicamentos_service import listar_doses_hoje, marcar_dose
from services.pendencias_service import listar_pendencias

def render_hoje(usuario_id):
    open_panel('Agenda de hoje', 'Confirme o que tomou ou registre por que não tomou.')
    doses=listar_doses_hoje(usuario_id)
    if doses.empty: st.success('Nenhuma dose prevista para hoje.')
    else:
        for _,r in doses.iterrows():
            dose_id=int(r['id']); status=r['status']; st.markdown('---')
            c1,c2,c3=st.columns([1,2.2,2.2])
            with c1:
                st.write(f"**{r['horario_previsto']}**")
                status_pill('Tomado' if status=='Tomado' else 'Pendente' if status=='Pendente' else 'Não tomado' if status in ['Esquecido','Não tomado','Nao tomado'] else status, 'aqua' if status=='Tomado' else 'warn' if status=='Pendente' else 'danger')
            with c2:
                st.write(f"**{r['medicamento']}**"); st.caption(r['dose'] or '')
                if r.get('motivo_nao_tomou'): st.caption(f"Motivo: {r.get('motivo_nao_tomou')}")
                if r.get('observacao'): st.caption(f"Obs.: {r.get('observacao')}")
            with c3:
                if status=='Pendente':
                    if st.button('Tomei', key=f'tomei_{dose_id}'):
                        marcar_dose(dose_id, usuario_id, 'Tomado'); st.success('Dose marcada como tomada.'); recarregar()
                    with st.expander('Não tomei'):
                        motivo=st.selectbox('Por quê?', ['Esqueci','Acabou a medicação','Fez mal','Orientação médica','Não quis tomar','Outro'], key=f'motivo_nao_{dose_id}')
                        obs=st.text_area('Observação', key=f'obs_nao_{dose_id}', placeholder='Ex.: senti enjoo, acabou ontem, vou pedir receita...')
                        if st.button('Registrar não tomada', key=f'btn_nao_{dose_id}'):
                            marcar_dose(dose_id, usuario_id, 'Não tomado', obs=obs, motivo_nao_tomou=motivo, acao_sugerida='Gerar pendência conforme motivo')
                            st.warning('Dose registrada como não tomada. Se o motivo exigir ação, uma pendência foi criada.'); recarregar()
                else: st.caption('Registro já realizado.')
    close_panel()
    open_panel('Pendências abertas', 'O que precisa ser resolvido depois dos registros de hoje')
    pend=listar_pendencias(usuario_id, status='Aberta')
    if pend.empty: st.success('Nenhuma pendência aberta.')
    else:
        for _,p in pend.head(8).iterrows():
            prioridade=p.get('prioridade') or ''; cor='danger' if prioridade=='Alta' else ('warn' if prioridade=='Média' else 'aqua')
            status_pill(prioridade, cor); mini_row(f"{p['tipo']} | {p['titulo']}", p.get('descricao') or '')
    close_panel()
