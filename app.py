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
    
    # TENTATIVA 1: Detectar delimitador automaticamente
    try:
        delimiter = Sniffer().sniff(csv_text[:10000]).delimiter
    except Exception:
        delimiter = ";"
    
    # TENTATIVA 2: Ler o CSV
    try:
        df = pd.read_csv(io.StringIO(csv_text), sep=delimiter, dtype=str, on_bad_lines='warn')
    except Exception as e:
        st.warning(f"Tentativa 1 falhou: {str(e)[:100]}... Tentando método alternativo.")
        
        # TENTATIVA 3: Tentar com diferentes delimitadores
        for delim in [';', ',', '\t', '|']:
            try:
                df = pd.read_csv(io.StringIO(csv_text), sep=delim, dtype=str, on_bad_lines='warn')
                if df.shape[1] > 1:  # Se encontrou mais de uma coluna
                    break
            except:
                continue
        
        # TENTATIVA 4: Se nada funcionar, tentar ler linha por linha
        try:
            lines = csv_text.strip().split('\n')
            # Encontrar o cabeçalho
            for i, line in enumerate(lines):
                if ';' in line and ('Instituição' in line or 'Índice' in line):
                    header_line = i
                    break
            else:
                header_line = 0
            
            # Ler a partir do cabeçalho
            df = pd.read_csv(io.StringIO('\n'.join(lines[header_line:])), sep=';', dtype=str)
        except Exception as e2:
            st.error(f"Não foi possível ler o arquivo CSV. Erro: {str(e2)[:200]}")
            # Retornar DataFrame vazio
            return pd.DataFrame()
    
    return df

# ================= FUNÇÃO PARA LIMPAR DADOS =================
def limpar_dados_csv(df):
    """
    Limpa e padroniza o DataFrame baixado do BACEN
    """
    if df.empty:
        return df
    
    # Fazer uma cópia para não modificar o original
    df = df.copy()
    
    # Remover colunas completamente vazias
    df = df.dropna(axis=1, how='all')
    
    # Remover linhas completamente vazias
    df = df.dropna(how='all')
    
    # Remover apenas colunas de índice do pandas (Unnamed: 0, etc.)
    colunas_para_remover = []
    for col in df.columns:
        if str(col).strip() in ['', 'Unnamed: 0', 'Unnamed: 0.1', 'index', 'Unnamed: 0.1.1']:
            colunas_para_remover.append(col)
    
    df = df.drop(columns=colunas_para_remover, errors='ignore')
    
    # Padronizar nomes de colunas - MANTENDO TODAS AS COLUNAS ORIGINAIS
    colunas_mapeamento = {
        'Instituição financeira': 'Instituição',
        'Administradora de consórcio': 'Instituição',
        'Instituição Financeira': 'Instituição',
        'Administradora de Consórcio': 'Instituição',
        'Índice': 'Índice'
    }
    
    # Renomear apenas as colunas principais
    df = df.rename(columns={col: colunas_mapeamento.get(col, col) for col in df.columns})
    
    # Garantir que todas as colunas sejam strings
    for col in df.columns:
        df[col] = df[col].astype(str)
    
    return df

# ================= FUNÇÃO PARA FORMATAR NÚMEROS NO PADRÃO BRASILEIRO =================
def formatar_numero_brasileiro(valor):
    """
    Formata números no padrão brasileiro: 1.234,56
    """
    if pd.isna(valor) or str(valor).strip() in ['', 'nan', 'None', 'NaN']:
        return ""
    
    try:
        # Se já for string formatada, retorna como está
        if isinstance(valor, str):
            valor_str = str(valor).strip()
            # Verifica se já está no formato brasileiro (tem vírgula como decimal)
            if ',' in valor_str and valor_str.replace(',', '').replace('.', '').replace('-', '').isdigit():
                # Garantir que está formatado corretamente
                try:
                    # Remover pontos de milhar existentes
                    if '.' in valor_str and ',' in valor_str:
                        # Verificar qual é o separador decimal
                        if valor_str.rfind('.') > valor_str.rfind(','):
                            # Ponto é o separador decimal, vírgula é milhar
                            num = float(valor_str.replace(',', '').replace('.', '').replace(',', '.'))
                        else:
                            # Vírgula é o separador decimal
                            num = float(valor_str.replace('.', '').replace(',', '.'))
                    elif ',' in valor_str:
                        # Apenas vírgula, provavelmente é decimal
                        num = float(valor_str.replace('.', '').replace(',', '.'))
                    else:
                        # Apenas número
                        num = float(valor_str)
                except:
                    num = float(valor_str.replace('.', '').replace(',', '.'))
            else:
                # Tentar converter para número
                try:
                    num = float(valor_str.replace('.', '').replace(',', '.'))
                except:
                    return valor_str
        else:
            num = float(valor)
        
        # Formata com separador de milhar e 2 casas decimais
        if num >= 1000:
            return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{num:.2f}".replace(".", ",")
    except Exception as e:
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

