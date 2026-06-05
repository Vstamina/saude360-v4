from datetime import date, timedelta

from core.database import consultar_df, executar
from core.helpers import agora


def salvar_atividade(usuario_id, data_atividade, tipo, duracao, calorias,
                     passos, frequencia_media, origem, observacao):
    return executar(
        """
        INSERT INTO atividades (
            usuario_id, data_atividade, tipo, duracao_min, calorias,
            passos, frequencia_media, origem, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_atividade.isoformat(),
            tipo,
            duracao,
            calorias,
            passos,
            frequencia_media,
            origem,
            observacao,
            agora(),
        ),
    )


def listar_atividades(usuario_id):
    return consultar_df(
        "SELECT * FROM atividades WHERE usuario_id = ? ORDER BY data_atividade DESC",
        (usuario_id,),
    )


def atividades_ultimos_7_dias(usuario_id):
    data_min = (date.today() - timedelta(days=7)).isoformat()
    return consultar_df(
        """
        SELECT *
        FROM atividades
        WHERE usuario_id = ?
          AND data_atividade >= ?
        ORDER BY data_atividade DESC
        """,
        (usuario_id, data_min),
    )
