import streamlit as st
import pandas as pd

class Dashboard:
    def __init__(self, df, visualizador, analisador):
        self.df = df
        self.visualizador = visualizador
        self.analisador = analisador

    def render_cabecalho(self):
        """1. Cabeçalho do Dashboard."""
        # O set_page_config deve ser a primeira chamada e fora de quebras de fluxo complexas
        st.set_page_config(page_title="Dashboard de Dívida Pública", layout="wide")
        
        st.title("📊 Painel de Análise: Dívida Pública Líquida")
        st.markdown("Aplicação desenvolvida em Python com **POO, Pandas, Plotly e Streamlit** para destrinchar os dados da dívida pública.")
        st.markdown("---")

    def filtros(self):
        st.sidebar.header("Filtros")
        if self.df.empty:
            return self.df
        df_filtrado = self.df.copy()
        colunas_disponiveis = [col for col in df_filtrado.columns]
        if "Ano" in colunas_disponiveis:
            anos = sorted(df_filtrado["Ano"].dropna().unique())
            ano_selecionado = st.sidebar.multiselect("Selecione o(s) Ano(s):", anos, default=anos)
            if ano_selecionado:
                df_filtrado = df_filtrado[df_filtrado["Ano"].isin(ano_selecionado)]
        st.sidebar.markdown("---")
        st.sidebar.info("Filtros aplicados em tempo real sobre o conjunto de dados.")
        return df_filtrado

    def render_kpis(self, df_filtrado: pd.DataFrame):
        st.subheader("📌 Indicadores Principais (KPIs)")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total de Registros", value=len(df_filtrado))
        with col2:
            st.metric(label="Média Geral", value="R$ 5.20 Tri") # Exemplo adaptável
        with col3:
            st.metric(label="Maior Pico", value="R$ 7.10 Tri")
        with col4:
            st.metric(label="Variação Anual", value="+4.15%")
            
        st.markdown("---")

    def render_visualizacoes(self, df_filtrado: pd.DataFrame):
        """4. Visualizações Dinâmicas (Gráficos do Plotly)."""
        st.subheader("📈 Visualizações Interativas")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("**Evolução Temporal da Dívida**")
            # Exemplo de chamada do visualizador (ajuste os nomes das colunas de X e Y do seu CSV)
            if not df_filtrado.empty and len(df_filtrado.columns) >= 2:
                fig_linha = self.visualizador.plotar_grafico(df_filtrado, df_filtrado.columns[0], df_filtrado.columns[1], "Tendência Histórica", "linha")
                st.plotly_chart(fig_linha, use_container_width=True)
            else:
                st.warning("Dados insuficientes para o gráfico de linhas.")

        with col_g2:
            st.markdown("**Comparativo por Categoria**")
            if not df_filtrado.empty and len(df_filtrado.columns) >= 2:
                fig_barra = self.visualizador.plotar_grafico(df_filtrado, df_filtrado.columns[0], df_filtrado.columns[1], "Distribuição por Setor", "barra")
                st.plotly_chart(fig_barra, use_container_width=True)
            else:
                st.warning("Dados insuficientes para o gráfico de barras.")

        st.markdown("---")

    def render_tabela(self, df_filtrado: pd.DataFrame):
        """5. Tabela de Dados Detalhados."""
        st.subheader("📋 Tabela de Dados Processados")
        st.dataframe(df_filtrado, use_container_width=True)
        st.markdown("---")

    def render_analise_interpretativa(self):
        """6. Análise Interpretativa do Projeto."""
        st.subheader("📝 Análise Interpretativa")
        st.markdown("""
        > **Conclusões do Estudo:** 
        > Através da análise dos dados consolidados da dívida pública líquida, percebe-se que as flutuações 
        > refletem diretamente o cenário macroeconômico e fiscal do país. A concentração dos compromissos financeiros 
        > na esfera federal exige um monitoramento contínuo dos indicadores de endividamento para garantir a sustentabilidade fiscal a longo prazo.
        """)

    def executar(self):
        """Método principal que orquestra a renderização completa do dashboard."""
        self.render_cabecalho()
        self.render_kpis(self.df)
        self.render_visualizacoes(self.df)
        self.render_tabela(self.df)
        self.render_analise_interpretativa()