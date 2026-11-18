
import streamlit as st
from supabase import create_client


def conectar_supabase():
    url = str(st.secrets["supabase"]["url"]).strip()
    chave = str(st.secrets["supabase"]["key"]).strip()

    return create_client(url, chave)


def testar_conexao():
    try:
        cliente = conectar_supabase()

        resposta = (
            cliente.table("icismep_versoes")
            .select("id")
            .limit(1)
            .execute()
        )

        return True, "Conexão estabelecida com sucesso!"

    except Exception as erro:
        return False, (
            "Falha na conexão com o Supabase. "
            f"Tipo do erro: {type(erro).__name__}"
        )
