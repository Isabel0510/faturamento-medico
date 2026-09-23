import io
import re
import unicodedata
from datetime import date

import pandas as pd
import pdfplumber
import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"

VERSAO = "1.8"

URL_ICISMEP = (
    "https://icismep.mg.gov.br/"
    "tabela-de-servicos-medicos-nos-municipios-entes-nao-consorciados/"
)


st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# FUNÇÕES BÁSICAS
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


def converter_numero(valor):

    if valor is None:
        return 0.0

    if isinstance(valor, float) and pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    texto = texto.replace(
        "R$",
        ""
    )

    texto = texto.replace(
        " ",
        ""
    )

    if texto == "":
        return 0.0

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

        return float(texto)

    except Exception:

        return 0.0


def formatar_moeda(valor):

    if valor is None:
        return "—"

    if isinstance(valor, float) and pd.isna(valor):
        return "—"

    texto = f"{float(valor):,.2f}"

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

    texto = f"{float(valor):,.{casas}f}"

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


def normalizar_codigo(valor):

    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    if isinstance(valor, (int, float)):

        if float(valor).is_integer():

            return str(
                int(valor)
            )

    texto = str(valor).strip().upper()

    texto = texto.replace(
        " ",
        ""
    )

    if re.fullmatch(
        r"\d+[\.,]0",
        texto
    ):

        texto = texto[:-2]

    return texto


def competencia_valida(texto):

    return bool(

        re.fullmatch(
            r"(0[1-9]|1[0-2])/\d{4}",
            str(texto).strip()
        )
    )


def competencias_do_periodo(
    data_inicial,
    data_final
):

    inicio = pd.Period(
        data_inicial,
        freq="M"
    )

    fim = pd.Period(
        data_final,
        freq="M"
    )

    periodos = pd.period_range(
        inicio,
        fim,
        freq="M"
    )

    return [

        periodo.strftime(
            "%m/%Y"
        )

        for periodo in periodos
    ]


def proximo(
    valor1,
    valor2,
    tolerancia=0.02
):

    return (

        abs(
            float(valor1)
            - float(valor2)
        )

        <= tolerancia
    )


# ============================================================
# CRM
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

    texto = str(valor).strip()

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
        limpar_crm(
            valor
        )
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
# PROFISSIONAL
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

    invalidos = [

        "profissionais",

        "profissional",

        "nome completo",

        "soma",

        "total",

        "valor total",

        "relatorio",

        "servicos medicos",

        "municipio",

        "competencia",

        "consolidado"
    ]

    for termo in invalidos:

        if nome_normalizado.startswith(
            normalizar_texto(
                termo
            )
        ):

            return False

    if not re.search(
        r"[a-z]",
        nome_normalizado
    ):

        return False

    return crm_valido(
        crm
    )


# ============================================================
# CABEÇALHO PRINCIPAL
# ============================================================

def linha_e_cabecalho(linha):

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


def localizar_coluna_exata(
    linha,
    nomes
):

    nomes_normalizados = {

        normalizar_texto(
            nome
        )

        for nome in nomes
    }

    for numero_coluna, valor in enumerate(
        linha
    ):

        if normalizar_texto(
            valor
        ) in nomes_normalizados:

            return numero_coluna

    return None


# ============================================================
# MODELO GENÉRICO
# ============================================================

def localizar_colunas_modelo_generico(
    cabecalho
):

    return {

        "codigo":

            localizar_coluna_exata(

                cabecalho,

                [
                    "cod do vinculo",
                    "codigo do vinculo",
                    "cod vinculo",
                    "codigo",
                    "cod"
                ]
            ),

        "servico":

            localizar_coluna_exata(

                cabecalho,

                [
                    "vinculo contratual utilizado",
                    "vinculo contratual",
                    "servico",
                    "atividade"
                ]
            ),

        "unidade":

            localizar_coluna_exata(

                cabecalho,

                [
                    "unidade de medida",
                    "unid de medida"
                ]
            ),

        "quantidade":

            localizar_coluna_exata(

                cabecalho,

                [
                    "quant",
                    "quantidade",
                    "qtd"
                ]
            ),

        "valor_unitario":

            localizar_coluna_exata(

                cabecalho,

                [
                    "valor unit",
                    "valor unitario",
                    "valor da unidade"
                ]
            ),

        "valor_bruto":

            localizar_coluna_exata(

                cabecalho,

                [
                    "valor total",
                    "valor bruto",
                    "total bruto"
                ]
            ),

        "valor_final":

            localizar_coluna_exata(

                cabecalho,

                [
                    "valor total final",
                    "valor liquido",
                    "valor final"
                ]
            )
    }


# ============================================================
# CLASSIFICAÇÃO DE PRODUÇÃO
# ============================================================

def classificar_unidade_medida(
    valor
):

    texto = normalizar_texto(
        valor
    )

    if "interconsulta" in texto:
        return "Interconsultas"

    if "pacote" in texto:
        return "Pacotes"

    if "plantao" in texto:
        return "Plantoes"

    if "procedimento" in texto:
        return "Procedimentos"

    if "exame" in texto:
        return "Exames"

    if "consulta" in texto:
        return "Consultas"

    if (
        texto == "hora"
        or "horas" in texto
        or texto.startswith(
            "hora "
        )
    ):

        return "Horas"

    return None


def unidade_por_campo(campo):

    mapa = {

        "Plantoes":
            "PLANTÃO",

        "Consultas":
            "CONSULTA",

        "Procedimentos":
            "PROCEDIMENTO",

        "Exames":
            "EXAME",

        "Interconsultas":
            "INTERCONSULTA",

        "Pacotes":
            "PACOTE",

        "Horas":
            "HORA"
    }

    return mapa.get(
        campo,
        ""
    )


