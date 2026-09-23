"""
============================================================
SISTEMA DE VALIDAÇÃO E FATURAMENTO MÉDICO
============================================================
Versão: 1.5
Linguagem: Python
Interface: Streamlit

OBJETIVO:
Ler relatórios médicos, identificar profissionais e produção,
preparar os dados para conferência, validação e faturamento.

REGRAS JÁ IMPLEMENTADAS:
- Profissionais únicos são contados pelo CRM.
- Relatórios com duas competências são analisados integralmente.
- O faturamento fica na competência do mês inicial.
- Consultas para faturamento =
  consultas + procedimentos + exames + interconsultas.
- Pacotes ficam separados.
============================================================
"""

import io
import re
import unicodedata
from datetime import date

import pandas as pd
import streamlit as st


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

NOME_SISTEMA = "Sistema de Validação e Faturamento Médico"
VERSAO = "1.5"

st.set_page_config(
    page_title=NOME_SISTEMA,
    page_icon="📊",
    layout="wide"
)


# ============================================================
# 2. FUNÇÕES BÁSICAS
# ============================================================

def normalizar_texto(valor):
    """Padroniza texto para facilitar a identificação de cabeçalhos."""
    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def converter_numero(valor):
    """Converte números e valores monetários do Excel para número."""
    if valor is None:
        return 0.0

    if isinstance(valor, float) and pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if texto == "":
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except Exception:
        return 0.0


def formatar_moeda(valor):
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_numero(valor, casas=0):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================
# 3. CRM E PROFISSIONAIS
# ============================================================

def limpar_crm(valor):
    if valor is None:
        return ""

    if isinstance(valor, float) and pd.isna(valor):
        return ""

    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return str(int(valor))

    texto = str(valor).strip()

    if re.fullmatch(r"\d+\.0", texto):
        texto = texto[:-2]

    return texto


def chave_crm(valor):
    return re.sub(r"\D", "", limpar_crm(valor))


def crm_valido(valor):
    numeros = chave_crm(valor)
    return 4 <= len(numeros) <= 10


def profissional_valido(nome, crm):
    """Evita contar cabeçalhos, SOMA e TOTAL como profissionais."""
    nome_normalizado = normalizar_texto(nome)

    if not nome_normalizado or len(nome_normalizado) < 4:
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
        if nome_normalizado.startswith(normalizar_texto(termo)):
            return False

    if not re.search(r"[a-z]", nome_normalizado):
        return False

    return crm_valido(crm)


# ============================================================
# 4. CABEÇALHO PRINCIPAL
# ============================================================

def linha_e_cabecalho(linha):
    encontrou_profissional = False
    encontrou_crm = False

    for valor in linha:
        texto = normalizar_texto(valor)

        if "profission" in texto:
            encontrou_profissional = True

        if texto == "crm" or texto.startswith("crm "):
            encontrou_crm = True

    return encontrou_profissional and encontrou_crm


def localizar_coluna_profissional(linha):
    for numero_coluna, valor in enumerate(linha):
        if "profission" in normalizar_texto(valor):
            return numero_coluna
    return None


def localizar_coluna_crm(linha):
    for numero_coluna, valor in enumerate(linha):
        texto = normalizar_texto(valor)

        if texto == "crm" or texto.startswith("crm "):
            return numero_coluna

    return None


def localizar_coluna_exata(linha, nomes):
    nomes_normalizados = {normalizar_texto(nome) for nome in nomes}

    for numero_coluna, valor in enumerate(linha):
        if normalizar_texto(valor) in nomes_normalizados:
            return numero_coluna

    return None


# ============================================================
# 5. MODELO COM UNIDADE DE MEDIDA + QUANT
# ============================================================

