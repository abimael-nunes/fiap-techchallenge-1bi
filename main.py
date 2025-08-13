import streamlit as st
import pandas as pd
import plotly.express as px
import warnings
    
warnings.filterwarnings('ignore')

# Configurar o layout da página
st.set_page_config(layout="wide")

# Título do dashboard
st.title('(FIAP) Tech Challenge: Análise de Exportação de Vinhos - Viti Brasil')

# Carregar e pré-processar os dados de exportação
try:
    df_exportacao_raw = pd.read_csv("bases/Exportacao.csv", sep=";")

    # Limpar a coluna 'País'
    df_exportacao_raw['País'] = df_exportacao_raw['País'].str.strip()

    # Separar colunas de quantidade (kg) e valor (US$)
    cols_quantidade = [col for col in df_exportacao_raw.columns if col.isnumeric()]
    df_quantidade = df_exportacao_raw[['País'] + cols_quantidade]

    # Colunas de valor têm ".1" no nome
    cols_valor = [col for col in df_exportacao_raw.columns if '.1' in col]
    df_valor = df_exportacao_raw[['País'] + cols_valor]

    # Derreter o DataFrame de quantidade
    df_quantidade_melted = df_quantidade.melt(id_vars="País",
                                              var_name="Ano",
                                              value_name="Quantidade_kg")

    # Derreter o DataFrame de valor
    # Renomear as colunas de valor para remover ".1" antes de derreter
    df_valor.columns = ['País'] + [col.replace('.1', '') for col in cols_valor]
    df_valor_melted = df_valor.melt(id_vars="País",
                                    var_name="Ano",
                                    value_name="Valor_dolar")

    # Unir os DataFrames derretidos em um só
    df_final = pd.merge(df_quantidade_melted, df_valor_melted, on=['País', 'Ano'])

    # Converter colunas para o tipo numérico e remover valores zero
    df_final['Ano'] = pd.to_numeric(df_final['Ano'])
    df_final['Quantidade_kg'] = pd.to_numeric(df_final['Quantidade_kg'])
    df_final['Valor_dolar'] = pd.to_numeric(df_final['Valor_dolar'])
    df_final = df_final[(df_final['Quantidade_kg'] > 0) & (df_final['Valor_dolar'] > 0)]

    # Filtro de anos (últimos 15 anos)
    ano_atual = df_final['Ano'].max()
    df_final = df_final[df_final['Ano'] >= (ano_atual - 15)]

    # Converter kg para Litros (1kg = 1L)
    df_final['Quantidade_litros'] = df_final['Quantidade_kg']

except FileNotFoundError:
    st.error("Arquivo 'Exportacao.csv' não encontrado. Por favor, verifique se o arquivo está no mesmo diretório.")
    st.stop()


# Adicionar filtros na barra lateral
st.sidebar.header('Filtros')

# Filtro de período
min_ano = int(df_final['Ano'].min())
max_ano = int(df_final['Ano'].max())
ano_inicio, ano_fim = st.sidebar.slider(
    "Período de Análise",
    min_value=min_ano,
    max_value=max_ano,
    value=(min_ano, max_ano)
)

# Filtro de país
paises = sorted(df_final['País'].unique())
paises.insert(0, "Todos")       # Adicionar opção para filtrar todos os países
pais_selecionado = st.sidebar.selectbox("País de Destino", paises)

# Filtrar o dataframe com base nos filtros selecionados
df_filtered = df_final[(df_final['Ano'] >= ano_inicio) & (df_final['Ano'] <= ano_fim)]
if pais_selecionado != "Todos":
    df_filtered = df_filtered[df_filtered['País'] == pais_selecionado]

# Títulos dinâmicos com base nos filtros
st.subheader(f'Dados de Exportação para {pais_selecionado} de {ano_inicio} a {ano_fim}')

# Configurar as colunas do layout
col1, col2 = st.columns(2)
col5, = st.columns(1)
col3, col4 = st.columns(2)

# Gráfico de barras com o top 10 de países por valor de exportação
df_total_paises = df_final[(df_final['Ano'] >= ano_inicio) & (df_final['Ano'] <= ano_fim)].groupby("País")["Valor_dolar"].sum().reset_index()
df_total_paises = df_total_paises.sort_values("Valor_dolar", ascending=False).head(10)
fig_top_paises = px.bar(df_total_paises, x="País", y="Valor_dolar", title=f"Top 10 Países por Valor Total de Exportação ({ano_inicio}-{ano_fim})",
                        labels={'País': 'País de Destino', 'Valor_dolar': 'Valor Total (US$)'})
col1.plotly_chart(fig_top_paises, use_container_width=True)

