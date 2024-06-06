import streamlit as st
import requests
import pandas as pd
import io
import chardet
import altair as alt
from PIL import Image, ImageDraw, ImageOps

# Configurar layout da página
st.set_page_config(layout="wide")

# Função para carregar os dados do JSON
def load_data():
    json_url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
    response = requests.get(json_url)
    data = response.json()
    df = pd.json_normalize(
        data,
        record_path=['anos', 'periodicidades', 'periodos', 'tipos'],
        meta=[['anos', 'ano'], ['anos', 'periodicidades', 'periodicidade'], ['anos', 'periodicidades', 'periodos', 'periodo']],
        meta_prefix=''
    )
    df.columns = ['tipo', 'ano', 'periodicidade', 'periodo']
    return df

# Função para gerar o link do CSV com base nos filtros
def gerar_link_csv(ano, periodicidade, periodo, tipo):
    base_url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo"
    return f"{base_url}?ano={ano}&periodicidade={periodicidade}&periodo={periodo}&tipo={tipo}"

def cantos_arredondados(image, radius):
    # Criar uma máscara com cantos arredondados
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width, image.height), radius, fill=255)

    # Aplicar a máscara à imagem
    result = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    result.putalpha(mask)

    return result
# Sidebar para filtro
with st.sidebar:
    st.subheader('BASES DE RECLAMAÇÕES DO BACEN')
    logo = Image.open('logo.png').convert("RGBA")  
    rounded_logo = cantos_arredondados(logo, 20)
    st.image(rounded_logo, use_column_width=True)
    
    # Carregar os dados
    df = load_data()

    # Obtendo listas únicas de tipos, anos e periodicidades
    tipos_unicos = df['tipo'].unique().tolist()

    # Criando widgets dropdown para seleção
    tipo_dropdown = st.selectbox('Selecione o tipo:', options=tipos_unicos, index=1)  # Define 'Consorcio' como a opção padrão
    ano_dropdown = st.selectbox('Selecione o ano:', options=df[df['tipo'] == tipo_dropdown]['ano'].unique().tolist(), index=9)
    periodicidade_dropdown = st.selectbox('Selecione a periodicidade:', options=df[(df['tipo'] == tipo_dropdown) & (df['ano'] == ano_dropdown)]['periodicidade'].unique().tolist())
    periodo_dropdown = st.selectbox('Selecione o período:', options=df[(df['tipo'] == tipo_dropdown) & (df['ano'] == ano_dropdown) & (df['periodicidade'] == periodicidade_dropdown)]['periodo'].unique().tolist())

# Gerar o link do CSV com base nos valores selecionados
csv_url = gerar_link_csv(ano_dropdown, periodicidade_dropdown, periodo_dropdown, tipo_dropdown)

# Fazer o download do arquivo CSV
response = requests.get(csv_url)
response.raise_for_status()

# Detectar a codificação do arquivo CSV
encoding = chardet.detect(response.content)['encoding']

# Tentar diferentes delimitadores para o CSV
delimiters = [';', ',', '\t', '|', ' ']
for delimiter in delimiters:
    try:
        csv_content = response.content.decode(encoding)
        df_csv = pd.read_csv(io.StringIO(csv_content), sep=delimiter)
        break
    except Exception as e:
        continue

# Identificar as colunas necessárias
colunas_possiveis = {
    'Instituição financeira': ['Instituição financeira', 'Índice', 'Quantidade de reclamações reguladas procedentes', 'Quantidade de reclamações reguladas - outras', 'Quantidade de reclamações não reguladas', 'Quantidade total de reclamações'],
    'Administradora de consórcio': ['Administradora de consórcio', 'Índice','Quantidade de reclamações reguladas procedentes', 'Quantidade de reclamações reguladas - outras', 'Quantidade de reclamações não reguladas', 'Quantidade total de reclamações']
}

coluna_empresa = None
for key, value in colunas_possiveis.items():
    if key in df_csv.columns:
        coluna_empresa = key
        colunas_selecionadas = value
        break

if coluna_empresa:
    df_csv = df_csv[colunas_selecionadas]
else:
    st.write("As colunas necessárias não estão presentes no arquivo CSV.")
    st.stop()

# Header e descrição
st.header('BACEN: Empresa x Quantidade de Reclamações')
fAdms = st.selectbox("Selecione a Empresa:", options=df_csv[coluna_empresa].unique())

dadosUsuario = df_csv[df_csv[coluna_empresa] == fAdms]

st.markdown(f'**Empresa**: {fAdms}')

# Ajustar os dados para o gráfico
dadosUsuario = dadosUsuario.melt(id_vars=[coluna_empresa], value_vars=['Quantidade de reclamações reguladas procedentes', 'Quantidade de reclamações reguladas - outras', 'Quantidade de reclamações não reguladas'], var_name='Tipo de Reclamação', value_name='Quantidade')

# Reduzir o nome das legendas do gráfico
dadosUsuario['Tipo de Reclamação'] = dadosUsuario['Tipo de Reclamação'].replace({
    'Quantidade de reclamações reguladas procedentes': 'Reguladas Procedentes',
    'Quantidade de reclamações reguladas - outras': 'Reguladas Outras',
    'Quantidade de reclamações não reguladas': 'Não Reguladas'
})

# Construir gráfico com Altair
grafCombEstado = alt.Chart(dadosUsuario).mark_bar().encode(
    x=alt.X('Tipo de Reclamação:N', title='Tipo de Reclamação', axis=alt.Axis(labelAngle=-45)),
    y=alt.Y('Quantidade:Q', title='Quantidade'),
    color='Tipo de Reclamação:N'
).properties(
    height=400,
    width=800
)

