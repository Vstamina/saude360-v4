from datetime import date, timedelta
import math

import pandas as pd

from core.database import consultar_df, executar
from core.helpers import agora
from services.pendencias_service import criar_pendencia


def listar_medicamentos_ativos_para_estoque(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND COALESCE(status, 'Ativo') = 'Ativo'
        ORDER BY nome
        """,
        (usuario_id,),
    )


def listar_documentos_receita(usuario_id):
    return consultar_df(
        """
        SELECT id, data_documento, tipo_documento, titulo, profissional, instituicao
        FROM documentos_saude
        WHERE usuario_id = ?
          AND COALESCE(excluido, 0) = 0
          AND (
                LOWER(COALESCE(tipo_documento, '')) LIKE '%receita%'
                OR LOWER(COALESCE(titulo, '')) LIKE '%receita%'
                OR LOWER(COALESCE(observacao, '')) LIKE '%receita%'
              )
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id,),
    )


def salvar_estoque(usuario_id, medicamento_id, data_compra, quantidade_total, unidade_estoque,
                   quantidade_por_dose, farmacia, valor_pago, documento_id=None, observacao=""):
    executar(
        """
        UPDATE estoque_medicamentos
        SET ativo = 0
        WHERE usuario_id = ?
          AND medicamento_id = ?
          AND ativo = 1
        """,
        (usuario_id, medicamento_id),
    )

    executar(
        """
        UPDATE medicamentos
        SET controlar_estoque = 1
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, medicamento_id),
    )

    return executar(
        """
        INSERT INTO estoque_medicamentos (
            usuario_id, medicamento_id, data_compra, quantidade_total, unidade_estoque,
            quantidade_por_dose, farmacia, valor_pago, documento_id, observacao, ativo, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            usuario_id,
            medicamento_id,
            data_compra.isoformat() if hasattr(data_compra, "isoformat") else data_compra,
            float(quantidade_total or 0),
            unidade_estoque,
            float(quantidade_por_dose or 1),
            farmacia,
            float(valor_pago or 0),
            documento_id,
            observacao,
            agora(),
        ),
    )


def salvar_receita(usuario_id, medicamento_id, documento_id, data_receita, tipo_receita,
                   validade_dias, precisa_receita, retencao_receita, observacao=""):
    executar(
        """
        UPDATE receitas_medicamentos
        SET ativo = 0
        WHERE usuario_id = ?
          AND medicamento_id = ?
          AND ativo = 1
        """,
        (usuario_id, medicamento_id),
    )

    executar(
        """
        UPDATE medicamentos
        SET precisa_receita = ?,
            tipo_receita = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (1 if precisa_receita else 0, tipo_receita, usuario_id, medicamento_id),
    )

    return executar(
        """
        INSERT INTO receitas_medicamentos (
            usuario_id, medicamento_id, documento_id, data_receita, tipo_receita,
            validade_dias, precisa_receita, retencao_receita, observacao, ativo, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            usuario_id,
            medicamento_id,
            documento_id,
            data_receita.isoformat() if hasattr(data_receita, "isoformat") else data_receita,
            tipo_receita,
            int(validade_dias or 0),
            1 if precisa_receita else 0,
            1 if retencao_receita else 0,
            observacao,
            agora(),
        ),
    )


def _parse_date(valor):
    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def consumo_diario_estimado(medicamento):
    modelo = medicamento.get("frequencia_modelo") if hasattr(medicamento, "get") else medicamento["frequencia_modelo"]
    intervalo = medicamento.get("intervalo_horas") if hasattr(medicamento, "get") else medicamento["intervalo_horas"]

    modelo = str(modelo or "")

    if modelo == "1 vez ao dia":
        return 1.0
    if modelo == "2 vezes ao dia":
        return 2.0
    if modelo == "3 vezes ao dia":
        return 3.0
    if modelo == "4 vezes ao dia":
        return 4.0
    if modelo == "A cada X horas":
        try:
            intervalo = int(intervalo)
            if intervalo > 0:
                return round(24 / intervalo, 2)
        except Exception:
            return 3.0
    if modelo == "Semanal":
        return round(1 / 7, 3)
    if modelo == "Horarios fixos":
        horarios = str(medicamento.get("horarios_fixos") if hasattr(medicamento, "get") else medicamento["horarios_fixos"] or "")
        partes = [p.strip() for p in horarios.replace(";", ",").split(",") if p.strip()]
        return float(len(partes)) if partes else 1.0

    return 1.0


