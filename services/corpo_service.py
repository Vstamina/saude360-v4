from datetime import date, timedelta

from core.database import consultar_df, executar
from core.helpers import agora


def salvar_bioimpedancia(usuario_id, data_medicao, peso, gordura, massa_magra,
                         massa_muscular, gordura_visceral, cintura, observacao):
    return executar(
        """
        INSERT INTO bioimpedancia (
            usuario_id, data_medicao, peso_kg, gordura_percentual,
            massa_magra_kg, massa_muscular_kg, gordura_visceral,
            cintura_cm, observacao, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_medicao.isoformat(),
            peso,
            gordura,
            massa_magra,
            massa_muscular,
            gordura_visceral,
            cintura,
            observacao,
            agora(),
        ),
    )


def ultima_bioimpedancia(usuario_id):
    return consultar_df(
        """
        SELECT *
        FROM bioimpedancia
        WHERE usuario_id = ?
        ORDER BY data_medicao DESC, id DESC
        LIMIT 1
        """,
        (usuario_id,),
    )


def listar_bioimpedancia(usuario_id):
    return consultar_df(
        "SELECT * FROM bioimpedancia WHERE usuario_id = ? ORDER BY data_medicao DESC",
        (usuario_id,),
    )