st.altair_chart(grafCombEstado)




# Exibir as primeiras linhas do DataFrame
st.markdown('<h2 style="font-size: 26px;">Ranking de Reclamações</h2>', unsafe_allow_html=True)

# Remover pontos (separadores de milhar) e substituir vírgulas por pontos (separadores decimais)
df_csv['Índice'] = df_csv['Índice'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
# Converter a coluna para numérico
df_csv['Índice'] = pd.to_numeric(df_csv['Índice'], errors='coerce')
# Ordenar a coluna do maior para o menor
df_ranking = df_csv.sort_values(by='Índice', ascending=False)
# Selecionar apenas as 10 primeiras linhas, resetar o índice e adicionar 1 ao índice
df_ranking_top_10 = df_ranking.head(10).reset_index(drop=True)
# Adicionar 1 ao índice
#df_ranking_top_10.index += 1 
# Criar um novo índice com o formato "1º", "2º", etc.
#df_ranking_top_10.index = [f"{i+1}º" for i in df_ranking_top_10.index]
#df_ranking_top_10.index.name = 'Rank'
# Criar a coluna "Rank" com o formato "1º", "2º", etc.
df_ranking_top_10['Rank'] = [f"{i+1}º" for i in df_ranking_top_10.index]
# Reordenar as colunas para que "Rank" seja a primeira coluna
cols = ['Rank'] + [col for col in df_ranking_top_10.columns if col != 'Rank']
df_ranking_top_10 = df_ranking_top_10[cols]
# Formatar a coluna 'Índice' para exibir dois números após a vírgula
df_ranking_top_10['Índice'] = df_ranking_top_10['Índice'].map(lambda x: f"{x:.2f}")



# Renomear as colunas
df_ranking_top_10 = df_ranking_top_10.rename(columns={
    'Instituição financeira': 'Instituição Financeira',
    'Administradora de consórcio': 'Administradora de Consórcio',
    'Índice': 'Índice <span style="cursor: pointer;" title="Número de reclamações dividido pelo número de consorciados ativos e multiplicado por 1.000.000">ℹ️</span>', 
    'Quantidade de reclamações reguladas procedentes': 'Reguladas Procedentes',
    'Quantidade de reclamações reguladas - outras': 'Reguladas Outras',
    'Quantidade de reclamações não reguladas': 'Não Reguladas',
    'Quantidade total de reclamações': 'Total'
})

#Estilo da tabela
#styled_df = df_ranking_top_10.style.set_table_styles([
#    {'selector': 'thead th', 'props': [('font-size', '12pt'), ('font-weight', 'bold'), ('text-align', 'center')]},
#    {'selector': 'tbody td', 'props': [('font-size', '10pt'), ('text-align', 'center')]},
#    {'selector': 'td.col0', 'props': [('max-width', 'none'), ('white-space', 'pre-wrap'), ('text-align', 'center'),  ('font-weight', 'bold')]},
#    {'selector': 'td.col1', 'props': [('max-width', '1000px'), ('white-space', 'normal'), ('text-align', 'left')]},  # Alinhamento à esquerda
#    {'selector': 'td.col2, td.col3, td.col4, td.col5, td.col6', 'props': [('max-width', 'none'), ('text-align', 'center')]},  # Alinhamento centralizado para as demais colunas
#]).set_properties(**{'white-space': 'pre-wrap', 'text-overflow': 'ellipsis'})


# Definindo o estilo da tabela
styled_df = df_ranking_top_10.style.set_table_styles([
    {'selector': 'thead th', 'props': [('font-size', '12pt'), ('font-weight', 'bold'), ('text-align', 'center'), ('background-color', '#404040'), ('color', 'white')]},  # Cor cinza escuro no cabeçalho
    {'selector': 'tbody td', 'props': [('font-size', '10pt'), ('text-align', 'center')]},
    {'selector': 'td.col0, td.col1', 'props': [('max-width', '1000px'), ('white-space', 'normal'), ('text-align', 'left'), ('background-color', '#F2F2F2')]},  # Cor cinza claro na coluna 0 e 1
    {'selector': 'td.col0', 'props': [('font-weight', 'bold')]},  # Mantendo a coluna de rank em negrito
    {'selector': 'tbody tr:nth-child(even) td:not(.col0)', 'props': [('background-color', '#F2F2F2')]},  # Cor cinza claro nas células das demais colunas
    {'selector': 'tbody tr:nth-child(odd) td:not(.col0)', 'props': [('background-color', 'white')]},  # Cor branca intercalada nas células das demais colunas
    {'selector': 'td.col1', 'props': [('max-width', '1000px'), ('white-space', 'normal'), ('text-align', 'left')]},  # Propriedades da coluna 1
    {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('border', '2px solid #D3D3D3')]}  # Borda moderna
]).set_properties(**{'white-space': 'pre-wrap', 'text-overflow': 'ellipsis'})

# Exibir a tabela estilizada sem o índice
st.markdown(styled_df.hide(axis='index').to_html(escape=False), unsafe_allow_html=True)

# Exibir a tabela estilizada
#st.markdown(styled_df.to_html(escape=False), unsafe_allow_html=True)

# Adicionar uma quebra de linha
st.markdown("")  

# Adicionar um botão de download para o CSV
st.download_button(
    label="Baixar CSV",
    data=df_ranking_top_10.to_csv(index=False).encode('utf-8'),
    file_name='df_ranking_top_10.csv',
    mime='text/csv'
)