def obter_estoque_ativo(usuario_id, medicamento_id):
    return consultar_df(
        """
        SELECT e.*, d.titulo AS documento_titulo
        FROM estoque_medicamentos e
        LEFT JOIN documentos_saude d ON d.id = e.documento_id
        WHERE e.usuario_id = ?
          AND e.medicamento_id = ?
          AND e.ativo = 1
        ORDER BY e.id DESC
        LIMIT 1
        """,
        (usuario_id, medicamento_id),
    )


def obter_receita_ativa(usuario_id, medicamento_id):
    return consultar_df(
        """
        SELECT r.*, d.titulo AS documento_titulo
        FROM receitas_medicamentos r
        LEFT JOIN documentos_saude d ON d.id = r.documento_id
        WHERE r.usuario_id = ?
          AND r.medicamento_id = ?
          AND r.ativo = 1
        ORDER BY r.id DESC
        LIMIT 1
        """,
        (usuario_id, medicamento_id),
    )


def calcular_continuidade_medicamento(usuario_id, medicamento):
    med_id = int(medicamento["id"])
    consumo = consumo_diario_estimado(medicamento)

    estoque_df = obter_estoque_ativo(usuario_id, med_id)
    receita_df = obter_receita_ativa(usuario_id, med_id)

    resultado = {
        "medicamento_id": med_id,
        "nome": medicamento["nome"],
        "dose": medicamento.get("dose", "") if hasattr(medicamento, "get") else medicamento["dose"],
        "frequencia": medicamento.get("frequencia_modelo", "") if hasattr(medicamento, "get") else medicamento["frequencia_modelo"],
        "consumo_diario_estimado": consumo,
        "controlar_estoque": int(medicamento.get("controlar_estoque") or 0) if hasattr(medicamento, "get") else 0,
        "precisa_receita": int(medicamento.get("precisa_receita") or 0) if hasattr(medicamento, "get") else 0,
        "tipo_receita": medicamento.get("tipo_receita", "") if hasattr(medicamento, "get") else "",
        "tem_estoque": False,
        "dias_restantes": None,
        "data_prevista_fim": None,
        "status_estoque": "Sem controle",
        "status_receita": "Sem controle",
        "alerta": "Sem estoque cadastrado",
        "prioridade": "Baixa",
        "estoque_observacao": "",
        "receita_observacao": "",
    }

    if not estoque_df.empty:
        e = estoque_df.iloc[0]
        data_compra = _parse_date(e.get("data_compra"))
        qtd_total = float(e.get("quantidade_total") or 0)
        qtd_por_dose = float(e.get("quantidade_por_dose") or 1)
        consumo_unidades_dia = consumo * max(qtd_por_dose, 0.0001)

        if consumo_unidades_dia > 0:
            dias_total = qtd_total / consumo_unidades_dia
        else:
            dias_total = 0

        if data_compra:
            dias_passados = max((date.today() - data_compra).days, 0)
        else:
            dias_passados = 0

        dias_restantes = math.floor(dias_total - dias_passados)
        data_fim = date.today() + timedelta(days=max(dias_restantes, 0))

        resultado.update({
            "tem_estoque": True,
            "dias_restantes": dias_restantes,
            "data_prevista_fim": data_fim.isoformat(),
            "unidade_estoque": e.get("unidade_estoque") or "",
            "quantidade_total": qtd_total,
            "quantidade_por_dose": qtd_por_dose,
            "farmacia": e.get("farmacia") or "",
            "valor_pago": float(e.get("valor_pago") or 0),
            "estoque_observacao": e.get("observacao") or "",
        })

        if dias_restantes < 0:
            resultado["status_estoque"] = "Acabou"
            resultado["alerta"] = "Medicação provavelmente acabou"
            resultado["prioridade"] = "Alta"
        elif dias_restantes <= 3:
            resultado["status_estoque"] = "Crítico"
            resultado["alerta"] = "Estoque acaba em até 3 dias"
            resultado["prioridade"] = "Alta"
        elif dias_restantes <= 7:
            resultado["status_estoque"] = "Atenção"
            resultado["alerta"] = "Estoque acaba em até 7 dias"
            resultado["prioridade"] = "Média"
        else:
            resultado["status_estoque"] = "OK"
            resultado["alerta"] = "Estoque suficiente no momento"
            resultado["prioridade"] = "Baixa"

    if not receita_df.empty:
        r = receita_df.iloc[0]
        data_receita = _parse_date(r.get("data_receita"))
        validade = int(r.get("validade_dias") or 0)
        precisa = int(r.get("precisa_receita") or 0)
        retencao = int(r.get("retencao_receita") or 0)

        resultado["precisa_receita"] = precisa
        resultado["tipo_receita"] = r.get("tipo_receita") or ""
        resultado["retencao_receita"] = retencao
        resultado["receita_observacao"] = r.get("observacao") or ""

        if precisa and data_receita and validade > 0:
            vence = data_receita + timedelta(days=validade)
            dias_validade = (vence - date.today()).days
            resultado["data_validade_receita"] = vence.isoformat()
            resultado["dias_validade_receita"] = dias_validade

            if dias_validade < 0:
                resultado["status_receita"] = "Vencida"
                if resultado["prioridade"] != "Alta":
                    resultado["prioridade"] = "Alta"
                resultado["alerta"] = "Receita possivelmente vencida"
            elif dias_validade <= 7:
                resultado["status_receita"] = "Vence em breve"
                if resultado["prioridade"] == "Baixa":
                    resultado["prioridade"] = "Média"
            else:
                resultado["status_receita"] = "OK"
        elif precisa:
            resultado["status_receita"] = "Precisa revisar"
        else:
            resultado["status_receita"] = "Não informada/Não necessária"

    return resultado