# ============================================================
# LOCALIZAR PRODUÇÃO EM VÁRIAS LINHAS
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

        "Valor bruto": [],

        "Valor final": []
    }

    linha_final = min(
        linha_cabecalho + 6,
        len(planilha)
    )

    for numero_coluna in range(
        planilha.shape[1]
    ):

        textos = []

        for numero_linha in range(
            linha_cabecalho,
            linha_final
        ):

            textos.append(

                normalizar_texto(

                    planilha.iat[
                        numero_linha,
                        numero_coluna
                    ]
                )
            )

        for texto in textos:

            if not texto:
                continue

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

            if (
                "quant de pacote" in texto
                or "quant pacote" in texto
                or "qtd pacote" in texto
                or "pacote de consulta" in texto
                or "pacote consultas" in texto
                or texto == "pacotes"
            ):

                resultado[
                    "Pacotes"
                ].append(
                    numero_coluna
                )

            if (

                (
                    "quant de consulta" in texto
                    or "quant consulta" in texto
                    or "qtd consulta" in texto
                    or texto == "consultas"
                )

                and "interconsulta" not in texto

                and "pacote" not in texto
            ):

                resultado[
                    "Consultas"
                ].append(
                    numero_coluna
                )

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

            if (

                "valor da hora" in texto

                or "valor do plantao" in texto

                or "valor da consulta" in texto

                or "valor consulta" in texto

                or "valor do procedimento" in texto

                or "valor procedimento" in texto

                or "valor do exame" in texto

                or "valor da interconsulta" in texto

                or "valor do pacote" in texto

                or texto == "valor unit"

                or texto == "valor unitario"
            ):

                resultado[
                    "Valor unitario"
                ].append(
                    numero_coluna
                )

            if texto in [

                "valor total final",

                "valor final",

                "valor liquido"
            ]:

                resultado[
                    "Valor final"
                ].append(
                    numero_coluna
                )

            elif texto in [

                "valor total",

                "valor bruto",

                "total bruto"
            ]:

                resultado[
                    "Valor bruto"
                ].append(
                    numero_coluna
                )

    for campo in resultado:

        resultado[campo] = list(

            dict.fromkeys(

                resultado[
                    campo
                ]
            )
        )

    return resultado


# ============================================================
# NOVO - IDENTIFICA CÓDIGO NO TÍTULO
# ============================================================

def extrair_codigo_servico_titulo(valor):

    """
    Exemplos:

    50. VIDEOLARINGOSCOPIA
    51. LARINGOSCOPIA
    52. ULTRASSONOGRAFIA TRANSFONTANELA

    Resultado:

    Código + nome do serviço
    """

    if valor is None:
        return "", ""

    if isinstance(valor, float) and pd.isna(valor):
        return "", ""

    texto = str(
        valor
    ).strip()

    padroes = [

        r"^\s*(\d+(?:[\.,]\d+)?)\s*[\.\-\)]\s*(.+?)\s*$",

        r"^\s*(\d{1,4})\s+([A-Za-zÀ-ÿ].+?)\s*$"
    ]

    for padrao in padroes:

        resultado = re.match(
            padrao,
            texto
        )

        if resultado:

            codigo = normalizar_codigo(
                resultado.group(1)
            )

            servico = resultado.group(
                2
            ).strip()

            if re.search(
                r"[A-Za-zÀ-ÿ]",
                servico
            ):

                return (
                    codigo,
                    servico
                )

    return "", ""


def localizar_titulo_atividade(
    planilha,
    linha_cabecalho,
    coluna_quantidade
):

    """
    Procura o código da atividade
    acima da coluna de quantidade.

    Também olha até duas colunas
    para a esquerda por causa
    das células mescladas do Excel.
    """

    inicio_linha = max(
        0,
        linha_cabecalho - 4
    )

    fim_linha = min(
        len(planilha),
        linha_cabecalho + 5
    )

    colunas = [

        coluna_quantidade,

        coluna_quantidade - 1,

        coluna_quantidade - 2
    ]

    for numero_coluna in colunas:

        if numero_coluna < 0:
            continue

        if numero_coluna >= planilha.shape[1]:
            continue

        for numero_linha in range(

            inicio_linha,

            fim_linha
        ):

            codigo, servico = extrair_codigo_servico_titulo(

                planilha.iat[

                    numero_linha,

                    numero_coluna
                ]
            )

            if codigo:

                return (
                    codigo,
                    servico
                )

    return "", ""


def encontrar_coluna_valor_associada(
    planilha,
    linha_cabecalho,
    coluna_quantidade
):

    """
    Normalmente:

    QUANTIDADE | VALOR

    Então procura o valor
    à direita da quantidade.
    """

    linha_final = min(

        len(planilha),

        linha_cabecalho + 6
    )

    for numero_coluna in [

        coluna_quantidade + 1,

        coluna_quantidade + 2
    ]:

        if numero_coluna >= planilha.shape[1]:
            continue

        for numero_linha in range(

            linha_cabecalho,

            linha_final
        ):

            texto = normalizar_texto(

                planilha.iat[

                    numero_linha,

                    numero_coluna
                ]
            )

            if (

                texto.startswith(
                    "valor "
                )

                or texto in [

                    "valor",

                    "valor unit",

                    "valor unitario"
                ]
            ):

                return numero_coluna

    return None


# ============================================================
# CRIA LANÇAMENTOS SEPARADOS POR CÓDIGO
# ============================================================

