import io
import re
import unicodedata
from datetime import date

import pandas as pd
import pdfplumber
import streamlit as st


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"
VERSAO = "1.7"

URL_ICISMEP = (
    "https://icismep.mg.gov.br/"
    "tabela-de-servicos-medicos-nos-municipios-entes-nao-consorciados/"
)

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide",
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

    texto = str(
        valor
    ).strip().upper()

    texto = texto.replace(
        " ",
        ""
    )

    if re.fullmatch(
        r"\d+[\.,]0",
        texto
    ):

        return texto[:-2]

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

    """
    Descobre todas as competências
    tocadas pelo período.

    Exemplo:

    15/08/2026 até 14/09/2026

    retorna:

    08/2026
    09/2026
    """

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

        and

        encontrou_crm
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
# CLASSIFICAR PRODUÇÃO
# ============================================================

def classificar_unidade_medida(
    valor
):

    texto = normalizar_texto(
        valor
    )


    if not texto:

        return None


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


# ============================================================
# CABEÇALHOS EM VÁRIAS LINHAS
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


            # HORAS

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


            # PLANTÕES

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


            # INTERCONSULTA

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


            # PACOTE

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


            # CONSULTA

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


            # PROCEDIMENTO

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


            # EXAME

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


            # VALOR UNITÁRIO

            if (

                "valor da hora" in texto

                or "valor da consulta" in texto

                or "valor consulta" in texto

                or "valor do procedimento" in texto

                or "valor procedimento" in texto

                or texto == "valor unit"

                or texto == "valor unitario"
            ):


                resultado[
                    "Valor unitario"
                ].append(
                    numero_coluna
                )


            # VALOR FINAL

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


            # VALOR BRUTO

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


def encontrar_valor_unitario_ativo(
    planilha,
    numero_linha,
    colunas_producao
):

    colunas_quantidade = set()


    for campo in [

        "Plantoes",

        "Consultas",

        "Procedimentos",

        "Exames",

        "Interconsultas",

        "Pacotes",

        "Horas"
    ]:


        colunas_quantidade.update(

            colunas_producao[
                campo
            ]
        )


    valores_ativos = []


    for coluna_valor in colunas_producao[
        "Valor unitario"
    ]:


        coluna_quantidade = (
            coluna_valor - 1
        )


        if coluna_quantidade in colunas_quantidade:


            quantidade = converter_numero(

                planilha.iat[

                    numero_linha,

                    coluna_quantidade
                ]
            )


            valor = converter_numero(

                planilha.iat[

                    numero_linha,

                    coluna_valor
                ]
            )


            if (

                quantidade != 0

                and valor != 0
            ):


                valores_ativos.append(
                    valor
                )


    valores_ativos = list(

        dict.fromkeys(
            valores_ativos
        )
    )


    if len(
        valores_ativos
    ) == 1:


        return valores_ativos[
            0
        ]


    return 0.0


# ============================================================
# LEITURA DO RELATÓRIO
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


            # ------------------------------------------------
            # VALOR UNITÁRIO
            # ------------------------------------------------

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


            if valor_unitario == 0:


                valor_unitario = encontrar_valor_unitario_ativo(

                    planilha,

                    numero_linha,

                    colunas_producao
                )


            # ------------------------------------------------
            # VALOR BRUTO
            # ------------------------------------------------

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


            else:


                for numero_coluna in colunas_producao[
                    "Valor bruto"
                ]:


                    valor_bruto += converter_numero(

                        planilha.iat[

                            numero_linha,

                            numero_coluna
                        ]
                    )


            # ------------------------------------------------
            # VALOR FINAL
            # ------------------------------------------------

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


            else:


                for numero_coluna in colunas_producao[
                    "Valor final"
                ]:


                    valor_final += converter_numero(

                        planilha.iat[

                            numero_linha,

                            numero_coluna
                        ]
                    )


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

                    "Codigo":

                        ""

                        if pd.isna(
                            codigo
                        )

                        else normalizar_codigo(
                            codigo
                        ),

                    "Servico":

                        ""

                        if pd.isna(
                            servico
                        )

                        else str(
                            servico
                        ).strip(),

                    "Unidade de medida":

                        ""

                        if pd.isna(
                            unidade_medida
                        )

                        else str(
                            unidade_medida
                        ).strip(),

                    "Arquivo":
                        nome_arquivo,

                    "Aba":
                        nome_aba,

                    "Linha do Excel":
                        numero_linha + 1,

                    **producao,

                    "Valor unitario":
                        valor_unitario,

                    "Valor bruto":
                        valor_bruto,

                    "Valor final":
                        valor_final
                }
            )


    dados = pd.DataFrame(
        registros
    )


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
# SUGESTÃO DE ABAS
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
# PROCESSAMENTO DO RELATÓRIO
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
# TABELA DE REFERÊNCIA - PDF
# ============================================================