try:
    df_csv = baixar_csv(csv_url)
except Exception as e:
    st.error(f"Erro ao baixar o CSV: {str(e)[:200]}")
    st.info(f"URL do CSV: {csv_url}")
    st.stop()

if df_csv.empty or df_csv.shape[0] == 0 or df_csv.shape[1] == 0:
    st.warning("O ranking para este período ainda não possui dados ou o formato do arquivo é incompatível.")
    st.info(f"Tente selecionar um período diferente. URL do CSV: {csv_url}")
    st.stop()

# ================= LIMPAR DADOS =================
df_csv = limpar_dados_csv(df_csv)

if df_csv.empty:
    st.warning("Não foi possível processar os dados do CSV.")
    st.stop()

# Mostrar colunas disponíveis na sidebar para debug
st.sidebar.markdown("---")
st.sidebar.markdown("**Colunas disponíveis no CSV:**")
for col in df_csv.columns:
    st.sidebar.text(f"- {col}")

# Identificar qual coluna contém o nome da instituição
coluna_instituicao = None
possiveis_colunas = ['Instituição', 'Instituição financeira', 'Administradora de consórcio', 
                     'Instituição Financeira', 'Administradora de Consórcio']

for col in possiveis_colunas:
    if col in df_csv.columns:
        coluna_instituicao = col
        break

# Se não encontrou, usar a primeira coluna que parece ser de instituição
if not coluna_instituicao:
    for col in df_csv.columns:
        if any(termo in str(col).lower() for termo in ['instituição', 'administradora', 'banco', 'financeira', 'nome']):
            coluna_instituicao = col
            break
    else:
        # Usar a primeira coluna como fallback
        coluna_instituicao = df_csv.columns[0]

# ================= CONVERTER ÍNDICE PARA NÚMERO (PARA ORDENAÇÃO) =================
if 'Índice' in df_csv.columns:
    # Criar cópia para exibição com formatação brasileira
    df_csv_display = df_csv.copy()
    
    # Converter para numérico para ordenação
    def converter_para_numerico(valor):
        if pd.isna(valor) or str(valor).strip() in ['', 'nan', 'None', 'NaN']:
            return 0
        try:
            valor_str = str(valor).strip()
            # Remover caracteres não numéricos exceto ponto, vírgula e hífen
            valor_limpo = ''.join(c for c in valor_str if c.isdigit() or c in '.,-')
            
            if ',' in valor_limpo and '.' in valor_limpo:
                # Tem ambos, decidir qual é o separador decimal
                if valor_limpo.rfind('.') > valor_limpo.rfind(','):
                    # Ponto é decimal
                    return float(valor_limpo.replace(',', ''))
                else:
                    # Vírgula é decimal
                    return float(valor_limpo.replace('.', '').replace(',', '.'))
            elif ',' in valor_limpo:
                # Apenas vírgula, assumir que é decimal
                return float(valor_limpo.replace('.', '').replace(',', '.'))
            elif '.' in valor_limpo:
                # Apenas ponto
                if valor_limpo.count('.') > 1:
                    # Múltiplos pontos, provavelmente separador de milhar
                    return float(valor_limpo.replace('.', ''))
                else:
                    # Apenas um ponto, pode ser decimal
                    return float(valor_limpo)
            else:
                return float(valor_limpo)
        except:
            return 0
    
    df_csv['Índice_num'] = df_csv['Índice'].apply(converter_para_numerico)
    
    # Manter a formatação original para exibição
    df_csv_display['Índice_formatado'] = df_csv['Índice'].apply(formatar_numero_brasileiro)
else:
    df_csv_display = df_csv.copy()

