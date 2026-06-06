from datetime import datetime, date, time, timedelta
from core.database import consultar_df, executar
from core.helpers import agora, hoje_iso
from services.pendencias_service import criar_pendencia_por_motivo_nao_tomou

def horarios_por_modelo(modelo, horario_inicial, intervalo_horas=None, horarios_fixos=''):
    if modelo=='1 vez ao dia': return [horario_inicial]
    base=datetime.combine(date.today(), horario_inicial)
    if modelo=='2 vezes ao dia': return [base.time(), (base+timedelta(hours=12)).time()]
    if modelo=='3 vezes ao dia': return [base.time(), (base+timedelta(hours=8)).time(), (base+timedelta(hours=16)).time()]
    if modelo=='4 vezes ao dia': return [base.time(), (base+timedelta(hours=6)).time(), (base+timedelta(hours=12)).time(), (base+timedelta(hours=18)).time()]
    if modelo=='A cada X horas':
        try: intervalo_horas=int(intervalo_horas)
        except Exception: intervalo_horas=8
        horarios=[]; atual=base; fim=datetime.combine(date.today(), time(23,59))
        while atual<=fim: horarios.append(atual.time()); atual += timedelta(hours=intervalo_horas)
        return horarios
    if modelo=='Horarios fixos':
        horarios=[]
        for p in str(horarios_fixos).replace(';',',').split(','):
            try: horarios.append(datetime.strptime(p.strip(), '%H:%M').time())
            except Exception: pass
        return horarios or [horario_inicial]
    if modelo=='Semanal': return [horario_inicial]
    return [horario_inicial]

def gerar_doses(medicamento_id, usuario_id, modelo, horario_inicial, data_inicio, data_fim, uso_continuo=False, intervalo_horas=None, horarios_fixos=''):
    if uso_continuo: data_fim=data_inicio+timedelta(days=120)
    data_atual=data_inicio
    while data_atual<=data_fim:
        gerar = (modelo!='Semanal') or (data_atual.weekday()==data_inicio.weekday())
        if gerar:
            for h in horarios_por_modelo(modelo, horario_inicial, intervalo_horas, horarios_fixos):
                executar("INSERT INTO doses (medicamento_id,usuario_id,data_prevista,horario_previsto,status) VALUES (?,?,?,?, 'Pendente')", (medicamento_id,usuario_id,data_atual.isoformat(),h.strftime('%H:%M')))
        data_atual += timedelta(days=1)

def salvar_medicamento(usuario_id,nome,dose,modelo,intervalo_horas,horarios_fixos,horario_inicial,data_inicio,duracao,data_fim,orientacao,medico,marco_id=None):
    uso_continuo=1 if duracao=='Uso continuo' else 0
    if duracao=='7 dias': data_fim_final=data_inicio+timedelta(days=6)
    elif duracao=='14 dias': data_fim_final=data_inicio+timedelta(days=13)
    elif duracao=='30 dias': data_fim_final=data_inicio+timedelta(days=29)
    elif duracao=='Uso continuo': data_fim_final=None
    else: data_fim_final=data_fim
    med_id=executar("""INSERT INTO medicamentos (usuario_id,nome,dose,frequencia_modelo,intervalo_horas,horarios_fixos,horario_inicial,data_inicio,data_fim,uso_continuo,orientacao,medico,status,data_status,motivo_status,marco_id,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'Ativo',?,?,?,?)""", (usuario_id,nome,dose,modelo,intervalo_horas,horarios_fixos,horario_inicial.strftime('%H:%M'),data_inicio.isoformat(),data_fim_final.isoformat() if data_fim_final else None,uso_continuo,orientacao,medico,data_inicio.isoformat(),'Inicio do tratamento',marco_id,agora()))
    gerar_doses(med_id,usuario_id,modelo,horario_inicial,data_inicio,data_fim_final if data_fim_final else data_inicio, bool(uso_continuo), intervalo_horas, horarios_fixos)
    executar("""INSERT INTO eventos_medicacao (usuario_id,medicamento_id,data_evento,tipo_evento,motivo,orientado_por,conduta,observacao,marco_id,criado_em) VALUES (?,?,?,'Inicio','Inicio do tratamento',?,?,?,?,?)""", (usuario_id,med_id,data_inicio.isoformat(),medico,orientacao,f'{nome} - {dose}',marco_id,agora()))
    return med_id