def inferir_unidade_referencia(
    texto
):

    t = normalizar_texto(
        texto
    )


    if "interconsulta" in t:

        return "INTERCONSULTA"


    if (
        "plantao" in t
        and "12" in t
    ):

        return "PLANTÃO 12H"


    if "plantao" in t:

        return "PLANTÃO"


    if "procedimento" in t:

        return "PROCEDIMENTO"


    if "consulta" in t:

        return "CONSULTA"


    if "exame" in t:

        return "EXAME"


    if "diaria" in t:

        return "DIÁRIA"


    if "hora" in t:

        return "HORA"


    if "mensal" in t:

        return "MENSAL"


    if "mes" in t:

        return "MÊS"


    return ""


def extrair_referencias_pdf(
    pdf_bytes
):

    """
    Lê os códigos e valores do PDF.

    NÃO existe separação por município.

    Se o mesmo código e valor aparecerem
    várias vezes no PDF, o sistema elimina
    apenas as repetições idênticas.
    """

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


                linha_limpa = linha.strip()


                match = re.match(

                    r"^\s*(\d+(?:[\.,]\d+)?)\s+"
                    r"(.+?)\s+"
                    r"R\$\s*([\d\.\s]+,\d{2})\s*$",

                    linha_limpa,

                    flags=re.IGNORECASE
                )


                if not match:

                    continue


                codigo = normalizar_codigo(
                    match.group(1)
                )


                descricao = match.group(
                    2
                ).strip()


                valor = converter_numero(
                    match.group(3)
                )


                if (
                    not codigo
                    or valor <= 0
                ):

                    continue


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


# ============================================================
# CADASTRO DA TABELA
# ============================================================

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


    # Se o mesmo arquivo for cadastrado
    # novamente com os mesmos dados,
    # substituímos somente aquela cópia.

    # Isso NÃO remove outras versões.

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


# ============================================================
# TODAS AS TABELAS DO PERÍODO
# ============================================================

