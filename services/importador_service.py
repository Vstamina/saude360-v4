import re
from datetime import date

import pandas as pd


def limpar_texto(texto):
    if texto is None:
        return ""
    texto = str(texto)
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    return texto.strip()


def extrair_texto_arquivo(arquivo):
    """
    V4.1:
    - TXT: le diretamente.
    - PDF textual: tenta ler com pypdf.
    - Imagem/foto: ainda nao faz OCR local. O arquivo fica salvo no repositorio,
      e o usuario pode colar o texto para importacao assistida.
    """
    if arquivo is None:
        return "", "Nenhum arquivo enviado."

    nome = arquivo.name.lower()

    if nome.endswith(".txt"):
        try:
            return arquivo.getvalue().decode("utf-8", errors="ignore"), "TXT lido com sucesso."
        except Exception:
            return arquivo.getvalue().decode("latin-1", errors="ignore"), "TXT lido com fallback latin-1."

    if nome.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(arquivo)
            partes = []
            for page in reader.pages:
                partes.append(page.extract_text() or "")
            texto = "\n".join(partes).strip()
            if texto:
                return texto, "PDF textual lido com sucesso."
            return "", "O PDF foi aberto, mas nao tinha texto extraivel. Pode ser imagem escaneada."
        except Exception as e:
            return "", f"Nao consegui ler o PDF automaticamente: {e}"

    return "", "Imagem/foto recebida. Nesta V4.1, salve o documento e cole o texto para importar."


def detectar_data_texto(texto):
    texto = texto or ""
    padroes = [r"(\d{2}/\d{2}/\d{4})", r"(\d{2}-\d{2}-\d{4})"]
    for p in padroes:
        m = re.search(p, texto)
        if m:
            val = m.group(1).replace("-", "/")
            try:
                from datetime import datetime
                return datetime.strptime(val, "%d/%m/%Y").date()
            except Exception:
                pass
    return date.today()


def normalizar_numero(txt):
    if txt is None:
        return None
    txt = str(txt).strip()
    txt = re.sub(r"[^0-9,.\-]", "", txt)

    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")

    try:
        return float(txt)
    except Exception:
        return None