# ================= HEADER =================
st.header("📊 BACEN: Análise de Reclamações")

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
try:
    if 'Índice_num' in df_csv.columns:
        empresa_data = df_csv[df_csv[coluna_instituicao] == empresa]
        if not empresa_data.empty:
            idx = empresa_data.index[0]
            dados_empresa = df_csv_display.iloc[idx]
            dados_empresa_raw = df_csv.iloc[idx]  # Dados brutos para conversão
        else:
            st.warning(f"Empresa {empresa} não encontrada nos dados.")
            st.stop()
    else:
        dados_empresa = df_csv[df_csv[coluna_instituicao] == empresa].iloc[0]
        dados_empresa_raw = df_csv[df_csv[coluna_instituicao] == empresa].iloc[0]
except Exception as e:
    st.error(f"Erro ao buscar dados da empresa: {str(e)}")
    st.stop()

# ================= EXIBIR DADOS DA EMPRESA =================
col1, col2, col3 = st.columns(3)

with col1:
    if 'Índice_formatado' in dados_empresa:
        valor_indice = dados_empresa['Índice_formatado']
    elif 'Índice' in dados_empresa:
        valor_indice = formatar_numero_brasileiro(dados_empresa['Índice'])
    else:
        valor_indice = "N/A"
    
    st.metric("Índice", valor_indice)

# Função para extrair valores numéricos das colunas
def extrair_valor_numerico(valor, default=0):
    if pd.isna(valor) or str(valor).strip() in ['', 'nan', 'None', 'NaN']:
        return default
    try:
        valor_str = str(valor).strip()
        # Remover pontos (separadores de milhar) e converter vírgula para ponto decimal
        valor_limpo = valor_str.replace('.', '').replace(',', '.')
        return float(valor_limpo)
    except:
        try:
            # Tentar converter diretamente
            return float(valor_str)
        except:
            return default

# ================= IDENTIFICAR COLUNAS DE RECLAMAÇÕES =================

# Lista de padrões para buscar colunas de reclamações
padroes_reclamacoes = {
    'Reguladas Procedentes': ['procedente', 'regulada.*procedente', 'reclamações.*procedente'],
    'Reguladas Outras': ['regulada.*outra', 'outra.*regulada', 'reclamações.*outra'],
    'Não Reguladas': ['não.*regulada', 'nao.*regulada', 'não regulada', 'nao regulada', 'reclamações.*não.*regulada'],
    'Total Reclamações': ['total.*reclamação', 'reclamações.*total', 'quantidade.*total']
}

# Buscar colunas correspondentes aos padrões
colunas_encontradas = {}

for tipo_nome, padroes in padroes_reclamacoes.items():
    for col in df_csv.columns:
        col_lower = str(col).lower()
        for padrao in padroes:
            if padrao in col_lower:
                colunas_encontradas[tipo_nome] = col
                break
        if tipo_nome in colunas_encontradas:
            break

# Se não encontrou pelo padrão, tentar nomes exatos
nomes_exatos = {
    'Reguladas Procedentes': 'Quantidade de reclamações reguladas procedentes',
    'Reguladas Outras': 'Quantidade de reclamações reguladas - outras',
    'Não Reguladas': 'Quantidade de reclamações não reguladas',
    'Total Reclamações': 'Quantidade total de reclamações'
}

for tipo_nome, nome_exato in nomes_exatos.items():
    if tipo_nome not in colunas_encontradas and nome_exato in df_csv.columns:
        colunas_encontradas[tipo_nome] = nome_exato

# Mostrar quais colunas foram encontradas
st.sidebar.markdown("**Colunas de reclamações identificadas:**")
for tipo, coluna in colunas_encontradas.items():
    st.sidebar.text(f"- {tipo}: {coluna}")

# Buscar valores para cada tipo de reclamação
valores_reclamacoes = {}

for tipo_nome, coluna_nome in colunas_encontradas.items():
    if coluna_nome in dados_empresa:
        valor = extrair_valor_numerico(dados_empresa[coluna_nome])
        valores_reclamacoes[tipo_nome] = valor
    else:
        valores_reclamacoes[tipo_nome] = 0

# Exibir métricas
with col2:
    valor_rp = int(valores_reclamacoes.get('Reguladas Procedentes', 0))
    st.metric("Reguladas Procedentes", f"{valor_rp:,}".replace(",", "."))

