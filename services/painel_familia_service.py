from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df
from services.familia_service import listar_usuarios_ativos, listar_usuarios_todos


def _classificar_exame(resultado, ref_min, ref_max):
    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        return "Sem referência"

    if ref_min == 0 and ref_max == 0:
        return "Sem referência"
    if resultado < ref_min:
        return "Abaixo"
    if resultado > ref_max:
        return "Acima"

    largura = max(ref_max - ref_min, 0.0001)
    margem = largura * 0.12

    if resultado <= ref_min + margem:
        return "Limite inferior"
    if resultado >= ref_max - margem:
        return "Limite superior"
    return "Dentro"


def _contar_df(sql, params):
    df = consultar_df(sql, params)
    if df.empty:
        return 0
    return int(df.iloc[0]["total"])


def medicamentos_ativos(usuario_id):
    return _contar_df(
        """
        SELECT COUNT(*) AS total
        FROM medicamentos
        WHERE usuario_id = ?
          AND COALESCE(status, 'Ativo') = 'Ativo'
        """,
        (usuario_id,),
    )


def doses_hoje(usuario_id):
    hoje = date.today().isoformat()
    df = consultar_df(
        """
        SELECT status
        FROM doses
        WHERE usuario_id = ?
          AND data_prevista = ?
        """,
        (usuario_id, hoje),
    )

    if df.empty:
        return {"total": 0, "pendentes": 0, "tomadas": 0, "nao_tomadas": 0}

    return {
        "total": len(df),
        "pendentes": int((df["status"] == "Pendente").sum()),
        "tomadas": int((df["status"] == "Tomado").sum()),
        "nao_tomadas": int(df["status"].isin(["Não tomado", "Nao tomado", "Esquecido"]).sum()),
    }


def pendencias_abertas(usuario_id):
    df = consultar_df(
        """
        SELECT prioridade
        FROM pendencias_cuidado
        WHERE usuario_id = ?
          AND status = 'Aberta'
        """,
        (usuario_id,),
    )

    if df.empty:
        return {"total": 0, "alta": 0, "media": 0, "baixa": 0}

    return {
        "total": len(df),
        "alta": int((df["prioridade"] == "Alta").sum()),
        "media": int((df["prioridade"] == "Média").sum()),
        "baixa": int((df["prioridade"] == "Baixa").sum()),
    }


