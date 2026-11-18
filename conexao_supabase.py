
import streamlit as st
from supabase import create_client


def conectar_supabase():
    url = str(st.secrets["supabase"]["url"]).strip()
    chave = str(st.secrets["supabase"]["key"]).strip()

    return create_client(url, chave)




def testar_conexao():
    try:
        cliente = conectar_supabase()

        cliente.table("icismep_versoes") \
            .select("id") \
            .limit(1) \
            .execute()

        return True, "Conexão estabelecida com sucesso!"

    except Exception as erro:
        tipo = type(erro).__name__
        codigo = getattr(erro, "code", "")
        mensagem = getattr(erro, "message", "")
        detalhes = getattr(erro, "details", "")

        return False, (
            f"Tipo: {tipo}\n\n"
            f"Código: {codigo}\n\n"
            f"Mensagem: {mensagem}\n\n"
            f"Detalhes: {detalhes}"
        )