def localizar_colunas_modelo_generico(cabecalho):
    """
    Exemplo:
    UNIDADE DE MEDIDA | QUANT | VALOR UNIT. | VALOR TOTAL
    """
    return {
        "codigo": localizar_coluna_exata(
            cabecalho,
            [
                "cod do vinculo",
                "codigo do vinculo",
                "cod vinculo",
                "codigo",
                "cod"
            ]
        ),
        "servico": localizar_coluna_exata(
            cabecalho,
            [
                "vinculo contratual utilizado",
                "vinculo contratual",
                "servico",
                "atividade"
            ]
        ),
        "unidade": localizar_coluna_exata(
            cabecalho,
            [
                "unidade de medida",
                "unid de medida"
            ]
        ),
        "quantidade": localizar_coluna_exata(
            cabecalho,
            [
                "quant",
                "quantidade",
                "qtd"
            ]
        ),
        "valor_unitario": localizar_coluna_exata(
            cabecalho,
            [
                "valor unit",
                "valor unitario",
                "valor da unidade"
            ]
        ),
        "valor_bruto": localizar_coluna_exata(
            cabecalho,
            [
                "valor total",
                "valor bruto",
                "total bruto"
            ]
        ),
        "valor_final": localizar_coluna_exata(
            cabecalho,
            [
                "valor total final",
                "valor liquido",
                "valor final"
            ]
        )
    }


def classificar_unidade_medida(valor):
    """
    Transforma o texto da unidade de medida em uma categoria.
    A ordem é importante porque INTERCONSULTA contém CONSULTA.
    """
    texto = normalizar_texto(valor)

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

    if texto == "hora" or "horas" in texto or texto.startswith("hora "):
        return "Horas"

    return None


# ============================================================
# 6. MODELO COM CABEÇALHO EM VÁRIAS LINHAS
# ============================================================

def localizar_colunas_producao_multilinha(planilha, linha_cabecalho):
    """
    Lê modelos nos quais o cabeçalho ocupa várias linhas,
    como QUANT. DE HORA / VALOR DA HORA ou
    QUANT. DE CONSULTA / VALOR DA CONSULTA.
    """
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

    linha_final = min(linha_cabecalho + 6, len(planilha))

    for numero_coluna in range(planilha.shape[1]):
        textos_coluna = []

        for numero_linha in range(linha_cabecalho, linha_final):
            valor = planilha.iat[numero_linha, numero_coluna]
            textos_coluna.append(normalizar_texto(valor))

        for texto in textos_coluna:
            if not texto:
                continue

            if (
                "quant de hora" in texto
                or "quantidade de hora" in texto
                or "qtd hora" in texto
                or texto == "horas"
            ):
                resultado["Horas"].append(numero_coluna)

            if (
                "quant de plantao" in texto
                or "quant plantao" in texto
                or "qtd plantao" in texto
                or texto == "plantoes"
            ):
                resultado["Plantoes"].append(numero_coluna)

            if (
                "quant de interconsulta" in texto
                or "quant interconsulta" in texto
                or "qtd interconsulta" in texto
                or texto == "interconsultas"
            ):
                resultado["Interconsultas"].append(numero_coluna)

            if (
                "quant de pacote" in texto
                or "quant pacote" in texto
                or "qtd pacote" in texto
                or "pacote de consulta" in texto
                or "pacote consultas" in texto
                or texto == "pacotes"
            ):
                resultado["Pacotes"].append(numero_coluna)

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
                resultado["Consultas"].append(numero_coluna)

            if (
                "quant de procedimento" in texto
                or "quant procedimento" in texto
                or "qtd procedimento" in texto
                or texto == "procedimentos"
            ):
                resultado["Procedimentos"].append(numero_coluna)

            if (
                "quant de exame" in texto
                or "quant exame" in texto
                or "qtd exame" in texto
                or texto == "exames"
            ):
                resultado["Exames"].append(numero_coluna)

            if (
                "valor da hora" in texto
                or "valor da consulta" in texto
                or "valor consulta" in texto
                or "valor do procedimento" in texto
                or "valor procedimento" in texto
                or texto == "valor unit"
                or texto == "valor unitario"
            ):
                resultado["Valor unitario"].append(numero_coluna)

            if (
                texto == "valor total final"
                or texto == "valor final"
                or texto == "valor liquido"
            ):
                resultado["Valor final"].append(numero_coluna)

            elif (
                texto == "valor total"
                or texto == "valor bruto"
                or texto == "total bruto"
            ):
                resultado["Valor bruto"].append(numero_coluna)

    for campo in resultado:
        resultado[campo] = list(dict.fromkeys(resultado[campo]))

    return resultado


