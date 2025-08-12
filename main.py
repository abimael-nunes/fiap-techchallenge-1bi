import streamlit as st
import pandas as pd
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')

# Configurar o layout da página
st.set_page_config(layout="wide")

# Título do dashboard
st.title('Tech Challenge: Análise de Exportação de Vinhos - Viti Brasil')

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
paises.insert(0, "Todos")
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

# Criar o gráfico de barras com 'Métrica' (Valor ou Volume) como a cor
fig_double_bar = px.bar(
    df_melted_top_10,
    x='País',
    y='Valor',
    color='Métrica',
    barmode='group',
    title='Volume e Valor de Exportação dos 10 Principais Países',
    labels={
        'País': 'País de Destino',
        'Valor': 'Total'
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

# Exibir a tabela de dados
tabela_exibicao = df_filtered.rename(columns={
    'País': 'País de Destino',
    'Quantidade_litros': 'Quantidade em litros',
    'Valor_dolar': 'Valor em US$'
})
tabela_exibicao.insert(0, 'País de Origem', 'Brasil')
st.dataframe(tabela_exibicao[['País de Origem', 'País de Destino', 'Ano', 'Quantidade em litros', 'Valor em US$']])

# Placeholder para a análise de fatores externos
st.subheader('Prospecções Futuras e Ações Possíveis para Melhoria')
st.write("""
Aqui você pode adicionar sua análise baseada nos dados e em fatores externos como dados climáticos, demográficos, econômicos e de avaliação de vinhos.
* **Análise Econômica:** Como a inflação ou o câmbio do dólar afetam as exportações?
* **Análise Demográfica:** Quais países com crescimento populacional ou com maior poder de compra podem ser mercados-alvo?
* **Análise Climática:** Como as variações climáticas afetam a produção de vinho no Brasil e, consequentemente, a exportação?
* **Análise de Avaliações:** Que tipos de vinho são mais bem avaliados e em quais mercados?
""")