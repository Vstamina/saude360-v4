from datetime import date
import re
import pandas as pd

from core.helpers import agora
from core.database import executar
from services.documentos_service import validar_paciente_documento


def limpar_texto(texto):
    texto = str(texto or "")
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_texto_arquivo_inteligente(arquivo):
    """
    Tenta ler PDF textual/TXT. Para imagem, tenta OCR se pytesseract estiver instalado.
    Se não conseguir OCR, devolve aviso para o usuário colar/revisar manualmente.
    """
    if arquivo is None:
        return "", "Nenhum arquivo enviado."

    nome = arquivo.name.lower()

    try:
        if nome.endswith(".txt"):
            conteudo = arquivo.getvalue()
            try:
                return conteudo.decode("utf-8"), "TXT lido com sucesso."
            except Exception:
                return conteudo.decode("latin-1", errors="ignore"), "TXT lido com ajuste de codificação."

        if nome.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(arquivo)
                partes = []
                for page in reader.pages:
                    partes.append(page.extract_text() or "")
                texto = "\n".join(partes).strip()
                if texto:
                    return texto, "PDF textual lido com sucesso."
                return "", "PDF não trouxe texto extraível. Se for escaneado, use OCR ou cole o texto revisado."
            except Exception as e:
                return "", f"Não consegui ler o PDF automaticamente: {e}"

        if nome.endswith((".png", ".jpg", ".jpeg", ".webp")):
            try:
                from PIL import Image, ImageOps, ImageEnhance
                import pytesseract

                img = Image.open(arquivo).convert("RGB")

                # Pré-processamento leve para tentar melhorar foto de receita.
                # Não resolve letra médica ruim, mas ajuda em documentos impressos e contraste baixo.
                gray = ImageOps.grayscale(img)
                gray = ImageEnhance.Contrast(gray).enhance(1.8)
                gray = ImageEnhance.Sharpness(gray).enhance(1.4)

                try:
                    texto = pytesseract.image_to_string(gray, lang="por")
                except Exception:
                    texto = pytesseract.image_to_string(gray)

                if texto.strip():
                    return texto, "Imagem lida por OCR. Revise porque letra manuscrita pode gerar erros."
                return "", "OCR não conseguiu extrair texto. Cole o texto revisado manualmente."
            except Exception:
                return "", (
                    "Imagem recebida, mas OCR local não está configurado ou não conseguiu ler. "
                    "Use a confirmação manual do paciente e cole o texto revisado se necessário."
                )

    except Exception as e:
        return "", f"Erro ao ler arquivo: {e}"

    return "", "Tipo de arquivo não tratado."


def detectar_tipo_documento(texto):
    t = limpar_texto(texto).lower()

    if "receituário" in t or "receituario" in t or "tomar" in t or "aplicar" in t or "uso oral" in t or "uso sc" in t:
        return "Receita medica"

    if "resultado" in t or "referência" in t or "referencia" in t or "laboratório" in t or "laboratorio" in t:
        return "Exame"

    return "Documento de saúde"


def detectar_profissional(texto):
    texto = limpar_texto(texto)
    m = re.search(r"(dr\.?|dra\.?|m[eé]dica|m[eé]dico)\s*([A-Za-zÀ-ÿ ]{3,80})", texto, flags=re.IGNORECASE)
    if m:
        return (m.group(0) or "").strip()[:90]

    m = re.search(r"CRM\s*[A-Z]{0,2}\s*\d{3,8}", texto, flags=re.IGNORECASE)
    if m:
        trecho = texto[max(0, m.start() - 60):m.end() + 20]
        return trecho.strip()[:120]

    return ""


def detectar_medicamentos(texto):
    """
    Heurística simples para receitas. O usuário sempre revisa.
    Retorna DataFrame editável.
    """
    texto = limpar_texto(texto)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatos = []

    padrao_dose = r"(\d+[,.]?\d*\s*(mg|mcg|g|ml|gotas?|comprimidos?|cápsulas?|capsulas?|cliques?))"

    for linha in linhas:
        low = linha.lower()
        if not any(x in low for x in ["mg", "mcg", "comprim", "cáps", "caps", "gotas", "cliques", "tomar", "aplicar", "uso "]):
            continue

        dose = ""
        m_dose = re.search(padrao_dose, linha, flags=re.IGNORECASE)
        if m_dose:
            dose = m_dose.group(1)

        freq = "1 vez ao dia"
        intervalo = None
        duracao = "Personalizado"
        dias = 30
        horario = "08:00"

        if re.search(r"1\s*x\s*/\s*sem|1x\s*sem|seman", low):
            freq = "Semanal"
            duracao = "Uso continuo"
            horario = "09:00"
        elif re.search(r"2\s*x\s*/\s*dia|2x\s*dia|12/12|a cada 12", low):
            freq = "2 vezes ao dia"
        elif re.search(r"3\s*x\s*/\s*dia|3x\s*dia|8/8|a cada 8", low):
            freq = "A cada X horas"
            intervalo = 8
        elif re.search(r"6/6|a cada 6", low):
            freq = "A cada X horas"
            intervalo = 6
        elif re.search(r"24/24|1\s*x\s*/\s*dia|1x\s*dia|uma vez ao dia", low):
            freq = "1 vez ao dia"

        m_dias = re.search(r"(\d+)\s*dias", low)
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

        nome = linha
        if m_dose:
            nome = linha[:m_dose.start()].strip(" .:-_0123456789")
        nome = re.sub(r"^(uso|uso oral|uso sc|uso tópico|uso topico)\s*[:\-]?", "", nome, flags=re.IGNORECASE).strip()
        nome = nome[:60] if nome else linha[:60]

        confianca = "Média"
        if not dose or len(nome) < 3:
            confianca = "Baixa"

        candidatos.append({
            "importar": True,
            "nome": nome,
            "dose": dose,
            "frequencia_modelo": freq,
            "intervalo_horas": intervalo,
            "horario_inicial": horario,
            "duracao": duracao,
            "dias_personalizados": dias,
            "orientacao": linha,
            "confianca": confianca,
        })

    if not candidatos:
        return pd.DataFrame(columns=[
            "importar", "nome", "dose", "frequencia_modelo", "intervalo_horas",
            "horario_inicial", "duracao", "dias_personalizados", "orientacao", "confianca"
        ])

    df = pd.DataFrame(candidatos)
    df = df.drop_duplicates(subset=["nome", "dose", "orientacao"])
    return df


