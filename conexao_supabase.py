
import streamlit as st
from supabase import create_client


@st.cache_resource
def conectar_supabase():
    url = st.secrets["supabase"]["url"]
    chave = st.secrets["supabase"]["key"]

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
            "Não foi possível conectar ao Supabase. "
            f"Detalhes: {type(erro).__name__}"
        )
