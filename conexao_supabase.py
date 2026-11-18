import streamlit as st
from supabase import create_client
from urllib.parse import urlparse


@st.cache_resource
def conectar_supabase():
    url = st.secrets["supabase"]["url"].strip()
    chave = st.secrets["supabase"]["key"].strip()

    return create_client(url, chave)


def testar_conexao():
    try:
        url = st.secrets["supabase"]["url"].strip()
        endereco = urlparse(url)

        if (
            endereco.scheme != "https"
