from core.database import consultar_df, executar
from core.helpers import agora


def documentos_para_revisao(usuario_id):
    return consultar_df(
        """
        SELECT d.*, m.titulo AS marco_titulo
        FROM documentos_saude d
        LEFT JOIN marcos_jornada m ON m.id = d.marco_id
        WHERE d.usuario_id = ?
          AND COALESCE(d.excluido, 0) = 0
          AND (
                COALESCE(d.paciente_detectado, '') = ''
                OR COALESCE(d.paciente_detectado, '') = 'Paciente não identificado'
                OR COALESCE(d.validacao_paciente, '') LIKE '%ALERTA%'
                OR COALESCE(d.validacao_paciente, '') LIKE '%revisar%'
                OR COALESCE(d.validacao_paciente, '') LIKE '%não identificado%'
              )
        ORDER BY d.data_documento DESC, d.id DESC
        """,
        (usuario_id,),
    )


def pendencias_revisao_importacao(usuario_id):
    return consultar_df(
        """
        SELECT p.*, med.nome AS medicamento
        FROM pendencias_cuidado p
        LEFT JOIN medicamentos med ON med.id = p.medicamento_id
        WHERE p.usuario_id = ?
          AND p.status = 'Aberta'
          AND (
                p.tipo = 'Revisar importação'
                OR p.origem = 'Importação inteligente'
              )
        ORDER BY CASE p.prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
                 p.data_criacao DESC,
                 p.id DESC
        """,
        (usuario_id,),
    )


def exames_incompletos(usuario_id):
    return consultar_df(
        """
        SELECT e.*, m.titulo AS marco_titulo
        FROM exames e
        LEFT JOIN marcos_jornada m ON m.id = e.marco_id
        WHERE e.usuario_id = ?
          AND (
                COALESCE(e.unidade, '') = ''
                OR COALESCE(e.referencia_min, 0) = 0
                OR COALESCE(e.referencia_max, 0) = 0
                OR e.marco_id IS NULL
              )
        ORDER BY e.data_exame DESC, e.nome_exame
        """,
        (usuario_id,),
    )


def medicamentos_incompletos(usuario_id):
    return consultar_df(
        """
        SELECT med.*, m.titulo AS marco_titulo
        FROM medicamentos med
        LEFT JOIN marcos_jornada m ON m.id = med.marco_id
        WHERE med.usuario_id = ?
          AND (
                COALESCE(med.dose, '') = ''
                OR COALESCE(med.frequencia_modelo, '') = ''
                OR COALESCE(med.horario_inicial, '') = ''
                OR med.marco_id IS NULL
              )
        ORDER BY med.data_inicio DESC, med.nome
        """,
        (usuario_id,),
    )


def documentos_sem_marco(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM documentos_saude
        WHERE usuario_id = ?
          AND COALESCE(excluido, 0) = 0
          AND marco_id IS NULL
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id,),
    )


def sintomas_sem_marco(usuario_id):
    return consultar_df(
        """
        SELECT s.*, med.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos med ON med.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.marco_id IS NULL
        ORDER BY s.data_sintoma DESC, s.horario DESC, s.id DESC
        """,
        (usuario_id,),
    )


def marcar_documento_revisado(usuario_id, documento_id, paciente_confirmado="", observacao=""):
    texto = "Revisado manualmente pelo usuário."
    if paciente_confirmado:
        texto += f" Paciente confirmado: {paciente_confirmado}."
    if observacao:
        texto += f" Observação: {observacao}"

    executar(
        """
        UPDATE documentos_saude
        SET paciente_detectado = CASE
                WHEN ? <> '' THEN ?
                ELSE COALESCE(NULLIF(paciente_detectado, ''), 'Paciente revisado manualmente')
            END,
            validacao_paciente = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (paciente_confirmado, paciente_confirmado, texto, usuario_id, documento_id),
    )


def atualizar_exame_basico(usuario_id, exame_id, unidade, referencia_min, referencia_max, observacao):
    executar(
        """
        UPDATE exames
        SET unidade = ?,
            referencia_min = ?,
            referencia_max = ?,
            observacao = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (unidade, referencia_min, referencia_max, observacao, usuario_id, exame_id),
    )


def atualizar_medicamento_basico(usuario_id, medicamento_id, dose, orientacao, medico):
    executar(
        """
        UPDATE medicamentos
        SET dose = ?,
            orientacao = ?,
            medico = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (dose, orientacao, medico, usuario_id, medicamento_id),
    )


def resumo_qualidade(usuario_id):
    docs_rev = documentos_para_revisao(usuario_id)
    pend_rev = pendencias_revisao_importacao(usuario_id)
    exames_inc = exames_incompletos(usuario_id)
    meds_inc = medicamentos_incompletos(usuario_id)
    docs_sem = documentos_sem_marco(usuario_id)
    sintomas_sem = sintomas_sem_marco(usuario_id)

    total_alertas = len(docs_rev) + len(pend_rev) + len(exames_inc) + len(meds_inc) + len(docs_sem) + len(sintomas_sem)

    score = 100
    score -= min(35, len(docs_rev) * 8)
    score -= min(25, len(pend_rev) * 6)
    score -= min(20, len(exames_inc) * 4)
    score -= min(15, len(meds_inc) * 5)
    score -= min(10, (len(docs_sem) + len(sintomas_sem)) * 2)
    score = max(0, score)

    if score >= 85:
        status = "Ótima"
        leitura = "A base está bem organizada. Há poucos pontos pendentes de revisão."
    elif score >= 65:
        status = "Boa, com ajustes"
        leitura = "A base está utilizável, mas há itens que precisam de revisão para melhorar a confiança."
    elif score >= 40:
        status = "Atenção"
        leitura = "Há vários itens sem confirmação ou incompletos. Revise antes de usar relatórios como base principal."
    else:
        status = "Crítica"
        leitura = "A base tem muitos pontos pendentes. É melhor revisar documentos, exames e medicamentos antes de confiar nas leituras."

    return {
        "score": score,
        "status": status,
        "leitura": leitura,
        "total_alertas": total_alertas,
        "documentos_para_revisao": len(docs_rev),
        "pendencias_revisao": len(pend_rev),
        "exames_incompletos": len(exames_inc),
        "medicamentos_incompletos": len(meds_inc),
        "documentos_sem_marco": len(docs_sem),
        "sintomas_sem_marco": len(sintomas_sem),
    }
