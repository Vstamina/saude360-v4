import pandas as pd

from core.database import consultar_df, executar
from core.helpers import agora
from components.gauges import classificar_exame


def salvar_exame(usuario_id, data_exame, nome_exame, resultado, unidade,
                 referencia_min, referencia_max, laboratorio, observacao, marco_id=None):
    return executar(
        """
        INSERT INTO exames (
            usuario_id, data_exame, nome_exame, resultado, unidade,
            referencia_min, referencia_max, laboratorio, observacao, marco_id, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data_exame.isoformat(),
            nome_exame.strip(),
            resultado,
            unidade.strip(),
            referencia_min,
            referencia_max,
            laboratorio,
            observacao,
            marco_id,
            agora(),
        ),
    )


def listar_exames(usuario_id):
    return consultar_df(
        """
        SELECT e.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM exames e
        LEFT JOIN marcos_jornada m ON m.id = e.marco_id
        WHERE e.usuario_id = ?
        ORDER BY e.data_exame DESC, e.nome_exame
        """,
        (usuario_id,),
    )


def exames_mais_recentes(usuario_id):
    exames = listar_exames(usuario_id)

    if exames.empty:
        return exames

    exames["data_exame_sort"] = pd.to_datetime(exames["data_exame"], errors="coerce")
    recentes = (
        exames.sort_values("data_exame_sort")
        .groupby("nome_exame", as_index=False)
        .tail(1)
        .sort_values("nome_exame")
    )
    return recentes


def contar_exames_alerta(df):
    if df.empty:
        return 0

    total = 0
    for _, r in df.iterrows():
        status, _, _ = classificar_exame(r["resultado"], r["referencia_min"], r["referencia_max"])
        if status in ["Abaixo da faixa", "Acima da faixa", "Na faixa, perto do minimo", "Na faixa, perto do maximo", "Abaixo", "Acima", "Limite inferior", "Limite superior"]:
            total += 1
    return total


def listar_nomes_exames(usuario_id):
    df = consultar_df(
        """
        SELECT DISTINCT nome_exame
        FROM exames
        WHERE usuario_id = ?
        ORDER BY nome_exame
        """,
        (usuario_id,),
    )
    return df["nome_exame"].tolist() if not df.empty else []


def trilha_exame(usuario_id, nome_exame):
    return consultar_df(
        """
        SELECT e.*, m.titulo AS marco_titulo, m.tipo_marco, m.data_marco
        FROM exames e
        LEFT JOIN marcos_jornada m ON m.id = e.marco_id
        WHERE e.usuario_id = ?
          AND e.nome_exame = ?
        ORDER BY e.data_exame ASC, e.id ASC
        """,
        (usuario_id, nome_exame),
    )


def gerar_leitura_trilha_exame(df, nome_exame):
    if df is None or df.empty:
        return f"Ainda nao ha registros para {nome_exame}."

    if len(df) == 1:
        r = df.iloc[0]
        status, _, leitura = classificar_exame(r["resultado"], r["referencia_min"], r["referencia_max"])
        return (
            f"Ha apenas um resultado cadastrado para {nome_exame}, em {pd.to_datetime(r['data_exame']).strftime('%d/%m/%Y')}. "
            f"O valor foi {r['resultado']} {r.get('unidade') or ''}, classificado como {status}. {leitura} "
            "Ainda nao ha comparacao temporal para esse marcador."
        )

    primeiro = df.iloc[0]
    ultimo = df.iloc[-1]

    try:
        variacao = float(ultimo["resultado"]) - float(primeiro["resultado"])
        sinal = "+" if variacao > 0 else ""
        variacao_txt = f"{sinal}{variacao:.2f}".replace(".", ",")
    except Exception:
        variacao_txt = "nao calculada"

    return (
        f"{nome_exame} possui {len(df)} registro(s) na trilha. "
        f"O primeiro resultado foi {primeiro['resultado']} {primeiro.get('unidade') or ''} em {pd.to_datetime(primeiro['data_exame']).strftime('%d/%m/%Y')}; "
        f"o mais recente foi {ultimo['resultado']} {ultimo.get('unidade') or ''} em {pd.to_datetime(ultimo['data_exame']).strftime('%d/%m/%Y')}. "
        f"A variacao absoluta no periodo foi {variacao_txt} {ultimo.get('unidade') or ''}. "
        "Essa leitura mostra tendencia numérica e deve ser interpretada junto ao motivo do exame, sintomas, medicamentos e marcos clínicos relacionados."
    )