with col3:
    valor_nr = int(valores_reclamacoes.get('Não Reguladas', 0))
    st.metric("Não Reguladas", f"{valor_nr:,}".replace(",", "."))

# # ================= GRÁFICO DE RECLAMAÇÕES =================
# st.markdown("## 📈 Distribuição de Reclamações")

# # Preparar dados para o gráfico
# dados_grafico = []

# tipos_grafico = ['Reguladas Procedentes', 'Reguladas Outras', 'Não Reguladas']
# for tipo_grafico in tipos_grafico:
#     valor = valores_reclamacoes.get(tipo_grafico, 0)
#     # Mostrar no gráfico mesmo se for 0, para visualização completa
#     dados_grafico.append({
#         'Tipo de Reclamação': tipo_grafico,
#         'Quantidade': valor
#     })

# # Verificar se há dados para mostrar
# total_reclamacoes = sum(valores_reclamacoes.values())

# if total_reclamacoes > 0:
#     df_grafico = pd.DataFrame(dados_grafico)
    
#     # Criar gráfico
#     grafico = alt.Chart(df_grafico).mark_bar().encode(
#         x=alt.X('Tipo de Reclamação:N', title='Tipo de Reclamação', sort=None),
#         y=alt.Y('Quantidade:Q', title='Quantidade'),
#         color=alt.Color('Tipo de Reclamação:N', 
#                        scale=alt.Scale(range=['#00aca8', '#1d2262', '#d4096a']),
#                        legend=alt.Legend(title="Tipo")),
#         tooltip=['Tipo de Reclamação', alt.Tooltip('Quantidade:Q', title='Quantidade', format=',.0f')]
#     ).properties(
#         title=f'Distribuição de Reclamações - {empresa}',
#         height=400
#     )
    
#     # Adicionar valores no topo das barras
#     texto = grafico.mark_text(
#         align='center',
#         baseline='bottom',
#         dy=-5,
#         fontSize=12,
#         fontWeight='bold',
#         color='white'
#     ).encode(
#         text=alt.Text('Quantidade:Q', format=',.0f')
#     )
    
#     st.altair_chart(grafico + texto, use_container_width=True)
# else:
#     # Mostrar gráfico mesmo com zeros, mas com mensagem
#     df_grafico = pd.DataFrame(dados_grafico)
    
#     grafico = alt.Chart(df_grafico).mark_bar().encode(
#         x=alt.X('Tipo de Reclamação:N', title='Tipo de Reclamação', sort=None),
#         y=alt.Y('Quantidade:Q', title='Quantidade'),
#         color=alt.Color('Tipo de Reclamação:N', 
#                        scale=alt.Scale(range=['#00aca8', '#1d2262', '#d4096a']),
#                        legend=alt.Legend(title="Tipo"))
#     ).properties(
#         title=f'Distribuição de Reclamações - {empresa} (Sem reclamações registradas)',
#         height=400
#     )
    
#     st.altair_chart(grafico, use_container_width=True)
#     st.info(f"A empresa {empresa} não possui reclamações registradas no período selecionado.")

# ... (código anterior permanece igual até a parte do gráfico) ...

# ================= GRÁFICO DE RECLAMAÇÕES =================
st.markdown("## 📈 Distribuição de Reclamações")

# Preparar dados para o gráfico
dados_grafico = []

tipos_grafico = ['Reguladas Procedentes', 'Reguladas Outras', 'Não Reguladas']
for tipo_grafico in tipos_grafico:
    valor = valores_reclamacoes.get(tipo_grafico, 0)
    # Mostrar no gráfico mesmo se for 0, para visualização completa
    dados_grafico.append({
        'Tipo de Reclamação': tipo_grafico,
        'Quantidade': valor
    })

# Verificar se há dados para mostrar
total_reclamacoes = sum(valores_reclamacoes.values())

