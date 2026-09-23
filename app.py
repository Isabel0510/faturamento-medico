"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================

Versão: 1.4
Linguagem: Python
Interface: Streamlit

OBJETIVO:
Auxiliar na leitura, conferência, validação e faturamento
de relatórios de serviços médicos.

REGRAS IMPLEMENTADAS NESTA VERSÃO:
- Identificação de uma ou duas competências.
- Faturamento integral no mês inicial do período.
- Leitura de profissionais e CRM.
- Contagem de profissionais únicos pelo CRM.
- Identificação de múltiplos lançamentos do mesmo CRM.
- Leitura de plantões, consultas, procedimentos, exames,
  interconsultas, pacotes, horas e valores.
- Suporte a cabeçalhos em várias linhas, como no modelo FHEMIG.
- Consultas para faturamento =
  consultas + procedimentos + exames + interconsultas.
============================================================
"""

import io
import re
import unicodedata
from datetime import date

import pandas as pd
import streamlit as st


# ============================================================
# BLOCO 1 - CONFIGURAÇÕES GERAIS
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"
VERSAO = "1.4"

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# BLOCO 2 - NORMALIZAÇÃO DE TEXTOS
# ============================================================

def normalizar_texto(valor):

    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("ascii")

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# ============================================================
# BLOCO 3 - TRATAMENTO DE CRM
# ============================================================

def limpar_crm(valor):

    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    if isinstance(valor, (int, float)):

        if float(valor).is_integer():

            return str(
                int(valor)
            )

    texto = str(
        valor
    ).strip()

    if re.fullmatch(
        r"\d+\.0",
        texto
    ):

        texto = texto[:-2]

    return texto


def chave_crm(valor):

    return re.sub(
        r"\D",
        "",
        limpar_crm(valor)
    )


def crm_valido(valor):

    numeros = chave_crm(
        valor
    )

    return (
        4
        <= len(numeros)
        <= 10
    )


# ============================================================
# BLOCO 4 - VALIDAÇÃO DO PROFISSIONAL
# ============================================================

def profissional_valido(
    nome,
    crm
):

    nome_normalizado = normalizar_texto(
        nome
    )

    if not nome_normalizado:

        return False

    if len(nome_normalizado) < 4:

        return False


    palavras_invalidas = [

        "profissionais",

        "profissional",

        "nome completo",

        "soma",

        "total",

        "valor total",

        "relatorio",

        "servicos medicos",

        "municipio",

        "competencia"
    ]


    for palavra in palavras_invalidas:

        if nome_normalizado.startswith(
            normalizar_texto(
                palavra
            )
        ):

            return False


    if not re.search(
        r"[a-z]",
        nome_normalizado
    ):

        return False


    if not crm_valido(
        crm
    ):

        return False


    return True


# ============================================================
# BLOCO 5 - IDENTIFICAÇÃO DO CABEÇALHO PRINCIPAL
# ============================================================

def linha_e_cabecalho(
    linha
):

    encontrou_profissional = False

    encontrou_crm = False


    for valor in linha:

        texto = normalizar_texto(
            valor
        )


        if "profission" in texto:

            encontrou_profissional = True


        if (
            texto == "crm"
            or texto.startswith(
                "crm "
            )
        ):

            encontrou_crm = True


    return (
        encontrou_profissional
        and encontrou_crm
    )


def localizar_coluna_profissional(
    linha
):

    for numero_coluna, valor in enumerate(
        linha
    ):

        if "profission" in normalizar_texto(
            valor
        ):

            return numero_coluna


    return None


def localizar_coluna_crm(
    linha
):

    for numero_coluna, valor in enumerate(
        linha
    ):

        texto = normalizar_texto(
            valor
        )


        if (
            texto == "crm"
            or texto.startswith(
                "crm "
            )
        ):

            return numero_coluna


    return None


# ============================================================
# BLOCO 6 - CONVERSÃO DE NÚMEROS
# ============================================================

def converter_numero(
    valor
):

    if valor is None:

        return 0.0


    if isinstance(
        valor,
        float
    ):

        if pd.isna(
            valor
        ):

            return 0.0


    if isinstance(
        valor,
        (int, float)
    ):

        return float(
            valor
        )


    texto = str(
        valor
    ).strip()


    if texto == "":

        return 0.0


    texto = texto.replace(
        "R$",
        ""
    )

    texto = texto.replace(
        " ",
        ""
    )


    if "," in texto:

        texto = texto.replace(
            ".",
            ""
        )

        texto = texto.replace(
            ",",
            "."
        )


    try:

        return float(
            texto
        )

    except:

        return 0.0


# ============================================================
# BLOCO 7 - IDENTIFICAÇÃO MULTILINHA DA PRODUÇÃO
# ============================================================

def localizar_colunas_producao_multilinha(
    planilha,
    linha_cabecalho
):

    resultado = {

        "Plantoes": [],

        "Consultas": [],

        "Procedimentos": [],

        "Exames": [],

        "Interconsultas": [],

        "Pacotes": [],

        "Horas": [],

        "Valor unitario": [],

        "Valor total": []
    }


    # Analisa o cabeçalho e algumas linhas logo abaixo.
    # Isso resolve casos como a FHEMIG.

    linha_final = min(

        linha_cabecalho + 6,

        len(planilha)
    )


    for numero_coluna in range(
        planilha.shape[1]
    ):


        textos_coluna = []


        for numero_linha in range(

            linha_cabecalho,

            linha_final
        ):


            valor = planilha.iat[

                numero_linha,

                numero_coluna
            ]


            textos_coluna.append(

                normalizar_texto(
                    valor
                )
            )


        for texto in textos_coluna:


            if not texto:

                continue


            # --------------------------------------------
            # HORAS
            # --------------------------------------------

            if (

                "quant de hora" in texto

                or "quantidade de hora" in texto

                or "qtd hora" in texto

                or texto == "horas"
            ):


                resultado[
                    "Horas"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # PLANTÕES
            # --------------------------------------------

            if (

                "quant de plantao" in texto

                or "quant plantao" in texto

                or "qtd plantao" in texto

                or texto == "plantoes"
            ):


                resultado[
                    "Plantoes"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # CONSULTAS
            # --------------------------------------------

            if (

                "quant de consulta" in texto

                or "quant consulta" in texto

                or "qtd consulta" in texto

                or texto == "consultas"
            ):


                resultado[
                    "Consultas"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # PROCEDIMENTOS
            # --------------------------------------------

            if (

                "quant de procedimento" in texto

                or "quant procedimento" in texto

                or "qtd procedimento" in texto

                or texto == "procedimentos"
            ):


                resultado[
                    "Procedimentos"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # EXAMES
            # --------------------------------------------

            if (

                "quant de exame" in texto

                or "quant exame" in texto

                or "qtd exame" in texto

                or texto == "exames"
            ):


                resultado[
                    "Exames"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # INTERCONSULTAS
            # --------------------------------------------

            if (

                "quant de interconsulta" in texto

                or "quant interconsulta" in texto

                or "qtd interconsulta" in texto

                or texto == "interconsultas"
            ):


                resultado[
                    "Interconsultas"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # PACOTES
            # --------------------------------------------

            if (

                "quant de pacote" in texto

                or "quant pacote" in texto

                or "qtd pacote" in texto

                or "pacote de consulta" in texto

                or texto == "pacotes"
            ):


                resultado[
                    "Pacotes"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # VALOR UNITÁRIO
            # --------------------------------------------

            if (

                "valor da hora" in texto

                or "valor unitario" in texto

                or "valor consulta" in texto

                or "valor procedimento" in texto
            ):


                resultado[
                    "Valor unitario"
                ].append(
                    numero_coluna
                )


            # --------------------------------------------
            # VALOR TOTAL
            # --------------------------------------------

            if (

                texto == "valor total"

                or "valor total final" in texto
            ):


                resultado[
                    "Valor total"
                ].append(
                    numero_coluna
                )


    # Remove colunas repetidas.

    for campo in resultado:


        resultado[campo] = list(

            dict.fromkeys(

                resultado[campo]
            )
        )


    return resultado


# ============================================================
# BLOCO 8 - LEITURA DE UMA ABA
# ============================================================

def ler_profissionais_da_aba(

    arquivo_bytes,

    nome_arquivo,

    nome_aba
):


    planilha = pd.read_excel(

        io.BytesIO(
            arquivo_bytes
        ),

        sheet_name=nome_aba,

        header=None,

        dtype=object
    )


    if planilha.empty:


        return (

            pd.DataFrame(),

            {

                "Aba":
                    nome_aba,

                "Cabeçalhos encontrados":
                    0,

                "Lançamentos válidos":
                    0,

                "Colunas de horas":
                    0,

                "Situação":
                    "Aba vazia"
            }
        )


    # --------------------------------------------------------
    # PROCURAR CABEÇALHOS
    # --------------------------------------------------------

    cabecalhos = []


    for numero_linha in range(
        len(planilha)
    ):


        linha = planilha.iloc[
            numero_linha
        ].tolist()


        if linha_e_cabecalho(
            linha
        ):


            cabecalhos.append(
                numero_linha
            )


    registros = []

    colunas_horas_encontradas = set()


    # --------------------------------------------------------
    # ANALISAR CADA BLOCO
    # --------------------------------------------------------

    for posicao, linha_cabecalho in enumerate(
        cabecalhos
    ):


        cabecalho = planilha.iloc[
            linha_cabecalho
        ].tolist()


        coluna_profissional = localizar_coluna_profissional(
            cabecalho
        )


        coluna_crm = localizar_coluna_crm(
            cabecalho
        )


        colunas_producao = localizar_colunas_producao_multilinha(

            planilha,

            linha_cabecalho
        )


        colunas_horas_encontradas.update(

            colunas_producao[
                "Horas"
            ]
        )


        if (

            coluna_profissional is None

            or coluna_crm is None
        ):


            continue


        # ----------------------------------------------------
        # FIM DO BLOCO
        # ----------------------------------------------------

        if posicao + 1 < len(
            cabecalhos
        ):


            linha_final = cabecalhos[
                posicao + 1
            ]


        else:


            linha_final = len(
                planilha
            )


        # ----------------------------------------------------
        # LER PROFISSIONAIS
        # ----------------------------------------------------

        for numero_linha in range(

            linha_cabecalho + 1,

            linha_final
        ):


            nome = planilha.iat[

                numero_linha,

                coluna_profissional
            ]


            crm = planilha.iat[

                numero_linha,

                coluna_crm
            ]


            if not profissional_valido(
                nome,
                crm
            ):


                continue


            # ------------------------------------------------
            # PRODUÇÃO
            # ------------------------------------------------

            producao = {}


            # Quantidades: soma todas as colunas encontradas.

            for campo in [

                "Plantoes",

                "Consultas",

                "Procedimentos",

                "Exames",

                "Interconsultas",

                "Pacotes",

                "Horas"
            ]:


                total_campo = 0.0


                for numero_coluna in colunas_producao[
                    campo
                ]:


                    valor = planilha.iat[

                        numero_linha,

                        numero_coluna
                    ]


                    total_campo += converter_numero(
                        valor
                    )


                producao[
                    campo
                ] = total_campo


            # ------------------------------------------------
            # VALOR UNITÁRIO
            # ------------------------------------------------

            valor_unitario = 0.0


            for numero_coluna in colunas_producao[
                "Valor unitario"
            ]:


                valor = converter_numero(

                    planilha.iat[

                        numero_linha,

                        numero_coluna
                    ]
                )


                if valor != 0:


                    valor_unitario = valor

                    break


            producao[
                "Valor unitario"
            ] = valor_unitario


            # ------------------------------------------------
            # VALOR TOTAL
            # ------------------------------------------------

            valor_total = 0.0


            for numero_coluna in colunas_producao[
                "Valor total"
            ]:


                valor_total += converter_numero(

                    planilha.iat[

                        numero_linha,

                        numero_coluna
                    ]
                )


            producao[
                "Valor total"
            ] = valor_total


            # ------------------------------------------------
            # SALVAR REGISTRO
            # ------------------------------------------------

            registros.append(

                {

                    "Profissional":
                        str(nome).strip(),

                    "CRM":
                        limpar_crm(
                            crm
                        ),

                    "CRM_ID":
                        chave_crm(
                            crm
                        ),

                    "Arquivo":
                        nome_arquivo,

                    "Aba":
                        nome_aba,

                    "Linha do Excel":
                        numero_linha + 1,

                    **producao
                }
            )


    dados = pd.DataFrame(
        registros
    )


    diagnostico = {

        "Aba":
            nome_aba,

        "Cabeçalhos encontrados":
            len(cabecalhos),

        "Lançamentos válidos":
            len(dados),

        "Colunas de horas":
            len(
                colunas_horas_encontradas
            ),

        "Situação":

            "OK"

            if cabecalhos

            else "Cabeçalho não reconhecido"
    }


    return (

        dados,

        diagnostico
    )


# ============================================================
# BLOCO 9 - SUGESTÃO DE ABA
# ============================================================

def sugerir_abas(

    nomes_abas,

    competencia_inicial,

    competencia_final
):


    if len(
        nomes_abas
    ) == 1:


        return nomes_abas


    mes_inicial = competencia_inicial[
        :2
    ]


    mes_final = competencia_final[
        :2
    ]


    candidatos = []


    for aba in nomes_abas:


        texto = normalizar_texto(
            aba
        )


        if (

            mes_inicial in texto

            or mes_final in texto
        ):


            candidatos.append(
                aba
            )


    if candidatos:


        return [
            candidatos[-1]
        ]


    for aba in nomes_abas:


        if normalizar_texto(
            aba
        ) != "modelo":


            return [
                aba
            ]


    return [
        nomes_abas[0]
    ]


# ============================================================
# BLOCO 10 - PROCESSAMENTO DO RELATÓRIO
# ============================================================

def processar_relatorio(

    arquivo_bytes,

    nome_arquivo,

    abas
):


    tabelas = []

    diagnosticos = []


    for aba in abas:


        try:


            dados_aba, diagnostico = ler_profissionais_da_aba(

                arquivo_bytes,

                nome_arquivo,

                aba
            )


            diagnosticos.append(
                diagnostico
            )


            if not dados_aba.empty:


                tabelas.append(
                    dados_aba
                )


        except Exception as erro:


            diagnosticos.append(

                {

                    "Aba":
                        aba,

                    "Cabeçalhos encontrados":
                        0,

                    "Lançamentos válidos":
                        0,

                    "Colunas de horas":
                        0,

                    "Situação":
                        f"ERRO: {erro}"
                }
            )


    if tabelas:


        dados = pd.concat(

            tabelas,

            ignore_index=True
        )


    else:


        dados = pd.DataFrame()


    return (

        dados,

        pd.DataFrame(
            diagnosticos
        )
    )


# ============================================================
# BLOCO 11 - PROFISSIONAIS ÚNICOS
# ============================================================

def contar_profissionais_unicos(
    dados
):


    if dados.empty:


        return 0


    return dados[
        "CRM_ID"
    ].nunique()


# ============================================================
# BLOCO 12 - CRM COM MAIS DE UM LANÇAMENTO
# ============================================================

def localizar_crms_com_varios_lancamentos(
    dados
):


    if dados.empty:


        return pd.DataFrame()


    contagem = (

        dados

        .groupby(
            "CRM_ID"
        )

        .size()
    )


    repetidos = contagem[
        contagem > 1
    ]


    resultado = []


    for crm_id, quantidade in repetidos.items():


        grupo = dados[

            dados[
                "CRM_ID"
            ] == crm_id
        ]


        nomes = list(

            dict.fromkeys(

                grupo[
                    "Profissional"
                ].tolist()
            )
        )


        resultado.append(

            {

                "CRM":

                    grupo.iloc[
                        0
                    ][
                        "CRM"
                    ],

                "Quantidade de lançamentos":

                    int(
                        quantidade
                    ),

                "Nome(s) encontrado(s)":

                    " | ".join(
                        nomes
                    )
            }
        )


    return pd.DataFrame(
        resultado
    )


# ============================================================
# BLOCO 13 - FORMATAÇÃO
# ============================================================

def formatar_moeda(
    valor
):


    texto = f"{valor:,.2f}"


    texto = texto.replace(
        ",",
        "X"
    )


    texto = texto.replace(
        ".",
        ","
    )


    texto = texto.replace(
        "X",
        "."
    )


    return f"R$ {texto}"


def formatar_numero(
    valor,
    casas=0
):


    texto = f"{valor:,.{casas}f}"


    texto = texto.replace(
        ",",
        "X"
    )


    texto = texto.replace(
        ".",
        ","
    )


    texto = texto.replace(
        "X",
        "."
    )


    return texto


# ============================================================
# BLOCO 14 - MOSTRAR ANÁLISE
# ============================================================

def mostrar_analise(

    dados,

    diagnostico
):


    if dados is None or dados.empty:


        st.error(
            "Nenhum profissional válido foi identificado."
        )


        st.write(
            "Consulte o diagnóstico abaixo."
        )


        if diagnostico is not None:


            st.dataframe(

                diagnostico,

                use_container_width=True,

                hide_index=True
            )


        return


    profissionais = contar_profissionais_unicos(
        dados
    )


    lancamentos = len(
        dados
    )


    coluna1, coluna2 = st.columns(
        2
    )


    coluna1.metric(

        "👨‍⚕️ Profissionais únicos (CRM)",

        profissionais
    )


    coluna2.metric(

        "📄 Lançamentos encontrados",

        lancamentos
    )


    st.caption(
        "Profissionais únicos = CRMs diferentes. "
        "Lançamentos = linhas válidas encontradas no relatório."
    )


    # --------------------------------------------------------
    # PRODUÇÃO
    # --------------------------------------------------------

    st.subheader(
        "📊 Produção encontrada"
    )


    plantoes = dados[
        "Plantoes"
    ].sum()


    consultas = dados[
        "Consultas"
    ].sum()


    procedimentos = dados[
        "Procedimentos"
    ].sum()


    exames = dados[
        "Exames"
    ].sum()


    interconsultas = dados[
        "Interconsultas"
    ].sum()


    pacotes = dados[
        "Pacotes"
    ].sum()


    horas = dados[
        "Horas"
    ].sum()


    valor_total = dados[
        "Valor total"
    ].sum()


    consultas_faturamento = (

        consultas

        + procedimentos

        + exames

        + interconsultas
    )


    linha1 = st.columns(
        4
    )


    linha1[
        0
    ].metric(

        "Plantões",

        formatar_numero(
            plantoes,
            0
        )
    )


    linha1[
        1
    ].metric(

        "Consultas",

        formatar_numero(
            consultas,
            0
        )
    )


    linha1[
        2
    ].metric(

        "Procedimentos",

        formatar_numero(
            procedimentos,
            0
        )
    )


    linha1[
        3
    ].metric(

        "Exames",

        formatar_numero(
            exames,
            0
        )
    )


    linha2 = st.columns(
        4
    )


    linha2[
        0
    ].metric(

        "Interconsultas",

        formatar_numero(
            interconsultas,
            0
        )
    )


    linha2[
        1
    ].metric(

        "Pacotes",

        formatar_numero(
            pacotes,
            0
        )
    )


    linha2[
        2
    ].metric(

        "Horas",

        formatar_numero(
            horas,
            2
        )
    )


    linha2[
        3
    ].metric(

        "Consultas p/ faturamento",

        formatar_numero(

            consultas_faturamento,

            0
        )
    )


    st.metric(

        "💰 Valor total encontrado",

        formatar_moeda(
            valor_total
        )
    )


    st.caption(
        "Consultas para faturamento = "
        "consultas + procedimentos + exames + interconsultas. "
        "Pacotes permanecem separados."
    )


    # --------------------------------------------------------
    # DETALHAMENTO
    # --------------------------------------------------------

    st.subheader(
        "📋 Detalhamento encontrado"
    )


    colunas_exibicao = [

        "Profissional",

        "CRM",

        "Plantoes",

        "Consultas",

        "Procedimentos",

        "Exames",

        "Interconsultas",

        "Pacotes",

        "Horas",

        "Valor unitario",

        "Valor total",

        "Aba",

        "Linha do Excel"
    ]


    st.dataframe(

        dados[
            colunas_exibicao
        ].copy(),

        use_container_width=True,

        hide_index=True
    )


    # --------------------------------------------------------
    # MAIS DE UM LANÇAMENTO POR CRM
    # --------------------------------------------------------

    varios_lancamentos = localizar_crms_com_varios_lancamentos(
        dados
    )


    if not varios_lancamentos.empty:


        st.info(
            "Alguns CRMs aparecem em mais de um lançamento. "
            "Isso não significa automaticamente duplicidade."
        )


        with st.expander(
            "Ver CRMs com mais de um lançamento"
        ):


            st.dataframe(

                varios_lancamentos,

                use_container_width=True,

                hide_index=True
            )


    # --------------------------------------------------------
    # DIAGNÓSTICO
    # --------------------------------------------------------

    with st.expander(
        "🔧 Diagnóstico da leitura"
    ):


        st.dataframe(

            diagnostico,

            use_container_width=True,

            hide_index=True
        )


# ============================================================
# BLOCO 15 - MENU LATERAL
# ============================================================

st.sidebar.title(
    "📊 Faturamento Médico"
)


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
# PÁGINA - INÍCIO
# ============================================================

if pagina == "🏠 Início":


    st.title(
        "🏠 Início"
    )


    st.write(
        "Sistema para leitura, conferência, "
        "validação e faturamento de serviços médicos."
    )


    colunas = st.columns(
        4
    )


    colunas[
        0
    ].metric(

        "⏳ Pendentes",

        "0"
    )


    colunas[
        1
    ].metric(

        "✅ Validados",

        "0"
    )


    colunas[
        2
    ].metric(

        "⚠️ Com alerta",

        "0"
    )


    colunas[
        3
    ].metric(

        "💰 Faturamento",

        "R$ 0,00"
    )


# ============================================================
# PÁGINA - TABELAS DE REFERÊNCIA
# ============================================================

elif pagina == "📋 Tabelas de referência":


    st.title(
        "📋 Tabelas de referência"
    )


    st.write(
        "Nesta área serão consultadas as "
        "tabelas oficiais utilizadas para conferência."
    )


    st.info(
        "A integração automática com as tabelas "
        "de referência será adicionada em uma próxima etapa."
    )


# ============================================================
# PÁGINA - NOVO RELATÓRIO
# ============================================================

elif pagina == "📤 Novo relatório":


    st.title(
        "📤 Novo relatório"
    )


    st.write(
        "Preencha os dados e envie o relatório "
        "que será analisado."
    )


    municipio = st.text_input(

        "Município",

        placeholder="Ex.: Brumadinho"
    )


    responsavel = st.text_input(

        "Responsável pelo preenchimento",

        placeholder="Nome de quem está enviando"
    )


    coluna1, coluna2 = st.columns(
        2
    )


    data_inicial = coluna1.date_input(

        "Data inicial",

        value=date.today()
    )


    data_final = coluna2.date_input(

        "Data final",

        value=date.today()
    )


    competencia_inicial = data_inicial.strftime(
        "%m/%Y"
    )


    competencia_final = data_final.strftime(
        "%m/%Y"
    )


    if data_final < data_inicial:


        st.error(
            "A data final não pode ser "
            "anterior à data inicial."
        )


    else:


        if competencia_inicial == competencia_final:


            st.success(
                f"✅ Competência identificada: "
                f"{competencia_inicial}"
            )


            st.info(
                "O relatório possui apenas "
                "uma competência."
            )


        else:


            st.warning(
                "⚠️ Este relatório envolve "
                "duas competências."
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
                "foi executado em cada mês, o relatório "
                "será analisado integralmente considerando "
                "as duas tabelas de referência."
            )


        st.subheader(
            "💰 Competência do faturamento"
        )


        st.success(
            f"O relatório será lançado integralmente "
            f"em {competencia_inicial}"
        )


    observacoes = st.text_area(

        "Outras informações / observações",

        placeholder="Campo opcional"
    )


    st.subheader(
        "📎 Relatório Excel"
    )


    arquivo = st.file_uploader(

        "Selecione o relatório",

        type=[
            "xlsx"
        ]
    )


    if arquivo is not None:


        arquivo_bytes = arquivo.getvalue()


        try:


            excel = pd.ExcelFile(

                io.BytesIO(
                    arquivo_bytes
                )
            )


            abas_disponiveis = excel.sheet_names


            sugestao = sugerir_abas(

                abas_disponiveis,

                competencia_inicial,

                competencia_final
            )


            abas_escolhidas = st.multiselect(

                "Aba(s) que devem ser analisadas",

                options=abas_disponiveis,

                default=sugestao
            )


            st.caption(
                "O sistema sugere uma aba, mas você pode "
                "alterar a seleção antes da análise."
            )


            if st.button(

                "🔍 Analisar relatório",

                type="primary"
            ):


                if data_final < data_inicial:


                    st.error(
                        "Corrija o período antes "
                        "de analisar o arquivo."
                    )


                elif not abas_escolhidas:


                    st.error(
                        "Escolha pelo menos uma aba."
                    )


                else:


                    with st.spinner(
                        "Lendo o relatório..."
                    ):


                        dados, diagnostico = processar_relatorio(

                            arquivo_bytes,

                            arquivo.name,

                            abas_escolhidas
                        )


                    st.session_state[
                        "dados_relatorio"
                    ] = dados


                    st.session_state[
                        "diagnostico_relatorio"
                    ] = diagnostico


                    st.session_state[
                        "municipio_relatorio"
                    ] = municipio


                    st.session_state[
                        "responsavel_relatorio"
                    ] = responsavel


                    st.session_state[
                        "observacoes_relatorio"
                    ] = observacoes


                    st.session_state[
                        "periodo_relatorio"
                    ] = (

                        f"{data_inicial.strftime('%d/%m/%Y')} "

                        f"a "

                        f"{data_final.strftime('%d/%m/%Y')}"
                    )


                    st.session_state[
                        "competencia_faturamento"
                    ] = competencia_inicial


                    st.success(
                        "✅ Análise concluída."
                    )


                    mostrar_analise(

                        dados,

                        diagnostico
                    )


        except Exception as erro:


            st.error(
                "Não foi possível abrir ou analisar "
                "o arquivo Excel."
            )


            with st.expander(
                "Ver detalhes do erro"
            ):


                st.code(
                    str(erro)
                )


# ============================================================
# PÁGINA - ANÁLISE
# ============================================================

elif pagina == "🔍 Análise":


    st.title(
        "🔍 Análise"
    )


    if "dados_relatorio" not in st.session_state:


        st.info(
            "Primeiro envie e analise um relatório "
            "em 📤 Novo relatório."
        )


    else:


        st.write(

            "**Município:**",

            st.session_state.get(

                "municipio_relatorio",

                "Não informado"
            )
        )


        st.write(

            "**Responsável:**",

            st.session_state.get(

                "responsavel_relatorio",

                "Não informado"
            )
        )


        st.write(

            "**Período:**",

            st.session_state.get(

                "periodo_relatorio",

                ""
            )
        )


        st.write(

            "**Competência do faturamento:**",

            st.session_state.get(

                "competencia_faturamento",

                ""
            )
        )


        st.divider()


        mostrar_analise(

            st.session_state[
                "dados_relatorio"
            ],

            st.session_state[
                "diagnostico_relatorio"
            ]
        )


# ============================================================
# PÁGINA - DIVERGÊNCIAS
# ============================================================

elif pagina == "⚠️ Divergências":


    st.title(
        "⚠️ Divergências"
    )


    st.write(
        "Nesta área aparecerão possíveis erros "
        "e itens para conferência."
    )


    st.info(
        "A auditoria dos códigos, valores oficiais "
        "e multiplicações será adicionada posteriormente."
    )


# ============================================================
# PÁGINA - VALIDAÇÃO
# ============================================================

elif pagina == "✅ Validação":


    st.title(
        "✅ Validação"
    )


    st.write(
        "A validação humana será adicionada "
        "nas próximas etapas."
    )


# ============================================================
# PÁGINA - FATURAMENTO
# ============================================================

elif pagina == "💰 Faturamento":


    st.title(
        "💰 Faturamento"
    )


    st.write(
        "Aqui serão exibidos os relatórios "
        "já validados."
    )


# ============================================================
# PÁGINA - HISTÓRICO
# ============================================================

elif pagina == "📚 Histórico":


    st.title(
        "📚 Histórico"
    )


    st.write(
        "Aqui ficará registrado "
        "o histórico do sistema."
    )


# ============================================================
# PÁGINA - CONFIGURAÇÕES
# ============================================================

elif pagina == "⚙️ Configurações":


    st.title(
        "⚙️ Configurações"
    )


    st.write(
        f"Versão atual: {VERSAO}"
    )
