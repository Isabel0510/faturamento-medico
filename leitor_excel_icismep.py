
import io
import pandas as pd


COLUNAS_OBRIGATORIAS = [
    "Tabela",
    "Município / Contratante",
    "Seção",
    "Descrição do Serviço",
    "Tipo de Serviço",
    "Unidade de Medida",
    "Valor ICISMEP",
]


def ler_excel_icismep(arquivo_bytes):
    """
    Lê o modelo Excel ICISMEP de novembro/2026.
    Não grava informações no banco de dados.
    """
    planilha = pd.read_excel(
        io.BytesIO(arquivo_bytes),
        sheet_name="Tabela de Serviços",
        header=8,
        engine="openpyxl",
    )

    planilha.columns = [
        str(coluna).strip()
        for coluna in planilha.columns
    ]

    ausentes = [
        coluna for coluna in COLUNAS_OBRIGATORIAS
        if coluna not in planilha.columns
    ]

    if ausentes:
        raise ValueError(
            "Colunas não encontradas: "
            + ", ".join(ausentes)
        )

    dados = planilha[COLUNAS_OBRIGATORIAS].copy()

    for coluna in [
        "Município / Contratante",
        "Seção",
        "Descrição do Serviço",
        "Tipo de Serviço",
        "Unidade de Medida",
    ]:
        dados[coluna] = dados[coluna].fillna("").astype(str).str.strip()

    dados["Valor ICISMEP"] = pd.to_numeric(
        dados["Valor ICISMEP"],
        errors="coerce",
    )

    validos = (
        dados["Município / Contratante"].ne("")
        & dados["Descrição do Serviço"].ne("")
        & dados["Unidade de Medida"].ne("")
        & dados["Valor ICISMEP"].notna()
        & dados["Valor ICISMEP"].gt(0)
    )

    invalidos = dados.loc[~validos].copy()

    if not invalidos.empty:
        raise ValueError(
            f"Foram encontradas {len(invalidos)} linhas "
            "com dados obrigatórios ausentes ou valores inválidos. "
            "Confira a planilha antes de continuar."
        )

    referencias = pd.DataFrame({
        "Codigo": "",
        "Descricao referencia": dados["Descrição do Serviço"],
        "Unidade referencia": dados["Unidade de Medida"],
        "Unidade/local referencia": dados["Tipo de Serviço"],
        "Secao referencia": dados["Município / Contratante"],
        "Valor oficial": dados["Valor ICISMEP"],
        "Pagina PDF": None,
        "Municipio": dados["Município / Contratante"],
        "Secao original": dados["Seção"],
        "Tipo servico original": dados["Tipo de Serviço"],
        "Numero tabela": dados["Tabela"],
    })

    referencias = referencias.reset_index(drop=True)

    return referencias