def extrair_atividades_largas(

    planilha,

    numero_linha,

    linha_cabecalho,

    colunas_producao,

    nome,

    crm,

    nome_arquivo,

    nome_aba
):

    atividades = []

    campos = [

        "Plantoes",

        "Consultas",

        "Procedimentos",

        "Exames",

        "Interconsultas",

        "Pacotes",

        "Horas"
    ]

    for campo in campos:

        for coluna_quantidade in colunas_producao[
            campo
        ]:

            quantidade = converter_numero(

                planilha.iat[

                    numero_linha,

                    coluna_quantidade
                ]
            )

            # Só cria lançamento
            # quando houve produção.
            if quantidade == 0:
                continue

            codigo, servico = localizar_titulo_atividade(

                planilha,

                linha_cabecalho,

                coluna_quantidade
            )

            coluna_valor = encontrar_coluna_valor_associada(

                planilha,

                linha_cabecalho,

                coluna_quantidade
            )

            valor_unitario = 0.0

            if coluna_valor is not None:

                valor_unitario = converter_numero(

                    planilha.iat[

                        numero_linha,

                        coluna_valor
                    ]
                )

            atividades.append(

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

                    "Codigo":
                        codigo,

                    "Servico":
                        servico,

                    "Tipo":
                        campo,

                    "Unidade de medida":
                        unidade_por_campo(
                            campo
                        ),

                    "Quantidade":
                        quantidade,

                    "Valor unitario":
                        valor_unitario,

                    "Valor bruto":
                        0.0,

                    "Valor final":
                        0.0,

                    "Arquivo":
                        nome_arquivo,

                    "Aba":
                        nome_aba,

                    "Linha do Excel":
                        numero_linha + 1
                }
            )

    return atividades


# ============================================================
# LEITURA DE UMA ABA
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

            pd.DataFrame(),

            {

                "Aba":
                    nome_aba,

                "Cabeçalhos encontrados":
                    0,

                "Lançamentos válidos":
                    0,

                "Atividades por código":
                    0,

                "Códigos reconhecidos":
                    0,

                "Colunas de horas":
                    0,

                "Situação":
                    "Aba vazia"
            }
        )

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

    atividades = []

    colunas_horas_encontradas = set()

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

        if (
            coluna_profissional is None
            or coluna_crm is None
        ):

            continue

        colunas_producao = localizar_colunas_producao_multilinha(

            planilha,

            linha_cabecalho
        )

        colunas_genericas = localizar_colunas_modelo_generico(
            cabecalho
        )

        colunas_horas_encontradas.update(

            colunas_producao[
                "Horas"
            ]
        )

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

            producao = {

                "Plantoes":
                    0.0,

                "Consultas":
                    0.0,

                "Procedimentos":
                    0.0,

                "Exames":
                    0.0,

                "Interconsultas":
                    0.0,

                "Pacotes":
                    0.0,

                "Horas":
                    0.0
            }

            # =================================================
            # MODELO LARGO
            # =================================================

            for campo in producao:

                for numero_coluna in colunas_producao[
                    campo
                ]:

                    producao[
                        campo
                    ] += converter_numero(

                        planilha.iat[

                            numero_linha,

                            numero_coluna
                        ]
                    )

            # =================================================
            # NOVO:
            # cria lançamento separado para cada código
            # =================================================

            atividades_largas = extrair_atividades_largas(

                planilha,

                numero_linha,

                linha_cabecalho,

                colunas_producao,

                nome,

                crm,

                nome_arquivo,

                nome_aba
            )

            atividades.extend(
                atividades_largas
            )

            # =================================================
            # MODELO GENÉRICO
            # =================================================

            codigo = ""

            servico = ""

            unidade_medida = ""

            quantidade_generica = 0.0

            if colunas_genericas[
                "codigo"
            ] is not None:

                codigo = planilha.iat[

                    numero_linha,

                    colunas_genericas[
                        "codigo"
                    ]
                ]

            if colunas_genericas[
                "servico"
            ] is not None:

                servico = planilha.iat[

                    numero_linha,

                    colunas_genericas[
                        "servico"
                    ]
                ]

            if colunas_genericas[
                "unidade"
            ] is not None:

                unidade_medida = planilha.iat[

                    numero_linha,

                    colunas_genericas[
                        "unidade"
                    ]
                ]

            if colunas_genericas[
                "quantidade"
            ] is not None:

                quantidade_generica = converter_numero(

                    planilha.iat[

                        numero_linha,

                        colunas_genericas[
                            "quantidade"
                        ]
                    ]
                )

            categoria = classificar_unidade_medida(
                unidade_medida
            )

            if (
                categoria is not None
                and quantidade_generica != 0
            ):

                producao[
                    categoria
                ] += quantidade_generica

            # VALOR UNITÁRIO

            valor_unitario = 0.0

            if colunas_genericas[
                "valor_unitario"
            ] is not None:

                valor_unitario = converter_numero(

                    planilha.iat[

                        numero_linha,

                        colunas_genericas[
                            "valor_unitario"
                        ]
                    ]
                )

            # VALOR BRUTO

            valor_bruto = 0.0

            if colunas_genericas[
                "valor_bruto"
            ] is not None:

                valor_bruto = converter_numero(

                    planilha.iat[

                        numero_linha,

                        colunas_genericas[
                            "valor_bruto"
                        ]
                    ]
                )

            # VALOR FINAL

            valor_final = 0.0

            if colunas_genericas[
                "valor_final"
            ] is not None:

                valor_final = converter_numero(

                    planilha.iat[

                        numero_linha,

                        colunas_genericas[
                            "valor_final"
                        ]
                    ]
                )

            codigo_generico = (

                ""

                if pd.isna(
                    codigo
                )

                else normalizar_codigo(
                    codigo
                )
            )

            servico_generico = (

                ""

                if pd.isna(
                    servico
                )

                else str(
                    servico
                ).strip()
            )

            unidade_generica = (

                ""

                if pd.isna(
                    unidade_medida
                )

                else str(
                    unidade_medida
                ).strip()
            )

            # Modelo genérico também vira
            # uma atividade individual.
            if (

                quantidade_generica != 0

                and (

                    codigo_generico

                    or servico_generico

                    or categoria is not None
                )
            ):

                atividades.append(

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

                        "Codigo":
                            codigo_generico,

                        "Servico":
                            servico_generico,

                        "Tipo":
                            categoria or "",

                        "Unidade de medida":
                            unidade_generica,

                        "Quantidade":
                            quantidade_generica,

                        "Valor unitario":
                            valor_unitario,

                        "Valor bruto":
                            valor_bruto,

                        "Valor final":
                            valor_final,

                        "Arquivo":
                            nome_arquivo,

                        "Aba":
                            nome_aba,

                        "Linha do Excel":
                            numero_linha + 1
                    }
                )

            # =================================================
            # RESUMO DA LINHA DO PROFISSIONAL
            # =================================================

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

                    **producao,

                    "Valor bruto":
                        valor_bruto,

                    "Valor final":
                        valor_final
                }
            )

    dados = pd.DataFrame(
        registros
    )

    dados_atividades = pd.DataFrame(
        atividades
    )

    if not dados_atividades.empty:

        codigos_reconhecidos = int(

            dados_atividades[
                "Codigo"
            ]

            .astype(
                str
            )

            .str.strip()

            .ne(
                ""
            )

            .sum()
        )

    else:

        codigos_reconhecidos = 0

    diagnostico = {

        "Aba":
            nome_aba,

        "Cabeçalhos encontrados":
            len(
                cabecalhos
            ),

        "Lançamentos válidos":
            len(
                dados
            ),

        "Atividades por código":
            len(
                dados_atividades
            ),

        "Códigos reconhecidos":
            codigos_reconhecidos,

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

        dados_atividades,

        diagnostico
    )


