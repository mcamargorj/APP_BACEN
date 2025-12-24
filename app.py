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

# ================= FUNÇÕES AUXILIARES =================
def safe_index(lista):
    return len(lista) - 1 if lista else 0


@st.cache_data
def load_data():
    url = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

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
    draw.rounded_rectangle(
        (0, 0, image.width, image.height),
        radius,
        fill=255
    )
    result = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    result.putalpha(mask)
    return result


@st.cache_data
def baixar_csv(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    encoding = chardet.detect(response.content)['encoding']
    csv_text = response.content.decode(encoding or "latin1", errors="ignore")

    try:
        delimiter = Sniffer().sniff(csv_text[:1000]).delimiter
    except Exception:
        delimiter = ";"

    df = pd.read_csv(io.StringIO(csv_text), sep=delimiter)
    return df

# ================= FUNÇÃO PARA LIMPAR DADOS =================
def limpar_dados_csv(df):
    """
    Limpa e padroniza o DataFrame baixado do BACEN
    """
    # Remover colunas completamente vazias
    df = df.dropna(axis=1, how='all')
    
    # Remover linhas completamente vazias
    df = df.dropna(how='all')
    
    # Padronizar nomes de colunas
    colunas_mapeamento = {
        'Instituição financeira': 'Instituição',
        'Administradora de consórcio': 'Instituição',
        'Índice': 'Índice',
        'Quantidade de reclamações reguladas procedentes': 'Reguladas Procedentes',
        'Quantidade de reclamações reguladas - outras': 'Reguladas Outras',
        'Quantidade de reclamações não reguladas': 'Não Reguladas',
        'Quantidade total de reclamações': 'Total Reclamações'
    }
    
    # Renomear colunas existentes
    df = df.rename(columns={col: colunas_mapeamento[col] for col in df.columns if col in colunas_mapeamento})
    
    # Converter índice para numérico
    if 'Índice' in df.columns:
        df["Índice"] = pd.to_numeric(
            df["Índice"]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False),
            errors="coerce"
        )
    
    return df

# ================= SIDEBAR =================
with st.sidebar:
    st.subheader("BASES DE RECLAMAÇÕES DO BACEN")

    try:
        logo = Image.open("logo.png").convert("RGBA")
        st.image(cantos_arredondados(logo, 20), use_column_width=True)
    except:
        st.info("Logo não encontrado")

    df_base = load_data()

    # ---- Tipo
    tipos = sorted(df_base['tipo'].dropna().unique().tolist())
    if not tipos:
        st.error("Nenhum tipo disponível.")
        st.stop()

    tipo = st.selectbox("Selecione o tipo:", tipos)

    # ---- Ano
    anos = sorted(
        df_base[df_base['tipo'] == tipo]['ano']
        .dropna()
        .unique()
        .tolist()
    )
    if not anos:
        st.error("Nenhum ano disponível.")
        st.stop()

    ano = st.selectbox("Selecione o ano:", anos, index=safe_index(anos))

    # ---- Periodicidade
    periodicidades = (
        df_base[
            (df_base['tipo'] == tipo) &
            (df_base['ano'] == ano)
        ]['periodicidade']
        .dropna()
        .unique()
        .tolist()
    )

    if not periodicidades:
        st.error("Nenhuma periodicidade disponível.")
        st.stop()

    periodicidade = st.selectbox(
        "Selecione a periodicidade:",
        periodicidades
    )

    # ---- Período
    periodos = (
        df_base[
            (df_base['tipo'] == tipo) &
            (df_base['ano'] == ano) &
            (df_base['periodicidade'] == periodicidade)
        ]['periodo']
        .dropna()
        .unique()
        .tolist()
    )

    if not periodos:
        st.warning("Não há períodos disponíveis para este filtro.")
        st.stop()

    periodo = st.selectbox(
        "Selecione o período:",
        periodos,
        index=safe_index(periodos)
    )

# ================= DOWNLOAD E LEITURA CSV =================
csv_url = gerar_link_csv(ano, periodicidade, periodo, tipo)
df_csv = baixar_csv(csv_url)

if df_csv.empty:
    st.warning("O ranking para este período ainda não possui dados.")
    st.stop()

# ================= LIMPAR DADOS =================
df_csv = limpar_dados_csv(df_csv)

# Identificar qual coluna contém o nome da instituição
coluna_instituicao = None
for col in ['Instituição', 'Instituição financeira', 'Administradora de consórcio']:
    if col in df_csv.columns:
        coluna_instituicao = col
        break

if not coluna_instituicao:
    st.error("Estrutura inesperada do CSV retornado pelo BACEN.")
    st.stop()

# ================= HEADER =================
st.header("BACEN: Empresa x Quantidade de Reclamações")

# Listar empresas disponíveis
empresas_disponiveis = sorted(df_csv[coluna_instituicao].dropna().unique())

if not empresas_disponiveis:
    st.warning("Nenhuma empresa encontrada nos dados.")
    st.stop()

empresa = st.selectbox(
    "Selecione a Empresa:",
    empresas_disponiveis
)

dados_empresa = df_csv[df_csv[coluna_instituicao] == empresa].iloc[0]

# ================= EXIBIR DADOS DA EMPRESA =================
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Índice", f"{dados_empresa.get('Índice', 0):.2f}")

