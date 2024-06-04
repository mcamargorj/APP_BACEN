# Análise de Reclamações do BACEN com Streamlit

![BACEN Logo](https://www.bcb.gov.br/contents/sobre/Logo-Banco-Central.jpg)

Este projeto utiliza o Streamlit para criar uma interface interativa que permite analisar dados de reclamações contra instituições financeiras registradas no Banco Central do Brasil (BACEN). O aplicativo permite ao usuário filtrar e visualizar dados específicos de acordo com o ano, periodicidade, período e tipo de instituição. Além disso, oferece a possibilidade de baixar o ranking das instituições com mais reclamações.

## Funcionalidades Principais

1. **Carregamento de Dados** 📊:
    - Os dados são carregados a partir de uma API do BACEN que retorna um JSON contendo informações sobre reclamações.
    - Os dados são normalizados e convertidos para um DataFrame do Pandas para facilitar a manipulação.

2. **Filtros Interativos** 🎛️:
    - A interface permite ao usuário selecionar o tipo de instituição, ano, periodicidade e período para filtrar os dados.
    - Com base nesses filtros, o aplicativo gera um link para baixar o arquivo CSV correspondente.

3. **Processamento e Visualização de Dados** 📈:
    - O CSV é baixado e processado para detectar a codificação correta e o delimitador adequado.
    - O DataFrame resultante é filtrado para selecionar as colunas relevantes e reorganizar os dados conforme necessário.
    - É gerado um gráfico interativo usando Altair para visualizar a quantidade de diferentes tipos de reclamações por instituição.
    - Um ranking das instituições com mais reclamações é exibido em uma tabela estilizada.

4. **Download de Dados** 💾:
    - O usuário pode baixar o ranking das 10 instituições com mais reclamações em formato CSV.

## Capturas de Tela

### Interface Principal
![Interface Principal](https://via.placeholder.com/800x400.png?text=Interface+Principal)

### Gráfico Interativo
![Gráfico Interativo](https://via.placeholder.com/800x400.png?text=Gráfico+Interativo)

### Ranking de Reclamações
![Ranking de Reclamações](https://via.placeholder.com/800x400.png?text=Ranking+de+Reclamações)

## Uso

### Configurar e Executar o Aplicativo

1. Clone este repositório:
    ```sh
    git clone https://github.com/seu-usuario/seu-repositorio.git
    cd seu-repositorio
    ```

2. Instale as dependências necessárias:
    ```sh
    pip install -r requirements.txt
    ```

3. Execute o aplicativo:
    ```sh
    streamlit run app.py
    ```

### Estrutura do Código

- **Carregamento e Processamento de Dados**:
    ```python
    def load_data():
        json_url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
        response = requests.get(json_url)
        data = response.json()
        df = pd.json_normalize(data, record_path=['anos', 'periodicidades', 'periodos', 'tipos'],
                               meta=[['anos', 'ano'], ['anos', 'periodicidades', 'periodicidade'],
                                     ['anos', 'periodicidades', 'periodos', 'periodo']])
        df.columns = ['tipo', 'ano', 'periodicidade', 'periodo']
        return df
    ```

- **Gerar Link para CSV e Processar Dados**:
    ```python
    def gerar_link_csv(ano, periodicidade, periodo, tipo):
        base_url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo"
        return f"{base_url}?ano={ano}&periodicidade={periodicidade}&periodo={periodo}&tipo={tipo}"
    ```

- **Visualização com Altair**:
    ```python
    grafCombEstado = alt.Chart(dadosUsuario).mark_bar().encode(
        x=alt.X('Tipo de Reclamação:N', title='Tipo de Reclamação', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Quantidade:Q', title='Quantidade'),
        color='Tipo de Reclamação:N'
    ).properties(
        height=400,
        width=800
    )
    st.altair_chart(grafCombEstado)
    ```

- **Tabela Estilizada e Botão de Download**:
    ```python
    styled_df = df_ranking_top_10.style.set_table_styles([
        {'selector': 'thead th', 'props': [('font-size', '12pt'), ('font-weight', 'bold')]},
        {'selector': 'tbody td', 'props': [('font-size', '10pt')]},
    ]).set_properties(**{'text-align': 'center', 'max-width': '100px'})
    
    st.table(styled_df)
    
    st.download_button(
        label="Baixar CSV",
        data=df_ranking_top_10.to_csv(index=False).encode('utf-8'),
        file_name='df_ranking_top_10.csv',
        mime='text/csv'
    )
    ```

## Contribuições

Sinta-se à vontade para contribuir com melhorias para este projeto. Você pode fazer isso através de issues e pull requests.

## Licença

Este projeto está licenciado sob os termos da licença MIT.