# ============================================================
# ABAS
# ============================================================

def sugerir_abas(

    nomes_abas,

    competencia_inicial,

    competencia_final
):

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
# PROCESSAR RELATÓRIO
# ============================================================

def processar_relatorio(

    arquivo_bytes,

    nome_arquivo,

    abas
):

    tabelas_resumo = []

    tabelas_atividades = []

    diagnosticos = []

    for aba in abas:

        try:

            dados_aba, atividades_aba, diagnostico = ler_profissionais_da_aba(

                arquivo_bytes,

                nome_arquivo,

                aba
            )

            diagnosticos.append(
                diagnostico
            )

            if not dados_aba.empty:

                tabelas_resumo.append(
                    dados_aba
                )

            if not atividades_aba.empty:

                tabelas_atividades.append(
                    atividades_aba
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

                    "Atividades por código":
                        0,

                    "Códigos reconhecidos":
                        0,

                    "Colunas de horas":
                        0,

                    "Situação":
                        f"ERRO: {erro}"
                }
            )

    if tabelas_resumo:

        dados = pd.concat(

            tabelas_resumo,

            ignore_index=True
        )

    else:

        dados = pd.DataFrame()

    if tabelas_atividades:

        atividades = pd.concat(

            tabelas_atividades,

            ignore_index=True
        )

    else:

        atividades = pd.DataFrame()

    return (

        dados,

        atividades,

        pd.DataFrame(
            diagnosticos
        )
    )


# ============================================================
# TABELAS DE REFERÊNCIA
# ============================================================

def inferir_unidade_referencia(texto):

    texto = normalizar_texto(
        texto
    )

    if "interconsulta" in texto:
        return "INTERCONSULTA"

    if (
        "plantao" in texto
        and "12" in texto
    ):
        return "PLANTÃO 12H"

    if "plantao" in texto:
        return "PLANTÃO"

    if "procedimento" in texto:
        return "PROCEDIMENTO"

    if "consulta" in texto:
        return "CONSULTA"

    if "exame" in texto:
        return "EXAME"

    if "diaria" in texto:
        return "DIÁRIA"

    if "hora" in texto:
        return "HORA"

    if "mensal" in texto:
        return "MENSAL"

    if "mes" in texto:
        return "MÊS"

    return ""


def extrair_referencias_pdf(
    pdf_bytes
):

    registros = []

    with pdfplumber.open(

        io.BytesIO(
            pdf_bytes
        )

    ) as pdf:

        for pagina_numero, pagina in enumerate(

            pdf.pages,

            start=1
        ):

            texto = pagina.extract_text(

                x_tolerance=2,

                y_tolerance=2

            ) or ""

            for linha in texto.splitlines():

                resultado = re.match(

                    r"^\s*(\d+(?:[\.,]\d+)?)\s+"
                    r"(.+?)\s+"
                    r"R\$\s*([\d\.\s]+,\d{2})\s*$",

                    linha.strip(),

                    flags=re.IGNORECASE
                )

                if not resultado:
                    continue

                codigo = normalizar_codigo(
                    resultado.group(1)
                )

                descricao = resultado.group(
                    2
                ).strip()

                valor = converter_numero(
                    resultado.group(3)
                )

                if (
                    codigo
                    and valor > 0
                ):

                    registros.append(

                        {

                            "Codigo":
                                codigo,

                            "Descricao referencia":
                                descricao,

                            "Unidade referencia":
                                inferir_unidade_referencia(
                                    descricao
                                ),

                            "Valor oficial":
                                valor,

                            "Pagina PDF":
                                pagina_numero
                        }
                    )

    dados = pd.DataFrame(
        registros
    )

    if not dados.empty:

        dados = dados.drop_duplicates(

            subset=[

                "Codigo",

                "Unidade referencia",

                "Valor oficial"
            ],

            keep="last"
        )

        dados = dados.reset_index(
            drop=True
        )

    return dados


def cadastrar_tabela_referencia(

    dados_pdf,

    competencia,

    data_tabela,

    versao,

    arquivo_nome
):

    if dados_pdf.empty:

        return 0

    dados = dados_pdf.copy()

    versao_limpa = (

        versao.strip()

        or "Sem identificação"
    )

    data_texto = data_tabela.strftime(
        "%d/%m/%Y"
    )

    id_tabela = (

        f"{competencia}|"

        f"{data_texto}|"

        f"{versao_limpa}|"

        f"{arquivo_nome}"
    )

    dados[
        "Competencia"
    ] = competencia

    dados[
        "Data tabela"
    ] = data_texto

    dados[
        "Versao"
    ] = versao_limpa

    dados[
        "Arquivo de origem"
    ] = arquivo_nome

    dados[
        "ID tabela"
    ] = id_tabela

    atual = st.session_state.get(

        "tabelas_referencia",

        pd.DataFrame()

    ).copy()

    if (
        not atual.empty
        and "ID tabela" in atual.columns
    ):

        atual = atual[

            atual[
                "ID tabela"
            ] != id_tabela
        ]

    st.session_state[
        "tabelas_referencia"
    ] = pd.concat(

        [
            atual,
            dados
        ],

        ignore_index=True
    )

    return len(
        dados
    )


