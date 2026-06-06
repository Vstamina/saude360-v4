from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df, executar
from core.helpers import agora
from services.continuidade_service import painel_continuidade


def _to_date(valor):
    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def criar_cuidado_manual(usuario_id, data_cuidado, tipo, titulo, prioridade,
                         origem="Manual", medicamento_id=None, exame_nome="",
                         marco_id=None, pendencia_id=None, observacao=""):
    return executar(
        """
        INSERT INTO cuidados_agendados (
            usuario_id, data_cuidado, tipo, titulo, prioridade, status, origem,
            medicamento_id, exame_nome, marco_id, pendencia_id, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, 'Aberto', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_cuidado.isoformat() if hasattr(data_cuidado, "isoformat") else data_cuidado,
            tipo,
            titulo,
            prioridade,
            origem,
            medicamento_id,
            exame_nome,
            marco_id,
            pendencia_id,
            observacao,
            agora(),
        ),
    )


def listar_cuidados_manuais(usuario_id, incluir_concluidos=False):
    sql = """
        SELECT c.*, m.nome AS medicamento
        FROM cuidados_agendados c
        LEFT JOIN medicamentos m ON m.id = c.medicamento_id
        WHERE c.usuario_id = ?
    """
    params = [usuario_id]
    if not incluir_concluidos:
        sql += " AND c.status <> 'Concluído' "
    sql += """
        ORDER BY
            CASE c.prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
            c.data_cuidado ASC,
            c.id DESC
    """
    return consultar_df(sql, tuple(params))


def concluir_cuidado(usuario_id, cuidado_id, observacao=""):
    executar(
        """
        UPDATE cuidados_agendados
        SET status = 'Concluído',
            observacao = CASE
                WHEN ? <> '' THEN COALESCE(observacao, '') || '\nConclusão: ' || ?
                ELSE observacao
            END
        WHERE usuario_id = ?
          AND id = ?
        """,
        (observacao, observacao, usuario_id, cuidado_id),
    )


def reabrir_cuidado(usuario_id, cuidado_id):
    executar(
        """
        UPDATE cuidados_agendados
        SET status = 'Aberto'
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, cuidado_id),
    )


