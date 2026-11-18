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
    envio, o registro permanece como rascunho, nunca como publicado.
    """
    resumo = validar_dados_excel(dados)
    if not isinstance(arquivo_bytes, bytes) or not arquivo_bytes:
        raise ValueError("É necessário informar o conteúdo original do Excel.")
    if not str(nome_arquivo).lower().endswith(".xlsx"):
        raise ValueError("O arquivo precisa ser Excel (.xlsx).")
    if not str(identificacao).strip():
        raise ValueError("Informe a identificação da versão.")
    if not isinstance(competencia_inicio, date):
        raise ValueError("Competência deve ser uma data (primeiro dia do mês).")
    if competencia_inicio.day != 1:
        raise ValueError("A competência deve usar o primeiro dia do mês.")
    if not isinstance(data_publicacao, date):
        raise ValueError("A data da tabela deve ser uma data válida.")

    cliente = conectar_supabase()
    assinatura = hashlib.sha256(arquivo_bytes).hexdigest()
    duplicadas = (cliente.table("icismep_versoes")
                  .select("id,status,identificacao")
                  .eq("hash_arquivo", assinatura).limit(1).execute()).data or []
    if duplicadas:
        existente = duplicadas[0]
        raise ValueError(
            "Este Excel já foi cadastrado no Supabase "
            f"(versão {existente['identificacao']}, situação {existente['status']})."
        )

    versao = {
        "identificacao": str(identificacao).strip(),
        "competencia_inicio": competencia_inicio.isoformat(),
        "data_publicacao": data_publicacao.isoformat(),
        "nome_arquivo": str(nome_arquivo),
        "formato_arquivo": "xlsx",
        "status": "rascunho",
        "cadastrado_por": str(cadastrado_por or "Não informado"),
        "observacoes": str(observacoes or ""),
        "hash_arquivo": assinatura,
    }
    resposta = cliente.table("icismep_versoes").insert(versao).execute()
    if not resposta.data:
        raise RuntimeError("O Supabase não retornou o ID da versão criada.")
    versao_id = resposta.data[0]["id"]

    registros = []
    for _, linha in dados.iterrows():
        municipio = str(linha["Municipio"]).strip()
        descricao = str(linha["Descricao referencia"]).strip()
        tipo = "" if pd.isna(linha["Tipo servico original"]) else str(linha["Tipo servico original"]).strip()
        unidade = str(linha["Unidade referencia"]).strip()
        secao = "" if pd.isna(linha["Secao original"]) else str(linha["Secao original"]).strip()
        codigo = "" if "Codigo" not in dados or pd.isna(linha.get("Codigo")) else str(linha["Codigo"]).strip()
        registros.append({
            "versao_id": versao_id,
            "codigo": codigo,
            "descricao": descricao,
            "descricao_normalizada": _normalizar(descricao),
            "municipio": municipio,
            "secao": secao,
            "tipo_servico": tipo,
            "unidade_medida": unidade,
            "valor": str(_valor_decimal(linha["Valor oficial"])),
        })

    for inicio in range(0, len(registros), 200):
        cliente.table("icismep_servicos").insert(registros[inicio:inicio + 200]).execute()

    quantidade_salva = len(listar_servicos(versao_id))
    if quantidade_salva != len(registros):
        raise RuntimeError(
            f"Rascunho {versao_id} incompleto: "
            f"{quantidade_salva} de {len(registros)} serviços gravados. "
            "Não publique esta versão."
        )
    return {"versao_id": versao_id, **resumo, "status": "rascunho"}
