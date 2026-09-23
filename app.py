def localizar_colunas_producao_multilinha(
    planilha,
    linha_cabecalho
):

    """
    Procura os dados de produção em várias linhas
    abaixo do cabeçalho principal.

    Isso é necessário porque algumas planilhas,
    como a da FHEMIG, possuem:

    linha 1 -> PROFISSIONAIS / CRM / especialidades
    linha 2 -> códigos
    linha 3 -> QUANT. DE HORA / VALOR DA HORA
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
        "Valor total": []
    }


    # Vamos observar o cabeçalho principal
    # e as quatro linhas seguintes.
    linha_final = min(
        linha_cabecalho + 5,
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
                normalizar_texto(valor)
            )


        for texto in textos_coluna:


            # -----------------------------
            # HORAS
            # -----------------------------

            if (
                "quant de hora" in texto
                or "quantidade de hora" in texto
                or "qtd hora" in texto
            ):

                resultado[
                    "Horas"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # PLANTÕES
            # -----------------------------

            if (
                "quant de plantao" in texto
                or "quant plantao" in texto
                or "qtd plantao" in texto
            ):

                resultado[
                    "Plantoes"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # CONSULTAS
            # -----------------------------

            if (
                "quant de consulta" in texto
                or "quant consulta" in texto
                or "qtd consulta" in texto
            ):

                resultado[
                    "Consultas"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # PROCEDIMENTOS
            # -----------------------------

            if (
                "quant procedimento" in texto
                or "quant de procedimento" in texto
                or "qtd procedimento" in texto
            ):

                resultado[
                    "Procedimentos"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # EXAMES
            # -----------------------------

            if (
                "quant exame" in texto
                or "quant de exame" in texto
                or "qtd exame" in texto
            ):

                resultado[
                    "Exames"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # INTERCONSULTAS
            # -----------------------------

            if (
                "quant interconsulta" in texto
                or "quant de interconsulta" in texto
                or "qtd interconsulta" in texto
            ):

                resultado[
                    "Interconsultas"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # PACOTES
            # -----------------------------

            if (
                "quant pacote" in texto
                or "qtd pacote" in texto
                or "pacote de consulta" in texto
            ):

                resultado[
                    "Pacotes"
                ].append(
                    numero_coluna
                )


            # -----------------------------
            # VALOR UNITÁRIO
            # -----------------------------

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


            # -----------------------------
            # VALOR TOTAL
            # -----------------------------

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