if total_reclamacoes > 0:
    df_grafico = pd.DataFrame(dados_grafico)
    
    # Criar gráfico com configurações para não cortar
    grafico = alt.Chart(df_grafico).mark_bar(
        size=60  # Aumentar a largura das barras
    ).encode(
        x=alt.X('Tipo de Reclamação:N', 
               title='Tipo de Reclamação', 
               sort=None,
               axis=alt.Axis(labelAngle=0)),  # Manter labels horizontais
        y=alt.Y('Quantidade:Q', 
               title='Quantidade',
               scale=alt.Scale(padding=0.2)),  # Adicionar padding no eixo Y
        color=alt.Color('Tipo de Reclamação:N', 
                       scale=alt.Scale(range=['#00aca8', '#1d2262', '#d4096a']),
                       legend=alt.Legend(title="Tipo de Reclamação")),
        tooltip=['Tipo de Reclamação', alt.Tooltip('Quantidade:Q', title='Quantidade', format=',.0f')]
    ).properties(
        title=f'Distribuição de Reclamações - {empresa}',
        height=450,  # Aumentar altura
        width=600    # Definir largura fixa para melhor controle
    )
    
    # Adicionar valores no topo das barras com configuração melhorada
    texto = grafico.mark_text(
        align='center',
        baseline='middle',  # Mudar para middle para melhor posicionamento
        dy=-25,  # Ajustar posição vertical (negativo = acima da barra)
        fontSize=14,
        fontWeight='bold',
        color='white'
    ).encode(
        text=alt.Text('Quantidade:Q', format=',.0f')
    )
    
    # Combinar gráfico e texto
    chart = (grafico + texto).configure_view(
        strokeWidth=0  # Remover borda do gráfico
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        anchor='start'  # Alinhar título à esquerda
    )
    
    st.altair_chart(chart, use_container_width=True)
    
else:
    # Mostrar gráfico mesmo com zeros, mas com mensagem
    df_grafico = pd.DataFrame(dados_grafico)
    
    grafico = alt.Chart(df_grafico).mark_bar(
        size=60
    ).encode(
        x=alt.X('Tipo de Reclamação:N', 
               title='Tipo de Reclamação', 
               sort=None,
               axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Quantidade:Q', 
               title='Quantidade',
               scale=alt.Scale(domain=[0, 1])),  # Domínio fixo para zeros
        color=alt.Color('Tipo de Reclamação:N', 
                       scale=alt.Scale(range=['#00aca8', '#1d2262', '#d4096a']),
                       legend=alt.Legend(title="Tipo de Reclamação"))
    ).properties(
        title=f'Distribuição de Reclamações - {empresa} (Sem reclamações registradas)',
        height=450,
        width=600
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        anchor='start'
    )
    
    st.altair_chart(grafico, use_container_width=True)
    st.info(f"A empresa {empresa} não possui reclamações registradas no período selecionado.")

# ... (restante do código permanece igual) ...

# ================= RANKING - TABELA PRINCIPAL =================
st.markdown("## 🏆 Ranking de Reclamações")

