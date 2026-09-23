"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================

Versão: 1.2
Linguagem: Python

OBJETIVO:
Auxiliar na leitura, conferência, validação
e faturamento de relatórios de serviços médicos.
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
# BLOCO 2 - CONFIGURAÇÕES
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"

VERSAO = "1.2"


# ============================================================
# BLOCO 3 - FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(valor):

    """
    Padroniza um texto para facilitar comparações.

    Exemplo:

    "MÉDICO"
          ↓
    "medico"

    Isso evita que diferenças de acento,
    letras maiúsculas ou espaços atrapalhem a leitura.
    """

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
        r"\s+",
        " ",
        texto
    )

    return texto


# ============================================================
# BLOCO 4 - TRATAMENTO DO CRM
# ============================================================

def limpar_crm(valor):

    """
    Deixa o CRM em um formato mais fácil de visualizar.

    Exemplo:

    Excel:
    45576.0

    Sistema:
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

    if re.fullmatch(r"\d+\.0", texto):
        texto = texto[:-2]

    return texto


def chave_crm(valor):

    """
    Cria uma identificação interna para o CRM.

    Usamos somente os números para comparar.

    Exemplo:

    CRM 45576
    45576
    45.576

    Todos poderão ser reconhecidos como o mesmo CRM.
    """

    crm = limpar_crm(valor)

    numeros = re.sub(
        r"\D",
        "",
        crm
    )

    return numeros


def crm_valido(valor):

    """
    Verifica se o conteúdo parece realmente um CRM.

    Isso impede que palavras como:

    CRM
    TOTAL
    SOMA

    sejam contadas como profissionais.
    """

    numeros = chave_crm(valor)

    return 4 <= len(numeros) <= 10


# ============================================================
# BLOCO 5 - VALIDAÇÃO DO NOME DO PROFISSIONAL
# ============================================================

def profissional_valido(nome, crm):

    """
    Decide se uma linha realmente representa
    um profissional.

    Essa regra é importante porque as planilhas possuem
    linhas como:

    PROFISSIONAIS (NOME COMPLETO)
    SOMA
    VALOR TOTAL

    Essas linhas NÃO podem ser contadas como médicos.
    """

    nome_normalizado = normalizar_texto(nome)

    if not nome_normalizado:
        return False

    if len(nome_normalizado) < 4:
        return False

    palavras_invalidas = [
        "profissionais",
        "profissional",
        "soma",
        "valor total",
        "relatorio",
        "servicos medicos",
        "municipio",
        "competencia"
    ]

    for palavra in palavras_invalidas:

        if nome_normalizado.startswith(palavra):
            return False

    # O nome precisa possuir letras.
    if not re.search(
        r"[a-z]",
        nome_normalizado
    ):
        return False

    # Também exigimos um CRM válido.
    if not crm_valido(crm):
        return False

    return True


# ============================================================
# BLOCO 6 - IDENTIFICAÇÃO DO CABEÇALHO
# ============================================================

def linha_e_cabecalho(linha):

    """
    Procura uma linha que contenha ao mesmo tempo:

    PROFISSIONAL
    +
    CRM

    Essa é uma das formas de identificar onde começa
    uma tabela de profissionais.
    """

    encontrou_profissional = False

    encontrou_crm = False

    for valor in linha:

        texto = normalizar_texto(valor)

        if "profission" in texto:
            encontrou_profissional = True

        if texto == "crm" or texto.startswith("crm "):
            encontrou_crm = True

    return (
        encontrou_profissional
        and encontrou_crm
    )


def localizar_coluna_profissional(linha):

    """
    Descobre em qual coluna está o nome do profissional.
    """

    for numero_coluna, valor in enumerate(linha):

        if "profission" in normalizar_texto(valor):
            return numero_coluna

    return None


def localizar_coluna_crm(linha):

    """
    Descobre em qual coluna está o CRM.
    """

    for numero_coluna, valor in enumerate(linha):

        texto = normalizar_texto(valor)

        if texto == "crm" or texto.startswith("crm "):
            return numero_coluna

    return None


# ============================================================
# BLOCO 7 - LEITURA DE UMA ABA DO EXCEL
# ============================================================

def ler_profissionais_da_aba(
    arquivo_bytes,
    nome_arquivo,
    nome_aba
):

    """
    Esta função abre uma aba da planilha e procura
    todos os blocos que possuam:

    PROFISSIONAL + CRM

    Depois coleta somente as linhas consideradas válidas.
    """

    planilha = pd.read_excel(
        io.BytesIO(arquivo_bytes),
        sheet_name=nome_aba,
        header=None,
        dtype=object
    )

    if planilha.empty:

        return (
            pd.DataFrame(),
            {
                "Aba": nome_aba,
                "Cabeçalhos encontrados": 0,
                "Lançamentos válidos": 0,
                "Situação": "Aba vazia"
            }
        )


    # --------------------------------------------------------
    # PROCURAR TODOS OS CABEÇALHOS
    # --------------------------------------------------------

    cabecalhos = []

    for numero_linha in range(len(planilha)):

        linha = planilha.iloc[
            numero_linha
        ].tolist()

        if linha_e_cabecalho(linha):

            cabecalhos.append(
                numero_linha
            )


    registros = []


    # --------------------------------------------------------
    # LER CADA BLOCO ENCONTRADO
    # --------------------------------------------------------

    for posicao, linha_cabecalho in enumerate(cabecalhos):

        cabecalho = planilha.iloc[
            linha_cabecalho
        ].tolist()


        coluna_profissional = localizar_coluna_profissional(
            cabecalho
        )

        coluna_crm = localizar_coluna_crm(
            cabecalho
        )


        if (
            coluna_profissional is None
            or coluna_crm is None
        ):
            continue


        # Se existir outro cabeçalho abaixo,
        # ele marca o fim deste bloco.
        if posicao + 1 < len(cabecalhos):

            linha_final = cabecalhos[
                posicao + 1
            ]

        else:

            linha_final = len(planilha)


        # ----------------------------------------------------
        # ANALISAR AS LINHAS DO BLOCO
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


            registros.append(
                {
                    "Profissional": str(nome).strip(),

                    "CRM": limpar_crm(crm),

                    "CRM_ID": chave_crm(crm),

                    "Arquivo": nome_arquivo,

                    "Aba": nome_aba,

                    "Linha do Excel": numero_linha + 1
                }
            )


    dados = pd.DataFrame(
        registros
    )


    diagnostico = {

        "Aba": nome_aba,

        "Cabeçalhos encontrados": len(cabecalhos),

        "Lançamentos válidos": len(dados),

        "Situação":
            "OK"
            if len(cabecalhos) > 0
            else "Cabeçalho não reconhecido"
    }


    return (
        dados,
        diagnostico
    )


# ============================================================
# BLOCO 8 - SUGESTÃO DE ABA
# ============================================================

def sugerir_abas(
    nomes_abas,
    competencia_inicial,
    competencia_final
):

    """
    Quando o Excel possui muitas abas,
    o sistema tenta sugerir uma aba relacionada
    à competência escolhida.

    O usuário continua podendo trocar manualmente.
    """

    if len(nomes_abas) == 1:
        return nomes_abas


    mes_inicial = competencia_inicial[:2]

    mes_final = competencia_final[:2]


    candidatos = []


    for aba in nomes_abas:

        texto = normalizar_texto(aba)


        if (
            mes_inicial in texto
            or mes_final in texto
        ):

            candidatos.append(
                aba
            )


    if candidatos:

        # Evitamos selecionar muitas abas automaticamente.
        return [
            candidatos[-1]
        ]


    # Se não souber qual escolher,
    # sugere a primeira aba que não seja MODELO.
    for aba in nomes_abas:

        if normalizar_texto(aba) != "modelo":
            return [aba]


    return [nomes_abas[0]]


# ============================================================
# BLOCO 9 - PROCESSAMENTO DAS ABAS ESCOLHIDAS
# ============================================================

def processar_relatorio(
    arquivo_bytes,
    nome_arquivo,
    abas
):

    """
    Processa todas as abas escolhidas pelo usuário.
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
                    "Aba": aba,

                    "Cabeçalhos encontrados": 0,

                    "Lançamentos válidos": 0,

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
        pd.DataFrame(diagnosticos)
    )