def atualizar_status_medicamento(med_id,usuario_id,novo_status,data_evento,motivo,sintomas,gravidade,orientado_por,conduta,substituto,observacao):
    executar("UPDATE medicamentos SET status=?, data_status=?, motivo_status=? WHERE id=? AND usuario_id=?", (novo_status,data_evento.isoformat(),motivo,med_id,usuario_id))
    if novo_status in ['Pausado','Suspenso','Substituido','Concluido']:
        status_dose='Pausada' if novo_status=='Pausado' else 'Cancelada'
        executar("UPDATE doses SET status=? WHERE medicamento_id=? AND usuario_id=? AND data_prevista>=? AND status='Pendente'", (status_dose,med_id,usuario_id,data_evento.isoformat()))
    executar("""INSERT INTO eventos_medicacao (usuario_id,medicamento_id,data_evento,tipo_evento,motivo,sintomas,gravidade,orientado_por,conduta,substituto,observacao,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (usuario_id,med_id,data_evento.isoformat(),novo_status,motivo,sintomas,gravidade,orientado_por,conduta,substituto,observacao,agora()))

def marcar_dose(dose_id, usuario_id, status, obs='', motivo_nao_tomou='', acao_sugerida=''):
    dose=consultar_df("""SELECT d.*, m.nome AS medicamento FROM doses d JOIN medicamentos m ON m.id=d.medicamento_id WHERE d.id=? AND d.usuario_id=?""", (dose_id,usuario_id))
    if dose.empty: return
    row=dose.iloc[0]; horario_tomado=datetime.now().strftime('%H:%M') if status=='Tomado' else None
    executar("""UPDATE doses SET status=?, horario_tomado=?, observacao=?, motivo_nao_tomou=?, acao_sugerida=? WHERE id=? AND usuario_id=?""", (status,horario_tomado,obs,motivo_nao_tomou,acao_sugerida,dose_id,usuario_id))
    tipo_evento='Dose tomada' if status=='Tomado' else 'Dose não tomada'
    motivo=f"{tipo_evento}: {row['medicamento']}" + (f" | Motivo: {motivo_nao_tomou}" if motivo_nao_tomou else '')
    executar("""INSERT INTO eventos_medicacao (usuario_id,medicamento_id,data_evento,tipo_evento,motivo,observacao,criado_em) VALUES (?,?,?,?,?,?,?)""", (usuario_id,int(row['medicamento_id']),hoje_iso(),tipo_evento,motivo,obs,agora()))
    if status in ['Esquecido','Não tomado','Nao tomado'] and motivo_nao_tomou:
        criar_pendencia_por_motivo_nao_tomou(usuario_id,int(row['medicamento_id']),int(dose_id),row['medicamento'],motivo_nao_tomou,obs)

def calcular_aderencia(usuario_id,dias=30):
    data_min=(date.today()-timedelta(days=dias)).isoformat(); df=consultar_df("SELECT status FROM doses WHERE usuario_id=? AND data_prevista>=? AND status NOT IN ('Cancelada','Pausada')", (usuario_id,data_min))
    if df.empty: return 0.0,0,0
    total=len(df); tomadas=len(df[df['status']=='Tomado']); return round((tomadas/total)*100,1),tomadas,total

def proxima_dose(usuario_id):
    now_hora=datetime.now().strftime('%H:%M')
    return consultar_df("""SELECT d.*, m.nome AS medicamento, m.dose FROM doses d JOIN medicamentos m ON m.id=d.medicamento_id WHERE d.usuario_id=? AND d.status='Pendente' AND (d.data_prevista>? OR (d.data_prevista=? AND d.horario_previsto>=?)) ORDER BY d.data_prevista,d.horario_previsto LIMIT 1""", (usuario_id,hoje_iso(),hoje_iso(),now_hora))

def listar_doses_hoje(usuario_id):
    return consultar_df("""SELECT d.*, m.nome AS medicamento, m.dose FROM doses d JOIN medicamentos m ON m.id=d.medicamento_id WHERE d.usuario_id=? AND d.data_prevista=? ORDER BY d.horario_previsto""", (usuario_id,hoje_iso()))

def listar_medicamentos(usuario_id):
    return consultar_df("""SELECT m.*, j.titulo AS marco_titulo, j.tipo_marco, j.data_marco FROM medicamentos m LEFT JOIN marcos_jornada j ON j.id=m.marco_id WHERE m.usuario_id=? ORDER BY m.data_inicio DESC,m.id DESC""", (usuario_id,))

def listar_medicamentos_ativos(usuario_id):
    return consultar_df("""SELECT * FROM medicamentos WHERE usuario_id=? AND COALESCE(status,'Ativo')='Ativo' ORDER BY data_inicio DESC""", (usuario_id,))

def listar_eventos_adversos(usuario_id):
    return consultar_df("""SELECT e.*, m.nome AS medicamento FROM eventos_medicacao e LEFT JOIN medicamentos m ON m.id=e.medicamento_id WHERE e.usuario_id=? AND e.tipo_evento IN ('Efeito adverso','Suspenso','Substituido','Pausado') ORDER BY e.data_evento DESC,e.id DESC""", (usuario_id,))
