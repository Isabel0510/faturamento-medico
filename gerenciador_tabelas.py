
import pandas as pd
from conexao_supabase import conectar_supabase


def listar_versoes():
    """Consulta as versões publicadas no Supabase."""
    cliente = conectar_supabase()

    resposta = (
        cliente.table("icismep_versoes")
        .select("*")
        .eq("status", "publicada")
        .order("competencia_inicio", desc=True)
        .execute()
    )

    return pd.DataFrame(resposta.data or [])


def listar_servicos(versao_id):
    """Consulta os serviços de uma versão."""
    cliente = conectar_supabase()
    registros = []
    inicio = 0
    tamanho = 500

    while True:
        resposta = (
            cliente.table("icismep_servicos")
            .select("*")
            .eq("versao_id", str(versao_id))
            .order("id")
            .range(inicio, inicio + tamanho - 1)
            .execute()
        )

        lote = resposta.data or []
        registros.extend(lote)

        if len(lote) < tamanho:
            break

        inicio += tamanho

    return pd.DataFrame(registros)


def testar_gerenciador():
    """Verifica se o gerenciador consegue consultar o banco."""
    try:
        cliente = conectar_supabase()

        cliente.table("icismep_versoes") \
            .select("id") \
            .limit(1) \
            .execute()

        cliente.table("icismep_servicos") \
            .select("id") \
            .limit(1) \
            .execute()

        return True, (
            "Gerenciador conectado às duas tabelas "
            "do Supabase com sucesso!"
        )

    except Exception as erro:
        return False, (
            "Não foi possível consultar o banco. "
            f"Tipo: {type(erro).__name__}"
        )