# Gráfico de barras para a participação de cada país no total de exportação
df_participacao_paises = (df_total_paises.set_index('País')['Valor_dolar'] / df_filtered["Valor_dolar"].sum() * 100).reset_index()
df_participacao_paises.columns = ['País', 'Participação (%)']
df_participacao_paises = df_participacao_paises.sort_values('Participação (%)', ascending=False)
fig_participacao = px.bar(df_participacao_paises, x='País', y='Participação (%)',
                          title=f'Participação dos 10 Principais Países no Valor de Exportação Total ({ano_inicio}-{ano_fim})',
                          labels={'País': 'País de Destino'})
col2.plotly_chart(fig_participacao, use_container_width=True)

# Agrupar os dados por país e somar valor e volume
df_volume_valor = df_final[(df_final['Ano'] >= ano_inicio) & (df_final['Ano'] <= ano_fim)].groupby("País").agg(
    Valor_dolar=('Valor_dolar', 'sum'),
    Quantidade_litros=('Quantidade_litros', 'sum')
).reset_index()

# Selecionar os 10 principais países por valor
df_top_10 = df_volume_valor.sort_values("Valor_dolar", ascending=False).head(10)

# Derreter o DataFrame para criar um gráfico de barras duplas
df_melted_top_10 = df_top_10.melt(id_vars="País", value_vars=['Valor_dolar', 'Quantidade_litros'], var_name='Métrica', value_name='Valor')

# Criar o gráfico de barras com métrica (Valor ou Volume) como a cor
fig_double_bar = px.bar(
    df_melted_top_10,
    x='País',
    y='Valor',
    color='Métrica',
    barmode='group',
    title='Volume e Valor de Exportação dos 10 Principais Países',
    labels={
        'Valor_dolar': 'Valor (US$)',
        'Quantidade_litros': 'Quantidade (L)'
    }
)

col5.plotly_chart(fig_double_bar, use_container_width=True)


# Gráfico de valor de exportação ao longo dos anos para o país/todos selecionados
df_agrupado_ano = df_filtered.groupby('Ano')[['Valor_dolar', 'Quantidade_litros']].sum().reset_index()
if pais_selecionado == "Todos":
    fig_time_valor = px.line(df_agrupado_ano, x="Ano", y="Valor_dolar", 
                             title=f"Valor Total de Exportação ao Longo dos Anos (US$)",
                             labels={'Valor_dolar': 'Valor Total (US$)'})
    fig_time_quantidade = px.line(df_agrupado_ano, x="Ano", y="Quantidade_litros", 
                                  title=f"Quantidade Total de Exportação ao Longo dos Anos (Litros)",
                                  labels={'Quantidade_litros': 'Qtd. Exportada (L)'})
else:
    fig_time_valor = px.line(df_agrupado_ano, x="Ano", y="Valor_dolar", 
                             title=f"Valor de Exportação para {pais_selecionado} ao Longo dos Anos (US$)")
    fig_time_quantidade = px.line(df_agrupado_ano, x="Ano", y="Quantidade_litros", 
                                  title=f"Quantidade de Exportação para {pais_selecionado} ao Longo dos Anos (Litros)")

col3.plotly_chart(fig_time_valor, use_container_width=True)
col4.plotly_chart(fig_time_quantidade, use_container_width=True)

########### RELATÓRIO ESCRITO ###########
st.divider()

