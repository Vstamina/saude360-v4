from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def _data_min(dias):
    if int(dias) >= 9999:
        return "1900-01-01"
    return (date.today() - timedelta(days=int(dias))).isoformat()


def _prioridade_ordem(prioridade):
    return {"Alta": 1, "Média": 2, "Baixa": 3}.get(str(prioridade or ""), 4)


def _classificar_exame(resultado, ref_min, ref_max):
    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        return "Sem referência", "Baixa"

    if ref_min == 0 and ref_max == 0:
        return "Sem referência", "Baixa"
    if resultado < ref_min:
        return "Abaixo da referência", "Alta"
    if resultado > ref_max:
        return "Acima da referência", "Alta"

    largura = max(ref_max - ref_min, 0.0001)
    margem = largura * 0.12

    if resultado <= ref_min + margem:
        return "Próximo do limite inferior", "Média"
    if resultado >= ref_max - margem:
        return "Próximo do limite superior", "Média"
    return "Dentro da referência", "Baixa"


def eventos_marcos(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco >= ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        eventos.append({
            "data": r.get("data_marco"),
            "horario": "",
            "tipo": "Marco clínico",
            "subtipo": r.get("tipo_marco") or "",
            "titulo": r.get("titulo") or "Marco da jornada",
            "descricao": " | ".join([x for x in [
                f"Especialidade: {r.get('especialidade')}" if r.get("especialidade") else "",
                f"Profissional: {r.get('profissional')}" if r.get("profissional") else "",
                f"Queixas: {r.get('queixas')}" if r.get("queixas") else "",
                f"Conduta: {r.get('conduta')}" if r.get("conduta") else "",
                f"Próximo passo: {r.get('proximo_passo')}" if r.get("proximo_passo") else "",
            ] if x]),
            "prioridade": "Média",
            "origem": "marcos_jornada",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_medicamentos(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND data_inicio >= ?
        ORDER BY data_inicio DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        eventos.append({
            "data": r.get("data_inicio"),
            "horario": r.get("horario_inicial") or "",
            "tipo": "Medicamento",
            "subtipo": "Início",
            "titulo": f"Início de {r.get('nome') or 'medicamento'}",
            "descricao": " | ".join([x for x in [
                f"Dose: {r.get('dose')}" if r.get("dose") else "",
                f"Frequência: {r.get('frequencia_modelo')}" if r.get("frequencia_modelo") else "",
                f"Orientação: {r.get('orientacao')}" if r.get("orientacao") else "",
                f"Médico: {r.get('medico')}" if r.get("medico") else "",
            ] if x]),
            "prioridade": "Média",
            "origem": "medicamentos",
            "referencia_id": int(r["id"]),
        })

        if r.get("data_status") and r.get("status") and r.get("status") != "Ativo":
            eventos.append({
                "data": r.get("data_status"),
                "horario": "",
                "tipo": "Medicamento",
                "subtipo": r.get("status") or "Status",
                "titulo": f"{r.get('status')} — {r.get('nome')}",
                "descricao": r.get("motivo_status") or "",
                "prioridade": "Alta" if r.get("status") in ["Suspenso", "Substituido", "Pausado"] else "Média",
                "origem": "medicamentos",
                "referencia_id": int(r["id"]),
            })
    return eventos


def eventos_eventos_medicacao(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT e.*, m.nome AS medicamento
        FROM eventos_medicacao e
        LEFT JOIN medicamentos m ON m.id = e.medicamento_id
        WHERE e.usuario_id = ?
          AND e.data_evento >= ?
        ORDER BY e.data_evento DESC, e.id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        tipo = r.get("tipo_evento") or "Evento"
        prioridade = "Alta" if tipo in ["Efeito adverso", "Suspenso", "Substituido", "Pausado", "Dose não tomada"] else "Média"
        eventos.append({
            "data": r.get("data_evento"),
            "horario": "",
            "tipo": "Evento de medicação",
            "subtipo": tipo,
            "titulo": f"{tipo} — {r.get('medicamento') or 'medicamento não informado'}",
            "descricao": " | ".join([x for x in [
                f"Motivo: {r.get('motivo')}" if r.get("motivo") else "",
                f"Sintomas: {r.get('sintomas')}" if r.get("sintomas") else "",
                f"Gravidade: {r.get('gravidade')}" if r.get("gravidade") else "",
                f"Conduta: {r.get('conduta')}" if r.get("conduta") else "",
                f"Substituto: {r.get('substituto')}" if r.get("substituto") else "",
                f"Obs.: {r.get('observacao')}" if r.get("observacao") else "",
            ] if x]),
            "prioridade": prioridade,
            "origem": "eventos_medicacao",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_exames(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame >= ?
        ORDER BY data_exame DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        leitura, prioridade = _classificar_exame(r.get("resultado"), r.get("referencia_min"), r.get("referencia_max"))
        nome = r.get("nome_padronizado") or r.get("nome_exame") or "Exame"
        eventos.append({
            "data": r.get("data_exame"),
            "horario": "",
            "tipo": "Exame",
            "subtipo": leitura,
            "titulo": f"{nome}: {fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''}",
            "descricao": " | ".join([x for x in [
                f"Nome original: {r.get('nome_exame')}" if r.get("nome_padronizado") else "",
                f"Referência: {fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)}" if r.get("referencia_min") is not None else "",
                f"Laboratório: {r.get('laboratorio')}" if r.get("laboratorio") else "",
                f"Categoria: {r.get('categoria_exame')}" if r.get("categoria_exame") else "",
                f"Obs.: {r.get('observacao')}" if r.get("observacao") else "",
            ] if x]),
            "prioridade": prioridade,
            "origem": "exames",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_sintomas(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT s.*, m.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma >= ?
        ORDER BY s.data_sintoma DESC, COALESCE(s.horario, '') DESC, s.id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        intensidade = int(r.get("intensidade") or 0)
        prioridade = "Alta" if intensidade >= 7 else "Média" if intensidade >= 4 else "Baixa"
        eventos.append({
            "data": r.get("data_sintoma"),
            "horario": r.get("horario") or "",
            "tipo": "Sintoma",
            "subtipo": f"{intensidade}/10" if intensidade else "Sem intensidade",
            "titulo": f"{r.get('sintoma') or 'Sintoma'}",
            "descricao": " | ".join([x for x in [
                f"Intensidade: {intensidade}/10" if intensidade else "",
                f"Duração: {r.get('duracao')}" if r.get("duracao") else "",
                f"Medicamento associado: {r.get('medicamento')}" if r.get("medicamento") else "",
                f"Gatilho: {r.get('gatilho')}" if r.get("gatilho") else "",
                f"Ação tomada: {r.get('acao_tomada')}" if r.get("acao_tomada") else "",
                f"Obs.: {r.get('observacao')}" if r.get("observacao") else "",
            ] if x]),
            "prioridade": prioridade,
            "origem": "sintomas_diario",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_documentos(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT *
        FROM documentos_saude
        WHERE usuario_id = ?
          AND data_documento >= ?
          AND COALESCE(excluido, 0) = 0
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        prioridade = "Média" if "ALERTA" in str(r.get("validacao_paciente") or "") else "Baixa"
        eventos.append({
            "data": r.get("data_documento"),
            "horario": "",
            "tipo": "Documento",
            "subtipo": r.get("tipo_documento") or "",
            "titulo": r.get("titulo") or "Documento",
            "descricao": " | ".join([x for x in [
                f"Profissional: {r.get('profissional')}" if r.get("profissional") else "",
                f"Instituição: {r.get('instituicao')}" if r.get("instituicao") else "",
                f"Relacionado a: {r.get('relacionado_a')}" if r.get("relacionado_a") else "",
                f"Paciente detectado: {r.get('paciente_detectado')}" if r.get("paciente_detectado") else "",
                f"Validação: {r.get('validacao_paciente')}" if r.get("validacao_paciente") else "",
            ] if x]),
            "prioridade": prioridade,
            "origem": "documentos_saude",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_pendencias(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT p.*, m.nome AS medicamento
        FROM pendencias_cuidado p
        LEFT JOIN medicamentos m ON m.id = p.medicamento_id
        WHERE p.usuario_id = ?
          AND p.data_criacao >= ?
        ORDER BY p.data_criacao DESC, p.id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        status = r.get("status") or "Aberta"
        eventos.append({
            "data": r.get("data_criacao"),
            "horario": "",
            "tipo": "Pendência",
            "subtipo": status,
            "titulo": r.get("titulo") or "Pendência",
            "descricao": " | ".join([x for x in [
                f"Tipo: {r.get('tipo')}" if r.get("tipo") else "",
                f"Prioridade: {r.get('prioridade')}" if r.get("prioridade") else "",
                f"Medicamento: {r.get('medicamento')}" if r.get("medicamento") else "",
                f"Descrição: {r.get('descricao')}" if r.get("descricao") else "",
                f"Resolução: {r.get('resolucao')}" if r.get("resolucao") else "",
            ] if x]),
            "prioridade": r.get("prioridade") or "Média",
            "origem": "pendencias_cuidado",
            "referencia_id": int(r["id"]),
        })
    return eventos


def eventos_corpo(usuario_id, data_min):
    df = consultar_df(
        """
        SELECT *
        FROM bioimpedancia
        WHERE usuario_id = ?
          AND data_medicao >= ?
        ORDER BY data_medicao DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    eventos = []
    for _, r in df.iterrows():
        eventos.append({
            "data": r.get("data_medicao"),
            "horario": "",
            "tipo": "Corpo",
            "subtipo": "Bioimpedância",
            "titulo": f"Peso {fmt_num(r.get('peso_kg'), 1)} kg",
            "descricao": " | ".join([x for x in [
                f"Gordura: {fmt_num(r.get('gordura_percentual'), 1)}%" if r.get("gordura_percentual") is not None else "",
                f"Massa magra: {fmt_num(r.get('massa_magra_kg'), 1)} kg" if r.get("massa_magra_kg") is not None else "",
                f"Massa muscular: {fmt_num(r.get('massa_muscular_kg'), 1)} kg" if r.get("massa_muscular_kg") is not None else "",
                f"Cintura: {fmt_num(r.get('cintura_cm'), 1)} cm" if r.get("cintura_cm") is not None else "",
                f"Obs.: {r.get('observacao')}" if r.get("observacao") else "",
            ] if x]),
            "prioridade": "Baixa",
            "origem": "bioimpedancia",
            "referencia_id": int(r["id"]),
        })
    return eventos


def montar_timeline(usuario_id, dias=365, tipos=None, prioridades=None):
    data_min = _data_min(dias)
    eventos = []
    eventos.extend(eventos_marcos(usuario_id, data_min))
    eventos.extend(eventos_medicamentos(usuario_id, data_min))
    eventos.extend(eventos_eventos_medicacao(usuario_id, data_min))
    eventos.extend(eventos_exames(usuario_id, data_min))
    eventos.extend(eventos_sintomas(usuario_id, data_min))
    eventos.extend(eventos_documentos(usuario_id, data_min))
    eventos.extend(eventos_pendencias(usuario_id, data_min))
    eventos.extend(eventos_corpo(usuario_id, data_min))

    if not eventos:
        return pd.DataFrame(columns=["data", "horario", "tipo", "subtipo", "titulo", "descricao", "prioridade", "origem", "referencia_id"])

    df = pd.DataFrame(eventos)
    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df["prioridade_ordem"] = df["prioridade"].apply(_prioridade_ordem)

    if tipos:
        df = df[df["tipo"].isin(tipos)]
    if prioridades:
        df = df[df["prioridade"].isin(prioridades)]

    df = df.sort_values(["data_dt", "horario", "prioridade_ordem"], ascending=[False, False, True])
    return df


def resumo_timeline(usuario_id, dias=365):
    df = montar_timeline(usuario_id, dias=dias)

    if df.empty:
        return {
            "total": 0,
            "alta": 0,
            "media": 0,
            "tipos": 0,
            "leitura": "Nenhum evento encontrado no período."
        }

    alta = int((df["prioridade"] == "Alta").sum())
    media = int((df["prioridade"] == "Média").sum())
    tipos = int(df["tipo"].nunique())

    if alta > 0:
        leitura = f"Há {alta} evento(s) de alta prioridade na linha do tempo."
    elif media > 0:
        leitura = f"Há {media} evento(s) de média prioridade para revisar."
    else:
        leitura = "Linha do tempo sem alertas relevantes no período."

    return {
        "total": len(df),
        "alta": alta,
        "media": media,
        "tipos": tipos,
        "leitura": leitura,
    }


def gerar_txt_timeline(usuario_id, dias=365):
    df = montar_timeline(usuario_id, dias=dias)

    linhas = []
    linhas.append("LINHA DO TEMPO CLÍNICA - SAÚDE 360")
    linhas.append("=" * 48)
    linhas.append(f"Gerada em: {date.today().strftime('%d/%m/%Y')}")
    linhas.append(f"Período: últimos {dias} dias" if int(dias) < 9999 else "Período: todos os registros")
    linhas.append("")

    if df.empty:
        linhas.append("Nenhum evento encontrado.")
        return "\n".join(linhas)

    data_atual = None
    for _, r in df.iterrows():
        data = r.get("data")
        if data != data_atual:
            data_atual = data
            linhas.append("")
            linhas.append(br_date(data))
            linhas.append("-" * 20)

        horario = f"{r.get('horario')} | " if r.get("horario") else ""
        linhas.append(f"{horario}[{r.get('prioridade')}] {r.get('tipo')} / {r.get('subtipo')}: {r.get('titulo')}")
        if r.get("descricao"):
            linhas.append(f"  {r.get('descricao')}")

    linhas.append("")
    linhas.append("Aviso: linha do tempo informativa; não diagnostica, não prescreve e não substitui avaliação médica.")
    return "\n".join(linhas)
