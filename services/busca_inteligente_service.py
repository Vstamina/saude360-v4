from datetime import date, timedelta
import pandas as pd

from core.database import consultar_df
from core.helpers import br_date, fmt_num


def _like_query(termo):
    termo = str(termo or "").strip()
    return f"%{termo}%"


def _data_min(dias):
    if int(dias) >= 9999:
        return "1900-01-01"
    return (date.today() - timedelta(days=int(dias))).isoformat()


def _normalizar_tipo(tipo):
    return str(tipo or "").strip()


def buscar_medicamentos(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            id,
            data_inicio AS data,
            'Medicamento' AS tipo,
            nome AS titulo,
            COALESCE(dose, '') || ' | ' || COALESCE(frequencia_modelo, '') || ' | ' || COALESCE(orientacao, '') AS descricao,
            COALESCE(status, 'Ativo') AS status,
            'medicamentos' AS origem
        FROM medicamentos
        WHERE usuario_id = ?
          AND data_inicio >= ?
          AND (
                nome LIKE ?
                OR COALESCE(dose, '') LIKE ?
                OR COALESCE(orientacao, '') LIKE ?
                OR COALESCE(medico, '') LIKE ?
                OR COALESCE(status, '') LIKE ?
                OR COALESCE(motivo_status, '') LIKE ?
              )
        ORDER BY data_inicio DESC, id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like, like),
    )


def buscar_exames(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            id,
            data_exame AS data,
            'Exame' AS tipo,
            COALESCE(NULLIF(nome_padronizado, ''), nome_exame) AS titulo,
            'Resultado: ' || COALESCE(CAST(resultado AS TEXT), '') || ' ' || COALESCE(unidade, '') ||
            ' | Ref.: ' || COALESCE(CAST(referencia_min AS TEXT), '') || ' a ' || COALESCE(CAST(referencia_max AS TEXT), '') ||
            ' | Original: ' || COALESCE(nome_exame, '') ||
            ' | Lab.: ' || COALESCE(laboratorio, '') ||
            ' | Obs.: ' || COALESCE(observacao, '') AS descricao,
            COALESCE(categoria_exame, 'Não classificado') AS status,
            'exames' AS origem
        FROM exames
        WHERE usuario_id = ?
          AND data_exame >= ?
          AND (
                nome_exame LIKE ?
                OR COALESCE(nome_padronizado, '') LIKE ?
                OR COALESCE(categoria_exame, '') LIKE ?
                OR COALESCE(unidade, '') LIKE ?
                OR COALESCE(laboratorio, '') LIKE ?
                OR COALESCE(observacao, '') LIKE ?
              )
        ORDER BY data_exame DESC, id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like, like),
    )


def buscar_sintomas(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            s.id,
            s.data_sintoma AS data,
            'Sintoma' AS tipo,
            s.sintoma AS titulo,
            'Intensidade: ' || COALESCE(CAST(s.intensidade AS TEXT), '') || '/10' ||
            ' | Medicamento: ' || COALESCE(m.nome, '') ||
            ' | Gatilho: ' || COALESCE(s.gatilho, '') ||
            ' | Ação: ' || COALESCE(s.acao_tomada, '') ||
            ' | Obs.: ' || COALESCE(s.observacao, '') AS descricao,
            COALESCE(CAST(s.intensidade AS TEXT), '') AS status,
            'sintomas_diario' AS origem
        FROM sintomas_diario s
        LEFT JOIN medicamentos m ON m.id = s.medicamento_id
        WHERE s.usuario_id = ?
          AND s.data_sintoma >= ?
          AND (
                s.sintoma LIKE ?
                OR COALESCE(s.gatilho, '') LIKE ?
                OR COALESCE(s.acao_tomada, '') LIKE ?
                OR COALESCE(s.observacao, '') LIKE ?
                OR COALESCE(m.nome, '') LIKE ?
              )
        ORDER BY s.data_sintoma DESC, s.id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like),
    )


