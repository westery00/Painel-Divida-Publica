import streamlit as st
import pandas as pd

from analisador_dados import AnalisadorDados
from config import ROTULOS_EIXO_Y, ROTULOS_TIPO, SERIE_PRINCIPAL, SERIES
from indicador import IndicadorPercentual, criar_indicador
from visualizador import Visualizador

PAPEL_TOTAL = "Total"
PAPEL_COMPONENTE = "Componente"
CORES_PAPEL = {PAPEL_TOTAL: "#FFA15A", PAPEL_COMPONENTE: "#636EFA"}
class Dashboard:
    def __init__(self, analisador: AnalisadorDados, visualizador: Visualizador):
        self.visualizador = visualizador
        self.analisador = analisador

    @staticmethod
    def configurar_pagina():
        st.set_page_config(page_title="Dashboard de Dívida Pública", page_icon="📊", layout="wide")

    def render_cabecalho(self):
        st.title("📊 Painel de Análise: Dívida Pública Líquida")
        st.markdown("Aplicação desenvolvida em Python com **POO, Pandas, Plotly e Streamlit** para destrinchar os dados da dívida pública.")
        st.markdown("---")

    def filtros(self):
        df = self.analisador.get_df_limpo()
        st.sidebar.header("Filtros")

        #nao misturar porcentagem e dinheiro
        presentes = set(df["tipo"])
        tipos = [t for t in SERIES if t in presentes]
        tipo = st.sidebar.radio("Tipo de medida:", tipos, format_func=ROTULOS_TIPO.get)
        df_tipo = self.analisador.filtrar_dados("tipo", tipo)

        #pedir para explicar direito
        categorias = self._categorias_na_ordem(df_tipo, tipo)
        padrao = [s.categoria for s in SERIES[tipo].values() if s.padrao and s.categoria in categorias]
        categorias_sel = st.sidebar.multiselect("Selecione a(s) Categoria(s):", categorias, default=padrao)

        anos = sorted(int(a) for a in df_tipo["ano"].unique())
        anos_sel = st.sidebar.multiselect("Selecione o(s) Ano(s):", anos, default=anos)

        st.sidebar.markdown("---")
        st.sidebar.info("Filtros aplicados em tempo real sobre o conjunto de dados.")

        df_periodo = self.analisador.filtrar_dados("ano", anos_sel, df_tipo)
        df_filtrado = self.analisador.filtrar_dados("categoria", categorias_sel, df_periodo)
        return df_filtrado, df_periodo, tipo
    
    def render_kpis(self, df_filtrado, tipo):
        st.subheader("📌 Indicadores Principais (KPIs)")
        
        opcoes = self._categorias_na_ordem(df_filtrado, tipo)
        categoria = st.selectbox("Categoria dos indicadores:", opcoes)
        df_ref = self.analisador.filtrar_dados("categoria", categoria, df_filtrado)

        indicadores = self.analisador.calcular_indicadores("valor", df_ref)
        valor_pico, data_pico = self.analisador.calcular_pico("valor", df_ref)
        variacao = self.analisador.calcular_variacao_anual("valor", df_ref)

        media = criar_indicador(tipo, "Média no Período", indicadores["media"], "Média dos valores mensais da categoria dentro dos filtros.")
        pico = criar_indicador(tipo, "Maior Pico", valor_pico, "Maior valor mensal da categoria dentro dos filtros "f"(em {data_pico:%m/%Y}).")
        var_anual = IndicadorPercentual("Variação Anual Média", variacao, "Média da variação percentual de um ano para o seguinte, usando o último valor de cada ano. 'n/d' com menos de dois anos ou com valores zero/negativos.")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total de Registros", value=f"{len(df_ref):,}".replace(",", "."), help="Meses com dado para a categoria dentro dos filtros.")
        with col2:
            st.metric(label=media.nome, value=media.formatar_valor(), help=media.descricao)
        with col3:
            st.metric(label=pico.nome, value=pico.formatar_valor(), help=pico.descricao)
        with col4:
            st.metric(label=var_anual.nome, value=var_anual.formatar_valor(), help=var_anual.descricao)
        st.markdown("---")

    def render_visualizacoes(self, df_filtrado,  df_periodo, tipo):
        st.subheader("📈 Visualizações Interativas")
        rotulo_y = ROTULOS_EIXO_Y[tipo]

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("**Evolução Temporal da Dívida**")
            fig_linha = self.visualizador.plotar_grafico(df_filtrado, "data", "valor", "Tendência Histórica", "linha", cor="categoria", rotulo_y=rotulo_y)
            st.plotly_chart(fig_linha)

        with col_g2:
            st.markdown("**Comparativo: Total x Componentes**")
            comparativo, periodo = self._dados_comparativo(df_filtrado, df_periodo)
            if comparativo.empty:
                st.info("O total e as categorias exibidas não têm meses em comum nos anos selecionados.")
            else:
                fig_barra = self.visualizador.plotar_grafico(comparativo, "categoria", "valor", "Média no Período por Categoria", "barra", cor="papel", rotulo_y=rotulo_y, cores=CORES_PAPEL)
                st.plotly_chart(fig_barra)
                st.caption(f"Média no período em que todas as barras têm dados "f"({periodo[0]:%m/%Y} a {periodo[1]:%m/%Y}). "f"O total ({SERIE_PRINCIPAL}) é sempre exibido como referência.")

        st.markdown("---")

    def render_tabela(self, df_filtrado):
        st.subheader("📋 Tabela de Dados Processados")
        tabela = self.analisador.ordenar_dados("data", ascending=False, df=df_filtrado)
        tabela = tabela[["data", "categoria", "valor"]].rename(
            columns={"data": "Data", "categoria": "Categoria", "valor": "Valor"})
        tabela["Data"] = tabela["Data"].dt.strftime("%m/%Y")
        st.dataframe(tabela, hide_index=True)
        st.markdown("---")

    def render_analise_interpretativa(self):
        st.subheader("📝 Análise Interpretativa")
        st.markdown("""
        > **Conclusões do Estudo:** 
        > Através da análise dos dados consolidados da dívida pública líquida, percebe-se que as flutuações 
        > refletem diretamente o cenário macroeconômico e fiscal do país. A concentração dos compromissos financeiros 
        > na esfera federal exige um monitoramento contínuo dos indicadores de endividamento para garantir a sustentabilidade fiscal a longo prazo.
        """)

    def executar(self):
        self.render_cabecalho()

        if self.analisador.get_df_limpo().empty:
            st.error("Não foi possível carregar os dados. Verifique a pasta 'dados/' e as mensagens no terminal.")
            return

        df_filtrado, df_periodo, tipo = self.filtros()
        if df_filtrado.empty:
            st.warning("Nenhum dado para os filtros selecionados. Escolha ao menos uma categoria e um ano na barra lateral.")
            return
        
        self.render_kpis(df_filtrado, tipo)
        self.render_visualizacoes(df_filtrado, df_periodo, tipo)
        self.render_tabela(df_filtrado)
        self.render_analise_interpretativa()

    @staticmethod
    def _categorias_na_ordem(df, tipo):
        """Categorias presentes em df, na ordem de config.SERIES (o total vem primeiro)."""
        presentes = set(df["categoria"])
        return [s.categoria for s in SERIES[tipo].values() if s.categoria in presentes]
    
    def _dados_comparativo(self, df_filtrado: pd.DataFrame, df_periodo: pd.DataFrame):
        """Prepara o gráfico de barras: o total (sempre) e as categorias selecionadas.

        Devolve (médias por categoria, (primeira data, última data) do período usado).
        O total vem primeiro; os componentes, do maior para o menor. Se o total não
        tiver dados nos anos escolhidos (ou não houver meses em comum), devolve um
        DataFrame vazio.
        """
        categorias = set(df_filtrado["categoria"]) | {SERIE_PRINCIPAL}
        df = self.analisador.filtrar_dados("categoria", list(categorias), df_periodo)
        if SERIE_PRINCIPAL not in set(df["categoria"]):
            return df.iloc[0:0], None  # sem o total nos anos escolhidos não há o que comparar
        df = self.analisador.restringir_periodo_comum(df)
        if df.empty:
            return df, None

        medias = self.analisador.agrupar_dados("categoria", "valor", "mean", df)
        eh_total = medias["categoria"] == SERIE_PRINCIPAL
        medias["papel"] = eh_total.map({True: PAPEL_TOTAL, False: PAPEL_COMPONENTE})
        componentes = self.analisador.ordenar_dados("valor", ascending=False, df=medias[~eh_total])
        comparativo = pd.concat([medias[eh_total], componentes], ignore_index=True)
        return comparativo, (df["data"].min(), df["data"].max())