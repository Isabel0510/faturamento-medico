"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================

Versão: 1.1
Linguagem: Python

OBJETIVO:
Auxiliar na leitura, conferência, validação
e faturamento de relatórios de serviços médicos.
============================================================
"""


# ============================================================
# BLOCO 1 - BIBLIOTECAS
# ============================================================

# Streamlit cria a interface do sistema no navegador.
import streamlit as st

# "date" permite trabalhar com datas.
from datetime import date


# ============================================================
# BLOCO 2 - CONFIGURAÇÕES GERAIS
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"

VERSAO = "1.1"


# ============================================================
# BLOCO 3 - CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# BLOCO 4 - MENU LATERAL
# ============================================================

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

    st.title("🏠 Início")

    st.write(
        "Sistema para leitura, conferência, "
        "validação e faturamento de serviços médicos."
    )

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

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
        "Preencha os dados abaixo e envie o relatório "
        "que será analisado pelo sistema."
    )


    # --------------------------------------------------------
    # MUNICÍPIO
    # --------------------------------------------------------

    municipio = st.text_input(
        "Município",
        placeholder="Ex.: Brumadinho"
    )


    # --------------------------------------------------------
    # RESPONSÁVEL
    # --------------------------------------------------------

    responsavel = st.text_input(
        "Responsável pelo preenchimento",
        placeholder="Nome de quem está enviando o relatório"
    )


    # --------------------------------------------------------
    # DATAS DO RELATÓRIO
    # --------------------------------------------------------

    coluna1, coluna2 = st.columns(2)

    data_inicial = coluna1.date_input(
        "Data inicial",
        value=date.today()
    )

    data_final = coluna2.date_input(
        "Data final",
        value=date.today()
    )


    # --------------------------------------------------------
    # CONFERÊNCIA DAS DATAS
    # --------------------------------------------------------

    if data_final < data_inicial:

        st.error(
            "A data final não pode ser anterior "
            "à data inicial."
        )

    else:

        # Converte as datas para mês/ano.
        competencia_inicial = data_inicial.strftime("%m/%Y")

        competencia_final = data_final.strftime("%m/%Y")


        # ----------------------------------------------------
        # UMA COMPETÊNCIA
        # ----------------------------------------------------

        if competencia_inicial == competencia_final:

            st.success(
                f"✅ Competência identificada: "
                f"{competencia_inicial}"
            )

            st.info(
                "O relatório será conferido utilizando "
                "uma tabela de referência."
            )


        # ----------------------------------------------------
        # DUAS COMPETÊNCIAS
        # ----------------------------------------------------

        else:

            st.warning(
                "⚠️ Este relatório envolve duas competências."
            )

            st.write(
                f"**Primeira competência:** "
                f"{competencia_inicial}"
            )

            st.write(
                f"**Segunda competência:** "
                f"{competencia_final}"
            )

            st.info(
                "Como não é possível identificar quanto "
                "foi executado em cada mês, o relatório será "
                "analisado integralmente considerando as duas "
                "tabelas de referência."
            )


        # ----------------------------------------------------
        # COMPETÊNCIA DO FATURAMENTO
        # ----------------------------------------------------

        st.subheader("💰 Competência do faturamento")

        st.success(
            f"O relatório será lançado integralmente em "
            f"{competencia_inicial}"
        )


    # --------------------------------------------------------
    # OUTRAS INFORMAÇÕES
    # --------------------------------------------------------

    observacoes = st.text_area(
        "Outras informações / observações",
        placeholder="Campo opcional"
    )


    # --------------------------------------------------------
    # UPLOAD DO RELATÓRIO
    # --------------------------------------------------------

    st.subheader("📎 Relatório")

    arquivo = st.file_uploader(
        "Selecione o arquivo Excel",
        type=["xlsx", "xls"]
    )


    # --------------------------------------------------------
    # ARQUIVO RECEBIDO
    # --------------------------------------------------------

    if arquivo is not None:

        st.success(
            f"✅ Arquivo recebido: {arquivo.name}"
        )

        st.write(
            "Na próxima etapa o sistema fará "
            "a leitura automática desse relatório."
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