# Relatório da análise (considerando fatores demográficos e econômicos)
st.header('Relatório de Análise do Mercado de Exportação de Vinhos da Viti Brasil (2008-2023)')
st.write("""
**Introdução:** Este relatório apresenta uma análise detalhada do desempenho da empresa Viti Brasil no mercado de exportação de vinhos, abrangendo o período de 2008 a 2023. A análise foi conduzida com base em gráficos que mostram o valor e a quantidade total de exportação, a participação dos principais países e o comparativo entre volume e valor para cada destino. O objetivo é identificar as tendências de mercado, os pontos de inflexão e os fatores que influenciaram o desempenho da empresa.
""")
###########
st.divider()
st.subheader('1. Desempenho Geral e Tendências Históricas (2008-2023)')
st.write("""
O desempenho da Viti Brasil no mercado internacional de vinhos foi marcado por uma grande volatilidade ao longo do período analisado.
* **Pico de Exportação em 2013:** O ano de 2013 se destacou como o auge das exportações, registrando um pico histórico de **$22.5M em valor** e **25M de litros em quantidade**. Este foi um período de grande sucesso para a empresa.
* **Queda Abrupta e Recuperação:** Após o recorde de 2013, as exportações sofreram uma queda acentuada, atingindo os menores níveis em 2015. Posteriormente, o mercado se recuperou, estabilizando-se em um patamar mais baixo do que o pico de 2013, mas com uma tendência de crescimento consistente entre 2019 e 2021.
* **Estagnação Recente:** Observa-se uma leve queda no valor e na quantidade de exportação em 2022, indicando uma possível estagnação ou o início de um novo ciclo de declínio.
""")
###########
st.divider()
st.subheader('2. Análise dos Principais Mercados de Destino')
st.write("""
A Viti Brasil demonstra uma forte concentração de suas exportações em poucos mercados-chave.
* **Paraguai e Rússia como Pilares:** O **Paraguai** e a **Rússia** são os principais destinos, respondendo juntos por uma fatia majoritária das exportações. O Paraguai lidera em valor total de US 400M, com uma participação de cerca de 35%. Enquanto a Rússia é o segundo principal mercado, com um valor total de exportação de aproximadamente US 250M (participação de 25%).
* **Diferença de Perfil de Compra:** A análise comparativa de volume e valor para esses países revela perfis de compra distintos:\\
        **-	Paraguai:** Compra vinhos com maior valor agregado, com um preço médio por litro considerável. Isso sugere que o mercado paraguaio valoriza a qualidade e a Viti Brasil exporta para este destino produtos mais sofisticados.\\
        **-	Rússia:** Apesar de ser um grande comprador em volume, o preço médio por litro é, em geral, mais baixo do que o do Paraguai. Isso sugere uma preferência por vinhos mais baratos, como os vinhos a granel.
* **Diversificação:** A presença de outros mercados importantes como **Estados Unidos**, **China**, **Reino Unido** e **Espanha** demonstra uma estratégia de diversificação de portfólio de clientes, o que ajuda a mitigar riscos e a não depender exclusivamente de um ou dois mercados.
""")
###########
st.divider()
st.subheader('3. Fatores que Influenciaram os Picos de 2009 e 2013')
st.write("""
A análise detalhada dos anos de 2009 e 2013, utilizando os gráficos com filtros específicos, revelou que as dinâmicas de mercado para esses anos foram significativamente diferentes.
""")
st.write('**_Desvalorização em 2009:_**')
st.write("""
A queda no valor médio do vinho brasileiro em 2009 pode ser atribuída à confluência de fatores globais e a uma estratégia de exportação específica:
* **Principal comprador: Rússia (baixo valor unitário):** O gráfico de 2009 mostra que a Rússia foi o principal destino das exportações. A relação entre volume e valor para a Rússia indica que a Viti Brasil exportou grandes quantidades de vinho com um preço médio por litro muito baixo, puxando a média geral de exportação para baixo.
* **Crise Financeira Global (2008-2009):** A crise econômica gerou um ambiente de recessão e incerteza, forçando a Viti Brasil, e a indústria vinícola em geral, a buscar mercados que comprassem grandes volumes, mesmo que a preços mais baixos, para escoar a produção.
* **Aumento da Concorrência e Vendas a Granel:** A forte concorrência global e a necessidade de liquidar estoques levaram a um foco em exportações de baixo valor agregado, como o vinho a granel, especialmente para mercados como o russo.
""")
st.write('**_Valorização em 2013:_**')
st.write("""
O pico histórico de 2013, com o aumento do valor médio por litro, pode ser explicado pela mudança de estratégia e condições de mercado:
* **Continuidade da Rússia como Principal Comprador, mas com maior valor agregado:** A Rússia continuou sendo o principal comprador, mas a análise do volume e valor em 2013 indica que o preço médio por litro exportado para este país aumentou substancialmente. Isso sugere uma mudança no mix de produtos, com a Viti Brasil exportando vinhos de maior valor agregado (vinhos finos engarrafados, por exemplo).
* **Melhora da Economia e Demanda na Rússia:** A estabilidade e o crescimento da economia russa no período pré-2014, impulsionados pelos preços do petróleo, aumentaram o poder de compra dos consumidores e a demanda por produtos importados de maior qualidade.
* **Estratégia de Posicionamento:** A empresa pode ter reposicionado sua marca no mercado russo, focando em nichos mais lucrativos e em vinhos premium, o que justificaria o aumento do valor total da exportação.
""")
###########
st.divider()
st.subheader('Fontes:')
st.write("""
* [Redalyc](https://www.redalyc.org/journal/762/76261661004/html/ "O impacto da crise financeira internacional de 2008 sobre a estrutura de capital das empresas de países desenvolvidos e emergentes"): O impacto da crise financeira internacional de 2008 sobre a estrutura de capital das empresas de países desenvolvidos e emergentes
* [Correio Braziliense](https://www.correiobraziliense.com.br/app/noticia/economia/2009/01/07/internas_economia,63810/venda-de-vinho-do-porto-em-2008-e-a-pior-em-duas-decadas.shtml "Venda de vinho do Porto em 2008 é a pior em duas décadas"): Venda de vinho do Porto em 2008 é a pior em duas décadas
* [Revista Adega](https://revistaadega.uol.com.br/artigo/consumo-de-vinho-importado-e-de-espumante-cresce-na-russia_9804.html "Consumo de vinho importado cresce na Rússia"): Consumo de vinho importado cresce na Rússia (2014)
""")