def encontrar_valor_unitario_ativo(planilha, numero_linha, colunas_producao):
    """
    Em modelos QUANTIDADE | VALOR, busca o valor ligado
    à coluna que realmente possui quantidade na linha.
    """
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
        colunas_quantidade.update(colunas_producao[campo])

    valores_ativos = []

    for coluna_valor in colunas_producao["Valor unitario"]:
        coluna_quantidade = coluna_valor - 1

        if coluna_quantidade in colunas_quantidade:
            quantidade = converter_numero(
                planilha.iat[numero_linha, coluna_quantidade]
            )

            valor = converter_numero(
                planilha.iat[numero_linha, coluna_valor]
            )

            if quantidade != 0 and valor != 0:
                valores_ativos.append(valor)

    valores_ativos = list(dict.fromkeys(valores_ativos))

    if len(valores_ativos) == 1:
        return valores_ativos[0]

    return 0.0


# ============================================================
# 7. LEITURA DE UMA ABA
# ============================================================

def ler_profissionais_da_aba(arquivo_bytes, nome_arquivo, nome_aba):
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
                "Colunas de horas": 0,
                "Situação": "Aba vazia"
            }
        )

    cabecalhos = []

    for numero_linha in range(len(planilha)):
        linha = planilha.iloc[numero_linha].tolist()

        if linha_e_cabecalho(linha):
            cabecalhos.append(numero_linha)

    registros = []
    colunas_horas_encontradas = set()

    for posicao, linha_cabecalho in enumerate(cabecalhos):
        cabecalho = planilha.iloc[linha_cabecalho].tolist()

        coluna_profissional = localizar_coluna_profissional(cabecalho)
        coluna_crm = localizar_coluna_crm(cabecalho)

        if coluna_profissional is None or coluna_crm is None:
            continue

        colunas_producao = localizar_colunas_producao_multilinha(
            planilha,
            linha_cabecalho
        )

        colunas_genericas = localizar_colunas_modelo_generico(cabecalho)

        colunas_horas_encontradas.update(
            colunas_producao["Horas"]
        )

        if posicao + 1 < len(cabecalhos):
            linha_final = cabecalhos[posicao + 1]
        else:
            linha_final = len(planilha)

        for numero_linha in range(linha_cabecalho + 1, linha_final):
            nome = planilha.iat[numero_linha, coluna_profissional]
            crm = planilha.iat[numero_linha, coluna_crm]

            if not profissional_valido(nome, crm):
                continue

            producao = {
                "Plantoes": 0.0,
                "Consultas": 0.0,
                "Procedimentos": 0.0,
                "Exames": 0.0,
                "Interconsultas": 0.0,
                "Pacotes": 0.0,
                "Horas": 0.0
            }

            # Modelo com colunas específicas.
            for campo in producao:
                for numero_coluna in colunas_producao[campo]:
                    producao[campo] += converter_numero(
                        planilha.iat[numero_linha, numero_coluna]
                    )

            # Modelo com UNIDADE DE MEDIDA + QUANT.
            codigo = ""
            servico = ""
            unidade_medida = ""
            quantidade_generica = 0.0

            if colunas_genericas["codigo"] is not None:
                codigo = planilha.iat[
                    numero_linha,
                    colunas_genericas["codigo"]
                ]

            if colunas_genericas["servico"] is not None:
                servico = planilha.iat[
                    numero_linha,
                    colunas_genericas["servico"]
                ]

            if colunas_genericas["unidade"] is not None:
                unidade_medida = planilha.iat[
                    numero_linha,
                    colunas_genericas["unidade"]
                ]

            if colunas_genericas["quantidade"] is not None:
                quantidade_generica = converter_numero(
                    planilha.iat[
                        numero_linha,
                        colunas_genericas["quantidade"]
                    ]
                )

            categoria = classificar_unidade_medida(unidade_medida)

            if categoria is not None and quantidade_generica != 0:
                producao[categoria] += quantidade_generica

            # Valor unitário.
            valor_unitario = 0.0

            if colunas_genericas["valor_unitario"] is not None:
                valor_unitario = converter_numero(
                    planilha.iat[
                        numero_linha,
                        colunas_genericas["valor_unitario"]
                    ]
                )

            if valor_unitario == 0:
                valor_unitario = encontrar_valor_unitario_ativo(
                    planilha,
                    numero_linha,
                    colunas_producao
                )

            # Valor bruto.
            valor_bruto = 0.0

            if colunas_genericas["valor_bruto"] is not None:
                valor_bruto = converter_numero(
                    planilha.iat[
                        numero_linha,
                        colunas_genericas["valor_bruto"]
                    ]
                )
            else:
                for numero_coluna in colunas_producao["Valor bruto"]:
                    valor_bruto += converter_numero(
                        planilha.iat[numero_linha, numero_coluna]
                    )

            # Valor final.
            valor_final = 0.0

            if colunas_genericas["valor_final"] is not None:
                valor_final = converter_numero(
                    planilha.iat[
                        numero_linha,
                        colunas_genericas["valor_final"]
                    ]
                )
            else:
                for numero_coluna in colunas_producao["Valor final"]:
                    valor_final += converter_numero(
                        planilha.iat[numero_linha, numero_coluna]
                    )

            registros.append(
                {
                    "Profissional": str(nome).strip(),
                    "CRM": limpar_crm(crm),
                    "CRM_ID": chave_crm(crm),
                    "Codigo": "" if pd.isna(codigo) else str(codigo).strip(),
                    "Servico": "" if pd.isna(servico) else str(servico).strip(),
                    "Unidade de medida": (
                        ""
                        if pd.isna(unidade_medida)
                        else str(unidade_medida).strip()
                    ),
                    "Arquivo": nome_arquivo,
                    "Aba": nome_aba,
                    "Linha do Excel": numero_linha + 1,
                    **producao,
                    "Valor unitario": valor_unitario,
                    "Valor bruto": valor_bruto,
                    "Valor final": valor_final
                }
            )

    dados = pd.DataFrame(registros)

    diagnostico = {
        "Aba": nome_aba,
        "Cabeçalhos encontrados": len(cabecalhos),
        "Lançamentos válidos": len(dados),
        "Colunas de horas": len(colunas_horas_encontradas),
        "Situação": "OK" if cabecalhos else "Cabeçalho não reconhecido"
    }

    return dados, diagnostico