def tabelas_do_periodo(

    tabelas,

    data_inicial,

    data_final
):

    if (
        tabelas is None
        or tabelas.empty
    ):

        return pd.DataFrame()

    competencias = competencias_do_periodo(

        data_inicial,

        data_final
    )

    return tabelas[

        tabelas[
            "Competencia"
        ]

        .astype(
            str
        )

        .isin(
            competencias
        )

    ].copy()


def referencias_do_codigo(

    tabelas_periodo,

    codigo
):

    if (
        tabelas_periodo is None
        or tabelas_periodo.empty
        or not codigo
    ):

        return pd.DataFrame()

    codigo_normalizado = normalizar_codigo(
        codigo
    )

    return tabelas_periodo[

        tabelas_periodo[
            "Codigo"
        ]

        .astype(
            str
        )

        .apply(
            normalizar_codigo
        )

        .eq(
            codigo_normalizado
        )

    ].copy()


# ============================================================
# VALIDAÇÃO
# ============================================================

def valor_relatorio_confere(

    valor_unitario,

    valor_total,

    quantidade,

    valor_oficial
):

    confere_unitario = (

        valor_unitario > 0

        and proximo(

            valor_unitario,

            valor_oficial
        )
    )

    total_oficial = (

        quantidade
        * valor_oficial

        if quantidade > 0

        else None
    )

    confere_total = (

        total_oficial is not None

        and valor_total > 0

        and proximo(

            valor_total,

            total_oficial
        )
    )

    return (

        confere_unitario
        or confere_total,

        total_oficial
    )


def texto_referencias(
    referencias
):

    if referencias.empty:

        return ""

    partes = []

    referencias = referencias.sort_values(

        [

            "Competencia",

            "Data tabela",

            "Versao",

            "Valor oficial"
        ]
    )

    for _, referencia in referencias.iterrows():

        partes.append(

            f"{referencia['Competencia']} | "

            f"{referencia['Versao']} | "

            f"{referencia['Arquivo de origem']} | "

            f"{formatar_moeda(referencia['Valor oficial'])}"
        )

    return " ; ".join(

        dict.fromkeys(
            partes
        )
    )


def validar_relatorio_todas_tabelas(

    atividades,

    data_inicial,

    data_final,

    tabelas
):

    referencias_periodo = tabelas_do_periodo(

        tabelas,

        data_inicial,

        data_final
    )

    if not referencias_periodo.empty:

        ids_tabelas_periodo = set(

            referencias_periodo[
                "ID tabela"
            ]

            .dropna()

            .astype(
                str
            )

            .unique()
        )

    else:

        ids_tabelas_periodo = set()

    total_tabelas_periodo = len(
        ids_tabelas_periodo
    )

    resultados = []

    for _, linha in atividades.iterrows():

        codigo = normalizar_codigo(

            linha.get(
                "Codigo",
                ""
            )
        )

        quantidade = converter_numero(

            linha.get(
                "Quantidade",
                0
            )
        )

        valor_unitario = converter_numero(

            linha.get(
                "Valor unitario",
                0
            )
        )

        valor_bruto = converter_numero(

            linha.get(
                "Valor bruto",
                0
            )
        )

        status = "🟡 ATENÇÃO"

        motivo = ""

        referencias_texto = ""

        tabelas_com_codigo = 0

        tabelas_sem_codigo = total_tabelas_periodo

        valor_calculado = None

        diferenca = None

        # SEM TABELA

        if total_tabelas_periodo == 0:

            motivo = (

                "Nenhuma tabela de referência foi cadastrada "
                "para as competências do período."
            )

        # SEM CÓDIGO

        elif not codigo:

            motivo = (

                "A atividade foi identificada, mas o código "
                "do título não foi reconhecido. "
                "É necessária conferência manual."
            )

        else:

            referencias = referencias_do_codigo(

                referencias_periodo,

                codigo
            )

            referencias_texto = texto_referencias(
                referencias
            )

            if not referencias.empty:

                ids_com_codigo = set(

                    referencias[
                        "ID tabela"
                    ]

                    .dropna()

                    .astype(
                        str
                    )

                    .unique()
                )

            else:

                ids_com_codigo = set()

            tabelas_com_codigo = len(
                ids_com_codigo
            )

            tabelas_sem_codigo = (

                total_tabelas_periodo

                - tabelas_com_codigo
            )

            # CÓDIGO NÃO EXISTE

            if referencias.empty:

                status = "🔴 ERRO"

                motivo = (

                    "Código não encontrado em nenhuma "
                    "das tabelas cadastradas do período."
                )

            else:

                valores = sorted(

                    {

                        round(
                            float(valor),
                            2
                        )

                        for valor in referencias[
                            "Valor oficial"
                        ].tolist()
                    }
                )

                valores_que_conferem = []

                for valor in valores:

                    combina, _ = valor_relatorio_confere(

                        valor_unitario,

                        valor_bruto,

                        quantidade,

                        valor
                    )

                    if combina:

                        valores_que_conferem.append(
                            valor
                        )

                # NÃO APARECE EM TODAS

                if tabelas_sem_codigo > 0:

                    status = "🟡 ATENÇÃO"

                    motivo = (

                        "O código aparece em algumas tabelas "
                        "do período, mas não em todas. "
                        "É necessária validação humana."
                    )

                # MESMO VALOR EM TODAS

                elif len(valores) == 1:

                    oficial = valores[
                        0
                    ]

                    confere, valor_calculado = valor_relatorio_confere(

                        valor_unitario,

                        valor_bruto,

                        quantidade,

                        oficial
                    )

                    if confere:

                        status = "🟢 OK"

                        motivo = (

                            "O código está presente em todas as tabelas, "
                            "o valor oficial é igual em todas "
                            "e o relatório confere."
                        )

                    else:

                        status = "🔴 ERRO"

                        motivo = (

                            "O código está presente em todas as tabelas "
                            "e o valor oficial é igual, "
                            "mas o valor do relatório não confere."
                        )

                # VALORES DIFERENTES

                elif valores_que_conferem:

                    status = "🟡 ATENÇÃO"

                    motivo = (

                        "Existem valores oficiais diferentes entre "
                        "as tabelas do período. O relatório coincide "
                        "com pelo menos uma referência e exige "
                        "validação humana."
                    )

                else:

                    status = "🔴 ERRO"

                    motivo = (

                        "Existem valores oficiais diferentes entre "
                        "as tabelas do período e o valor do relatório "
                        "não coincide com nenhuma referência."
                    )

        if (
            valor_calculado is not None
            and valor_bruto > 0
        ):

            diferenca = (

                valor_bruto

                - valor_calculado
            )

        resultados.append(

            {

                "Status":
                    status,

                "Profissional":
                    linha.get(
                        "Profissional",
                        ""
                    ),

                "CRM":
                    linha.get(
                        "CRM",
                        ""
                    ),

                "Código":
                    codigo,

                "Serviço":
                    linha.get(
                        "Servico",
                        ""
                    ),

                "Tipo":
                    linha.get(
                        "Tipo",
                        ""
                    ),

                "Unidade relatório":
                    linha.get(
                        "Unidade de medida",
                        ""
                    ),

                "Quantidade":
                    quantidade,

                "Valor unitário relatório":
                    valor_unitario,

                "Valor bruto relatório":
                    valor_bruto,

                "Tabelas do período":
                    total_tabelas_periodo,

                "Tabelas com o código":
                    tabelas_com_codigo,

                "Tabelas sem o código":
                    tabelas_sem_codigo,

                "Referências encontradas":
                    referencias_texto,

                "Valor calculado oficial":
                    valor_calculado,

                "Diferença":
                    diferenca,

                "Motivo":
                    motivo,

                "Aba":
                    linha.get(
                        "Aba",
                        ""
                    ),

                "Linha do Excel":
                    linha.get(
                        "Linha do Excel",
                        ""
                    )
            }
        )

    return (

        pd.DataFrame(
            resultados
        ),

        referencias_periodo
    )


