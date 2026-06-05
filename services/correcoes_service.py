from core.database import consultar_df, executar


def listar_usuarios():
    return consultar_df(
        """
        SELECT id, nome
        FROM usuarios
        ORDER BY nome
        """
    )


def listar_documentos_para_correcao(usuario_id):
    return consultar_df(
        """
        SELECT d.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM documentos_saude d
        LEFT JOIN marcos_jornada m ON m.id = d.marco_id
        WHERE d.usuario_id = ?
          AND COALESCE(d.excluido, 0) = 0
        ORDER BY d.data_documento DESC, d.id DESC
        """,
        (usuario_id,),
    )


def listar_exames_para_correcao(usuario_id):
    return consultar_df(
        """
        SELECT e.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM exames e
        LEFT JOIN marcos_jornada m ON m.id = e.marco_id
        WHERE e.usuario_id = ?
        ORDER BY e.data_exame DESC, e.nome_exame, e.id DESC
        """,
        (usuario_id,),
    )


def listar_medicamentos_para_correcao(usuario_id):
    return consultar_df(
        """
        SELECT med.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM medicamentos med
        LEFT JOIN marcos_jornada m ON m.id = med.marco_id
        WHERE med.usuario_id = ?
        ORDER BY med.data_inicio DESC, med.nome, med.id DESC
        """,
        (usuario_id,),
    )


def listar_sintomas_para_correcao(usuario_id):
    return consultar_df(
        """
        SELECT s.*, m.titulo AS marco_titulo, med.nome AS medicamento
        FROM sintomas_diario s
        LEFT JOIN marcos_jornada m ON m.id = s.marco_id
        LEFT JOIN medicamentos med ON med.id = s.medicamento_id
        WHERE s.usuario_id = ?
        ORDER BY s.data_sintoma DESC, s.horario DESC, s.id DESC
        """,
        (usuario_id,),
    )


def listar_marcos_opcoes(usuario_id):
    df = consultar_df(
        """
        SELECT id, data_marco, tipo_marco, titulo
        FROM marcos_jornada
        WHERE usuario_id = ?
        ORDER BY data_marco DESC, id DESC
        """,
        (usuario_id,),
    )

    opcoes = {"Sem marco relacionado": None}
    for _, r in df.iterrows():
        opcoes[f"{r['data_marco']} | {r['tipo_marco']} | {r['titulo']} | ID {r['id']}"] = int(r["id"])
    return opcoes


def mover_documento_para_usuario(usuario_origem_id, documento_id, usuario_destino_id):
    """
    Move apenas o documento. O marco_id e limpo porque marcos pertencem ao usuario de origem.
    O arquivo fisico permanece no mesmo caminho, mas o registro passa para outro usuario.
    """
    doc = consultar_df(
        """
        SELECT id
        FROM documentos_saude
        WHERE id = ?
          AND usuario_id = ?
          AND COALESCE(excluido, 0) = 0
        """,
        (documento_id, usuario_origem_id),
    )

    if doc.empty:
        return False, "Documento nao encontrado no usuario ativo."

    executar(
        """
        UPDATE documentos_saude
        SET usuario_id = ?,
            marco_id = NULL
        WHERE id = ?
          AND usuario_id = ?
        """,
        (usuario_destino_id, documento_id, usuario_origem_id),
    )

    return True, "Documento movido para outro usuario. O vinculo com marco foi limpo para evitar associacao errada."


def atualizar_marco_documento(usuario_id, documento_id, marco_id):
    executar(
        """
        UPDATE documentos_saude
        SET marco_id = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (marco_id, usuario_id, documento_id),
    )


def atualizar_marco_exame(usuario_id, exame_id, marco_id):
    executar(
        """
        UPDATE exames
        SET marco_id = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (marco_id, usuario_id, exame_id),
    )


def atualizar_marco_medicamento(usuario_id, medicamento_id, marco_id):
    executar(
        """
        UPDATE medicamentos
        SET marco_id = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (marco_id, usuario_id, medicamento_id),
    )

    # Tambem tenta associar o evento de inicio ao mesmo marco.
    executar(
        """
        UPDATE eventos_medicacao
        SET marco_id = ?
        WHERE usuario_id = ?
          AND medicamento_id = ?
          AND tipo_evento = 'Inicio'
        """,
        (marco_id, usuario_id, medicamento_id),
    )


def atualizar_marco_sintoma(usuario_id, sintoma_id, marco_id):
    executar(
        """
        UPDATE sintomas_diario
        SET marco_id = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (marco_id, usuario_id, sintoma_id),
    )


def excluir_exame(usuario_id, exame_id):
    exame = consultar_df(
        """
        SELECT id
        FROM exames
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, exame_id),
    )

    if exame.empty:
        return False, "Exame nao encontrado."

    executar(
        """
        DELETE FROM exames
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, exame_id),
    )

    return True, "Exame excluido."


def excluir_sintoma(usuario_id, sintoma_id):
    sintoma = consultar_df(
        """
        SELECT id
        FROM sintomas_diario
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, sintoma_id),
    )

    if sintoma.empty:
        return False, "Sintoma nao encontrado."

    executar(
        """
        DELETE FROM sintomas_diario
        WHERE usuario_id = ?
          AND id = ?
        """,
        (usuario_id, sintoma_id),
    )

    return True, "Sintoma excluido."


def gerar_resumo_correcoes(usuario_id):
    docs = listar_documentos_para_correcao(usuario_id)
    exames = listar_exames_para_correcao(usuario_id)
    meds = listar_medicamentos_para_correcao(usuario_id)
    sintomas = listar_sintomas_para_correcao(usuario_id)

    docs_sem_marco = len(docs[docs["marco_id"].isna()]) if not docs.empty and "marco_id" in docs.columns else 0
    exames_sem_marco = len(exames[exames["marco_id"].isna()]) if not exames.empty and "marco_id" in exames.columns else 0
    meds_sem_marco = len(meds[meds["marco_id"].isna()]) if not meds.empty and "marco_id" in meds.columns else 0
    sintomas_sem_marco = len(sintomas[sintomas["marco_id"].isna()]) if not sintomas.empty and "marco_id" in sintomas.columns else 0

    return {
        "documentos": len(docs),
        "exames": len(exames),
        "medicamentos": len(meds),
        "sintomas": len(sintomas),
        "docs_sem_marco": docs_sem_marco,
        "exames_sem_marco": exames_sem_marco,
        "meds_sem_marco": meds_sem_marco,
        "sintomas_sem_marco": sintomas_sem_marco,
    }