def buscar_eventos(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            e.id,
            e.data_evento AS data,
            'Evento de medicação' AS tipo,
            COALESCE(e.tipo_evento, 'Evento') || ' - ' || COALESCE(m.nome, 'medicamento não informado') AS titulo,
            'Motivo: ' || COALESCE(e.motivo, '') ||
            ' | Sintomas: ' || COALESCE(e.sintomas, '') ||
            ' | Gravidade: ' || COALESCE(e.gravidade, '') ||
            ' | Conduta: ' || COALESCE(e.conduta, '') ||
            ' | Substituto: ' || COALESCE(e.substituto, '') ||
            ' | Obs.: ' || COALESCE(e.observacao, '') AS descricao,
            COALESCE(e.tipo_evento, '') AS status,
            'eventos_medicacao' AS origem
        FROM eventos_medicacao e
        LEFT JOIN medicamentos m ON m.id = e.medicamento_id
        WHERE e.usuario_id = ?
          AND e.data_evento >= ?
          AND (
                COALESCE(e.tipo_evento, '') LIKE ?
                OR COALESCE(e.motivo, '') LIKE ?
                OR COALESCE(e.sintomas, '') LIKE ?
                OR COALESCE(e.conduta, '') LIKE ?
                OR COALESCE(e.substituto, '') LIKE ?
                OR COALESCE(e.observacao, '') LIKE ?
                OR COALESCE(m.nome, '') LIKE ?
              )
        ORDER BY e.data_evento DESC, e.id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like, like, like),
    )


def buscar_marcos(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            id,
            data_marco AS data,
            'Marco clínico' AS tipo,
            titulo AS titulo,
            COALESCE(tipo_marco, '') ||
            ' | Especialidade: ' || COALESCE(especialidade, '') ||
            ' | Profissional: ' || COALESCE(profissional, '') ||
            ' | Queixas: ' || COALESCE(queixas, '') ||
            ' | Motivo: ' || COALESCE(motivo, '') ||
            ' | Conduta: ' || COALESCE(conduta, '') ||
            ' | Próximo passo: ' || COALESCE(proximo_passo, '') ||
            ' | Obs.: ' || COALESCE(observacao, '') AS descricao,
            COALESCE(tipo_marco, '') AS status,
            'marcos_jornada' AS origem
        FROM marcos_jornada
        WHERE usuario_id = ?
          AND data_marco >= ?
          AND (
                titulo LIKE ?
                OR COALESCE(tipo_marco, '') LIKE ?
                OR COALESCE(especialidade, '') LIKE ?
                OR COALESCE(profissional, '') LIKE ?
                OR COALESCE(queixas, '') LIKE ?
                OR COALESCE(motivo, '') LIKE ?
                OR COALESCE(conduta, '') LIKE ?
                OR COALESCE(proximo_passo, '') LIKE ?
                OR COALESCE(observacao, '') LIKE ?
              )
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like, like, like, like, like),
    )


def buscar_documentos(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            id,
            data_documento AS data,
            'Documento' AS tipo,
            titulo AS titulo,
            COALESCE(tipo_documento, '') ||
            ' | Profissional: ' || COALESCE(profissional, '') ||
            ' | Instituição: ' || COALESCE(instituicao, '') ||
            ' | Relacionado a: ' || COALESCE(relacionado_a, '') ||
            ' | Paciente: ' || COALESCE(paciente_detectado, '') ||
            ' | Validação: ' || COALESCE(validacao_paciente, '') ||
            ' | Obs.: ' || COALESCE(observacao, '') AS descricao,
            COALESCE(tipo_documento, '') AS status,
            'documentos_saude' AS origem
        FROM documentos_saude
        WHERE usuario_id = ?
          AND data_documento >= ?
          AND COALESCE(excluido, 0) = 0
          AND (
                titulo LIKE ?
                OR COALESCE(tipo_documento, '') LIKE ?
                OR COALESCE(profissional, '') LIKE ?
                OR COALESCE(instituicao, '') LIKE ?
                OR COALESCE(relacionado_a, '') LIKE ?
                OR COALESCE(paciente_detectado, '') LIKE ?
                OR COALESCE(validacao_paciente, '') LIKE ?
                OR COALESCE(observacao, '') LIKE ?
              )
        ORDER BY data_documento DESC, id DESC
        """,
        (usuario_id, data_min, like, like, like, like, like, like, like, like),
    )


def buscar_pendencias(usuario_id, termo):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            p.id,
            p.data_criacao AS data,
            'Pendência' AS tipo,
            p.titulo AS titulo,
            'Prioridade: ' || COALESCE(p.prioridade, '') ||
            ' | Tipo: ' || COALESCE(p.tipo, '') ||
            ' | Origem: ' || COALESCE(p.origem, '') ||
            ' | Medicamento: ' || COALESCE(m.nome, '') ||
            ' | Descrição: ' || COALESCE(p.descricao, '') ||
            ' | Resolução: ' || COALESCE(p.resolucao, '') AS descricao,
            COALESCE(p.status, '') AS status,
            'pendencias_cuidado' AS origem
        FROM pendencias_cuidado p
        LEFT JOIN medicamentos m ON m.id = p.medicamento_id
        WHERE p.usuario_id = ?
          AND (
                p.titulo LIKE ?
                OR COALESCE(p.tipo, '') LIKE ?
                OR COALESCE(p.prioridade, '') LIKE ?
                OR COALESCE(p.origem, '') LIKE ?
                OR COALESCE(p.descricao, '') LIKE ?
                OR COALESCE(p.resolucao, '') LIKE ?
                OR COALESCE(m.nome, '') LIKE ?
              )
        ORDER BY p.data_criacao DESC, p.id DESC
        """,
        (usuario_id, like, like, like, like, like, like, like),
    )