# ============================================================
# RESUMOS
# ============================================================

def contar_profissionais_unicos(
    dados
):

    if dados.empty:

        return 0

    return dados[
        "CRM_ID"
    ].nunique()


def localizar_crms_com_varios_lancamentos(
    dados
):

    if dados.empty:

        return pd.DataFrame()

    contagem = dados.groupby(
        "CRM_ID"
    ).size()

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
                    ]["CRM"],

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
# MOSTRAR ANÁLISE
# ============================================================

def mostrar_analise(

    dados,

    atividades,

    diagnostico
):

    if (
        dados is None
        or dados.empty
    ):

        st.error(
            "Nenhum profissional válido foi identificado."
        )

        if diagnostico is not None:

            st.dataframe(

                diagnostico,

                use_container_width=True,

                hide_index=True
            )

        return

    coluna1, coluna2 = st.columns(
        2
    )

    coluna1.metric(

        "👨‍⚕️ Profissionais únicos (CRM)",

        contar_profissionais_unicos(
            dados
        )
    )

    coluna2.metric(

        "📄 Lançamentos encontrados",

        len(
            dados
        )
    )

    # PRODUÇÃO

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

    valor_bruto = dados[
        "Valor bruto"
    ].sum()

    valor_final = dados[
        "Valor final"
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

    linha1[0].metric(
        "Plantões",
        formatar_numero(
            plantoes
        )
    )

    linha1[1].metric(
        "Consultas",
        formatar_numero(
            consultas
        )
    )

    linha1[2].metric(
        "Procedimentos",
        formatar_numero(
            procedimentos
        )
    )

    linha1[3].metric(
        "Exames",
        formatar_numero(
            exames
        )
    )

    linha2 = st.columns(
        4
    )

    linha2[0].metric(
        "Interconsultas",
        formatar_numero(
            interconsultas
        )
    )

    linha2[1].metric(
        "Pacotes",
        formatar_numero(
            pacotes
        )
    )

    linha2[2].metric(
        "Horas",
        formatar_numero(
            horas,
            2
        )
    )

    linha2[3].metric(
        "Consultas p/ faturamento",
        formatar_numero(
            consultas_faturamento
        )
    )

    linha3 = st.columns(
        2
    )

    linha3[0].metric(
        "💰 Valor bruto encontrado",
        formatar_moeda(
            valor_bruto
        )
    )

    linha3[1].metric(
        "💰 Valor final encontrado",

        (
            formatar_moeda(
                valor_final
            )

            if valor_final != 0

            else "Não informado"
        )
    )

    # ========================================================
    # NOVA TABELA DE CÓDIGOS
    # ========================================================

    st.subheader(
        "🔢 Atividades e códigos identificados"
    )

    if (
        atividades is None
        or atividades.empty
    ):

        st.warning(
            "Nenhuma atividade por código foi identificada."
        )

    else:

        codigos_reconhecidos = int(

            atividades[
                "Codigo"
            ]

            .astype(
                str
            )

            .str.strip()

            .ne(
                ""
            )

            .sum()
        )

        codigos_nao_reconhecidos = (

            len(
                atividades
            )

            - codigos_reconhecidos
        )

        col1, col2, col3 = st.columns(
            3
        )

        col1.metric(
            "Atividades encontradas",
            len(
                atividades
            )
        )

        col2.metric(
            "Códigos reconhecidos",
            codigos_reconhecidos
        )

        col3.metric(
            "Códigos não reconhecidos",
            codigos_nao_reconhecidos
        )

        colunas_atividades = [

            "Profissional",

            "CRM",

            "Codigo",

            "Servico",

            "Tipo",

            "Unidade de medida",

            "Quantidade",

            "Valor unitario",

            "Aba",

            "Linha do Excel"
        ]

        st.dataframe(

            atividades[
                colunas_atividades
            ].copy(),

            use_container_width=True,

            hide_index=True
        )

    with st.expander(
        "📋 Resumo por linha do relatório"
    ):

        colunas_resumo = [

            "Profissional",

            "CRM",

            "Plantoes",

            "Consultas",

            "Procedimentos",

            "Exames",

            "Interconsultas",

            "Pacotes",

            "Horas",

            "Valor bruto",

            "Valor final",

            "Aba",

            "Linha do Excel"
        ]

        st.dataframe(

            dados[
                colunas_resumo
            ].copy(),

            use_container_width=True,

            hide_index=True
        )

    varios = localizar_crms_com_varios_lancamentos(
        dados
    )

    if not varios.empty:

        with st.expander(
            "Ver CRMs com mais de um lançamento"
        ):

            st.dataframe(

                varios,

                use_container_width=True,

                hide_index=True
            )

    with st.expander(
        "🔧 Diagnóstico da leitura"
    ):

        st.dataframe(

            diagnostico,

            use_container_width=True,

            hide_index=True
        )


# ============================================================
# MENU
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
# INÍCIO
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
# TABELAS DE REFERÊNCIA
# ============================================================

elif pagina == "📋 Tabelas de referência":

    st.title(
        "📋 Tabelas de referência"
    )

    st.write(
        "As tabelas são gerais. "
        "Cadastre todas as versões existentes "
        "de cada competência."
    )

    st.link_button(

        "🌐 Abrir página oficial do ICISMEP",

        URL_ICISMEP
    )

    st.info(

        "Na validação, o sistema considera TODAS "
        "as tabelas cadastradas das competências "
        "que fazem parte do período."
    )

    coluna1, coluna2 = st.columns(
        2
    )

    competencia_ref = coluna1.text_input(

        "Competência da tabela",

        value=date.today().strftime(
            "%m/%Y"
        ),

        placeholder="09/2026"
    )

    data_tabela_ref = coluna2.date_input(

        "Data da tabela / atualização",

        value=date.today(),

        key="data_tabela_referencia"
    )

    versao_ref = st.text_input(

        "Versão / identificação",

        placeholder=(
            "Ex.: Tabela inicial, "
            "Atualização I, Atualização II"
        )
    )

    pdfs_ref = st.file_uploader(

        "PDF(s) oficial(is) desta versão",

        type=[
            "pdf"
        ],

        accept_multiple_files=True,

        key="pdfs_referencia"
    )

    if st.button(

        "📥 Cadastrar tabela(s)",

        type="primary"
    ):

        if not competencia_valida(
            competencia_ref
        ):

            st.error(
                "Informe a competência no formato MM/AAAA."
            )

        elif not pdfs_ref:

            st.error(
                "Envie pelo menos um PDF oficial."
            )

        else:

            total_arquivos = 0

            total_codigos = 0

            falhas = []

            with st.spinner(
                "Lendo as tabelas oficiais..."
            ):

                for pdf_ref in pdfs_ref:

                    try:

                        dados_pdf = extrair_referencias_pdf(

                            pdf_ref.getvalue()
                        )

                        if dados_pdf.empty:

                            falhas.append(

                                f"{pdf_ref.name}: "
                                f"nenhum código/valor reconhecido"
                            )

                            continue

                        quantidade = cadastrar_tabela_referencia(

                            dados_pdf,

                            competencia_ref.strip(),

                            data_tabela_ref,

                            versao_ref,

                            pdf_ref.name
                        )

                        total_arquivos += 1

                        total_codigos += quantidade

                    except Exception as erro:

                        falhas.append(

                            f"{pdf_ref.name}: {erro}"
                        )

            if total_arquivos > 0:

                st.success(

                    f"✅ {total_arquivos} tabela(s) cadastrada(s), "
                    f"com {total_codigos} registros de referência."
                )

            for falha in falhas:

                st.warning(
                    falha
                )

    tabelas = st.session_state.get(

        "tabelas_referencia",

        pd.DataFrame()
    )

    if not tabelas.empty:

        st.subheader(
            "📚 Tabelas cadastradas nesta sessão"
        )

        resumo = (

            tabelas

            .groupby(

                [

                    "Competencia",

                    "Data tabela",

                    "Versao",

                    "Arquivo de origem",

                    "ID tabela"
                ],

                dropna=False
            )

            .size()

            .reset_index(

                name="Referências encontradas"
            )
        )

        st.dataframe(

            resumo[

                [

                    "Competencia",

                    "Data tabela",

                    "Versao",

                    "Arquivo de origem",

                    "Referências encontradas"
                ]
            ],

            use_container_width=True,

            hide_index=True
        )

        with st.expander(
            "Ver códigos e valores cadastrados"
        ):

            st.dataframe(

                tabelas,

                use_container_width=True,

                hide_index=True
            )

        if st.button(
            "🗑️ Limpar tabelas desta sessão"
        ):

            st.session_state[
                "tabelas_referencia"
            ] = pd.DataFrame()

            st.rerun()


# ============================================================
# NOVO RELATÓRIO
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
            "A data final não pode ser anterior à data inicial."
        )

    else:

        competencias = competencias_do_periodo(

            data_inicial,

            data_final
        )

        if len(competencias) == 1:

            st.success(

                f"✅ Competência identificada: "
                f"{competencias[0]}"
            )

        else:

            st.warning(

                "⚠️ Este relatório envolve mais de uma competência: "

                + " | ".join(
                    competencias
                )
            )

            st.info(

                "As quantidades não serão divididas entre os meses. "
                "Todas as tabelas dessas competências serão analisadas."
            )

        st.success(

            f"💰 Competência do faturamento: "
            f"{competencia_inicial}"
        )

    observacoes = st.text_area(

        "Outras informações / observações",

        placeholder="Campo opcional"
    )

    arquivo = st.file_uploader(

        "📎 Selecione o relatório Excel",

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

                abas_disponiveis,

                default=sugestao
            )

            if st.button(

                "🔍 Analisar relatório",

                type="primary"
            ):

                if data_final < data_inicial:

                    st.error(
                        "Corrija o período antes de analisar."
                    )

                elif not municipio.strip():

                    st.error(
                        "Informe o município do relatório."
                    )

                elif not abas_escolhidas:

                    st.error(
                        "Escolha pelo menos uma aba."
                    )

                else:

                    with st.spinner(
                        "Lendo o relatório..."
                    ):

                        dados, atividades, diagnostico = processar_relatorio(

                            arquivo_bytes,

                            arquivo.name,

                            abas_escolhidas
                        )

                    st.session_state[
                        "dados_relatorio"
                    ] = dados

                    st.session_state[
                        "atividades_relatorio"
                    ] = atividades

                    st.session_state[
                        "diagnostico_relatorio"
                    ] = diagnostico

                    st.session_state[
                        "municipio_relatorio"
                    ] = municipio.strip()

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
                        "competencia_faturamento"
                    ] = competencia_inicial

                    st.success(
                        "✅ Análise concluída."
                    )

                    mostrar_analise(

                        dados,

                        atividades,

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
# ANÁLISE
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

            st.session_state.get(

                "atividades_relatorio",

                pd.DataFrame()
            ),

            st.session_state[
                "diagnostico_relatorio"
            ]
        )


