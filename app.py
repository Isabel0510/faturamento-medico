"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================

Versão: 1.0
Linguagem: Python

OBJETIVO:
Auxiliar na leitura, conferência, validação
e faturamento de relatórios de serviços médicos.
============================================================
"""


# ============================================================
# BLOCO 1 - BIBLIOTECAS
# ============================================================

# Importamos o Streamlit.
# Ele será responsável por criar as telas do sistema
# que serão abertas no navegador.

from datetime import date


# ============================================================
# BLOCO 2 - CONFIGURAÇÕES GERAIS
# ============================================================

# Aqui definimos informações que poderão ser alteradas
# facilmente no futuro.

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"

VERSAO = "1.0"


# ============================================================
# BLOCO 3 - CONFIGURAÇÃO DA PÁGINA
# ============================================================

# Esta função configura a aparência básica da página.

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# BLOCO 4 - MENU LATERAL
# ============================================================

# O usuário escolherá no menu qual parte do sistema deseja abrir.

st.sidebar.title("📊 Faturamento Médico")

pagina = st.sidebar.radio(
    "Menu",
    [
        "🏠 Início",
        "📋 Tabelas de referência",
        "📤 Novo relatório",
        "🔍 Análise",
        "⚠️ Divergências",
        "✅ Validação",
        "💰 Faturamento",
        "📚 Histórico",
        "⚙️ Configurações"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    f"Versão {VERSAO}"
)


# ============================================================
# BLOCO 5 - PÁGINA INICIAL
# ============================================================

if pagina == "🏠 Início":

    st.title(NOME_SISTEMA)

    st.write(
        "Sistema para leitura, conferência, "
        "validação e faturamento de serviços médicos."
    )

    # Criamos quatro espaços lado a lado.
    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

    # Cada espaço recebe um indicador.
    coluna1.metric(
        "⏳ Pendentes",
        "0"
    )

    coluna2.metric(
        "✅ Validados",
        "0"
    )

    coluna3.metric(
        "⚠️ Com alerta",
        "0"
    )

    coluna4.metric(
        "💰 Faturamento",
        "R$ 0,00"
    )


# ============================================================
# BLOCO 6 - TABELAS DE REFERÊNCIA
# ============================================================

elif pagina == "📋 Tabelas de referência":

    st.title("📋 Tabelas de referência")

    st.write(
        "Nesta área serão consultadas e armazenadas "
        "as tabelas utilizadas para conferência dos serviços."
    )


# ============================================================
# BLOCO 7 - NOVO RELATÓRIO
# ============================================================

elif pagina == "📤 Novo relatório":

    st.title("📤 Novo relatório")

    st.write(
        "Aqui será realizado o envio do relatório "
        "que será analisado pelo sistema."
    )


# ============================================================
# BLOCO 8 - ANÁLISE
# ============================================================

elif pagina == "🔍 Análise":

    st.title("🔍 Análise")

    st.write(
        "Aqui aparecerão os dados encontrados "
        "automaticamente no relatório."
    )


# ============================================================
# BLOCO 9 - DIVERGÊNCIAS
# ============================================================

elif pagina == "⚠️ Divergências":

    st.title("⚠️ Divergências")

    st.write(
        "Aqui serão apresentados possíveis erros "
        "ou informações que precisam de conferência."
    )


# ============================================================
# BLOCO 10 - VALIDAÇÃO
# ============================================================

elif pagina == "✅ Validação":

    st.title("✅ Validação")

    st.write(
        "Nesta etapa uma pessoa poderá conferir "
        "e validar o resultado da análise."
    )


# ============================================================
# BLOCO 11 - FATURAMENTO
# ============================================================

elif pagina == "💰 Faturamento":

    st.title("💰 Faturamento")

    st.write(
        "Aqui serão preparados os dados que irão "
        "alimentar a planilha oficial de faturamento."
    )


# ============================================================
# BLOCO 12 - HISTÓRICO
# ============================================================

elif pagina == "📚 Histórico":

    st.title("📚 Histórico")

    st.write(
        "Aqui ficarão registrados os relatórios, "
        "validações e lançamentos realizados."
    )


# ============================================================
# BLOCO 13 - CONFIGURAÇÕES
# ============================================================

elif pagina == "⚙️ Configurações":

    st.title("⚙️ Configurações")

    st.write(
        "Aqui ficarão as opções de aparência "
        "e funcionamento do sistema."
    )
