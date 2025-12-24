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
    
    # Remover colunas completamente vazias
    df = df.dropna(axis=1, how='all')
    
    # Remover linhas completamente vazias
    df = df.dropna(how='all')
    
    # Remover colunas que são apenas índices numéricos
    colunas_para_remover = []
    for col in df.columns:
        if str(col).strip() in ['', 'Unnamed: 0', 'Unnamed: 0.1', 'index']:
            colunas_para_remover.append(col)
        elif df[col].astype(str).str.contains('^[0-9]+$').all():
            colunas_para_remover.append(col)
    
    df = df.drop(columns=colunas_para_remover, errors='ignore')
    
    # Padronizar nomes de colunas
    colunas_mapeamento = {
        'Instituição financeira': 'Instituição',
        'Administradora de consórcio': 'Instituição',
        'Instituição Financeira': 'Instituição',
        'Administradora de Consórcio': 'Instituição',
        'Índice': 'Índice',
        'Quantidade de reclamações reguladas procedentes': 'Reguladas Procedentes',
        'Quantidade de reclamações reguladas - outras': 'Reguladas Outras',
        'Quantidade de reclamações não reguladas': 'Não Reguladas',
        'Quantidade total de reclamações': 'Total Reclamações'
    }
    
    # Renomear colunas existentes
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
        if any(termo in str(col).lower() for termo in ['instituição', 'administradora', 'banco', 'financeira']):
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
        else:
            st.warning(f"Empresa {empresa} não encontrada nos dados.")
            st.stop()
    else:
        dados_empresa = df_csv[df_csv[coluna_instituicao] == empresa].iloc[0]
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

# Verificar se as colunas existem antes de acessá-las
quantidades_cols = ['Reguladas Procedentes', 'Reguladas Outras', 'Não Reguladas']

with col2:
    if 'Reguladas Procedentes' in dados_empresa:
        try:
            valor = int(float(str(dados_empresa['Reguladas Procedentes']).replace('.', '').replace(',', '.')))
            st.metric("Reguladas Procedentes", f"{valor:,}".replace(",", "."))
        except:
            st.metric("Reguladas Procedentes", dados_empresa.get('Reguladas Procedentes', 0))
    else:
        st.metric("Reguladas Procedentes", "N/A")

with col3:
    if 'Não Reguladas' in dados_empresa:
        try:
            valor = int(float(str(dados_empresa['Não Reguladas']).replace('.', '').replace(',', '.')))
            st.metric("Não Reguladas", f"{valor:,}".replace(",", "."))
        except:
            st.metric("Não Reguladas", dados_empresa.get('Não Reguladas', 0))
    else:
        st.metric("Não Reguladas", "N/A")

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
                help="Índice de reclamações (formato brasileiro: ponto separador de milhar, vírgula decimal)"
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
                help="Índice de reclamações"
            )
        }
    )
else:
    st.warning("Não foi possível gerar o ranking - coluna 'Índice' não encontrada.")
    # Mostrar dados brutos para debug
    with st.expander("Ver dados brutos (para debug)"):
        st.write(df_csv.head())

# ================= INFORMAÇÕES ADICIONAIS =================
with st.expander("ℹ️ Informações sobre os dados"):
    st.markdown(f"""
    ### Sobre os dados:
    - **Índice**: Medida calculada pelo BACEN que considera o volume de reclamações em relação ao tamanho da instituição. 
      Formato brasileiro: **5.151,45** (ponto separador de milhar, vírgula separador decimal)
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
    
    ### Estrutura dos dados:
    - Total de instituições: {len(df_csv)}
    - Colunas disponíveis: {', '.join(df_csv.columns.tolist())}
    """)
