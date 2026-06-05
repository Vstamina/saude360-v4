from datetime import date

from components.gauges import classificar_exame
from core.helpers import br_date, fmt_num
from services.medicamentos_service import listar_medicamentos_ativos, listar_eventos_adversos
from services.exames_service import exames_mais_recentes
from services.documentos_service import listar_documentos
from services.sintomas_service import sintomas_ultimos_dias, gerar_leitura_sintomas
from services.marcos_service import listar_marcos_recentes


def gerar_relatorio_consulta(usuario_id, usuario):
    nome_usuario = usuario.get("nome", "Usuario") if hasattr(usuario, "get") else str(usuario)
    hoje = date.today().strftime("%d/%m/%Y")

    meds_ativos = listar_medicamentos_ativos(usuario_id)
    eventos_adversos = listar_eventos_adversos(usuario_id)
    exames_rec = exames_mais_recentes(usuario_id)
    docs = listar_documentos(usuario_id, limite=10)
    sintomas = sintomas_ultimos_dias(usuario_id, dias=30)
    marcos = listar_marcos_recentes(usuario_id, limite=10)
    leitura_sintomas = gerar_leitura_sintomas(usuario_id, dias=30)

    linhas = []

    linhas.append("RELATORIO PARA CONSULTA MEDICA")
    linhas.append("=" * 34)
    linhas.append("")
    linhas.append(f"Paciente: {nome_usuario}")
    linhas.append(f"Data do resumo: {hoje}")
    linhas.append("")
    linhas.append("Observacao:")
    linhas.append("Este relatorio organiza dados informados pelo usuario. Ele nao realiza diagnostico, nao prescreve tratamento e nao substitui avaliacao medica.")
    linhas.append("")

    linhas.append("1. CONSULTAS E MARCOS RECENTES")
    linhas.append("-" * 34)
    if marcos.empty:
        linhas.append("Nenhum marco registrado.")
    else:
        for _, m in marcos.iterrows():
            linhas.append(f"- {br_date(m['data_marco'])} | {m['tipo_marco']} | {m['titulo']}")
            if m.get("especialidade"):
                linhas.append(f"  Especialidade: {m.get('especialidade')}")
            if m.get("profissional"):
                linhas.append(f"  Profissional: {m.get('profissional')}")
            if m.get("queixas"):
                linhas.append(f"  Queixas: {m.get('queixas')}")
            if m.get("conduta"):
                linhas.append(f"  Conduta: {m.get('conduta')}")
            if m.get("proximo_passo"):
                linhas.append(f"  Proximo passo: {m.get('proximo_passo')}")
    linhas.append("")

    linhas.append("2. MEDICAMENTOS ATIVOS")
    linhas.append("-" * 24)
    if meds_ativos.empty:
        linhas.append("Nenhum medicamento ativo registrado.")
    else:
        for _, m in meds_ativos.iterrows():
            linhas.append(f"- {m['nome']} | Dose: {m['dose'] or 'nao informada'}")
            linhas.append(f"  Inicio: {br_date(m['data_inicio'])}")
            if m.get("data_fim"):
                linhas.append(f"  Fim previsto: {br_date(m['data_fim'])}")
            if int(m.get("uso_continuo") or 0) == 1:
                linhas.append("  Uso continuo: sim")
            if m.get("medico"):
                linhas.append(f"  Profissional: {m.get('medico')}")
            if m.get("orientacao"):
                linhas.append(f"  Orientacao: {m.get('orientacao')}")
    linhas.append("")

    linhas.append("3. MEDICAMENTOS SUSPENSOS, SUBSTITUIDOS OU COM EVENTOS")
    linhas.append("-" * 58)
    if eventos_adversos.empty:
        linhas.append("Nenhum evento adverso/STOP registrado.")
    else:
        for _, e in eventos_adversos.head(12).iterrows():
            linhas.append(f"- {br_date(e['data_evento'])} | {e.get('medicamento') or 'medicamento nao informado'} | {e.get('tipo_evento') or ''}")
            if e.get("motivo"):
                linhas.append(f"  Motivo: {e.get('motivo')}")
            if e.get("sintomas"):
                linhas.append(f"  Sintomas: {e.get('sintomas')}")
            if e.get("gravidade"):
                linhas.append(f"  Gravidade: {e.get('gravidade')}")
            if e.get("orientado_por"):
                linhas.append(f"  Orientado por: {e.get('orientado_por')}")
            if e.get("conduta"):
                linhas.append(f"  Conduta: {e.get('conduta')}")
            if e.get("substituto"):
                linhas.append(f"  Substituto: {e.get('substituto')}")
            if e.get("observacao"):
                linhas.append(f"  Observacao: {e.get('observacao')}")
    linhas.append("")

    linhas.append("4. SINTOMAS DOS ULTIMOS 30 DIAS")
    linhas.append("-" * 34)
    linhas.append(leitura_sintomas)
    if sintomas.empty:
        linhas.append("Nenhum sintoma registrado no periodo.")
    else:
        for _, s in sintomas.head(15).iterrows():
            med = f" | Medicamento: {s.get('medicamento')}" if s.get("medicamento") else ""
            linhas.append(f"- {br_date(s['data_sintoma'])} {s.get('horario') or ''} | {s.get('sintoma')} | intensidade {int(s.get('intensidade') or 0)}/10{med}")
            if s.get("gatilho"):
                linhas.append(f"  Gatilho percebido: {s.get('gatilho')}")
            if s.get("acao_tomada"):
                linhas.append(f"  Acao tomada: {s.get('acao_tomada')}")
            if s.get("observacao"):
                linhas.append(f"  Observacao: {s.get('observacao')}")
    linhas.append("")

    linhas.append("5. EXAMES EM ATENCAO")
    linhas.append("-" * 22)
    encontrou_exame = False
    if exames_rec.empty:
        linhas.append("Nenhum exame registrado.")
    else:
        for _, r in exames_rec.iterrows():
            status, _, leitura = classificar_exame(r["resultado"], r["referencia_min"], r["referencia_max"])
            if status in [
                "Abaixo da faixa",
                "Acima da faixa",
                "Na faixa, perto do minimo",
                "Na faixa, perto do maximo",
                "Abaixo",
                "Acima",
                "Limite inferior",
                "Limite superior",
            ]:
                encontrou_exame = True
                unidade = r.get("unidade") or ""
                linhas.append(f"- {r['nome_exame']}: {fmt_num(r['resultado'])} {unidade} | {status}")
                linhas.append(f"  Data: {br_date(r['data_exame'])}")
                linhas.append(f"  Referencia cadastrada: {fmt_num(r['referencia_min'])} a {fmt_num(r['referencia_max'])} {unidade}")
                linhas.append(f"  Leitura: {leitura}")
        if not encontrou_exame:
            linhas.append("Nenhum exame em alerta pelos parametros cadastrados.")
    linhas.append("")

    linhas.append("6. DOCUMENTOS RECENTES")
    linhas.append("-" * 24)
    if docs.empty:
        linhas.append("Nenhum documento salvo no repositorio.")
    else:
        for _, d in docs.iterrows():
            linhas.append(f"- {br_date(d['data_documento'])} | {d['tipo_documento']} | {d['titulo']}")
            if d.get("profissional"):
                linhas.append(f"  Profissional: {d.get('profissional')}")
            if d.get("instituicao"):
                linhas.append(f"  Instituicao: {d.get('instituicao')}")
            if d.get("relacionado_a"):
                linhas.append(f"  Relacionado a: {d.get('relacionado_a')}")
            if d.get("caminho_arquivo"):
                linhas.append(f"  Arquivo: {d.get('caminho_arquivo')}")
    linhas.append("")

    linhas.append("7. PONTOS PARA CONVERSAR NA CONSULTA")
    linhas.append("-" * 38)
    linhas.append("- Confirmar se os medicamentos ativos continuam adequados.")
    linhas.append("- Revisar sintomas recentes, principalmente os de maior intensidade ou associados a medicamentos.")
    linhas.append("- Avaliar medicamentos suspensos, substituidos ou mal tolerados.")
    linhas.append("- Conferir exames em atencao e necessidade de acompanhamento.")
    linhas.append("- Revisar os marcos recentes e o proximo passo de cada consulta/conduta.")
    linhas.append("- Atualizar orientacoes, dose, frequencia e duracao dos tratamentos.")
    linhas.append("")

    return "\n".join(linhas)