# ============================================================
# 8. ABAS E PROCESSAMENTO
# ============================================================

def sugerir_abas(nomes_abas, competencia_inicial, competencia_final):
    if len(nomes_abas) == 1:
        return nomes_abas

    mes_inicial = competencia_inicial[:2]
    mes_final = competencia_final[:2]
    candidatos = []

    for aba in nomes_abas:
        texto = normalizar_texto(aba)

        if mes_inicial in texto or mes_final in texto:
            candidatos.append(aba)

    if candidatos:
        return [candidatos[-1]]

    for aba in nomes_abas:
        if normalizar_texto(aba) != "modelo":
            return [aba]

    return [nomes_abas[0]]


def processar_relatorio(arquivo_bytes, nome_arquivo, abas):
    tabelas = []
    diagnosticos = []

    for aba in abas:
        try:
            dados_aba, diagnostico = ler_profissionais_da_aba(
                arquivo_bytes,
                nome_arquivo,
                aba
            )

            diagnosticos.append(diagnostico)

            if not dados_aba.empty:
                tabelas.append(dados_aba)

        except Exception as erro:
            diagnosticos.append(
                {
                    "Aba": aba,
                    "Cabeçalhos encontrados": 0,
                    "Lançamentos válidos": 0,
                    "Colunas de horas": 0,
                    "Situação": f"ERRO: {erro}"
                }
            )

    if tabelas:
        dados = pd.concat(tabelas, ignore_index=True)
    else:
        dados = pd.DataFrame()

    return dados, pd.DataFrame(diagnosticos)


# ============================================================
# 9. RESUMOS
# ============================================================

def contar_profissionais_unicos(dados):
    if dados.empty:
        return 0

    return dados["CRM_ID"].nunique()