# ============================================================
# DIVERGÊNCIAS
# ============================================================

elif pagina == "⚠️ Divergências":

    st.title(
        "⚠️ Divergências"
    )

    atividades = st.session_state.get(

        "atividades_relatorio",

        pd.DataFrame()
    )

    tabelas = st.session_state.get(

        "tabelas_referencia",

        pd.DataFrame()
    )

    data_inicial = st.session_state.get(
        "data_inicial_relatorio"
    )

    data_final = st.session_state.get(
        "data_final_relatorio"
    )

    if (
        atividades is None
        or atividades.empty
    ):

        st.info(

            "Primeiro analise um relatório "
            "com atividades reconhecidas."
        )

    elif tabelas.empty:

        st.warning(

            "Cadastre primeiro todas as tabelas "
            "oficiais do período."
        )

    elif (
        data_inicial is None
        or data_final is None
    ):

        st.warning(

            "O período do relatório não está disponível. "
            "Analise o arquivo novamente."
        )

    else:

        resultado, referencias = validar_relatorio_todas_tabelas(

            atividades,

            data_inicial,

            data_final,

            tabelas
        )

        st.session_state[
            "resultado_validacao"
        ] = resultado

        quantidade_tabelas = (

            referencias[
                "ID tabela"
            ].nunique()

            if not referencias.empty

            else 0
        )

        st.info(

            f"Foram consideradas {quantidade_tabelas} "
            f"tabela(s) de referência do período."
        )

        ok = int(

            (
                resultado[
                    "Status"
                ] == "🟢 OK"
            ).sum()
        )

        atencao = int(

            (
                resultado[
                    "Status"
                ] == "🟡 ATENÇÃO"
            ).sum()
        )

        erro = int(

            (
                resultado[
                    "Status"
                ] == "🔴 ERRO"
            ).sum()
        )

        coluna1, coluna2, coluna3 = st.columns(
            3
        )

        coluna1.metric(
            "🟢 OK",
            ok
        )

        coluna2.metric(
            "🟡 Atenção",
            atencao
        )

        coluna3.metric(
            "🔴 Erro",
            erro
        )

        filtro = st.multiselect(

            "Mostrar status",

            [

                "🟢 OK",

                "🟡 ATENÇÃO",

                "🔴 ERRO"
            ],

            default=[

                "🟡 ATENÇÃO",

                "🔴 ERRO"
            ]
        )

        if filtro:

            exibicao = resultado[

                resultado[
                    "Status"
                ].isin(
                    filtro
                )
            ]

        else:

            exibicao = resultado

        st.dataframe(

            exibicao,

            use_container_width=True,

            hide_index=True
        )


