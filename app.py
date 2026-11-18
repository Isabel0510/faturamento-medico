                    if x.strip()
                ],
                reverse=True,
            )

            municipios = sorted(
                [
                    x for x in historico_df["Município / Ente"].astype(str).unique()
                    if x.strip()
                ]
            )

            filtro_responsavel = f1.selectbox(
                "Responsável",
                ["Todos"] + responsaveis,
            )

            filtro_competencia = f2.selectbox(
                "Competência",
                ["Todas"] + competencias,
            )

            filtro_municipio = f3.selectbox(
                "Município / ente",
                ["Todos"] + municipios,
            )

            filtrado = historico_df.copy()

            if filtro_responsavel != "Todos":
                filtrado = filtrado[
                    filtrado["Responsável"].astype(str) == filtro_responsavel
                ]

            if filtro_competencia != "Todas":
                filtrado = filtrado[
                    filtrado["Competência"].astype(str) == filtro_competencia
                ]

            if filtro_municipio != "Todos":
                filtrado = filtrado[
                    filtrado["Município / Ente"].astype(str) == filtro_municipio
                ]

            st.subheader("📊 Resumo")

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "Lançamentos",
                len(filtrado),
            )

            m2.metric(
                "Valor lançado",
                formatar_moeda(
                    filtrado["Novo valor"].sum()
                ),
            )

            m3.metric(
                "Municípios / entes",
                filtrado["Município / Ente"].astype(str).nunique(),
            )

            m4.metric(
                "Responsáveis",
                filtrado["Responsável"].astype(str).nunique(),
            )

            st.subheader("📋 Lançamentos")

            exibicao = filtrado.copy()

            exibicao["Valor anterior"] = exibicao[
                "Valor anterior"
            ].apply(formatar_moeda)

            exibicao["Novo valor"] = exibicao[
                "Novo valor"
            ].apply(formatar_moeda)

            st.dataframe(
                exibicao,
                use_container_width=True,
                hide_index=True,
            )

            csv_historico = filtrado.to_csv(
                index=False,
                sep=";",
                decimal=",",
            ).encode("utf-8-sig")

            st.download_button(
                "⬇️ Baixar histórico filtrado em CSV",
                data=csv_historico,
                file_name="historico_faturamento.csv",
                mime="text/csv",
            )


elif pagina == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    st.write(f"Versão atual: {VERSAO}")
    st.code(URL_ICISMEP)

    st.divider()
    st.subheader("🗄️ Conexão com Supabase")

    if st.button("🔌 Testar conexão com o banco"):
        sucesso, mensagem = testar_conexao()

        if sucesso:
            st.success(mensagem)
        else:
            st.error(mensagem)

    st.divider()
    st.subheader("📋 Gerenciador de Tabelas ICISMEP")

    if st.button("📚 Testar gerenciador de tabelas"):
        sucesso, mensagem = testar_gerenciador()

        if sucesso:
            st.success(mensagem)
        else:
            st.error(mensagem)
