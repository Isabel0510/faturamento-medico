"""Gerenciador de versões ICISMEP no Supabase.

Dependências: pandas, supabase-py e conexao_supabase.py.
A importação é feita em rascunho. Publicação exige conferência posterior.
"""
import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from conexao_supabase import conectar_supabase


def listar_versoes():
    cliente = conectar_supabase()
    resposta = (cliente.table("icismep_versoes").select("*")
                .eq("status", "publicada")
                .order("competencia_inicio", desc=True).execute())
    return pd.DataFrame(resposta.data or [])


def listar_servicos(versao_id):
    cliente = conectar_supabase()
    registros = []
    inicio = 0
    tamanho = 500
    while True:
        resposta = (cliente.table("icismep_servicos").select("*")
                    .eq("versao_id", str(versao_id)).order("id")
                    .range(inicio, inicio + tamanho - 1).execute())
        lote = resposta.data or []
        registros.extend(lote)
        if len(lote) < tamanho:
            break
        inicio += tamanho
    return pd.DataFrame(registros)


def testar_gerenciador():
    try:
        cliente = conectar_supabase()
        cliente.table("icismep_versoes").select("id").limit(1).execute()
        cliente.table("icismep_servicos").select("id").limit(1).execute()
        return True, "Gerenciador conectado às duas tabelas do Supabase com sucesso!"
    except Exception as erro:
        return False, "Não foi possível consultar o banco. " + f"Tipo: {type(erro).__name__}"


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def _valor_decimal(valor):
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero <= 0:
            raise ValueError("Valor não positivo ou inválido")
        return numero
    except (InvalidOperation, ValueError, TypeError) as erro:
        raise ValueError(f"Valor ICISMEP inválido: {valor!r}") from erro


def validar_dados_excel(dados):
    """Valida o formato gerado por ler_excel_icismep, sem alterar o DataFrame."""
    campos = [
        "Municipio", "Descricao referencia", "Unidade referencia",
        "Secao original", "Tipo servico original", "Valor oficial",
    ]
    faltantes = [campo for campo in campos if campo not in dados.columns]
    if faltantes:
        raise ValueError("Campos ausentes: " + ", ".join(faltantes))
    if dados.empty:
        raise ValueError("A tabela Excel não contém serviços.")
    for indice, linha in dados.iterrows():
        for campo in ("Municipio", "Descricao referencia", "Unidade referencia"):
            valor = linha[campo]
            if pd.isna(valor) or not str(valor).strip():
                raise ValueError(f"Linha {indice + 1}: {campo} está vazio.")
        _valor_decimal(linha["Valor oficial"])
    return {
        "servicos": len(dados),
        "contratantes": int(dados["Municipio"].nunique()),
        "grupos": int(dados["Numero tabela"].nunique()) if "Numero tabela" in dados else None,
    }


def cadastrar_rascunho_excel(dados, arquivo_bytes, nome_arquivo, identificacao,
                             competencia_inicio, data_publicacao, cadastrado_por,
                             observacoes=""):
    """Grava uma versão em rascunho, sem torná-la disponível à auditoria.

    Retorna o ID e contagens para conferência. Se ocorrer falha durante o
