from datetime import date
from core.database import consultar_df, executar
from core.helpers import agora

def criar_pendencia(usuario_id, tipo, prioridade, titulo, descricao, origem='', medicamento_id=None, dose_id=None, marco_id=None):
    return executar("""INSERT INTO pendencias_cuidado (usuario_id,data_criacao,tipo,prioridade,titulo,descricao,origem,medicamento_id,dose_id,marco_id,status,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,'Aberta',?)""", (usuario_id,date.today().isoformat(),tipo,prioridade,titulo,descricao,origem,medicamento_id,dose_id,marco_id,agora()))

def criar_pendencia_por_motivo_nao_tomou(usuario_id, medicamento_id, dose_id, medicamento_nome, motivo, observacao=''):
    motivo = str(motivo or '').strip()
    if motivo == 'Acabou a medicação':
        return criar_pendencia(usuario_id,'Reposição / receita','Alta',f'Providenciar {medicamento_nome}',f'A dose de {medicamento_nome} não foi tomada porque a medicação acabou. Verificar compra, nova receita ou contato com profissional.','Dose não tomada',medicamento_id,dose_id)
    if motivo == 'Fez mal':
        return criar_pendencia(usuario_id,'Avisar profissional','Alta',f'Avisar profissional sobre reação a {medicamento_nome}',f'A dose de {medicamento_nome} não foi tomada porque fez mal. Registrar sintomas e avaliar orientação profissional, troca, pausa ou consulta. Observação: {observacao or ""}','Dose não tomada',medicamento_id,dose_id)
    if motivo == 'Orientação médica':
        return criar_pendencia(usuario_id,'Atualizar tratamento','Média',f'Atualizar orientação de {medicamento_nome}',f'Dose não tomada por orientação médica. Atualizar status, conduta, data e documento relacionado.','Dose não tomada',medicamento_id,dose_id)
    if motivo == 'Esqueci':
        return criar_pendencia(usuario_id,'Aderência','Baixa',f'Revisar lembrete de {medicamento_nome}',f'Dose esquecida. Avaliar ajuste de horário, alarme ou rotina de tomada.','Dose não tomada',medicamento_id,dose_id)
    return criar_pendencia(usuario_id,'Revisar tratamento','Média',f'Revisar dose não tomada de {medicamento_nome}',f'Motivo informado: {motivo}. Observação: {observacao or ""}','Dose não tomada',medicamento_id,dose_id)

def listar_pendencias(usuario_id, status=None):
    sql="""SELECT p.*, m.nome AS medicamento FROM pendencias_cuidado p LEFT JOIN medicamentos m ON m.id=p.medicamento_id WHERE p.usuario_id=?"""; params=[usuario_id]
    if status: sql += " AND p.status=?"; params.append(status)
    sql += " ORDER BY CASE p.prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END, p.data_criacao DESC, p.id DESC"
    return consultar_df(sql, tuple(params))

def resolver_pendencia(usuario_id, pendencia_id, resolucao):
    executar("""UPDATE pendencias_cuidado SET status='Resolvida', data_resolucao=?, resolucao=? WHERE usuario_id=? AND id=?""", (date.today().isoformat(), resolucao, usuario_id, pendencia_id))

def reabrir_pendencia(usuario_id, pendencia_id):
    executar("""UPDATE pendencias_cuidado SET status='Aberta', data_resolucao=NULL, resolucao=NULL WHERE usuario_id=? AND id=?""", (usuario_id, pendencia_id))

def contar_pendencias_abertas(usuario_id):
    df=consultar_df("SELECT COUNT(*) AS total FROM pendencias_cuidado WHERE usuario_id=? AND status='Aberta'", (usuario_id,)); return int(df.iloc[0]['total']) if not df.empty else 0
