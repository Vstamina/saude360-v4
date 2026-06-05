from datetime import datetime, date
import pandas as pd
import streamlit as st


def agora():
    return datetime.now().isoformat(timespec="seconds")


def hoje_iso():
    return date.today().isoformat()


def br_date(valor):
    if valor is None or str(valor).strip() == "":
        return ""
    try:
        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")
        return pd.to_datetime(valor).strftime("%d/%m/%Y")
    except Exception:
        return str(valor)


def br_datetime(valor):
    if valor is None or str(valor).strip() == "":
        return ""
    try:
        return pd.to_datetime(valor).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def parse_data_br(txt, campo="data"):
    txt = str(txt).strip()
    try:
        return datetime.strptime(txt, "%d/%m/%Y").date()
    except Exception:
        st.error(f"Formato invalido em {campo}. Use dd/mm/aaaa.")
        st.stop()


def data_input_br(label, valor=None, key=None, help_text=None):
    if valor is None:
        valor = date.today()
    default = valor.strftime("%d/%m/%Y")
    txt = st.text_input(label, value=default, key=key, help=help_text)
    return parse_data_br(txt, label)


def recarregar():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def to_float(valor):
    try:
        if valor is None or str(valor).strip() == "":
            return None
        if isinstance(valor, str):
            valor = valor.replace(".", "").replace(",", ".")
        return float(valor)
    except Exception:
        return None


def fmt_num(valor, casas=2):
    try:
        if valor is None or pd.isna(valor):
            return ""
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor)