# ============================================================
# VALIDAÇÃO
# ============================================================

elif pagina == "✅ Validação":

    st.title(
        "✅ Validação"
    )

    resultado = st.session_state.get(
        "resultado_validacao"
    )

    if (
        resultado is None
        or resultado.empty
    ):

        st.info(
            "Abra primeiro ⚠️ Divergências."
        )

    else:

        st.write(
            "A validação humana permanece como etapa final."
        )

        st.dataframe(

            resultado,

            use_container_width=True,

            hide_index=True
        )


# ============================================================
# FATURAMENTO
# ============================================================

elif pagina == "💰 Faturamento":

    st.title(
        "💰 Faturamento"
    )

    st.write(

        "A geração do faturamento será liberada "
        "após a validação das divergências."
    )


# ============================================================
# HISTÓRICO
# ============================================================

elif pagina == "📚 Histórico":

    st.title(
        "📚 Histórico"
    )

    st.write(

        "As diferentes versões das tabelas "
        "não substituem umas às outras."
    )

    st.info(

        "O armazenamento permanente "
        "será adicionado depois."
    )


# ============================================================
# CONFIGURAÇÕES
# ============================================================

elif pagina == "⚙️ Configurações":

    st.title(
        "⚙️ Configurações"
    )

    st.write(
        f"Versão atual: {VERSAO}"
    )

    st.code(
        URL_ICISMEP
    )
