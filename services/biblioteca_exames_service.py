import unicodedata
import pandas as pd

from core.database import consultar_df, executar


CATALOGO_EXAMES = [
    {
        "nome_padronizado": "Ferritina",
        "categoria": "Ferro e vitaminas",
        "aliases": ["ferritina", "ferritina serica", "ferritina sérica", "ferritina - soro"],
        "unidades_comuns": "ng/mL",
        "o_que_observar": "Ajuda a acompanhar estoques de ferro. Deve ser interpretada com contexto clínico e outros exames.",
        "perguntas": "Minha ferritina está coerente com meus sintomas e demais exames? Preciso repetir ou investigar causas?"
    },
    {
        "nome_padronizado": "Vitamina D",
        "categoria": "Ferro e vitaminas",
        "aliases": ["vitamina d", "25 oh vitamina d", "25-oh vitamina d", "25 hidroxivitamina d", "25-hidroxivitamina d"],
        "unidades_comuns": "ng/mL",
        "o_que_observar": "Acompanha níveis de vitamina D. Referências variam por laboratório e condição clínica.",
        "perguntas": "O resultado exige acompanhamento, suplementação ou repetição futura?"
    },
    {
        "nome_padronizado": "Vitamina B12",
        "categoria": "Ferro e vitaminas",
        "aliases": ["b12", "vitamina b12", "cobalamina", "vit b12"],
        "unidades_comuns": "pg/mL",
        "o_que_observar": "Útil em sintomas neurológicos, anemia e acompanhamento nutricional.",
        "perguntas": "O nível está adequado para meu contexto clínico e sintomas?"
    },
    {
        "nome_padronizado": "Glicose",
        "categoria": "Metabolismo glicêmico",
        "aliases": ["glicose", "glicemia", "glicemia de jejum", "glucose"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Ajuda a acompanhar metabolismo glicêmico, especialmente junto de insulina e hemoglobina glicada.",
        "perguntas": "O resultado é compatível com jejum, alimentação, peso e demais marcadores?"
    },
    {
        "nome_padronizado": "Insulina",
        "categoria": "Metabolismo glicêmico",
        "aliases": ["insulina", "insulina basal", "insulina de jejum"],
        "unidades_comuns": "uUI/mL",
        "o_que_observar": "Pode ajudar a discutir resistência à insulina quando combinada a outros marcadores.",
        "perguntas": "Como interpretar este resultado junto da glicose, peso, circunferência abdominal e sintomas?"
    },
    {
        "nome_padronizado": "Hemoglobina glicada",
        "categoria": "Metabolismo glicêmico",
        "aliases": ["hemoglobina glicada", "hba1c", "hb a1c", "a1c", "hemoglobina glicosilada"],
        "unidades_comuns": "%",
        "o_que_observar": "Mostra tendência glicêmica de médio prazo. Deve ser interpretada pelo profissional.",
        "perguntas": "O resultado mudou em relação aos anteriores? Qual meta é adequada para mim?"
    },
    {
        "nome_padronizado": "Colesterol total",
        "categoria": "Perfil lipídico",
        "aliases": ["colesterol total", "colesterol"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Parte do perfil lipídico. Deve ser visto junto de HDL, LDL, triglicerídeos e risco global.",
        "perguntas": "Como este resultado se encaixa no meu risco cardiovascular?"
    },
    {
        "nome_padronizado": "HDL",
        "categoria": "Perfil lipídico",
        "aliases": ["hdl", "colesterol hdl", "hdl colesterol"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Fração do colesterol associada ao perfil lipídico.",
        "perguntas": "Meu HDL deve ser interpretado junto de quais outros fatores?"
    },
    {
        "nome_padronizado": "LDL",
        "categoria": "Perfil lipídico",
        "aliases": ["ldl", "colesterol ldl", "ldl colesterol"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Fração importante para avaliação de risco cardiovascular.",
        "perguntas": "Qual meta de LDL faz sentido para meu perfil?"
    },
    {
        "nome_padronizado": "Triglicerídeos",
        "categoria": "Perfil lipídico",
        "aliases": ["triglicerideos", "triglicerídeos", "tg"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Pode variar com alimentação, peso, álcool, metabolismo e medicamentos.",
        "perguntas": "O resultado exige ajuste alimentar, repetição ou investigação?"
    },
    {
        "nome_padronizado": "TGO/AST",
        "categoria": "Fígado",
        "aliases": ["tgo", "ast", "aspartato aminotransferase", "transaminase oxalacetica", "transaminase oxalacética"],
        "unidades_comuns": "U/L",
        "o_que_observar": "Marcador hepático/muscular. Deve ser interpretado com TGP/ALT, GGT e contexto clínico.",
        "perguntas": "Pode ter relação com medicamento, treino, álcool, fígado gorduroso ou outro fator?"
    },
    {
        "nome_padronizado": "TGP/ALT",
        "categoria": "Fígado",
        "aliases": ["tgp", "alt", "alanina aminotransferase", "transaminase piruvica", "transaminase pirúvica"],
        "unidades_comuns": "U/L",
        "o_que_observar": "Marcador hepático relevante, geralmente avaliado com outros exames.",
        "perguntas": "O resultado exige acompanhamento, repetição ou ajuste de medicação?"
    },
    {
        "nome_padronizado": "GGT",
        "categoria": "Fígado",
        "aliases": ["ggt", "gama gt", "gama glutamil transferase", "gama-glutamiltransferase"],
        "unidades_comuns": "U/L",
        "o_que_observar": "Pode compor investigação hepática/biliar e deve ser interpretado no conjunto.",
        "perguntas": "Como interpretar o GGT junto dos demais marcadores hepáticos?"
    },
    {
        "nome_padronizado": "Creatinina",
        "categoria": "Rim",
        "aliases": ["creatinina", "creatinine"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Usada para acompanhar função renal junto de taxa de filtração e outros dados.",
        "perguntas": "Minha função renal está adequada para meu contexto e medicamentos em uso?"
    },
    {
        "nome_padronizado": "Ureia",
        "categoria": "Rim",
        "aliases": ["ureia", "uréia", "urea"],
        "unidades_comuns": "mg/dL",
        "o_que_observar": "Pode variar por hidratação, dieta, rim e contexto clínico.",
        "perguntas": "O resultado deve ser interpretado junto de creatinina e hidratação?"
    },
    {
        "nome_padronizado": "TSH",
        "categoria": "Tireoide",
        "aliases": ["tsh", "hormonio tireoestimulante", "hormônio tireoestimulante"],
        "unidades_comuns": "uUI/mL",
        "o_que_observar": "Marcador central no acompanhamento tireoidiano, interpretado com T4 livre e sintomas.",
        "perguntas": "O resultado explica sintomas ou exige avaliar T4 livre/anticorpos?"
    },
    {
        "nome_padronizado": "T4 livre",
        "categoria": "Tireoide",
        "aliases": ["t4 livre", "tiroxina livre", "ft4"],
        "unidades_comuns": "ng/dL",
        "o_que_observar": "Complementa avaliação da tireoide junto de TSH.",
        "perguntas": "Como interpretar este T4 livre junto do TSH?"
    },
    {
        "nome_padronizado": "Hemoglobina",
        "categoria": "Hemograma",
        "aliases": ["hemoglobina", "hb"],
        "unidades_comuns": "g/dL",
        "o_que_observar": "Parte do hemograma, útil em avaliação de anemia e outros quadros.",
        "perguntas": "Há sinais de anemia ou necessidade de investigar ferro/B12/folato?"
    },
]


def normalizar_texto(txt):
    txt = str(txt or "").strip().lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    txt = txt.replace("-", " ").replace("_", " ").replace("/", " ")
    txt = " ".join(txt.split())
    return txt


def catalogo_df():
    return pd.DataFrame(CATALOGO_EXAMES)


def sugerir_padronizacao(nome_exame):
    n = normalizar_texto(nome_exame)

    if not n:
        return {
            "nome_padronizado": "",
            "categoria": "Não classificado",
            "confianca": "Baixa",
            "observacao": "Nome vazio ou inválido.",
        }

    # Match exato por alias
    for item in CATALOGO_EXAMES:
        aliases = [normalizar_texto(a) for a in item["aliases"]]
        if n in aliases or n == normalizar_texto(item["nome_padronizado"]):
            return {
                "nome_padronizado": item["nome_padronizado"],
                "categoria": item["categoria"],
                "confianca": "Alta",
                "observacao": "Correspondência direta na biblioteca.",
            }

    # Match parcial controlado
    for item in CATALOGO_EXAMES:
        aliases = [normalizar_texto(a) for a in item["aliases"]]
        for a in aliases:
            if len(a) >= 3 and (a in n or n in a):
                return {
                    "nome_padronizado": item["nome_padronizado"],
                    "categoria": item["categoria"],
                    "confianca": "Média",
                    "observacao": f"Correspondência aproximada com '{a}'. Conferir.",
                }

    return {
        "nome_padronizado": str(nome_exame).strip(),
        "categoria": "Não classificado",
        "confianca": "Baixa",
        "observacao": "Não encontrado na biblioteca. Manter nome original ou padronizar manualmente.",
    }


def exames_para_padronizar(usuario_id):
    df = consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
        ORDER BY data_exame DESC, nome_exame
        """,
        (usuario_id,),
    )

    if df.empty:
        return df

    linhas = []
    for _, r in df.iterrows():
        sugestao = sugerir_padronizacao(r.get("nome_exame"))
        linhas.append({
            "id": int(r["id"]),
            "data_exame": r.get("data_exame"),
            "nome_exame": r.get("nome_exame"),
            "resultado": r.get("resultado"),
            "unidade": r.get("unidade"),
            "referencia_min": r.get("referencia_min"),
            "referencia_max": r.get("referencia_max"),
            "nome_padronizado_atual": r.get("nome_padronizado") or "",
            "categoria_atual": r.get("categoria_exame") or "",
            "nome_padronizado_sugerido": sugestao["nome_padronizado"],
            "categoria_sugerida": sugestao["categoria"],
            "confianca": sugestao["confianca"],
            "observacao_padronizacao": sugestao["observacao"],
            "aplicar": not bool(r.get("nome_padronizado")),
        })

    return pd.DataFrame(linhas)


def aplicar_padronizacao_exame(usuario_id, exame_id, nome_padronizado, categoria, observacao=""):
    executar(
        """
        UPDATE exames
        SET nome_padronizado = ?,
            categoria_exame = ?,
            observacao_padronizacao = ?
        WHERE usuario_id = ?
          AND id = ?
        """,
        (nome_padronizado, categoria, observacao, usuario_id, exame_id),
    )


def aplicar_padronizacao_lote(usuario_id, df_editado):
    total = 0
    if df_editado is None or df_editado.empty:
        return total

    for _, r in df_editado.iterrows():
        aplicar = bool(r.get("aplicar"))
        if not aplicar:
            continue

        exame_id = int(r.get("id"))
        nome_pad = str(r.get("nome_padronizado_sugerido") or r.get("nome_exame") or "").strip()
        categoria = str(r.get("categoria_sugerida") or "Não classificado").strip()
        obs = str(r.get("observacao_padronizacao") or "").strip()

        aplicar_padronizacao_exame(usuario_id, exame_id, nome_pad, categoria, obs)
        total += 1

    return total


def trilhas_por_exame_padronizado(usuario_id):
    df = consultar_df(
        """
        SELECT
            COALESCE(NULLIF(nome_padronizado, ''), nome_exame) AS exame,
            COALESCE(NULLIF(categoria_exame, ''), 'Não classificado') AS categoria,
            COUNT(*) AS registros,
            MIN(data_exame) AS primeira_data,
            MAX(data_exame) AS ultima_data
        FROM exames
        WHERE usuario_id = ?
        GROUP BY COALESCE(NULLIF(nome_padronizado, ''), nome_exame),
                 COALESCE(NULLIF(categoria_exame, ''), 'Não classificado')
        ORDER BY registros DESC, ultima_data DESC
        """,
        (usuario_id,),
    )
    return df


def detalhes_trilha(usuario_id, exame_nome):
    return consultar_df(
        """
        SELECT *
        FROM exames
        WHERE usuario_id = ?
          AND COALESCE(NULLIF(nome_padronizado, ''), nome_exame) = ?
        ORDER BY data_exame ASC, id ASC
        """,
        (usuario_id, exame_nome),
    )


def info_catalogo(nome_padronizado):
    n = normalizar_texto(nome_padronizado)
    for item in CATALOGO_EXAMES:
        if n == normalizar_texto(item["nome_padronizado"]):
            return item
    return {
        "nome_padronizado": nome_padronizado,
        "categoria": "Não classificado",
        "aliases": [],
        "unidades_comuns": "",
        "o_que_observar": "Exame ainda não descrito na biblioteca.",
        "perguntas": "Pergunte ao profissional como interpretar este exame no seu contexto."
    }


def resumo_biblioteca(usuario_id):
    df = exames_para_padronizar(usuario_id)

    if df.empty:
        return {
            "total": 0,
            "sem_padronizar": 0,
            "baixa_confianca": 0,
            "categorias": 0,
            "leitura": "Nenhum exame cadastrado ainda."
        }

    sem = int((df["nome_padronizado_atual"] == "").sum())
    baixa = int((df["confianca"] == "Baixa").sum())
    trilhas = trilhas_por_exame_padronizado(usuario_id)
    categorias = int(trilhas["categoria"].nunique()) if not trilhas.empty else 0

    if sem > 0:
        leitura = f"Há {sem} exame(s) sem padronização. Padronizar melhora as trilhas e leituras."
    elif baixa > 0:
        leitura = f"Há {baixa} exame(s) com baixa confiança de biblioteca. Revise manualmente se necessário."
    else:
        leitura = "Os exames estão bem padronizados para análise longitudinal."

    return {
        "total": len(df),
        "sem_padronizar": sem,
        "baixa_confianca": baixa,
        "categorias": categorias,
        "leitura": leitura,
    }
