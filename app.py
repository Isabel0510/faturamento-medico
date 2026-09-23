"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================

Versão: 1.3
Linguagem: Python
Interface: Streamlit

OBJETIVO:
Auxiliar na leitura, conferência, validação
e faturamento de relatórios de serviços médicos.

REGRAS IMPLEMENTADAS NESTA VERSÃO:

- Identificação de uma ou duas competências.
- Faturamento integral no mês inicial do período.
- Leitura de profissionais e CRM.
- Contagem de profissionais únicos pelo CRM.
- Identificação de múltiplos lançamentos do mesmo CRM.
- Leitura inicial de:
    plantões
    consultas
    procedimentos
    exames
    interconsultas
    pacotes
    horas
    valores
- Consultas para faturamento =
  consultas + procedimentos + exames + interconsultas.
============================================================
"""


# ============================================================
# BLOCO 1 - BIBLIOTECAS
# ============================================================

import io
import re
import unicodedata

from datetime import date

import pandas as pd
import streamlit as st


# ============================================================
# BLOCO 2 - CONFIGURAÇÕES GERAIS
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"

VERSAO = "1.3"


# ============================================================
# BLOCO 3 - NORMALIZAÇÃO DE TEXTOS
# ============================================================

def normalizar_texto(valor):

    """
    Padroniza textos para facilitar comparações.

    Exemplo:

    "QUANT. DE HORA"
           ↓
    "quant de hora"

    Isso facilita a identificação de cabeçalhos
    escritos de formas diferentes.
    """

    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    # Remove acentos.
    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = texto.encode(
        "ascii",
        "ignore"
    ).decode("ascii")

    # Substitui pontuação por espaços.
    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    # Remove espaços duplicados.
    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# ============================================================
# BLOCO 4 - TRATAMENTO DE CRM
# ============================================================

def limpar_crm(valor):

    """
    Deixa o CRM em um formato mais simples.

    Exemplo:

    45576.0
       ↓
    45576
    """

    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    if isinstance(valor, (int, float)):

        if float(valor).is_integer():
            return str(int(valor))

    texto = str(valor).strip()

    if re.fullmatch(
        r"\d+\.0",
        texto
    ):

        texto = texto[:-2]

    return texto


def chave_crm(valor):

    """
    Cria uma identificação interna do CRM.

    Exemplo:

    CRM 45576
    45.576
    45576

    passam a ter a mesma identificação:
    45576
    """

    crm = limpar_crm(
        valor
    )

    numeros = re.sub(
        r"\D",
        "",
        crm
    )

    return numeros


def crm_valido(valor):

    """
    Verifica se o conteúdo parece realmente um CRM.
    """

    numeros = chave_crm(
        valor
    )

    return (
        4 <= len(numeros) <= 10
    )


# ============================================================
# BLOCO 5 - VALIDAÇÃO DO PROFISSIONAL
# ============================================================

def profissional_valido(nome, crm):

    """
    Impede que cabeçalhos, SOMA, TOTAL etc.
    sejam contados como médicos.
    """

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
            normalizar_texto(palavra)
        ):

            return False


    # O nome deve possuir letras.
    if not re.search(
        r"[a-z]",
        nome_normalizado
    ):

        return False


    # Também deve possuir CRM válido.
    if not crm_valido(
        crm
    ):

        return False


    return True


# ============================================================
# BLOCO 6 - IDENTIFICAÇÃO DO CABEÇALHO
# ============================================================

def linha_e_cabecalho(linha):

    """
    Procura uma linha que contenha:

    PROFISSIONAL
    +
    CRM
    """

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
            or texto.startswith("crm ")
        ):

            encontrou_crm = True


    return (
        encontrou_profissional
        and encontrou_crm
    )


def localizar_coluna_profissional(linha):

    """
    Descobre em qual coluna está
    o nome do profissional.
    """

    for numero_coluna, valor in enumerate(
        linha
    ):

        texto = normalizar_texto(
            valor
        )

        if "profission" in texto:

            return numero_coluna


    return None


def localizar_coluna_crm(linha):

    """
    Descobre em qual coluna está o CRM.
    """

    for numero_coluna, valor in enumerate(
        linha
    ):

        texto = normalizar_texto(
            valor
        )


        if (
            texto == "crm"
            or texto.startswith("crm ")
        ):

            return numero_coluna


    return None


# ============================================================
# BLOCO 7 - NOMES POSSÍVEIS DAS COLUNAS DE PRODUÇÃO
# ============================================================

CAMPOS_PRODUCAO = {

    "Plantoes": [

        "plantao",

        "plantoes",

        "quant plantao",

        "quant de plantao",

        "qtd plantao"
    ],


    "Consultas": [

        "consulta",

        "consultas",

        "quant consulta",

        "quant de consulta",

        "qtd consulta"
    ],


    "Procedimentos": [

        "procedimento",

        "procedimentos",

        "quant procedimento",

        "quant de procedimento",

        "qtd procedimento"
    ],


    "Exames": [

        "exame",

        "exames",

        "quant exame",

        "quant de exame",

        "qtd exame"
    ],


    "Interconsultas": [

        "interconsulta",

        "interconsultas",

        "quant interconsulta",

        "quant de interconsulta",

        "qtd interconsulta"
    ],


    "Pacotes": [

        "pacote",

        "pacotes",

        "pacote consulta",

        "pacote de consulta",

        "quant pacote",

        "qtd pacote"
    ],


    "Horas": [

        "hora",

        "horas",

        "quant hora",

        "quant de hora",

        "quantidade de hora",

        "qtd hora",

        "carga horaria"
    ],


    "Valor unitario": [

        "valor unitario",

        "valor da hora",

        "valor hora",

        "valor consulta",

        "valor procedimento",

        "valor do procedimento"
    ],


    "Valor total": [

        "valor total",

        "valor total final",

        "total bruto",

        "valor bruto",

        "valor a pagar"
    ]
}


# ============================================================
# BLOCO 8 - LOCALIZAÇÃO DAS COLUNAS DE PRODUÇÃO
# ============================================================

def localizar_coluna_por_nomes(
    linha,
    nomes
):

    """
    Procura uma coluna utilizando
    vários nomes possíveis.
    """

    textos = [

        normalizar_texto(
            valor
        )

        for valor in linha
    ]


    nomes_normalizados = [

        normalizar_texto(
            nome
        )

        for nome in nomes
    ]


    # Primeiro procura correspondência EXATA.
    for numero_coluna, texto in enumerate(
        textos
    ):

        for nome in nomes_normalizados:

            if texto == nome:

                return numero_coluna


    # Se não encontrar, procura correspondência parcial.
    for numero_coluna, texto in enumerate(
        textos
    ):

        for nome in nomes_normalizados:

            if (
                len(nome) >= 5
                and nome in texto
            ):

                return numero_coluna


    return None


def localizar_colunas_producao(
    cabecalho
):

    """
    Descobre onde estão as colunas
    relacionadas à produção.
    """

    resultado = {}


    for campo, nomes in CAMPOS_PRODUCAO.items():

        resultado[campo] = localizar_coluna_por_nomes(

            cabecalho,

            nomes
        )


    return resultado


# ============================================================
# BLOCO 9 - CONVERSÃO DE NÚMEROS
# ============================================================

def converter_numero(valor):

    """
    Converte valores do Excel para números.

    Exemplos:

    25
    "25"
    "1.250,50"
    "R$ 1.250,50"

    passam a ser números que o Python
    consegue somar.
    """

    if valor is None:
        return 0.0


    if isinstance(valor, float):

        if pd.isna(valor):
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


    # Formato brasileiro:
    # 1.250,50
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
# BLOCO 10 - LEITURA DE UMA ABA
# ============================================================

def ler_profissionais_da_aba(
    arquivo_bytes,
    nome_arquivo,
    nome_aba
):

    """
    Abre uma aba do Excel e procura
    blocos contendo:

    PROFISSIONAL + CRM

    Depois coleta os profissionais
    e os dados de produção.
    """

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

                "Situação":
                    "Aba vazia"
            }
        )


    # --------------------------------------------------------
    # LOCALIZAR TODOS OS CABEÇALHOS
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


        colunas_producao = localizar_colunas_producao(
            cabecalho
        )


        if (
            coluna_profissional is None
            or coluna_crm is None
        ):

            continue


        # ----------------------------------------------------
        # DEFINIR ONDE O BLOCO TERMINA
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
        # LER AS LINHAS DE PROFISSIONAIS
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
            # PRODUÇÃO DA LINHA
            # ------------------------------------------------

            producao = {}


            for campo, numero_coluna in colunas_producao.items():


                if numero_coluna is None:

                    producao[
                        campo
                    ] = 0.0


                else:

                    valor = planilha.iat[

                        numero_linha,

                        numero_coluna
                    ]


                    producao[
                        campo
                    ] = converter_numero(
                        valor
                    )


            # ------------------------------------------------
            # REGISTRO FINAL
            # ------------------------------------------------

            registros.append(

                {

                    "Profissional":
                        str(nome).strip(),

                    "CRM":
                        limpar_crm(crm),

                    "CRM_ID":
                        chave_crm(crm),

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

        "Situação":
            (
                "OK"
                if len(cabecalhos) > 0
                else "Cabeçalho não reconhecido"
            )
    }


    return (
        dados,
        diagnostico
    )


# ============================================================
# BLOCO 11 - SUGESTÃO DE ABA
# ============================================================

def sugerir_abas(
    nomes_abas,
    competencia_inicial,
    competencia_final
):

    """
    Quando o arquivo possui várias abas,
    tenta sugerir qual deve ser analisada.

    O usuário continua podendo alterar
    manualmente.
    """

    if len(nomes_abas) == 1:

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
# BLOCO 12 - PROCESSAMENTO DO RELATÓRIO
# ============================================================

def processar_relatorio(
    arquivo_bytes,
    nome_arquivo,
    abas
):

    """
    Processa todas as abas escolhidas.
    """

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
# BLOCO 13 - CONTAGEM DOS PROFISSIONAIS
# ============================================================

def contar_profissionais_unicos(
    dados
):

    """
    Conta profissionais utilizando
    CRM como identificação principal.
    """

    if dados.empty:

        return 0


    return dados[
        "CRM_ID"
    ].nunique()


# ============================================================
# BLOCO 14 - CRM COM MAIS DE UM LANÇAMENTO
# ============================================================

def localizar_crms_com_varios_lancamentos(
    dados
):

    """
    Identifica CRMs presentes em mais
    de uma linha.

    IMPORTANTE:

    isso não significa automaticamente
    que exista duplicidade.
    """

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

            dados["CRM_ID"]
            == crm_id
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
                    ]["CRM"],

                "Quantidade de lançamentos":
                    int(quantidade),

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
# BLOCO 15 - FORMATAÇÃO DE VALORES
# ============================================================

def formatar_moeda(valor):

    """
    Transforma:

    1250.50

    em:

    R$ 1.250,50
    """

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


# ============================================================
# BLOCO 16 - MOSTRAR ANÁLISE
# ============================================================

def mostrar_analise(
    dados,
    diagnostico
):

    """
    Exibe os resultados encontrados
    no relatório.
    """

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


    # --------------------------------------------------------
    # PROFISSIONAIS
    # --------------------------------------------------------

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
        "Profissionais únicos = quantidade de CRMs diferentes. "
        "Lançamentos = quantidade de linhas válidas encontradas."
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


    # --------------------------------------------------------
    # REGRA DO FATURAMENTO
    # --------------------------------------------------------

    consultas_faturamento = (

        consultas

        + procedimentos

        + exames

        + interconsultas
    )


    linha1 = st.columns(
        4
    )


    linha1[0].metric(
        "Plantões",
        f"{plantoes:,.0f}"
    )


    linha1[1].metric(
        "Consultas",
        f"{consultas:,.0f}"
    )


    linha1[2].metric(
        "Procedimentos",
        f"{procedimentos:,.0f}"
    )


    linha1[3].metric(
        "Exames",
        f"{exames:,.0f}"
    )


    linha2 = st.columns(
        4
    )


    linha2[0].metric(
        "Interconsultas",
        f"{interconsultas:,.0f}"
    )


    linha2[1].metric(
        "Pacotes",
        f"{pacotes:,.0f}"
    )


    linha2[2].metric(
        "Horas",
        f"{horas:,.2f}"
    )


    linha2[3].metric(
        "Consultas p/ faturamento",
        f"{consultas_faturamento:,.0f}"
    )


    st.metric(
        "💰 Valor total encontrado",
        formatar_moeda(
            valor_total
        )
    )


    st.caption(
        "Consultas para faturamento = "
        "consultas + procedimentos + exames + interconsultas."
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


    tabela_visualizacao = dados[
        colunas_exibicao
    ].copy()


    st.dataframe(

        tabela_visualizacao,

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
            "Isso não significa automaticamente que exista duplicidade."
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
# BLOCO 17 - CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(

    page_title=NOME_SISTEMA,

    page_icon="📊",

    layout="wide"
)


# ============================================================
# BLOCO 18 - MENU LATERAL
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


    colunas[0].metric(
        "⏳ Pendentes",
        "0"
    )


    colunas[1].metric(
        "✅ Validados",
        "0"
    )


    colunas[2].metric(
        "⚠️ Com alerta",
        "0"
    )


    colunas[3].metric(
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
        "Nesta área serão consultadas "
        "as tabelas oficiais utilizadas "
        "para conferência."
    )


# ============================================================
# PÁGINA - NOVO RELATÓRIO
# ============================================================

elif pagina == "📤 Novo relatório":


    st.title(
        "📤 Novo relatório"
    )


    st.write(
        "Preencha os dados e envie "
        "o relatório que será analisado."
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

        placeholder="Nome de quem está enviando"
    )


    # --------------------------------------------------------
    # PERÍODO
    # --------------------------------------------------------

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


    # Calculamos antes para que as variáveis
    # existam durante toda a página.

    competencia_inicial = data_inicial.strftime(
        "%m/%Y"
    )


    competencia_final = data_final.strftime(
        "%m/%Y"
    )


    # --------------------------------------------------------
    # CONFERÊNCIA DO PERÍODO
    # --------------------------------------------------------

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
                "Como não é possível identificar "
                "quanto foi executado em cada mês, "
                "o relatório será analisado "
                "integralmente considerando "
                "as duas tabelas de referência."
            )


        # ----------------------------------------------------
        # COMPETÊNCIA DO FATURAMENTO
        # ----------------------------------------------------

        st.subheader(
            " Competência do faturamento"
        )


        st.success(
            f"O relatório será lançado "
            f"integralmente em "
            f"{competencia_inicial}"
        )


    # --------------------------------------------------------
    # OBSERVAÇÕES
    # --------------------------------------------------------

    observacoes = st.text_area(

        "Outras informações / observações",

        placeholder="Campo opcional"
    )


    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

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
                "O sistema sugere uma aba. "
                "Você pode alterar a seleção."
            )


            # ------------------------------------------------
            # BOTÃO DE ANÁLISE
            # ------------------------------------------------

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


                    # ----------------------------------------
                    # GUARDAR RESULTADO TEMPORARIAMENTE
                    # ----------------------------------------

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
                        "data_inicial_relatorio"
                    ] = data_inicial


                    st.session_state[
                        "data_final_relatorio"
                    ] = data_final


                    st.session_state[
                        "periodo_relatorio"
                    ] = (

                        f"{data_inicial.strftime('%d/%m/%Y')} "

                        f"a "

                        f"{data_final.strftime('%d/%m/%Y')}"
                    )


                    st.session_state[
                        "competencia_inicial"
                    ] = competencia_inicial


                    st.session_state[
                        "competencia_final"
                    ] = competencia_final


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
                "Não foi possível abrir "
                "o arquivo Excel."
            )


            st.write(
                "Detalhes técnicos:"
            )


            st.code(
                str(erro)
            )


# ============================================================
# PÁGINA - ANÁLISE
# ============================================================

elif pagina == " Análise":


    st.title(
        " Análise"
    )


    if "dados_relatorio" not in st.session_state:


        st.info(
            "Primeiro envie e analise "
            "um relatório em 📤 Novo relatório."
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

elif pagina == " Divergências - Apontamentos":


    st.title(
        " Divergências"
    )


    st.write(
        "Nesta área aparecerão "
        "possíveis erros e itens "
        "que precisam de conferência."
    )


    st.info(
        "A auditoria de códigos e valores "
        "será adicionada na próxima etapa."
    )


# ============================================================
# PÁGINA - VALIDAÇÃO
# ============================================================

elif pagina == " Validação":


    st.title(
        " Validação"
    )


    st.write(
        "A validação humana será "
        "adicionada nas próximas etapas."
    )


# ============================================================
# PÁGINA - FATURAMENTO
# ============================================================

elif pagina == " Faturamento":


    st.title(
        " Faturamento"
    )


    st.write(
        "Aqui serão exibidos os "
        "relatórios já validados."
    )


# ============================================================
# PÁGINA - HISTÓRICO
# ============================================================

elif pagina == " Histórico":


    st.title(
        " Histórico"
    )


    st.write(
        "Aqui ficará registrado "
        "o histórico do sistema."
    )


# ============================================================
# PÁGINA - CONFIGURAÇÕES
# ============================================================

elif pagina == " Configurações":


    st.title(
        " Configurações"
    )


    st.write(
        f"Versão atual: {VERSAO}"
    )