def extrair_exames_de_texto(texto):
    """
    Parser assistido para exames laboratoriais.
    Funciona melhor com linhas tipo:
    Ferritina 32,20 ng/mL 30 a 300
    Glicose: 98 mg/dL Ref 70 - 99
    TGP 42 U/L ate 50
    Vitamina D 21 ng/mL 30 a 100
    """
    texto = limpar_texto(texto)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]

    unidades = r"(mg/dL|ng/mL|pg/mL|U/L|UI/L|uUI/mL|µUI/mL|mUI/L|g/dL|mmol/L|%|mil/mm3|10\^3/uL|10\^6/uL)"
    resultados = []

    ignorar = [
        "material", "coleta", "liberado", "metodo", "laboratorio", "paciente",
        "resultado", "referencia", "unidade", "pedido", "medico", "convênio",
    ]

    for linha in linhas:
        linha_original = linha
        linha_lower = linha.lower()

        if len(linha) < 5:
            continue

        if any(x in linha_lower for x in ignorar) and not re.search(r"\d", linha):
            continue

        padrao = re.compile(
            rf"^([A-Za-zÀ-ÿ0-9 \-/()]+?)[:\s]+([<>]?\s*\d+[.,]?\d*)\s*{unidades}?\s*(?:ref(?:er[eê]ncia)?\.?:?)?\s*([<>]?\s*\d+[.,]?\d*)?\s*(?:a|-|até|ate)?\s*([<>]?\s*\d+[.,]?\d*)?",
            re.IGNORECASE,
        )

        m = padrao.search(linha)
        if not m:
            continue

        nome = (m.group(1) or "").strip(" :-")
        resultado = normalizar_numero(m.group(2))
        unidade = (m.group(3) or "").strip()
        ref1 = normalizar_numero(m.group(4))
        ref2 = normalizar_numero(m.group(5))

        if not nome or resultado is None:
            continue

        if len(nome) > 60:
            continue

        ref_min = 0
        ref_max = 0

        if ref1 is not None and ref2 is not None:
            ref_min = min(ref1, ref2)
            ref_max = max(ref1, ref2)
        elif ref1 is not None and ("até" in linha_lower or "ate" in linha_lower or "<" in linha_lower):
            ref_min = 0
            ref_max = ref1
        elif ref1 is not None:
            ref_min = 0
            ref_max = ref1

        resultados.append({
            "importar": True,
            "nome_exame": nome,
            "resultado": resultado,
            "unidade": unidade,
            "referencia_min": ref_min,
            "referencia_max": ref_max,
            "observacao": f"Importado de texto: {linha_original[:160]}",
        })

    vistos = set()
    unicos = []
    for item in resultados:
        chave = (item["nome_exame"].lower(), item["resultado"], item["unidade"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)

    return pd.DataFrame(unicos)


def sugerir_medicamento_de_texto(texto):
    """
    Parser simples para receita. A ideia da V4.1 e sugerir, nao salvar sozinho.
    """
    texto = limpar_texto(texto)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    texto_lower = texto.lower()

    nome = ""
    dose = ""
    frequencia_modelo = "1 vez ao dia"
    intervalo_horas = None
    duracao = "Personalizado"
    dias = 7

    m = re.search(r"a cada\s+(\d{1,2})\s*h", texto_lower)
    if not m:
        m = re.search(r"de\s+(\d{1,2})\s*/\s*(\d{1,2})\s*h", texto_lower)
    if m:
        frequencia_modelo = "A cada X horas"
        intervalo_horas = int(m.group(1))

    if "2 vezes ao dia" in texto_lower or "duas vezes ao dia" in texto_lower:
        frequencia_modelo = "2 vezes ao dia"
    elif "3 vezes ao dia" in texto_lower or "tres vezes ao dia" in texto_lower or "três vezes ao dia" in texto_lower:
        frequencia_modelo = "3 vezes ao dia"
    elif "4 vezes ao dia" in texto_lower or "quatro vezes ao dia" in texto_lower:
        frequencia_modelo = "4 vezes ao dia"
    elif "1 vez ao dia" in texto_lower or "uma vez ao dia" in texto_lower:
        frequencia_modelo = "1 vez ao dia"

    m_dias = re.search(r"por\s+(\d{1,3})\s+dias", texto_lower)
    if m_dias:
        dias = int(m_dias.group(1))
        if dias == 7:
            duracao = "7 dias"
        elif dias == 14:
            duracao = "14 dias"
        elif dias == 30:
            duracao = "30 dias"
        else:
            duracao = "Personalizado"

    if "uso continuo" in texto_lower or "uso contínuo" in texto_lower:
        duracao = "Uso continuo"

    candidatos = []
    for linha in linhas:
        ll = linha.lower()
        if any(x in ll for x in ["paciente", "medico", "médico", "crm", "data", "receita", "assinatura"]):
            continue
        if re.search(r"\d+\s*(mg|mcg|g|ml|ui|comprimido|capsula|cápsula|gotas)", ll):
            candidatos.append(linha)

    if candidatos:
        primeira = candidatos[0]
        nome = re.split(r"\d+\s*(mg|mcg|g|ml|ui)", primeira, flags=re.IGNORECASE)[0].strip(" -:")
        dose_match = re.search(r"(\d+[.,]?\d*\s*(mg|mcg|g|ml|ui)|\d+\s*(comprimido|comprimidos|capsula|cápsula|capsulas|cápsulas|gotas))", primeira, re.IGNORECASE)
        if dose_match:
            dose = dose_match.group(0)

    if not nome and linhas:
        nome = linhas[0][:60]

    return {
        "nome": nome,
        "dose": dose,
        "frequencia_modelo": frequencia_modelo,
        "intervalo_horas": intervalo_horas,
        "duracao": duracao,
        "dias_personalizados": dias,
        "orientacao": texto[:1000],
    }
