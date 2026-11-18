import io
import hashlib
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher

import pandas as pd
import pdfplumber
import streamlit as st
import requests
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from conexao_supabase import testar_conexao
from gerenciador_tabelas import testar_gerenciador
from leitor_excel_icismep import ler_excel_icismep

# ============================================================
# CONFIGURAÇÃO
# ============================================================
NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"
VERSAO = "3.20"
PARSER_VERSION = "3.20-ignora-linhas-totalizadoras"
URL_ICISMEP = "https://icismep.mg.gov.br/tabela-de-servicos-medicos-nos-municipios-entes-nao-consorciados/"

st.set_page_config(page_title=NOME_SISTEMA, page_icon="📊", layout="wide")

# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================
def normalizar_texto(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def converter_numero(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except Exception:
        return 0.0


def formatar_moeda(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    texto = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_numero(valor, casas=0):
    return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def normalizar_codigo(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return str(int(valor))
    texto = str(valor).strip().upper().replace(" ", "")
    if re.fullmatch(r"\d+[\.,]0", texto):
        texto = texto[:-2]
    return texto


def competencia_valida(texto):
    return bool(re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", str(texto).strip()))


def competencias_do_periodo(data_inicial, data_final):
    inicio = pd.Period(data_inicial, freq="M")
    fim = pd.Period(data_final, freq="M")
    return [p.strftime("%m/%Y") for p in pd.period_range(inicio, fim, freq="M")]


def proximo(a, b, tolerancia=0.02):
    return abs(float(a) - float(b)) <= tolerancia


# ============================================================
# IDENTIFICAÇÃO DO USUÁRIO E PERFIS DE ACESSO
# ============================================================
def usuarios_configurados():
    try:
