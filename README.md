# Análise de Reclamações do BACEN com Streamlit

Este projeto utiliza o Streamlit para criar uma interface interativa que permite analisar dados de reclamações de instituições financeiras registradas no Banco Central do Brasil (BACEN). O aplicativo permite ao usuário filtrar e visualizar dados específicos de acordo com o ano, periodicidade, período e tipo de instituição. Além disso, oferece a possibilidade de baixar o ranking das instituições com mais reclamações.

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
  
## 💖 Contribua!

Ajude a fortalecer o desenvolvimento seguro! Sua contribuição faz a diferença no futuro da MSCHelp.

Clique no link abaixo para fazer sua doação:

[**Faça uma doação no PayPal**](https://www.paypal.com/donate/?business=3ZQZK7TPGPSAA&no_recurring=0&item_name=Ajude+a+fortalecer+o+desenvolvimento+seguro%21+Sua+contribui%C3%A7%C3%A3o+faz+a+diferen%C3%A7a+no+futuro+da+MSCHelp.&currency_code=BRL)

      
## Contribuições

Sinta-se à vontade para contribuir com melhorias para este projeto. Você pode fazer isso através de issues e pull requests.

## Licença

Este projeto está licenciado sob os termos da licença MIT.
