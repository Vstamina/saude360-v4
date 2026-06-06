from datetime import date, timedelta
from html import escape

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def _safe(valor):
    if valor is None:
        return ""
    return str(valor)


def _periodo_inicio(dias):
    try:
        dias = int(dias)
    except Exception:
        dias = 90
    return (date.today() - timedelta(days=dias)).isoformat()


def obter_dados_relatorio_consulta(usuario_id, dias=90):
    data_min = _periodo_inicio(dias)

    medicamentos_ativos = consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND COALESCE(status, 'Ativo') = 'Ativo'
        ORDER BY data_inicio DESC, nome
        """,
        (usuario_id,),
    )

    medicamentos_periodo = consultar_df(
        """
        SELECT *
        FROM medicamentos
        WHERE usuario_id = ?
          AND data_inicio >= ?
        ORDER BY data_inicio DESC, nome
        """,
        (usuario_id, data_min),
    )

    eventos = consultar_df(
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

    doses_nao_tomadas = consultar_df(
        """
        SELECT d.*, m.nome AS medicamento, m.dose
        FROM doses d
        LEFT JOIN medicamentos m ON m.id = d.medicamento_id
        WHERE d.usuario_id = ?
          AND d.data_prevista >= ?
          AND d.status IN ('Não tomado', 'Nao tomado', 'Esquecido')
        ORDER BY d.data_prevista DESC, d.horario_previsto DESC
        """,
        (usuario_id, data_min),
    )

    exames = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND data_exame >= ?
        ORDER BY data_exame DESC, nome_exame
        """,
        (usuario_id, data_min),
    )

    sintomas = consultar_df(
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

    marcos = consultar_df(
        """
        SELECT *
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco >= ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    pendencias = consultar_df(
        """
        SELECT p.*, m.nome AS medicamento
        FROM pendencias_cuidado p
        LEFT JOIN medicamentos m ON m.id = p.medicamento_id
        WHERE p.usuario_id = ?
          AND p.status = 'Aberta'
        ORDER BY CASE p.prioridade WHEN 'Alta' THEN 1 WHEN 'Média' THEN 2 ELSE 3 END,
                 p.data_criacao DESC,
                 p.id DESC
        """,
        (usuario_id,),
    )

    documentos = consultar_df(
        """
        SELECT *
        FROM documentos_saude
        WHERE usuario_id = ?
          AND COALESCE(excluido, 0) = 0
          AND data_documento >= ?
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    bio = consultar_df(
        """
        SELECT *
        FROM bioimpedancia
        WHERE usuario_id = ?
          AND data_medicao >= ?
        ORDER BY data_medicao DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    atividades = consultar_df(
        """
        SELECT *
        FROM atividades
        WHERE usuario_id = ?
          AND data_atividade >= ?
        ORDER BY data_atividade DESC, id DESC
        """,
        (usuario_id, data_min),
    )

    return {
        "data_min": data_min,
        "medicamentos_ativos": medicamentos_ativos,
        "medicamentos_periodo": medicamentos_periodo,
        "eventos": eventos,
        "doses_nao_tomadas": doses_nao_tomadas,
        "exames": exames,
        "sintomas": sintomas,
        "marcos": marcos,
        "pendencias": pendencias,
        "documentos": documentos,
        "bio": bio,
        "atividades": atividades,
    }


def classificar_exame(resultado, ref_min, ref_max):
    try:
        resultado = float(resultado)
        ref_min = float(ref_min)
        ref_max = float(ref_max)
    except Exception:
        return "Sem referência"

    if ref_min == 0 and ref_max == 0:
        return "Sem referência"

    if resultado < ref_min:
        return "Abaixo da referência"
    if resultado > ref_max:
        return "Acima da referência"

    largura = max(ref_max - ref_min, 0.0001)
    margem = largura * 0.12

    if resultado <= ref_min + margem:
        return "Dentro, próximo do limite inferior"
    if resultado >= ref_max - margem:
        return "Dentro, próximo do limite superior"
    return "Dentro da referência"


def exames_em_atencao(exames):
    if exames.empty:
        return exames

    df = exames.copy()
    df["classificacao"] = df.apply(
        lambda r: classificar_exame(r.get("resultado"), r.get("referencia_min"), r.get("referencia_max")),
        axis=1,
    )

    return df[df["classificacao"] != "Dentro da referência"]


def gerar_leitura_consulta(dados, motivo_consulta="", foco_consulta=""):
    partes = []

    pend = dados["pendencias"]
    eventos = dados["eventos"]
    doses = dados["doses_nao_tomadas"]
    exames = dados["exames"]
    sintomas = dados["sintomas"]
    meds_ativos = dados["medicamentos_ativos"]
    alertas_exames = exames_em_atencao(exames)

    partes.append("Resumo para consulta:")
    if motivo_consulta:
        partes.append(f"- Motivo informado para a consulta: {motivo_consulta}.")
    if foco_consulta:
        partes.append(f"- Foco principal da conversa: {foco_consulta}.")

    partes.append(f"- Medicamentos ativos: {len(meds_ativos)}.")
    partes.append(f"- Pendências abertas: {len(pend)}.")
    partes.append(f"- Eventos/alterações de medicação no período: {len(eventos)}.")
    partes.append(f"- Doses não tomadas no período: {len(doses)}.")
    partes.append(f"- Exames cadastrados no período: {len(exames)}; em atenção: {len(alertas_exames)}.")
    partes.append(f"- Sintomas registrados no período: {len(sintomas)}.")

    if not pend.empty:
        prioridades = pend["prioridade"].fillna("").value_counts().to_dict()
        if prioridades:
            partes.append(f"- Prioridades das pendências: {prioridades}.")

    if not alertas_exames.empty:
        nomes = ", ".join(alertas_exames["nome_exame"].dropna().astype(str).head(5).tolist())
        partes.append(f"- Exames que merecem revisão na consulta: {nomes}.")

    if not eventos.empty:
        eventos_relevantes = eventos[eventos["tipo_evento"].isin(["Efeito adverso", "Suspenso", "Substituido", "Pausado"])]
        if not eventos_relevantes.empty:
            nomes = ", ".join(eventos_relevantes["medicamento"].fillna("medicamento não informado").astype(str).head(5).tolist())
            partes.append(f"- Houve evento adverso, pausa, suspensão ou substituição relacionado a: {nomes}.")

    return "\n".join(partes)


def gerar_perguntas_para_medico(dados, motivo_consulta="", foco_consulta=""):
    perguntas = []

    pend = dados["pendencias"]
    eventos = dados["eventos"]
    doses = dados["doses_nao_tomadas"]
    alertas_exames = exames_em_atencao(dados["exames"])

    if motivo_consulta:
        perguntas.append(f"Este motivo da consulta está adequadamente coberto pelo tratamento atual: {motivo_consulta}?")

    if foco_consulta:
        perguntas.append(f"O que devo priorizar em relação a {foco_consulta}?")

    if not alertas_exames.empty:
        perguntas.append("Quais exames em atenção precisam de repetição, acompanhamento ou investigação?")
        perguntas.append("Algum resultado pode estar relacionado a medicamento, alimentação, peso, treino ou outro fator recente?")

    if not eventos.empty:
        perguntas.append("Os eventos adversos ou sintomas registrados podem estar relacionados a algum medicamento?")
        perguntas.append("Há necessidade de ajustar dose, horário, pausa, troca ou monitoramento?")

    if not doses.empty:
        perguntas.append("O que devo fazer quando esquecer uma dose ou quando a medicação acabar?")
        perguntas.append("Há alguma dose perdida que exige orientação específica?")

    if not pend.empty:
        perguntas.append("Quais pendências abertas devo resolver primeiro?")

    perguntas.append("Quais sinais de alerta devem me fazer procurar atendimento antes do retorno?")
    perguntas.append("Quando devo retornar e quais exames/documentos devo levar?")

    return perguntas


def _table_rows_html(headers, rows):
    html = "<table><thead><tr>"
    for h in headers:
        html += f"<th>{escape(str(h))}</th>"
    html += "</tr></thead><tbody>"
    for row in rows:
        html += "<tr>"
        for cell in row:
            html += f"<td>{escape(str(cell))}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


def gerar_html_relatorio(usuario, dados, motivo_consulta="", foco_consulta="", observacoes=""):
    nome = _safe(usuario.get("nome") if hasattr(usuario, "get") else usuario["nome"])
    data_geracao = date.today().strftime("%d/%m/%Y")
    leitura = gerar_leitura_consulta(dados, motivo_consulta, foco_consulta)
    perguntas = gerar_perguntas_para_medico(dados, motivo_consulta, foco_consulta)

    meds = dados["medicamentos_ativos"]
    eventos = dados["eventos"]
    doses = dados["doses_nao_tomadas"]
    exames = dados["exames"]
    alertas_exames = exames_em_atencao(exames)
    sintomas = dados["sintomas"]
    marcos = dados["marcos"]
    pendencias = dados["pendencias"]

    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório para consulta - Saúde 360</title>
<style>
body {{
    font-family: Arial, sans-serif;
    color: #0B1F33;
    background: #F6FAFB;
    margin: 0;
    padding: 28px;
}}
.report {{
    max-width: 980px;
    margin: 0 auto;
    background: white;
    border-radius: 22px;
    padding: 28px;
    box-shadow: 0 12px 35px rgba(15,31,51,.10);
}}
.hero {{
    background: linear-gradient(135deg, #0B3A5B, #36C2D6, #7C5CE1);
    color: white;
    border-radius: 22px;
    padding: 26px;
    margin-bottom: 22px;
}}
.hero h1 {{
    margin: 0 0 8px 0;
    font-size: 30px;
}}
.badge {{
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    background: #E6E0FF;
    color: #312E81;
    font-weight: bold;
    margin: 4px 4px 4px 0;
}}
.section {{
    margin-top: 26px;
}}
h2 {{
    border-bottom: 1px solid #DCEAF5;
    padding-bottom: 8px;
}}
pre {{
    white-space: pre-wrap;
    background: #F4F6F8;
    padding: 16px;
    border-radius: 14px;
    line-height: 1.45;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 10px;
    font-size: 14px;
}}
th, td {{
    border-bottom: 1px solid #E5EDF3;
    padding: 9px;
    text-align: left;
    vertical-align: top;
}}
th {{
    background: #F4F6F8;
}}
.warn {{
    color: #92400E;
    font-weight: bold;
}}
.danger {{
    color: #991B1B;
    font-weight: bold;
}}
.footer {{
    margin-top: 30px;
    color: #64748B;
    font-size: 12px;
}}
</style>
</head>
<body>
<div class="report">
<div class="hero">
<h1>Relatório para consulta médica</h1>
<p><strong>Paciente:</strong> {escape(nome)}</p>
<p><strong>Gerado em:</strong> {data_geracao}</p>
<p><strong>Período analisado desde:</strong> {escape(br_date(dados["data_min"]))}</p>
</div>

<div>
<span class="badge">Uso informativo</span>
<span class="badge">Não substitui avaliação médica</span>
<span class="badge">Dados revisáveis</span>
</div>

<div class="section">
<h2>Resumo executivo</h2>
<pre>{escape(leitura)}</pre>
</div>
"""

    if observacoes:
        html += f"""
<div class="section">
<h2>Observações do paciente</h2>
<pre>{escape(observacoes)}</pre>
</div>
"""

    html += """
<div class="section">
<h2>Perguntas sugeridas para a consulta</h2>
<ol>
"""
    for p in perguntas:
        html += f"<li>{escape(p)}</li>"
    html += "</ol></div>"

    html += "<div class='section'><h2>Medicamentos ativos</h2>"
    if meds.empty:
        html += "<p>Nenhum medicamento ativo registrado.</p>"
    else:
        rows = []
        for _, r in meds.iterrows():
            rows.append([
                br_date(r.get("data_inicio")),
                r.get("nome") or "",
                r.get("dose") or "",
                r.get("frequencia_modelo") or "",
                r.get("horario_inicial") or "",
                r.get("orientacao") or "",
            ])
        html += _table_rows_html(["Início", "Medicamento", "Dose", "Frequência", "Horário", "Orientação"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Exames em atenção</h2>"
    if alertas_exames.empty:
        html += "<p>Nenhum exame em atenção no período.</p>"
    else:
        rows = []
        for _, r in alertas_exames.iterrows():
            rows.append([
                br_date(r.get("data_exame")),
                r.get("nome_exame") or "",
                f"{fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''}",
                f"{fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)}",
                r.get("classificacao") or "",
            ])
        html += _table_rows_html(["Data", "Exame", "Resultado", "Referência", "Leitura"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Eventos de medicação</h2>"
    if eventos.empty:
        html += "<p>Nenhum evento de medicação registrado no período.</p>"
    else:
        rows = []
        for _, r in eventos.head(30).iterrows():
            rows.append([
                br_date(r.get("data_evento")),
                r.get("tipo_evento") or "",
                r.get("medicamento") or "",
                r.get("motivo") or "",
                r.get("sintomas") or "",
                r.get("conduta") or "",
            ])
        html += _table_rows_html(["Data", "Evento", "Medicamento", "Motivo", "Sintomas", "Conduta"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Doses não tomadas</h2>"
    if doses.empty:
        html += "<p>Nenhuma dose não tomada registrada no período.</p>"
    else:
        rows = []
        for _, r in doses.head(40).iterrows():
            rows.append([
                br_date(r.get("data_prevista")),
                r.get("horario_previsto") or "",
                r.get("medicamento") or "",
                r.get("dose") or "",
                r.get("motivo_nao_tomou") or "",
                r.get("observacao") or "",
            ])
        html += _table_rows_html(["Data", "Horário", "Medicamento", "Dose", "Motivo", "Observação"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Sintomas registrados</h2>"
    if sintomas.empty:
        html += "<p>Nenhum sintoma registrado no período.</p>"
    else:
        rows = []
        for _, r in sintomas.head(40).iterrows():
            rows.append([
                br_date(r.get("data_sintoma")),
                r.get("horario") or "",
                r.get("sintoma") or "",
                r.get("intensidade") or "",
                r.get("medicamento") or "",
                r.get("observacao") or "",
            ])
        html += _table_rows_html(["Data", "Horário", "Sintoma", "Intensidade", "Medicamento associado", "Observação"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Pendências abertas</h2>"
    if pendencias.empty:
        html += "<p>Nenhuma pendência aberta.</p>"
    else:
        rows = []
        for _, r in pendencias.head(40).iterrows():
            rows.append([
                br_date(r.get("data_criacao")),
                r.get("prioridade") or "",
                r.get("tipo") or "",
                r.get("titulo") or "",
                r.get("descricao") or "",
            ])
        html += _table_rows_html(["Data", "Prioridade", "Tipo", "Título", "Descrição"], rows)
    html += "</div>"

    html += "<div class='section'><h2>Marcos recentes</h2>"
    if marcos.empty:
        html += "<p>Nenhum marco registrado no período.</p>"
    else:
        rows = []
        for _, r in marcos.head(30).iterrows():
            rows.append([
                br_date(r.get("data_marco")),
                r.get("tipo_marco") or "",
                r.get("titulo") or "",
                r.get("especialidade") or "",
                r.get("conduta") or "",
                r.get("proximo_passo") or "",
            ])
        html += _table_rows_html(["Data", "Tipo", "Título", "Especialidade", "Conduta", "Próximo passo"], rows)
    html += "</div>"

    html += """
<div class="footer">
<p>Relatório gerado pelo Saúde 360. Uso informativo. O sistema organiza dados e gera leituras de acompanhamento; não realiza diagnóstico, não prescreve tratamento e não substitui avaliação médica.</p>
</div>
</div>
</body>
</html>
"""
    return html


def gerar_txt_relatorio(usuario, dados, motivo_consulta="", foco_consulta="", observacoes=""):
    nome = _safe(usuario.get("nome") if hasattr(usuario, "get") else usuario["nome"])
    leitura = gerar_leitura_consulta(dados, motivo_consulta, foco_consulta)
    perguntas = gerar_perguntas_para_medico(dados, motivo_consulta, foco_consulta)

    linhas = []
    linhas.append("RELATÓRIO PARA CONSULTA MÉDICA - SAÚDE 360")
    linhas.append("=" * 52)
    linhas.append(f"Paciente: {nome}")
    linhas.append(f"Gerado em: {date.today().strftime('%d/%m/%Y')}")
    linhas.append(f"Período analisado desde: {br_date(dados['data_min'])}")
    linhas.append("")
    linhas.append(leitura)
    linhas.append("")

    if observacoes:
        linhas.append("OBSERVAÇÕES DO PACIENTE")
        linhas.append("-" * 30)
        linhas.append(observacoes)
        linhas.append("")

    linhas.append("PERGUNTAS PARA A CONSULTA")
    linhas.append("-" * 30)
    for i, p in enumerate(perguntas, start=1):
        linhas.append(f"{i}. {p}")
    linhas.append("")

    linhas.append("MEDICAMENTOS ATIVOS")
    linhas.append("-" * 30)
    meds = dados["medicamentos_ativos"]
    if meds.empty:
        linhas.append("Nenhum medicamento ativo registrado.")
    else:
        for _, r in meds.iterrows():
            linhas.append(
                f"- {br_date(r.get('data_inicio'))} | {r.get('nome') or ''} | {r.get('dose') or ''} | "
                f"{r.get('frequencia_modelo') or ''} | {r.get('horario_inicial') or ''}"
            )
            if r.get("orientacao"):
                linhas.append(f"  Orientação: {r.get('orientacao')}")
    linhas.append("")

    linhas.append("EXAMES EM ATENÇÃO")
    linhas.append("-" * 30)
    alertas = exames_em_atencao(dados["exames"])
    if alertas.empty:
        linhas.append("Nenhum exame em atenção no período.")
    else:
        for _, r in alertas.iterrows():
            linhas.append(
                f"- {br_date(r.get('data_exame'))} | {r.get('nome_exame') or ''}: "
                f"{fmt_num(r.get('resultado'), 2)} {r.get('unidade') or ''} "
                f"(ref. {fmt_num(r.get('referencia_min'), 2)} a {fmt_num(r.get('referencia_max'), 2)}) "
                f"| {r.get('classificacao') or ''}"
            )
    linhas.append("")

    linhas.append("EVENTOS DE MEDICAÇÃO")
    linhas.append("-" * 30)
    eventos = dados["eventos"]
    if eventos.empty:
        linhas.append("Nenhum evento de medicação registrado.")
    else:
        for _, r in eventos.head(30).iterrows():
            linhas.append(
                f"- {br_date(r.get('data_evento'))} | {r.get('tipo_evento') or ''} | "
                f"{r.get('medicamento') or ''} | {r.get('motivo') or ''}"
            )
            if r.get("sintomas"):
                linhas.append(f"  Sintomas: {r.get('sintomas')}")
            if r.get("conduta"):
                linhas.append(f"  Conduta: {r.get('conduta')}")
    linhas.append("")

    linhas.append("PENDÊNCIAS ABERTAS")
    linhas.append("-" * 30)
    pend = dados["pendencias"]
    if pend.empty:
        linhas.append("Nenhuma pendência aberta.")
    else:
        for _, r in pend.head(40).iterrows():
            linhas.append(f"- {r.get('prioridade') or ''} | {r.get('tipo') or ''} | {r.get('titulo') or ''}")
            if r.get("descricao"):
                linhas.append(f"  {r.get('descricao')}")
    linhas.append("")

    linhas.append("Uso informativo. Não realiza diagnóstico, não prescreve tratamento e não substitui avaliação médica.")
    return "\n".join(linhas)
