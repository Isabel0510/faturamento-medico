
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
        codigo = getattr(erro, "code", None)
        status = getattr(erro, "status_code", None)

        detalhes = f"Tipo: {tipo}"

        if codigo:
            detalhes += f" | Código: {codigo}"

        if status:
            detalhes += f" | HTTP: {status}"

        if tipo == "APIError":
            return False, (
                "O Supabase respondeu, mas não autorizou "
                "ou não conseguiu executar a consulta. "
                + detalhes
            )

        return False, (
            "Não foi possível completar a conexão. "
            + detalhes
        )