def exames_atencao(usuario_id, dias=180):
    data_min = (date.today() - timedelta(days=dias)).isoformat()
    df = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame >= ?
        ORDER BY data_exame DESC
        """,
        (usuario_id, data_min),
    )

    if df.empty:
        return {"total": 0, "nomes": ""}

    df["leitura"] = df.apply(
        lambda r: _classificar_exame(r.get("resultado"), r.get("referencia_min"), r.get("referencia_max")),
        axis=1,
    )
    alerta = df[df["leitura"] != "Dentro"]

    nomes = ", ".join(alerta["nome_exame"].dropna().astype(str).head(4).tolist())
    return {"total": len(alerta), "nomes": nomes}


def eventos_relevantes(usuario_id, dias=90):
    data_min = (date.today() - timedelta(days=dias)).isoformat()
    df = consultar_df(
        """
        SELECT COUNT(*) AS total
        FROM eventos_medicacao
        WHERE usuario_id = ?
          AND data_evento >= ?
          AND tipo_evento IN ('Efeito adverso', 'Suspenso', 'Substituido', 'Pausado', 'Dose não tomada')
        """,
        (usuario_id, data_min),
    )
    return int(df.iloc[0]["total"]) if not df.empty else 0


def sintomas_fortes(usuario_id, dias=30):
    data_min = (date.today() - timedelta(days=dias)).isoformat()
    df = consultar_df(
        """
        SELECT COUNT(*) AS total
        FROM sintomas_diario
        WHERE usuario_id = ?
          AND data_sintoma >= ?
          AND COALESCE(intensidade, 0) >= 7
        """,
        (usuario_id, data_min),
    )
    return int(df.iloc[0]["total"]) if not df.empty else 0


def documentos_revisar(usuario_id):
    df = consultar_df(
        """
        SELECT COUNT(*) AS total
        FROM documentos_saude
        WHERE usuario_id = ?
          AND COALESCE(excluido, 0) = 0
          AND (
                COALESCE(paciente_detectado, '') = ''
                OR COALESCE(paciente_detectado, '') = 'Paciente não identificado'
                OR COALESCE(validacao_paciente, '') LIKE '%ALERTA%'
                OR COALESCE(validacao_paciente, '') LIKE '%revisar%'
                OR COALESCE(validacao_paciente, '') LIKE '%não identificado%'
              )
        """,
        (usuario_id,),
    )
    return int(df.iloc[0]["total"]) if not df.empty else 0


def continuidade_alertas(usuario_id):
    """
    Tenta aproveitar o serviço de continuidade. Se alguma versão antiga não tiver as tabelas,
    retorna zero sem quebrar a tela.
    """
    try:
        from services.continuidade_service import painel_continuidade
        df = painel_continuidade(usuario_id)
        if df.empty:
            return {"estoque": 0, "receita": 0, "nomes": ""}

        estoque = df[df["status_estoque"].isin(["Acabou", "Crítico", "Atenção"])]
        receita = df[df["status_receita"].isin(["Vencida", "Vence em breve", "Precisa revisar"])]
        nomes = ", ".join(
            pd.concat([estoque["nome"], receita["nome"]]).dropna().astype(str).drop_duplicates().head(4).tolist()
        )
        return {"estoque": len(estoque), "receita": len(receita), "nomes": nomes}
    except Exception:
        return {"estoque": 0, "receita": 0, "nomes": ""}


def calcular_score_pessoa(row):
    score = 100
    score -= min(30, row["pendencias_alta"] * 15)
    score -= min(20, row["doses_pendentes_hoje"] * 5)
    score -= min(20, row["exames_atencao"] * 5)
    score -= min(15, row["eventos_relevantes"] * 5)
    score -= min(15, row["estoque_alertas"] * 8)
    score -= min(10, row["receita_alertas"] * 5)
    score -= min(10, row["documentos_revisar"] * 4)
    score -= min(10, row["sintomas_fortes"] * 3)
    return max(0, score)


def classificar_status(score, pendencias_alta=0):
    if pendencias_alta > 0 or score < 55:
        return "Atenção alta"
    if score < 75:
        return "Atenção"
    if score < 90:
        return "Estável com ajustes"
    return "Estável"


def painel_familia(incluir_inativos=False):
    usuarios = listar_usuarios_todos() if incluir_inativos else listar_usuarios_ativos()

    if usuarios.empty:
        return pd.DataFrame()

    linhas = []
    for _, u in usuarios.iterrows():
        uid = int(u["id"])
        doses = doses_hoje(uid)
        pend = pendencias_abertas(uid)
        exames = exames_atencao(uid)
        cont = continuidade_alertas(uid)

        linha = {
            "usuario_id": uid,
            "nome": u["nome"],
            "ativo": int(u.get("ativo") or 1),
            "medicamentos_ativos": medicamentos_ativos(uid),
            "doses_hoje": doses["total"],
            "doses_pendentes_hoje": doses["pendentes"],
            "doses_nao_tomadas_hoje": doses["nao_tomadas"],
            "pendencias_abertas": pend["total"],
            "pendencias_alta": pend["alta"],
            "exames_atencao": exames["total"],
            "exames_atencao_nomes": exames["nomes"],
            "eventos_relevantes": eventos_relevantes(uid),
            "sintomas_fortes": sintomas_fortes(uid),
            "documentos_revisar": documentos_revisar(uid),
            "estoque_alertas": cont["estoque"],
            "receita_alertas": cont["receita"],
            "continuidade_nomes": cont["nomes"],
        }

        linha["score"] = calcular_score_pessoa(linha)
        linha["status"] = classificar_status(linha["score"], linha["pendencias_alta"])
        linhas.append(linha)

    df = pd.DataFrame(linhas)
    df = df.sort_values(["score", "pendencias_alta", "pendencias_abertas"], ascending=[True, False, False])
    return df


def resumo_familia():
    df = painel_familia()

    if df.empty:
        return {
            "pessoas": 0,
            "atencao_alta": 0,
            "pendencias": 0,
            "doses_pendentes": 0,
            "exames": 0,
            "continuidade": 0,
            "leitura": "Nenhum cadastro ativo encontrado."
        }

    atencao_alta = int((df["status"] == "Atenção alta").sum())
    pendencias = int(df["pendencias_abertas"].sum())
    doses = int(df["doses_pendentes_hoje"].sum())
    exames = int(df["exames_atencao"].sum())
    continuidade = int(df["estoque_alertas"].sum() + df["receita_alertas"].sum())

    if atencao_alta > 0:
        leitura = f"{atencao_alta} pessoa(s) precisam de atenção alta. Comece por elas."
    elif doses > 0:
        leitura = f"Há {doses} dose(s) pendente(s) hoje na família."
    elif pendencias > 0:
        leitura = f"Há {pendencias} pendência(s) aberta(s) na família."
    else:
        leitura = "A família está sem alertas críticos no momento."

    return {
        "pessoas": len(df),
        "atencao_alta": atencao_alta,
        "pendencias": pendencias,
        "doses_pendentes": doses,
        "exames": exames,
        "continuidade": continuidade,
        "leitura": leitura,
    }


def prioridades_familia():
    df = painel_familia()
    itens = []

    if df.empty:
        return itens

    for _, r in df.iterrows():
        nome = r["nome"]

        if r["pendencias_alta"] > 0:
            itens.append({
                "pessoa": nome,
                "prioridade": "Alta",
                "tipo": "Pendências",
                "titulo": f"{r['pendencias_alta']} pendência(s) de alta prioridade",
                "descricao": "Abrir Pendências ou Agenda de cuidado para resolver."
            })

        if r["doses_pendentes_hoje"] > 0:
            itens.append({
                "pessoa": nome,
                "prioridade": "Alta",
                "tipo": "Medicação hoje",
                "titulo": f"{r['doses_pendentes_hoje']} dose(s) pendente(s) hoje",
                "descricao": "Confirmar tomada ou registrar motivo de não tomada."
            })

        if r["estoque_alertas"] > 0 or r["receita_alertas"] > 0:
            itens.append({
                "pessoa": nome,
                "prioridade": "Média",
                "tipo": "Continuidade",
                "titulo": f"{r['estoque_alertas']} alerta(s) de estoque e {r['receita_alertas']} de receita",
                "descricao": r["continuidade_nomes"] or "Revisar continuidade do tratamento."
            })

        if r["exames_atencao"] > 0:
            itens.append({
                "pessoa": nome,
                "prioridade": "Média",
                "tipo": "Exames",
                "titulo": f"{r['exames_atencao']} exame(s) em atenção",
                "descricao": r["exames_atencao_nomes"] or "Revisar exames."
            })

        if r["documentos_revisar"] > 0:
            itens.append({
                "pessoa": nome,
                "prioridade": "Baixa",
                "tipo": "Revisão",
                "titulo": f"{r['documentos_revisar']} documento(s) para revisar",
                "descricao": "Conferir paciente identificado, documento ou dados importados."
            })

    prioridade_ordem = {"Alta": 1, "Média": 2, "Baixa": 3}
    itens = sorted(itens, key=lambda x: prioridade_ordem.get(x["prioridade"], 4))
    return itens


def gerar_txt_painel_familia():
    df = painel_familia()
    resumo = resumo_familia()
    prioridades = prioridades_familia()

    linhas = []
    linhas.append("PAINEL DA FAMÍLIA - SAÚDE 360")
    linhas.append("=" * 42)
    linhas.append(f"Gerado em: {date.today().strftime('%d/%m/%Y')}")
    linhas.append("")
    linhas.append("RESUMO")
    linhas.append("-" * 20)
    linhas.append(f"Pessoas ativas: {resumo['pessoas']}")
    linhas.append(f"Atenção alta: {resumo['atencao_alta']}")
    linhas.append(f"Pendências abertas: {resumo['pendencias']}")
    linhas.append(f"Doses pendentes hoje: {resumo['doses_pendentes']}")
    linhas.append(f"Exames em atenção: {resumo['exames']}")
    linhas.append(f"Alertas de continuidade: {resumo['continuidade']}")
    linhas.append(resumo["leitura"])
    linhas.append("")

    linhas.append("PRIORIDADES")
    linhas.append("-" * 20)
    if not prioridades:
        linhas.append("Nenhuma prioridade familiar relevante no momento.")
    else:
        for p in prioridades:
            linhas.append(f"- [{p['prioridade']}] {p['pessoa']} | {p['tipo']} | {p['titulo']}")
            linhas.append(f"  {p['descricao']}")
    linhas.append("")

    linhas.append("RESUMO POR PESSOA")
    linhas.append("-" * 20)
    if df.empty:
        linhas.append("Nenhuma pessoa ativa.")
    else:
        for _, r in df.iterrows():
            linhas.append(f"- {r['nome']} | {r['status']} | Score {r['score']}/100")
            linhas.append(
                f"  Pendências: {r['pendencias_abertas']} | Doses pendentes hoje: {r['doses_pendentes_hoje']} | "
                f"Exames em atenção: {r['exames_atencao']} | Continuidade: {r['estoque_alertas'] + r['receita_alertas']}"
            )

    return "\n".join(linhas)