# Garantir que temos a coluna de índice para ordenar
if 'Índice_num' in df_csv.columns:
    # Criar DataFrame para ranking
    df_ranking = df_csv.copy()
    
    # Ordenar por índice numérico (decrescente)
    df_ranking = df_ranking.sort_values("Índice_num", ascending=False).reset_index(drop=True)
    
    # Adicionar coluna de ranking
    df_ranking.insert(0, "Rank", [f"{i+1}º" for i in df_ranking.index])
    
    # Formatar índice no padrão brasileiro
    if 'Índice' in df_ranking.columns:
        df_ranking["Índice"] = df_ranking["Índice"].apply(formatar_numero_brasileiro)
    elif 'Índice_num' in df_ranking.columns:
        df_ranking["Índice"] = df_ranking["Índice_num"].apply(formatar_numero_brasileiro)
    
    # Selecionar colunas para exibir - APENAS AS 3 COLUNAS SOLICITADAS
    colunas_exibir = ["Rank", coluna_instituicao, "Índice"]
    
    # Manter apenas as colunas que existem
    colunas_exibir = [col for col in colunas_exibir if col in df_ranking.columns]
    
    # Exibir apenas top 30
    ranking_exibir = df_ranking[colunas_exibir].head(30).reset_index(drop=True)
    
    # Estilizar a tabela SEM MOSTRAR O ÍNDICE DO DATAFRAME
    st.dataframe(
        ranking_exibir,
        use_container_width=True,
        height=800,
        hide_index=True,  # <--- ISSO OCULTA O ÍNDICE
        column_config={
            coluna_instituicao: st.column_config.Column(
                "Instituição",
                width="large"
            ),
            "Índice": st.column_config.TextColumn(
                "Índice",
                help="Número de reclamações reguladas procedentes dividido pelo número de clientes e multiplicado por 1.000.000"
            ),
            "Rank": st.column_config.Column(
                "Posição",
                width="small"
            )
        }
    )
    
    # Botão para download
    try:
        csv = ranking_exibir.to_csv(index=False, sep=';', decimal=',')
        st.download_button(
            label="📥 Baixar Ranking (CSV)",
            data=csv,
            file_name=f"ranking_bacen_{ano}_{periodo}.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.warning(f"Não foi possível gerar o arquivo CSV para download: {str(e)[:100]}")
    
elif 'Índice' in df_csv.columns:
    # Se não tiver a coluna numérica, usar a original
    df_ranking = df_csv.copy()
    
    # Tentar ordenar convertendo na hora
    try:
        df_ranking['Índice_num_temp'] = df_ranking['Índice'].apply(converter_para_numerico)
        df_ranking = df_ranking.sort_values("Índice_num_temp", ascending=False).reset_index(drop=True)
        df_ranking = df_ranking.drop(columns=['Índice_num_temp'], errors='ignore')
    except:
        # Se não conseguir ordenar numericamente, manter ordem original
        pass
    
    # Adicionar coluna de ranking
    df_ranking.insert(0, "Rank", [f"{i+1}º" for i in df_ranking.index])
    
    # Formatar os números
    if 'Índice' in df_ranking.columns:
        df_ranking["Índice"] = df_ranking["Índice"].apply(formatar_numero_brasileiro)
    
    # Selecionar colunas para exibir
    colunas_exibir = ["Rank", coluna_instituicao, "Índice"]
    colunas_exibir = [col for col in colunas_exibir if col in df_ranking.columns]
    
    # Exibir apenas top 30
    ranking_exibir = df_ranking[colunas_exibir].head(30).reset_index(drop=True)
    
    # Estilizar a tabela SEM MOSTRAR O ÍNDICE
    st.dataframe(
        ranking_exibir,
        use_container_width=True,
        height=800,
        hide_index=True,  # <--- ISSO OCULTA O ÍNDICE
        column_config={
            coluna_instituicao: st.column_config.Column(
                "Instituição",
                width="large"
            ),
            "Índice": st.column_config.TextColumn(
                "Índice",
                help="Número de reclamações reguladas procedentes dividido pelo número de clientes e multiplicado por 1.000.000"
            )
        }
    )
else:
    st.warning("Não foi possível gerar o ranking - coluna 'Índice' não encontrada.")

# ================= INFORMAÇÕES ADICIONAIS =================
with st.expander("ℹ️ Informações sobre os dados"):
    st.markdown(f"""
    ### Sobre os dados:
    - **Índice**: Número de reclamações reguladas procedentes dividido pelo número de clientes e multiplicado por 1.000.000. 
    - **Reguladas Procedentes**: Reclamações onde o cliente tinha razão
    - **Reguladas Outras**: Reclamações reguladas mas não procedentes
    - **Não Reguladas**: Reclamações fora do escopo de regulação do BACEN
    
    ### Fonte:
    Dados obtidos diretamente do Banco Central do Brasil (BACEN)
    
    ### Período selecionado:
    - **Tipo**: {tipo}
    - **Ano**: {ano}
    - **Periodicidade**: {periodicidade}
    - **Período**: {periodo}
    
    ### Empresa selecionada:
    - **Nome**: {empresa}
    - **Índice**: {valor_indice}
    - **Reguladas Procedentes**: {valor_rp:,}
    - **Não Reguladas**: {valor_nr:,}
    - **Total de reclamações**: {sum(valores_reclamacoes.values()):,}
    """)

# Mostrar dados completos da empresa selecionada para debug
with st.expander("🔍 Ver dados completos da empresa selecionada"):
    st.write(f"Dados completos para **{empresa}**:")
    
    # Criar uma tabela com todos os dados da empresa
    dados_tabela = []
    for col in df_csv.columns:
        if col in dados_empresa:
            dados_tabela.append({
                'Coluna': col,
                'Valor': dados_empresa[col]
            })
    
    df_debug = pd.DataFrame(dados_tabela)
    st.dataframe(df_debug, use_container_width=True)