# ============================================================
# BLOCO 10 - PROFISSIONAIS ÚNICOS
# ============================================================

def contar_profissionais_unicos(dados):

    """
    Conta CRMs únicos.

    IMPORTANTE:

    Um CRM pode aparecer em duas ou mais linhas
    por atividades ou funções diferentes.

    Nesse caso:

    1 CRM
    =
    1 profissional

    mas podem existir vários lançamentos.
    """

    if dados.empty:
        return 0

    return dados[
        "CRM_ID"
    ].nunique()


# ============================================================
# BLOCO 11 - CRMs COM MAIS DE UM LANÇAMENTO
# ============================================================

def localizar_crms_com_varios_lancamentos(dados):

    """
    Mostra CRMs que aparecem em mais de uma linha.

    Isso NÃO significa necessariamente duplicidade.

    O mesmo profissional pode possuir atividades
    diferentes dentro do relatório.
    """

    if dados.empty:
        return pd.DataFrame()


    contagem = (
        dados
        .groupby("CRM_ID")
        .size()
    )


    repetidos = contagem[
        contagem > 1
    ]


    resultado = []


    for crm_id, quantidade in repetidos.items():

        grupo = dados[
            dados["CRM_ID"] == crm_id
        ]


        nomes = list(
            dict.fromkeys(
                grupo["Profissional"].tolist()
            )
        )


        resultado.append(
            {
                "CRM": grupo.iloc[0]["CRM"],

                "Quantidade de lançamentos":
                    int(quantidade),

                "Nome(s) encontrado(s)":
                    " | ".join(nomes)
            }
        )


    return pd.DataFrame(
        resultado
    )


