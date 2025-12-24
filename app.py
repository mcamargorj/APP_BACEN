import streamlit as st
import requests
import pandas as pd
import io
import chardet
import altair as alt
from PIL import Image, ImageDraw, ImageOps
from csv import Sniffer

# ================= CONFIGURAÇÃO DA PÁGINA =================
st.set_page_config(
    page_title="Dashboard BACEN",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ================= FUNÇÕES =================
@st.cache_data
def load_data():
    url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
    response = requests.get(url)
    data = response.json()

    df = pd.json_normalize(
        data,
        record_path=['anos', 'periodicidades', 'periodos', 'tipos'],
        meta=[
            ['anos', 'ano'],
            ['anos', 'periodicidades', 'periodicidade'],
            ['anos', 'periodicidades', 'periodos', 'periodo']
        ]
    )

    df.columns = ['tipo', 'ano', 'periodicidade', 'periodo']
    return df


def gerar_link_csv(ano, periodicidade, periodo, tipo):
    base = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo"
    return f"{base}?ano={ano}&periodicidade={periodicidade}&periodo={periodo}&tipo={tipo}"


def cantos_arredondados(image, radius):
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width, image.height), radius, fill=255)
    result = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    result.putalpha(mask)
    return result

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("BASES DE RECLAMAÇÕES DO BACEN")

    logo = Image.open("logo.png").convert("RGBA")
    st.image(cantos_arredondados(logo, 20), use_column_width=True)

    df = load_data()

    # ---- Tipo
    tipos = sorted(df['tipo'].unique().tolist())
    if not tipos:
        st.error("Nenhum tipo disponível.")
        st.stop()

    tipo = st.selectbox("Selecione o tipo:", tipos)

    # ---- Ano
    anos = sorted(df[df['tipo'] == tipo]['ano'].unique().tolist())
    if not anos:
        st.error("Nenhum ano disponível.")
        st.stop()

    ano = st.selectbox("Selecione o ano:", anos, index=len(anos) - 1)

    # ---- Periodicidade
    periodicidades = df[
        (df['tipo'] == tipo) &
        (df['ano'] == ano)
    ]['periodicidade'].unique().tolist()

    if not periodicidades:
        st.error("Nenhuma periodicidade disponível.")
        st.stop()

    periodicidade = st.selectbox("Selecione a periodicidade:", periodicidades)

    # ---- Período
    periodos = df[
        (df['tipo'] == tipo) &
        (df['ano'] == ano) &
        (df['periodicidade'] == periodicidade)
    ]['periodo'].unique().tolist()

    if not periodos:
        st.warning("Não há períodos disponíveis para este filtro.")
        st.stop()

    periodo = st.selectbox("Selecione o período:", periodos, index=len(periodos) - 1)

# ================= DOWNLOAD CSV =================
csv_url = gerar_link_csv(ano, periodicidade, periodo, tipo)
response = requests.get(csv_url)
response.raise_for_status()

encoding = chardet.detect(response.content)['encoding']
csv_text = response.content.decode(encoding, errors="ignore")

try:
    delimiter = Sniffer().sniff(csv_text[:1000]).delimiter
    df_csv = pd.read_csv(io.StringIO(csv_text), sep=delimiter)
except Exception:
    st.error("Erro ao interpretar o CSV retornado pelo BACEN.")
    st.stop()

if df_csv.empty:
    st.warning("O ranking para este período ainda não possui dados.")
    st.stop()

# ================= COLUNAS =================
colunas_possiveis = {
    'Instituição financeira': [
        'Instituição financeira', 'Índice',
        'Quantidade de reclamações reguladas procedentes',
        'Quantidade de reclamações reguladas - outras',
        'Quantidade de reclamações não reguladas',
        'Quantidade total de reclamações'
    ],
    'Administradora de consórcio': [
        'Administradora de consórcio', 'Índice',
        'Quantidade de reclamações reguladas procedentes',
        'Quantidade de reclamações reguladas - outras',
        'Quantidade de reclamações não reguladas',
        'Quantidade total de reclamações'
    ]
}

coluna_empresa = None
for k, cols in colunas_possiveis.items():
    if k in df_csv.columns:
        coluna_empresa = k
        df_csv = df_csv[cols]
        break

if not coluna_empresa:
    st.error("Estrutura inesperada do CSV.")
    st.stop()

# ================= HEADER =================
st.header("BACEN: Empresa x Quantidade de Reclamações por Tipo")

empresa = st.selectbox(
    "Selecione a Empresa:",
    sorted(df_csv[coluna_empresa].unique())
)

dados_empresa = df_csv[df_csv[coluna_empresa] == empresa]

# ================= GRÁFICO =================
dados_grafico = dados_empresa.melt(
    id_vars=[coluna_empresa],
    value_vars=[
        'Quantidade de reclamações reguladas procedentes',
        'Quantidade de reclamações reguladas - outras',
        'Quantidade de reclamações não reguladas'
    ],
    var_name="Tipo de Reclamação",
    value_name="Quantidade"
)

dados_grafico["Tipo de Reclamação"] = dados_grafico["Tipo de Reclamação"].replace({
    'Quantidade de reclamações reguladas procedentes': 'Reguladas Procedentes',
    'Quantidade de reclamações reguladas - outras': 'Reguladas Outras',
    'Quantidade de reclamações não reguladas': 'Não Reguladas'
})

grafico = alt.Chart(dados_grafico).mark_bar().encode(
    x=alt.X("Tipo de Reclamação:N", axis=alt.Axis(labelAngle=-30)),
    y="Quantidade:Q",
    color=alt.Color(
        "Tipo de Reclamação:N",
        scale=alt.Scale(range=["#00aca8", "#1d2262", "#d4096a"])
    )
).properties(height=400, width=600)

texto = grafico.mark_text(dy=-5).encode(text="Quantidade:Q")

st.altair_chart(grafico + texto)

# ================= TABELA =================
st.markdown("## Ranking de Reclamações")

df_csv["Índice"] = (
    df_csv["Índice"]
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

ranking = (
    df_csv
    .sort_values("Índice", ascending=False)
    .head(30)
    .reset_index(drop=True)
)

ranking.insert(0, "Rank", [f"{i+1}º" for i in ranking.index])
ranking["Índice"] = ranking["Índice"].map(lambda x: f"{x:.2f}")

st.dataframe(ranking, use_container_width=True)

st.download_button(
    "Baixar CSV",
    ranking.to_csv(index=False).encode("utf-8"),
    "ranking_bacen.csv",
    "text/csv"
)