# Verificar se as colunas existem antes de acessá-las
if 'Reguladas Procedentes' in df_csv.columns:
    with col2:
        st.metric("Reguladas Procedentes", int(dados_empresa.get('Reguladas Procedentes', 0)))
    
    with col3:
        st.metric("Não Reguladas", int(dados_empresa.get('Não Reguladas', 0)))

# ================= GRÁFICO (se houver dados) =================
colunas_grafico = []
if 'Reguladas Procedentes' in df_csv.columns:
    colunas_grafico.append('Reguladas Procedentes')
if 'Reguladas Outras' in df_csv.columns:
    colunas_grafico.append('Reguladas Outras')
if 'Não Reguladas' in df_csv.columns:
    colunas_grafico.append('Não Reguladas')

if colunas_grafico and empresa:
    dados_grafico = dados_empresa[colunas_grafico].reset_index()
    dados_grafico = dados_grafico.melt(
        var_name="Tipo de Reclamação",
        value_name="Quantidade"
    )
    
    if not dados_grafico.empty and dados_grafico['Quantidade'].sum() > 0:
        # Mapear nomes amigáveis
        mapeamento_nomes = {
            'Reguladas Procedentes': 'Reguladas Procedentes',
            'Reguladas Outras': 'Reguladas Outras',
            'Não Reguladas': 'Não Reguladas'
        }
        dados_grafico["Tipo de Reclamação"] = dados_grafico["Tipo de Reclamação"].map(mapeamento_nomes)
        
        grafico = alt.Chart(dados_grafico).mark_bar().encode(
            x=alt.X("Tipo de Reclamação:N", axis=alt.Axis(labelAngle=-30), sort=None),
            y=alt.Y("Quantidade:Q", title="Quantidade"),
            color=alt.Color(
                "Tipo de Reclamação:N",
                scale=alt.Scale(range=["#00aca8", "#1d2262", "#d4096a"]),
                legend=alt.Legend(title="Tipo de Reclamação")
            ),
            tooltip=['Tipo de Reclamação', 'Quantidade']
        ).properties(
            height=400,
            title=f"Reclamações - {empresa}"
        )
        
        # Adicionar texto com os valores
        texto = grafico.mark_text(
            align='center',
            baseline='bottom',
            dy=-5,
            fontSize=12,
            fontWeight='bold',
            color='white'
        ).encode(
            text=alt.Text('Quantidade:Q', format=',.0f')
        )
        
        st.altair_chart(grafico + texto, use_container_width=True)
    else:
        st.info(f"Não há dados de reclamações disponíveis para {empresa}")

# ================= RANKING =================
st.markdown("## 📊 Ranking de Reclamações")

# Garantir que temos a coluna de índice para ordenar
if 'Índice' in df_csv.columns:
    # Remover linhas sem índice
    df_ranking = df_csv.dropna(subset=["Índice"]).copy()
    
    # Ordenar por índice (decrescente)
    df_ranking = df_ranking.sort_values("Índice", ascending=False).reset_index(drop=True)
    
    # Adicionar coluna de ranking
    df_ranking.insert(0, "Rank", [f"{i+1}º" for i in df_ranking.index])
    
    # Formatar índice com 2 casas decimais
    df_ranking["Índice"] = df_ranking["Índice"].apply(lambda x: f"{x:.2f}")
    
    # Selecionar colunas para exibir
    colunas_exibir = ["Rank", coluna_instituicao, "Índice"]
    
    # Adicionar colunas de quantidade se existirem
    for col in ['Reguladas Procedentes', 'Reguladas Outras', 'Não Reguladas', 'Total Reclamações']:
        if col in df_ranking.columns:
            colunas_exibir.append(col)
    
    # Manter apenas as colunas que existem
    colunas_exibir = [col for col in colunas_exibir if col in df_ranking.columns]
    
    # Exibir apenas top 30
    ranking_exibir = df_ranking[colunas_exibir].head(30)
    
    # Estilizar a tabela
    st.dataframe(
        ranking_exibir,
        use_container_width=True,
        height=800,
        column_config={
            coluna_instituicao: st.column_config.Column(
                "Instituição",
                width="large"
            ),
            "Índice": st.column_config.NumberColumn(
                format="%.2f"
            )
        }
    )
    
    # Botão para download
    csv = ranking_exibir.to_csv(index=False, sep=';', decimal=',')
    st.download_button(
        label="📥 Baixar Ranking (CSV)",
        data=csv,
        file_name=f"ranking_bacen_{ano}_{periodo}.csv",
        mime="text/csv"
    )
else:
    st.warning("Não foi possível gerar o ranking - coluna 'Índice' não encontrada.")

# ================= INFORMAÇÕES ADICIONAIS =================
with st.expander("ℹ️ Informações sobre os dados"):
    st.markdown("""
    ### Sobre os dados:
    - **Índice**: Medida calculada pelo BACEN que considera o volume de reclamações em relação ao tamanho da instituição
    - **Reguladas Procedentes**: Reclamações onde o cliente tinha razão
    - **Reguladas Outras**: Reclamações reguladas mas não procedentes
    - **Não Reguladas**: Reclamações fora do escopo de regulação do BACEN
    
    ### Fonte:
    Dados obtidos diretamente do Banco Central do Brasil (BACEN)
    
    ### Período:
    """ + f"{periodicidade} - {periodo}/{ano}")