def excluir_cuidado(usuario_id, cuidado_id):
    executar(
        """
        DELETE FROM cuidados_agendados
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, cuidado_id),
    )


def eventos_agenda_por_doses(usuario_id, dias=30):
    data_ini = date.today().isoformat()
    data_fim = (date.today() + timedelta(days=dias)).isoformat()
    return consultar_df(
        """
        SELECT
            d.data_prevista AS data,
            d.horario_previsto AS horario,
            'Medicação' AS tipo,
            m.nome || CASE WHEN COALESCE(m.dose, '') <> '' THEN ' - ' || m.dose ELSE '' END AS titulo,
            CASE
                WHEN d.data_prevista = ? THEN 'Alta'
                ELSE 'Baixa'
            END AS prioridade,
            'Dose prevista' AS origem,
            m.id AS medicamento_id,
            d.id AS dose_id,
            d.status AS status,
            '' AS observacao
        FROM doses d
        JOIN medicamentos m ON m.id = d.medicamento_id
        WHERE d.usuario_id = ?
          AND d.data_prevista BETWEEN ? AND ?
          AND d.status = 'Pendente'
        ORDER BY d.data_prevista, d.horario_previsto
        """,
        (date.today().isoformat(), usuario_id, data_ini, data_fim),
    )


def eventos_agenda_por_marcos(usuario_id, dias=90):
    data_ini = date.today().isoformat()
    data_fim = (date.today() + timedelta(days=dias)).isoformat()
    return consultar_df(
        """
        SELECT
            data_marco AS data,
            '' AS horario,
            tipo_marco AS tipo,
            titulo AS titulo,
            'Média' AS prioridade,
            'Marco da jornada' AS origem,
            NULL AS medicamento_id,
            NULL AS dose_id,
            'Aberto' AS status,
            COALESCE(proximo_passo, '') || ' ' || COALESCE(observacao, '') AS observacao
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco BETWEEN ? AND ?
        ORDER BY data_marco ASC, id DESC
        """,
        (usuario_id, data_ini, data_fim),
    )


def eventos_agenda_por_pendencias(usuario_id):
    return consultar_df(
        """
        SELECT
            data_criacao AS data,
            '' AS horario,
            tipo AS tipo,
            titulo AS titulo,
            COALESCE(prioridade, 'Média') AS prioridade,
            COALESCE(origem, 'Pendência') AS origem,
            medicamento_id,
            dose_id,
            status,
            COALESCE(descricao, '') AS observacao
        FROM pendencias_cuidado
        WHERE usuario_id = ?
          AND status = 'Aberta'
        ORDER BY
            CASE prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
            data_criacao ASC
        """,
        (usuario_id,),
    )


def eventos_agenda_por_continuidade(usuario_id):
    df = painel_continuidade(usuario_id)
    eventos = []

    if df.empty:
        return pd.DataFrame(columns=[
            "data", "horario", "tipo", "titulo", "prioridade", "origem",
            "medicamento_id", "dose_id", "status", "observacao"
        ])

    for _, r in df.iterrows():
        med_id = int(r.get("medicamento_id") or 0)
        nome = r.get("nome") or "Medicamento"

        if r.get("data_prevista_fim"):
            data_fim = _to_date(r.get("data_prevista_fim"))
            if data_fim:
                dias = (data_fim - date.today()).days
                if dias <= 7:
                    eventos.append({
                        "data": data_fim.isoformat(),
                        "horario": "",
                        "tipo": "Estoque",
                        "titulo": f"Estoque de {nome} acaba",
                        "prioridade": "Alta" if dias <= 3 else "Média",
                        "origem": "Continuidade do tratamento",
                        "medicamento_id": med_id,
                        "dose_id": None,
                        "status": "Aberto",
                        "observacao": r.get("alerta") or "",
                    })

        if r.get("data_validade_receita"):
            data_val = _to_date(r.get("data_validade_receita"))
            if data_val:
                dias = (data_val - date.today()).days
                if dias <= 14:
                    eventos.append({
                        "data": data_val.isoformat(),
                        "horario": "",
                        "tipo": "Receita",
                        "titulo": f"Receita de {nome} vence/revisar",
                        "prioridade": "Alta" if dias <= 0 else "Média",
                        "origem": "Continuidade do tratamento",
                        "medicamento_id": med_id,
                        "dose_id": None,
                        "status": "Aberto",
                        "observacao": f"Status da receita: {r.get('status_receita') or ''}",
                    })

    return pd.DataFrame(eventos)


def eventos_agenda_manuais(usuario_id):
    df = listar_cuidados_manuais(usuario_id, incluir_concluidos=False)
    if df.empty:
        return pd.DataFrame(columns=[
            "data", "horario", "tipo", "titulo", "prioridade", "origem",
            "medicamento_id", "dose_id", "status", "observacao", "cuidado_id"
        ])

    out = pd.DataFrame({
        "data": df["data_cuidado"],
        "horario": "",
        "tipo": df["tipo"],
        "titulo": df["titulo"],
        "prioridade": df["prioridade"],
        "origem": df["origem"],
        "medicamento_id": df["medicamento_id"],
        "dose_id": None,
        "status": df["status"],
        "observacao": df["observacao"],
        "cuidado_id": df["id"],
    })
    return out


def montar_agenda_inteligente(usuario_id, dias_doses=30, dias_marcos=90):
    partes = [
        eventos_agenda_por_doses(usuario_id, dias=dias_doses),
        eventos_agenda_por_marcos(usuario_id, dias=dias_marcos),
        eventos_agenda_por_pendencias(usuario_id),
        eventos_agenda_por_continuidade(usuario_id),
        eventos_agenda_manuais(usuario_id),
    ]

    partes = [p for p in partes if p is not None and not p.empty]
    if not partes:
        return pd.DataFrame(columns=[
            "data", "horario", "tipo", "titulo", "prioridade", "origem",
            "medicamento_id", "dose_id", "status", "observacao"
        ])

    df = pd.concat(partes, ignore_index=True)
    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["prioridade_ordem"] = df["prioridade"].map({"Alta": 1, "Média": 2, "Baixa": 3}).fillna(4)
    df = df.sort_values(["data_dt", "prioridade_ordem", "horario"], ascending=[True, True, True])
    return df


def resumo_agenda(usuario_id):
    df = montar_agenda_inteligente(usuario_id)

    if df.empty:
        return {
            "total": 0,
            "hoje": 0,
            "semana": 0,
            "alta": 0,
            "pendencias": 0,
            "leitura": "Nenhum cuidado futuro ou pendência relevante no momento."
        }

    hoje = date.today()
    sete = hoje + timedelta(days=7)

    datas = pd.to_datetime(df["data"], errors="coerce").dt.date
    total = len(df)
    hoje_count = int((datas == hoje).sum())
    semana_count = int(((datas >= hoje) & (datas <= sete)).sum())
    alta = int((df["prioridade"] == "Alta").sum())
    pend = int((df["origem"].fillna("").str.contains("Pendência|Continuidade", case=False, regex=True)).sum())

    if alta > 0:
        leitura = f"Há {alta} item(ns) de alta prioridade. Comece por eles."
    elif hoje_count > 0:
        leitura = f"Há {hoje_count} cuidado(s) para hoje."
    elif semana_count > 0:
        leitura = f"Há {semana_count} cuidado(s) previstos para os próximos 7 dias."
    else:
        leitura = "Agenda sem urgências imediatas."

    return {
        "total": total,
        "hoje": hoje_count,
        "semana": semana_count,
        "alta": alta,
        "pendencias": pend,
        "leitura": leitura,
    }


def gerar_txt_agenda(usuario_id):
    df = montar_agenda_inteligente(usuario_id)
    linhas = []
    linhas.append("AGENDA INTELIGENTE DE CUIDADO - SAÚDE 360")
    linhas.append("=" * 52)
    linhas.append(f"Gerada em: {date.today().strftime('%d/%m/%Y')}")
    linhas.append("")

    if df.empty:
        linhas.append("Nenhum cuidado futuro ou pendência relevante no momento.")
        return "\n".join(linhas)

    for _, r in df.iterrows():
        data_txt = _to_date(r.get("data"))
        data_txt = data_txt.strftime("%d/%m/%Y") if data_txt else str(r.get("data") or "")
        horario = r.get("horario") or ""
        linhas.append(f"- {data_txt} {horario} | {r.get('prioridade') or ''} | {r.get('tipo') or ''} | {r.get('titulo') or ''}")
        if r.get("origem"):
            linhas.append(f"  Origem: {r.get('origem')}")
        if r.get("observacao"):
            linhas.append(f"  Obs.: {r.get('observacao')}")
        linhas.append("")

    return "\n".join(linhas)
