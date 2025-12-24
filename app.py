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
    
    return df

# ================= FUNÇÃO PARA FORMATAR NÚMEROS NO PADRÃO BRASILEIRO =================
def formatar_numero_brasileiro(valor):
    """
    Formata números no padrão brasileiro: 1.234,56
    """
    if pd.isna(valor):
        return ""
    
    try:
        # Se já for string formatada, retorna como está
        if isinstance(valor, str):
            # Verifica se já está no formato brasileiro
            if ',' in valor and '.' in valor:
                return valor
            # Se for string numérica, converte
            try:
                num = float(valor.replace('.', '').replace(',', '.'))
            except:
                num = float(valor)
        else:
            num = float(valor)
        
        # Formata com separador de milhar e 2 casas decimais
        return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

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

# ================= CONVERTER ÍNDICE PARA NÚMERO (PARA ORDENAÇÃO) =================
if 'Índice' in df_csv.columns:
    # Criar cópia para exibição com formatação brasileira
    df_csv_display = df_csv.copy()
    
    # Converter para numérico para ordenação (removendo pontos de milhar e convertendo vírgula para ponto decimal)
    df_csv['Índice_num'] = pd.to_numeric(
        df_csv['Índice']
        .astype(str)
        .str.replace(r'\.', '', regex=True)  # Remove pontos (separadores de milhar)
        .str.replace(',', '.', regex=False),  # Substitui vírgula por ponto (decimal)
        errors='coerce'
    )
    
    # Manter a formatação original para exibição
    df_csv_display['Índice_formatado'] = df_csv['Índice'].apply(formatar_numero_brasileiro)
else:
    df_csv_display = df_csv.copy()

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

# Encontrar dados da empresa
if 'Índice_num' in df_csv.columns:
    idx = df_csv[df_csv[coluna_instituicao] == empresa].index[0]
    dados_empresa = df_csv_display.iloc[idx]
else:
    dados_empresa = df_csv[df_csv[coluna_instituicao] == empresa].iloc[0]

# ================= EXIBIR DADOS DA EMPRESA =================
col1, col2, col3 = st.columns(3)

with col1:
    if 'Índice_formatado' in dados_empresa:
        st.metric("Índice", dados_empresa['Índice_formatado'])
    elif 'Índice' in dados_empresa:
        st.metric("Índice", formatar_numero_brasileiro(dados_empresa['Índice']))

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
    # Converter valores para numérico para o gráfico
    dados_para_grafico = {}
    for col in colunas_grafico:
        if col in dados_empresa:
            try:
                # Tentar converter para número
                valor = pd.to_numeric(str(dados_empresa[col]).replace('.', '').replace(',', '.'), errors='coerce')
                dados_para_grafico[col] = valor if not pd.isna(valor) else 0
            except:
                dados_para_grafico[col] = 0
    
    if dados_para_grafico and sum(dados_para_grafico.values()) > 0:
        df_grafico = pd.DataFrame(list(dados_para_grafico.items()), columns=['Tipo de Reclamação', 'Quantidade'])
        
        # Mapear nomes amigáveis
        mapeamento_nomes = {
            'Reguladas Procedentes': 'Reguladas Procedentes',
            'Reguladas Outras': 'Reguladas Outras',
            'Não Reguladas': 'Não Reguladas'
        }
        df_grafico["Tipo de Reclamação"] = df_grafico["Tipo de Reclamação"].map(mapeamento_nomes)
        
        grafico = alt.Chart(df_grafico).mark_bar().encode(
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
if 'Índice_num' in df_csv.columns:
    # Criar DataFrame para ranking
    df_ranking = df_csv.copy()
    
    # Ordenar por índice numérico (decrescente)
    df_ranking = df_ranking.sort_values("Índice_num", ascending=False).reset_index(drop=True)
    
    # Adicionar coluna de ranking
    df_ranking.insert(0, "Rank", [f"{i+1}º" for i in df_ranking.index])
    
    # Formatar índice no padrão brasileiro
    df_ranking["Índice"] = df_ranking["Índice"].apply(formatar_numero_brasileiro)
    
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
            "Índice": st.column_config.TextColumn(
                "Índice",
                help="Índice de reclamações (formato brasileiro: ponto separador de milhar, vírgula decimal)"
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
elif 'Índice' in df_csv.columns:
    # Se não tiver a coluna numérica, usar a original
    df_ranking = df_csv.copy()
    
    # Tentar ordenar convertendo na hora
    df_ranking['Índice_num_temp'] = pd.to_numeric(
        df_ranking['Índice']
        .astype(str)
        .str.replace(r'\.', '', regex=True)
        .str.replace(',', '.', regex=False),
        errors='coerce'
    )
    
    df_ranking = df_ranking.sort_values("Índice_num_temp", ascending=False).reset_index(drop=True)
    df_ranking = df_ranking.drop(columns=['Índice_num_temp'])
    
    # Adicionar coluna de ranking
    df_ranking.insert(0, "Rank", [f"{i+1}º" for i in df_ranking.index])
    
    # Formatar os números
    df_ranking["Índice"] = df_ranking["Índice"].apply(formatar_numero_brasileiro)
    
    # Resto do código igual...
else:
    st.warning("Não foi possível gerar o ranking - coluna 'Índice' não encontrada.")

# ================= INFORMAÇÕES ADICIONAIS =================
with st.expander("ℹ️ Informações sobre os dados"):
    st.markdown("""
    ### Sobre os dados:
    - **Índice**: Medida calculada pelo BACEN que considera o volume de reclamações em relação ao tamanho da instituição. 
      Formato brasileiro: **5.151,45** (ponto separador de milhar, vírgula separador decimal)
    - **Reguladas Procedentes**: Reclamações onde o cliente tinha razão
    - **Reguladas Outras**: Reclamações reguladas mas não procedentes
    - **Não Reguladas**: Reclamações fora do escopo de regulação do BACEN
    
    ### Fonte:
    Dados obtidos diretamente do Banco Central do Brasil (BACEN)
    
    ### Período:
    """ + f"{periodicidade} - {periodo}/{ano}")