def tabelas_do_periodo(

    tabelas,

    data_inicial,

    data_final
):

    """
    REGRA IMPORTANTE:

    nenhuma tabela é escolhida como principal.

    Se o relatório envolve agosto e setembro,
    TODAS as tabelas cadastradas de agosto
    e TODAS as tabelas cadastradas de setembro
    serão consideradas.
    """

    if (
        tabelas is None
        or tabelas.empty
    ):

        return pd.DataFrame()


    competencias = competencias_do_periodo(

        data_inicial,

        data_final
    )


    resultado = tabelas[

        tabelas[
            "Competencia"
        ].astype(
            str
        ).isin(
            competencias
        )

    ].copy()


    return resultado


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


    resultado = tabelas_periodo[

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


    return resultado


# ============================================================
# VALIDAÇÃO DOS VALORES
# ============================================================

def quantidade_linha(
    linha
):

    campos = [

        "Plantoes",

        "Consultas",

        "Procedimentos",

        "Exames",

        "Interconsultas",

        "Pacotes",

        "Horas"
    ]


    return sum(

        converter_numero(

            linha.get(
                campo,
                0
            )
        )

        for campo in campos
    )


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


    if quantidade > 0:


        total_oficial = (

            quantidade
            * valor_oficial
        )


    else:


        total_oficial = None


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


    referencias_ordenadas = referencias.sort_values(

        [

            "Competencia",

            "Data tabela",

            "Versao",

            "Valor oficial"
        ]
    )


    for _, referencia in referencias_ordenadas.iterrows():


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

    dados,

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

            .tolist()
        )


    else:


        ids_tabelas_periodo = set()


    total_tabelas_periodo = len(
        ids_tabelas_periodo
    )


    resultados = []


    for _, linha in dados.iterrows():


        codigo = normalizar_codigo(

            linha.get(
                "Codigo",
                ""
            )
        )


        quantidade = quantidade_linha(
            linha
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

        valores_oficiais_texto = ""

        tabelas_com_codigo = 0

        tabelas_sem_codigo = total_tabelas_periodo

        valor_calculado = None

        diferenca = None


        # ----------------------------------------------------
        # NÃO HÁ TABELAS DO PERÍODO
        # ----------------------------------------------------

        if total_tabelas_periodo == 0:


            motivo = (

                "Nenhuma tabela de referência foi cadastrada "
                "para as competências do período do relatório."
            )


        # ----------------------------------------------------
        # RELATÓRIO SEM CÓDIGO
        # ----------------------------------------------------

        elif not codigo:


            motivo = (

                "O relatório não trouxe código suficiente "
                "para validar automaticamente esta linha."
            )


        # ----------------------------------------------------
        # EXISTE CÓDIGO
        # ----------------------------------------------------

        else:


            referencias = referencias_do_codigo(

                referencias_periodo,

                codigo
            )


            valores_oficiais_texto = texto_referencias(
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

                    .tolist()
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


            # ------------------------------------------------
            # CÓDIGO NÃO EXISTE EM NENHUMA TABELA
            # ------------------------------------------------

            if referencias.empty:


                status = "🔴 ERRO"


                motivo = (

                    "Código não encontrado em nenhuma "
                    "das tabelas cadastradas do período."
                )


            # ------------------------------------------------
            # CÓDIGO NÃO EXISTE EM TODAS
            # ------------------------------------------------

            elif tabelas_sem_codigo > 0:


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


                combina_algum = False


                for valor in valores:


                    combina, _ = valor_relatorio_confere(

                        valor_unitario,

                        valor_bruto,

                        quantidade,

                        valor
                    )


                    if combina:


                        combina_algum = True

                        break


                status = "🟡 ATENÇÃO"


                if combina_algum:


                    motivo = (

                        "O código aparece em algumas tabelas do período, "
                        "mas não em todas. O valor do relatório coincide "
                        "com pelo menos uma referência encontrada. "
                        "É necessária validação humana."
                    )


                else:


                    motivo = (

                        "O código aparece em algumas tabelas do período, "
                        "mas não em todas. Como as versões não apresentam "
                        "a mesma referência, é necessária validação humana."
                    )


            # ------------------------------------------------
            # CÓDIGO EXISTE EM TODAS AS TABELAS
            # ------------------------------------------------

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


                # --------------------------------------------
                # MESMO VALOR EM TODAS AS TABELAS
                # --------------------------------------------

                if len(
                    valores
                ) == 1:


                    oficial = valores[
                        0
                    ]


                    confere, total_oficial = valor_relatorio_confere(

                        valor_unitario,

                        valor_bruto,

                        quantidade,

                        oficial
                    )


                    valor_calculado = total_oficial


                    if confere:


                        status = "🟢 OK"


                        motivo = (

                            "O código está presente em todas as tabelas "
                            "do período, o valor oficial é igual em todas "
                            "e o relatório confere."
                        )


                    else:


                        status = "🔴 ERRO"


                        motivo = (

                            "O código está presente em todas as tabelas "
                            "do período e o valor oficial é igual entre "
                            "elas, mas o relatório não confere."
                        )


                # --------------------------------------------
                # VALORES DIFERENTES ENTRE AS TABELAS
                # --------------------------------------------

                else:


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


                    if valores_que_conferem:


                        status = "🟡 ATENÇÃO"


                        motivo = (

                            "Foram encontrados valores oficiais diferentes "
                            "entre as tabelas do período. O relatório coincide "
                            "com pelo menos uma delas, portanto exige "
                            "validação humana."
                        )


                    else:


                        status = "🔴 ERRO"


                        motivo = (

                            "Foram encontrados valores oficiais diferentes "
                            "entre as tabelas do período, e o valor do relatório "
                            "não coincide com nenhuma referência encontrada."
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
                    valores_oficiais_texto,

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
# PROFISSIONAIS ÚNICOS
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
# MOSTRAR ANÁLISE
# ============================================================

def mostrar_analise(

    dados,

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


    st.caption(

        "Profissionais únicos = CRMs diferentes. "
        "Lançamentos = linhas válidas encontradas."
    )


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


    st.caption(

        "Consultas para faturamento = consultas + procedimentos "
        "+ exames + interconsultas. Pacotes permanecem separados."
    )


    st.subheader(
        "📋 Detalhamento encontrado"
    )


    colunas_exibicao = [

        "Profissional",

        "CRM",

        "Codigo",

        "Servico",

        "Unidade de medida",

        "Plantoes",

        "Consultas",

        "Procedimentos",

        "Exames",

        "Interconsultas",

        "Pacotes",

        "Horas",

        "Valor unitario",

        "Valor bruto",

        "Valor final",

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


    varios = localizar_crms_com_varios_lancamentos(
        dados
    )


    if not varios.empty:


        st.info(

            "Alguns CRMs aparecem em mais de um lançamento. "
            "Isso não significa automaticamente duplicidade."
        )


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

        "As tabelas são gerais: não existe cadastro por município. "
        "Cadastre todas as versões existentes de cada competência."
    )


    st.link_button(

        "🌐 Abrir página oficial do ICISMEP",

        URL_ICISMEP
    )


    st.info(

        "Na validação, o sistema considera TODAS as tabelas "
        "cadastradas das competências que fazem parte do período "
        "do relatório. Nenhuma versão substitui a anterior."
    )


    col1, col2 = st.columns(
        2
    )


    competencia_ref = col1.text_input(

        "Competência da tabela",

        value=date.today().strftime(
            "%m/%Y"
        ),

        placeholder="09/2026"
    )


    data_tabela_ref = col2.date_input(

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


            if falhas:


                st.warning(
                    "Alguns arquivos não puderam ser lidos:"
                )


                for falha in falhas:


                    st.write(
                        f"• {falha}"
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


        resumo = resumo.sort_values(

            [

                "Competencia",

                "Data tabela",

                "Versao",

                "Arquivo de origem"
            ]
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


    st.warning(

        "Por enquanto, as tabelas ficam salvas apenas durante "
        "a sessão do Streamlit. O armazenamento permanente será "
        "adicionado depois."
    )


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

            "A data final não pode ser "
            "anterior à data inicial."
        )


    else:


        competencias = competencias_do_periodo(

            data_inicial,

            data_final
        )


        if len(
            competencias
        ) == 1:


            st.success(

                f"✅ Competência identificada: "
                f"{competencias[0]}"
            )


        else:


            st.warning(

                "⚠️ Este relatório envolve mais de uma "
                "competência: "

                + " | ".join(
                    competencias
                )
            )


            st.info(

                "As quantidades não serão divididas entre os meses. "
                "A validação usará todas as tabelas cadastradas "
                "dessas competências."
            )


        st.subheader(
            "💰 Competência do faturamento"
        )


        st.success(

            f"O relatório será lançado integralmente "
            f"em {competencia_inicial}."
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


            if st.button(

                "🔍 Analisar relatório",

                type="primary"
            ):


                if data_final < data_inicial:


                    st.error(

                        "Corrija o período antes "
                        "de analisar."
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


    dados = st.session_state.get(
        "dados_relatorio"
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
        dados is None
        or dados.empty
    ):


        st.info(

            "Primeiro analise um relatório "
            "em 📤 Novo relatório."
        )


    elif tabelas.empty:


        st.warning(

            "Cadastre primeiro todas as tabelas oficiais "
            "do período em 📋 Tabelas de referência."
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


        competencias = competencias_do_periodo(

            data_inicial,

            data_final
        )


        st.write(

            "**Competências analisadas:** "

            + " | ".join(
                competencias
            )
        )


        resultado, referencias_periodo = validar_relatorio_todas_tabelas(

            dados,

            data_inicial,

            data_final,

            tabelas
        )


        st.session_state[
            "resultado_validacao"
        ] = resultado


        if not referencias_periodo.empty:


            quantidade_tabelas = referencias_periodo[
                "ID tabela"
            ].nunique()


        else:


            quantidade_tabelas = 0


        st.info(

            f"Foram consideradas {quantidade_tabelas} "
            f"tabela(s) de referência cadastrada(s) "
            f"para as competências do período."
        )


        if quantidade_tabelas == 0:


            st.error(

                "Nenhuma tabela cadastrada corresponde "
                "às competências do período."
            )


        else:


            with st.expander(
                "Ver tabelas consideradas nesta validação"
            ):


                resumo_referencias = (

                    referencias_periodo[

                        [

                            "Competencia",

                            "Data tabela",

                            "Versao",

                            "Arquivo de origem",

                            "ID tabela"
                        ]
                    ]

                    .drop_duplicates()

                    .sort_values(

                        [

                            "Competencia",

                            "Data tabela",

                            "Versao"
                        ]
                    )
                )


                st.dataframe(

                    resumo_referencias[

                        [

                            "Competencia",

                            "Data tabela",

                            "Versao",

                            "Arquivo de origem"
                        ]
                    ],

                    use_container_width=True,

                    hide_index=True
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


        col1, col2, col3 = st.columns(
            3
        )


        col1.metric(
            "🟢 OK",
            ok
        )


        col2.metric(
            "🟡 Atenção",
            atencao
        )


        col3.metric(
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


        st.caption(

            "O sistema não corrige valores automaticamente. "
            "A validação humana continua sendo a etapa final."
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

            "Abra primeiro ⚠️ Divergências para executar "
            "a conferência com todas as tabelas do período."
        )


    else:


        st.write(

            "A validação humana permanece "
            "como etapa final."
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

        "A geração do faturamento será liberada depois "
        "da validação das divergências. A competência de "
        "faturamento continua sendo o mês da data inicial "
        "do relatório."
    )


# ============================================================
# HISTÓRICO
# ============================================================

elif pagina == "📚 Histórico":


    st.title(
        "📚 Histórico"
    )


    st.write(

        "As diferentes versões das tabelas não substituem "
        "umas às outras. Nesta fase, elas ficam preservadas "
        "durante a sessão."
    )


    st.info(

        "Depois vamos adicionar armazenamento permanente "
        "para relatórios, tabelas de referência e validações."
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


    st.write(
        "Fonte oficial configurada:"
    )


    st.code(
        URL_ICISMEP
    )