def detectar_exames(texto):
    texto = limpar_texto(texto)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    candidatos = []

    for linha in linhas:
        m = re.search(
            r"([A-Za-zÀ-ÿ0-9 \-/().%]{3,45})\s+(-?\d+[,.]?\d*)\s*([A-Za-z/%µμ\.]+)?\s*(?:ref\.?|refer[eê]ncia|VR|valor de refer[eê]ncia)?\s*[:\-]?\s*(-?\d+[,.]?\d*)?\s*(?:a|-|até|ate)?\s*(-?\d+[,.]?\d*)?",
            linha,
            flags=re.IGNORECASE
        )
        if not m:
            continue

        nome = m.group(1).strip(" :-")
        resultado = (m.group(2) or "").replace(",", ".")
        unidade = m.group(3) or ""
        ref_min = (m.group(4) or "0").replace(",", ".")
        ref_max = (m.group(5) or "0").replace(",", ".")

        if len(nome) < 3:
            continue

        try:
            resultado_f = float(resultado)
            ref_min_f = float(ref_min)
            ref_max_f = float(ref_max)
        except Exception:
            continue

        candidatos.append({
            "importar": True,
            "nome_exame": nome[:60],
            "resultado": resultado_f,
            "unidade": unidade,
            "referencia_min": ref_min_f,
            "referencia_max": ref_max_f,
            "observacao": linha,
            "confianca": "Média" if ref_min_f or ref_max_f else "Baixa",
        })

    return pd.DataFrame(candidatos)


def gerar_plano_uso_medicamentos(df_meds):
    if df_meds is None or df_meds.empty:
        return pd.DataFrame(columns=["medicamento", "horario_sugerido", "acao", "observacao"])

    linhas = []

    for _, r in df_meds.iterrows():
        nome = r.get("nome", "")
        dose = r.get("dose", "")
        freq = r.get("frequencia_modelo", "1 vez ao dia")
        horario = r.get("horario_inicial", "08:00")

        if freq == "2 vezes ao dia":
            horarios = [horario, "20:00"]
        elif freq == "A cada X horas" and int(r.get("intervalo_horas") or 8) == 8:
            horarios = ["08:00", "16:00", "00:00"]
        elif freq == "A cada X horas" and int(r.get("intervalo_horas") or 6) == 6:
            horarios = ["06:00", "12:00", "18:00", "00:00"]
        elif freq == "Semanal":
            horarios = [horario + " - 1x por semana"]
        else:
            horarios = [horario]

        for h in horarios:
            linhas.append({
                "medicamento": nome,
                "horario_sugerido": h,
                "acao": f"{dose}".strip(),
                "observacao": r.get("orientacao", ""),
            })

    return pd.DataFrame(linhas)


def salvar_importacao_assistida(usuario_id, tipo_documento, titulo, paciente_detectado,
                                validacao_paciente, texto_extraido, documento_id=None, status="Confirmada"):
    return executar(
        """
        INSERT INTO importacoes_assistidas (
            usuario_id, data_importacao, tipo_documento, titulo, paciente_detectado,
            validacao_paciente, texto_extraido, status, documento_id, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            date.today().isoformat(),
            tipo_documento,
            titulo,
            paciente_detectado,
            validacao_paciente,
            texto_extraido,
            status,
            documento_id,
            agora(),
        )
    )


def analisar_documento_saude(usuario_id, arquivo, texto_manual):
    texto_auto, status_leitura = extrair_texto_arquivo_inteligente(arquivo) if arquivo else ("", "Nenhum arquivo enviado.")
    texto = limpar_texto(texto_manual if str(texto_manual or "").strip() else texto_auto)

    paciente_detectado, validacao = validar_paciente_documento(usuario_id, texto)
    tipo_doc = detectar_tipo_documento(texto)
    profissional = detectar_profissional(texto)
    meds = detectar_medicamentos(texto)
    exames = detectar_exames(texto)
    plano = gerar_plano_uso_medicamentos(meds)

    return {
        "texto": texto,
        "status_leitura": status_leitura,
        "paciente_detectado": paciente_detectado,
        "validacao_paciente": validacao,
        "tipo_documento": tipo_doc,
        "profissional": profissional,
        "medicamentos": meds,
        "exames": exames,
        "plano_uso": plano,
    }
