from core.database import consultar_df, executar
from core.helpers import agora


def listar_usuarios():
    return consultar_df("SELECT * FROM usuarios ORDER BY nome")


def salvar_usuario(nome, data_nascimento, sexo, altura_cm, objetivo):
    return executar(
        """
        INSERT INTO usuarios (nome, data_nascimento, sexo, altura_cm, objetivo, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (nome, data_nascimento.isoformat(), sexo, altura_cm, objetivo, agora()),
    )