# ============================================================
# BLOCO 12 - MOSTRAR RESULTADO DA ANÁLISE
# ============================================================

def mostrar_analise(dados, diagnostico):

    """
    Monta a tela com o resultado da leitura.
    """

    if dados is None or dados.empty:

        st.error(
            "Nenhum profissional válido foi identificado."
        )

        st.write(
            "Veja o diagnóstico abaixo para descobrir "
            "se alguma aba ou cabeçalho não foi reconhecido."
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


    coluna1, coluna2 = st.columns(2)


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
    # TABELA DE PROFISSIONAIS
    # --------------------------------------------------------

    st.subheader(
        "Profissionais encontrados"
    )


    tabela_visualizacao = dados[
        [
            "Profissional",
            "CRM",
            "Aba",
            "Linha do Excel"
        ]
    ].copy()


    st.dataframe(
        tabela_visualizacao,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # CRM EM MAIS DE UMA LINHA
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
# BLOCO 13 - CONFIGURAÇÃO VISUAL
# ============================================================

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# BLOCO 14 - MENU
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
# PÁGINA - TABELAS
# ============================================================

elif pagina == "📋 Tabelas de referência":

    st.title(
        "📋 Tabelas de referência"
    )


    st.write(
        "Nesta área serão consultadas as "
        "tabelas oficiais de referência."
    )


# ============================================================
# PÁGINA - NOVO RELATÓRIO
# ============================================================

elif pagina == "📤 Novo relatório":

    st.title(
        "📤 Novo relatório"
    )


    municipio = st.text_input(
        "Município",
        placeholder="Ex.: Brumadinho"
    )


    responsavel = st.text_input(
        "Responsável pelo preenchimento",
        placeholder="Nome de quem está enviando"
    )


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
    # COMPETÊNCIAS
    # --------------------------------------------------------

    if data_final < data_inicial:

        st.error(
            "A data final não pode ser anterior "
            "à data inicial."
        )


    else:

        competencia_inicial = data_inicial.strftime(
            "%m/%Y"
        )


        competencia_final = data_final.strftime(
            "%m/%Y"
        )


        if competencia_inicial == competencia_final:

            st.success(
                f"✅ Competência: "
                f"{competencia_inicial}"
            )


        else:

            st.warning(
                "⚠️ Relatório com duas competências"
            )


            st.write(
                f"**Competências:** "
                f"{competencia_inicial} + "
                f"{competencia_final}"
            )


            st.info(
                "A produção será analisada integralmente "
                "contra as duas tabelas, sem divisão "
                "artificial entre os meses."
            )


        st.success(
            f"💰 Competência do faturamento: "
            f"{competencia_inicial}"
        )


    observacoes = st.text_area(
        "Outras informações / observações"
    )


    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    st.subheader(
        "📎 Relatório Excel"
    )


    arquivo = st.file_uploader(
        "Selecione o relatório",
        type=["xlsx"]
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
                "🔍 Ler profissionais e CRMs",
                type="primary"
            ):


                if not abas_escolhidas:

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


                    # Guardamos o resultado para a tela ANÁLISE.
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
                        "✅ Leitura concluída."
                    )


                    mostrar_analise(
                        dados,
                        diagnostico
                    )


        except Exception as erro:

            st.error(
                "Não foi possível abrir o arquivo Excel."
            )


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
            "Primeiro envie e leia um relatório "
            "na opção 📤 Novo relatório."
        )


    else:

        municipio_salvo = st.session_state.get(
            "municipio_relatorio",
            ""
        )


        periodo_salvo = st.session_state.get(
            "periodo_relatorio",
            ""
        )


        competencia_salva = st.session_state.get(
            "competencia_faturamento",
            ""
        )


        st.write(
            f"**Município:** "
            f"{municipio_salvo or 'Não informado'}"
        )


        st.write(
            f"**Período:** "
            f"{periodo_salvo}"
        )


        st.write(
            f"**Competência do faturamento:** "
            f"{competencia_salva}"
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
        "Nesta área ficarão os possíveis erros "
        "e situações que exigem conferência."
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
        "Aqui ficarão os relatórios já validados "
        "e preparados para faturamento."
    )


# ============================================================
# PÁGINA - HISTÓRICO
# ============================================================

elif pagina == "📚 Histórico":

    st.title(
        "📚 Histórico"
    )


    st.write(
        "Aqui ficará registrado o histórico "
        "de análises e validações."
    )


# ============================================================
# PÁGINA - CONFIGURAÇÕES
# ============================================================

elif pagina == "⚙️ Configurações":

    st.title(
        "⚙️ Configurações"
    )


    st.write(
        f"Versão atual do sistema: {VERSAO}"
    )