def buscar_corpo(usuario_id, termo, data_min):
    like = _like_query(termo)
    return consultar_df(
        """
        SELECT
            id,
            data_medicao AS data,
            'Corpo' AS tipo,
            'Bioimpedância / medidas' AS titulo,
            'Peso: ' || COALESCE(CAST(peso_kg AS TEXT), '') ||
            ' | Gordura: ' || COALESCE(CAST(gordura_percentual AS TEXT), '') ||
            ' | Massa magra: ' || COALESCE(CAST(massa_magra_kg AS TEXT), '') ||
            ' | Massa muscular: ' || COALESCE(CAST(massa_muscular_kg AS TEXT), '') ||
            ' | Cintura: ' || COALESCE(CAST(cintura_cm AS TEXT), '') ||
            ' | Obs.: ' || COALESCE(observacao, '') AS descricao,
            'Bioimpedância' AS status,
            'bioimpedancia' AS origem
        FROM bioimpedancia
        WHERE usuario_id = ?
          AND data_medicao >= ?
          AND (
                COALESCE(observacao, '') LIKE ?
                OR CAST(peso_kg AS TEXT) LIKE ?
                OR CAST(gordura_percentual AS TEXT) LIKE ?
                OR CAST(cintura_cm AS TEXT) LIKE ?
              )
        ORDER BY data_medicao DESC, id DESC
        """,
        (usuario_id, data_min, like, like, like, like),
    )


def busca_global(usuario_id, termo, dias=365, tipos=None):
    termo = str(termo or "").strip()
    data_min = _data_min(dias)

    if not termo:
        return pd.DataFrame(columns=["id", "data", "tipo", "titulo", "descricao", "status", "origem"])

    fontes = {
        "Medicamento": buscar_medicamentos,
        "Exame": buscar_exames,
        "Sintoma": buscar_sintomas,
        "Evento de medicação": buscar_eventos,
        "Marco clínico": buscar_marcos,
        "Documento": buscar_documentos,
        "Pendência": buscar_pendencias,
        "Corpo": buscar_corpo,
    }

    if tipos:
        fontes = {k: v for k, v in fontes.items() if k in tipos}

    partes = []
    for tipo, func in fontes.items():
        try:
            if tipo == "Pendência":
                df = func(usuario_id, termo)
            else:
                df = func(usuario_id, termo, data_min)
            if df is not None and not df.empty:
                partes.append(df)
        except Exception:
            # Não quebra a busca se uma tabela ainda não existir.
            pass

    if not partes:
        return pd.DataFrame(columns=["id", "data", "tipo", "titulo", "descricao", "status", "origem"])

    df = pd.concat(partes, ignore_index=True)
    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.sort_values(["data_dt", "tipo"], ascending=[False, True])
    return df


def resumo_busca(df, termo):
    if df.empty:
        return f"Nenhum resultado encontrado para '{termo}'."

    por_tipo = df["tipo"].value_counts().to_dict()
    partes = [f"{tipo}: {total}" for tipo, total in por_tipo.items()]
    return f"{len(df)} resultado(s) encontrado(s) para '{termo}': " + "; ".join(partes)


def gerar_txt_busca(df, termo):
    linhas = []
    linhas.append("BUSCA INTELIGENTE - SAÚDE 360")
    linhas.append("=" * 42)
    linhas.append(f"Termo pesquisado: {termo}")
    linhas.append(f"Resultados: {len(df)}")
    linhas.append("")

    if df.empty:
        linhas.append("Nenhum resultado encontrado.")
        return "\n".join(linhas)

    for _, r in df.iterrows():
        linhas.append(f"- {br_date(r.get('data'))} | {r.get('tipo')} | {r.get('titulo')}")
        linhas.append(f"  Status/subtipo: {r.get('status') or ''}")
        linhas.append(f"  Origem: {r.get('origem')} | ID: {r.get('id')}")
        if r.get("descricao"):
            linhas.append(f"  {r.get('descricao')}")
        linhas.append("")

    return "\n".join(linhas)