def localizar_crms_com_varios_lancamentos(dados):
    if dados.empty:
        return pd.DataFrame()

    contagem = dados.groupby("CRM_ID").size()
    repetidos = contagem[contagem > 1]
    resultado = []

    for crm_id, quantidade in repetidos.items():
        grupo = dados[dados["CRM_ID"] == crm_id]
        nomes = list(dict.fromkeys(grupo["Profissional"].tolist()))

        resultado.append(
            {
                "CRM": grupo.iloc[0]["CRM"],
                "Quantidade de lançamentos": int(quantidade),
                "Nome(s) encontrado(s)": " | ".join(nomes)
            }
        )

    return pd.DataFrame(resultado)


def mostrar_analise(dados, diagnostico):
    if dados is None or dados.empty:
        st.error("Nenhum profissional válido foi identificado.")

        if diagnostico is not None:
            st.dataframe(
                diagnostico,
                use_container_width=True,
                hide_index=True
            )
        return

    profissionais = contar_profissionais_unicos(dados)
    lancamentos = len(dados)

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
        "Profissionais únicos = CRMs diferentes. "
        "Lançamentos = linhas válidas encontradas."
    )

    st.subheader("📊 Produção encontrada")

    plantoes = dados["Plantoes"].sum()
    consultas = dados["Consultas"].sum()
    procedimentos = dados["Procedimentos"].sum()
    exames = dados["Exames"].sum()
    interconsultas = dados["Interconsultas"].sum()
    pacotes = dados["Pacotes"].sum()
    horas = dados["Horas"].sum()
    valor_bruto = dados["Valor bruto"].sum()
    valor_final = dados["Valor final"].sum()

    consultas_faturamento = (
        consultas
        + procedimentos
        + exames
        + interconsultas
    )

    linha1 = st.columns(4)

    linha1[0].metric("Plantões", formatar_numero(plantoes))
    linha1[1].metric("Consultas", formatar_numero(consultas))
    linha1[2].metric("Procedimentos", formatar_numero(procedimentos))
    linha1[3].metric("Exames", formatar_numero(exames))

    linha2 = st.columns(4)

    linha2[0].metric(
        "Interconsultas",
        formatar_numero(interconsultas)
    )
    linha2[1].metric("Pacotes", formatar_numero(pacotes))
    linha2[2].metric("Horas", formatar_numero(horas, 2))
    linha2[3].metric(
        "Consultas p/ faturamento",
        formatar_numero(consultas_faturamento)
    )

    linha3 = st.columns(2)

    linha3[0].metric(
        "💰 Valor bruto encontrado",
        formatar_moeda(valor_bruto)
    )

    if valor_final != 0:
        linha3[1].metric(
            "💰 Valor final encontrado",
            formatar_moeda(valor_final)
        )
    else:
        linha3[1].metric(
            "💰 Valor final encontrado",
            "Não informado"
        )

    st.caption(
        "Consultas para faturamento = consultas + procedimentos "
        "+ exames + interconsultas. Pacotes permanecem separados."
    )

    st.subheader("📋 Detalhamento encontrado")

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
        dados[colunas_exibicao].copy(),
        use_container_width=True,
        hide_index=True
    )

    varios_lancamentos = localizar_crms_com_varios_lancamentos(dados)

    if not varios_lancamentos.empty:
        st.info(
            "Alguns CRMs aparecem em mais de um lançamento. "
            "Isso não significa automaticamente duplicidade."
        )

        with st.expander("Ver CRMs com mais de um lançamento"):
            st.dataframe(
                varios_lancamentos,
                use_container_width=True,
                hide_index=True
            )

    with st.expander("🔧 Diagnóstico da leitura"):
        st.dataframe(
            diagnostico,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# 10. MENU
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
st.sidebar.caption(f"Versão {VERSAO}")


# ============================================================
# 11. PÁGINAS
# ============================================================

if pagina == "🏠 Início":
    st.title("🏠 Início")

    st.write(
        "Sistema para leitura, conferência, "
        "validação e faturamento de serviços médicos."
    )

    colunas = st.columns(4)
    colunas[0].metric("⏳ Pendentes", "0")
    colunas[1].metric("✅ Validados", "0")
    colunas[2].metric("⚠️ Com alerta", "0")
    colunas[3].metric("💰 Faturamento", "R$ 0,00")


elif pagina == "📋 Tabelas de referência":
    st.title("📋 Tabelas de referência")

    st.write(
        "Nesta área serão consultadas as tabelas oficiais "
        "utilizadas para conferência."
    )

    st.info(
        "A integração automática com o ICISMEP será "
        "adicionada na próxima etapa."
    )


elif pagina == "📤 Novo relatório":
    st.title("📤 Novo relatório")

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

    competencia_inicial = data_inicial.strftime("%m/%Y")
    competencia_final = data_final.strftime("%m/%Y")

    if data_final < data_inicial:
        st.error(
            "A data final não pode ser anterior à data inicial."
        )

    else:
        if competencia_inicial == competencia_final:
            st.success(
                f"✅ Competência identificada: {competencia_inicial}"
            )

        else:
            st.warning(
                "⚠️ Este relatório envolve duas competências."
            )

            st.write(
                f"**Primeira competência:** {competencia_inicial}"
            )
            st.write(
                f"**Segunda competência:** {competencia_final}"
            )

            st.info(
                "Como não é possível identificar quanto foi executado "
                "em cada mês, o relatório será analisado integralmente "
                "considerando as duas tabelas de referência."
            )

        st.subheader("💰 Competência do faturamento")

        st.success(
            f"O relatório será lançado integralmente "
            f"em {competencia_inicial}"
        )

    observacoes = st.text_area(
        "Outras informações / observações",
        placeholder="Campo opcional"
    )

    st.subheader("📎 Relatório Excel")

    arquivo = st.file_uploader(
        "Selecione o relatório",
        type=["xlsx"]
    )

    if arquivo is not None:
        arquivo_bytes = arquivo.getvalue()

        try:
            excel = pd.ExcelFile(
                io.BytesIO(arquivo_bytes)
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
                    st.error("Corrija o período antes de analisar.")

                elif not abas_escolhidas:
                    st.error("Escolha pelo menos uma aba.")

                else:
                    with st.spinner("Lendo o relatório..."):
                        dados, diagnostico = processar_relatorio(
                            arquivo_bytes,
                            arquivo.name,
                            abas_escolhidas
                        )

                    st.session_state["dados_relatorio"] = dados
                    st.session_state["diagnostico_relatorio"] = diagnostico
                    st.session_state["municipio_relatorio"] = municipio
                    st.session_state["responsavel_relatorio"] = responsavel
                    st.session_state["observacoes_relatorio"] = observacoes
                    st.session_state["periodo_relatorio"] = (
                        f"{data_inicial.strftime('%d/%m/%Y')} "
                        f"a "
                        f"{data_final.strftime('%d/%m/%Y')}"
                    )
                    st.session_state[
                        "competencia_faturamento"
                    ] = competencia_inicial

                    st.success("✅ Análise concluída.")

                    mostrar_analise(
                        dados,
                        diagnostico
                    )

        except Exception as erro:
            st.error(
                "Não foi possível abrir ou analisar o arquivo Excel."
            )

            with st.expander("Ver detalhes do erro"):
                st.code(str(erro))


elif pagina == "🔍 Análise":
    st.title("🔍 Análise")

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
            st.session_state["dados_relatorio"],
            st.session_state["diagnostico_relatorio"]
        )


elif pagina == "⚠️ Divergências":
    st.title("⚠️ Divergências")

    st.info(
        "A auditoria por município + competência + código + "
        "valor oficial será adicionada na próxima etapa."
    )


elif pagina == "✅ Validação":
    st.title("✅ Validação")

    st.write(
        "A validação humana será adicionada "
        "nas próximas etapas."
    )


elif pagina == "💰 Faturamento":
    st.title("💰 Faturamento")

    st.write(
        "Aqui serão exibidos os relatórios já validados."
    )


elif pagina == "📚 Histórico":
    st.title("📚 Histórico")

    st.write(
        "Aqui ficará registrado o histórico do sistema."
    )


elif pagina == "⚙️ Configurações":
    st.title("⚙️ Configurações")

    st.write(
        f"Versão atual: {VERSAO}"
    )
