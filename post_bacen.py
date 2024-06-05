import streamlit as st

# Estilo para o título
st.markdown("""
    <style>
        .title {
            font-size: 36px;
            font-weight: bold;
            color: #00b8a9;
            text-align: center;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown('<h1 class="title">Explorando Reclamações do BACEN com Streamlit</h1>', unsafe_allow_html=True)

# Estilo para o texto
st.markdown("""
    <style>
        .text {
            font-size: 18px;
            color: #2e2e2e;
            text-align: justify;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Texto
st.markdown("""
    <p class="text">Neste post, vamos explorar como usar o Streamlit, uma biblioteca de código aberto para criação de aplicativos da web com Python, para analisar e visualizar dados de reclamações registradas no Banco Central do Brasil (BACEN).</p>
    <p class="text">Com o Streamlit, podemos criar uma interface de usuário simples e interativa para explorar os dados de maneira eficiente e intuitiva.</p>
""", unsafe_allow_html=True)

# Estilo para subtítulo
st.markdown("""
    <style>
        .subtitle {
            font-size: 24px;
            font-weight: bold;
            color: #00b8a9;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Subtítulo
st.markdown('<h2 class="subtitle">Passo a Passo da Funcionalidade</h2>', unsafe_allow_html=True)

# Lista numerada
st.markdown("""
    <p class="text">1. <strong>Carregando os Dados:</strong> Utilizamos a função <code>load_data()</code> para fazer uma requisição HTTP para o endpoint JSON do BACEN e carregar os dados das reclamações em um DataFrame do Pandas.</p>
    <p class="text">2. <strong>Sidebar de Filtros:</strong> Na barra lateral do aplicativo, oferecemos opções para filtrar os dados por tipo de instituição, ano, periodicidade e período.</p>
    <p class="text">3. <strong>Gráfico Interativo:</strong> Com base nos filtros selecionados, criamos um gráfico interativo utilizando a biblioteca Altair. O usuário pode escolher uma empresa para visualizar a quantidade de reclamações reguladas procedentes, reguladas - outras e não reguladas.</p>
    <p class="text">4. <strong>Tabela de Ranking:</strong> Apresentamos uma tabela com o ranking das instituições financeiras com base no índice de reclamações. Este índice é calculado como o número de reclamações dividido pelo número de consorciados ativos e multiplicado por 1.000.000.</p>
    <p class="text">5. <strong>Estilo da Tabela:</strong> Estilizamos a tabela para melhorar a legibilidade e apresentação dos dados. Isso inclui ajustes de tamanho, alinhamento e formatação do texto.</p>
    <p class="text">6. <strong>Download do CSV:</strong> Por fim, adicionamos um botão de download para permitir que o usuário baixe os dados da tabela em formato CSV.</p>
""", unsafe_allow_html=True)

# Estilo para a conclusão
st.markdown("""
    <style>
        .conclusion {
            font-size: 20px;
            color: #2e2e2e;
            text-align: justify;
            margin-top: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# Conclusão
st.markdown("""
    <p class="conclusion">Com este aplicativo web, os usuários podem explorar e entender melhor as reclamações registradas no BACEN. A interface simples e intuitiva fornecida pelo Streamlit torna a análise de dados mais acessível, permitindo que usuários de diferentes níveis de habilidade interajam com os dados de maneira eficaz.</p>
    <p class="conclusion">Esperamos que este post tenha sido útil e inspirador para você começar a criar seus próprios aplicativos de análise de dados com Python e Streamlit!</p>
""", unsafe_allow_html=True)