def painel_continuidade(usuario_id):
    meds = listar_medicamentos_ativos_para_estoque(usuario_id)
    linhas = []

    if meds.empty:
        return pd.DataFrame()

    for _, med in meds.iterrows():
        r = calcular_continuidade_medicamento(usuario_id, med)
        linhas.append(r)

    return pd.DataFrame(linhas)


def criar_pendencias_continuidade(usuario_id):
    df = painel_continuidade(usuario_id)
    criadas = 0

    if df.empty:
        return criadas

    abertas = consultar_df(
        """
        SELECT medicamento_id, titulo, status
        FROM pendencias_cuidado
        WHERE usuario_id = ?
          AND status = 'Aberta'
          AND origem = 'Continuidade do tratamento'
        """,
        (usuario_id,),
    )

    existentes = set()
    if not abertas.empty:
        for _, p in abertas.iterrows():
            existentes.add((int(p.get("medicamento_id") or 0), str(p.get("titulo") or "")))

    for _, r in df.iterrows():
        med_id = int(r["medicamento_id"])
        nome = r["nome"]
        prioridade = r["prioridade"]

        if r["status_estoque"] in ["Acabou", "Crítico", "Atenção"]:
            titulo = f"Providenciar {nome}"
            if (med_id, titulo) not in existentes:
                criar_pendencia(
                    usuario_id=usuario_id,
                    tipo="Continuidade do tratamento",
                    prioridade=prioridade,
                    titulo=titulo,
                    descricao=(
                        f"{nome}: {r['alerta']}. "
                        "Verificar compra, nova receita ou contato com profissional de saúde."
                    ),
                    origem="Continuidade do tratamento",
                    medicamento_id=med_id,
                )
                criadas += 1

        if r["status_receita"] in ["Vencida", "Vence em breve", "Precisa revisar"]:
            titulo = f"Revisar receita de {nome}"
            if (med_id, titulo) not in existentes:
                criar_pendencia(
                    usuario_id=usuario_id,
                    tipo="Receita / prescrição",
                    prioridade="Alta" if r["status_receita"] == "Vencida" else "Média",
                    titulo=titulo,
                    descricao=(
                        f"{nome}: status da receita: {r['status_receita']}. "
                        "Verificar validade, necessidade de nova prescrição ou retorno."
                    ),
                    origem="Continuidade do tratamento",
                    medicamento_id=med_id,
                )
                criadas += 1

    return criadas
