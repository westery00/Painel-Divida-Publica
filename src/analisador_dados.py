import logging
import pandas as pd
log = logging.getLogger(__name__)
class AnalisadorDados:
    COLUNAS_OBRIGATORIAS = ("data", "valor")
    FUNCOES_AGRUPAMENTO = ("sum", "mean", "max", "min", "median")

    def __init__(self, df):
            self.df = df
            self.__df_limpo = None

    def get_df_limpo(self):
        if self.__df_limpo is None:
            self.limpar_dados()
        return self.__df_limpo

    def limpar_dados(self):
        if self.df is None or self.df.empty:
            self.__df_limpo = pd.DataFrame()
            return

        faltando = [c for c in self.COLUNAS_OBRIGATORIAS if c not in self.df.columns]
        if faltando:
            raise ValueError(f"O DataFrame não tem as colunas obrigatórias: {faltando}")

        df = self.df.copy()
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

        total = len(df)
        df = df.dropna(subset=["data", "valor"])
        invalidos = total - len(df)

        chaves = [c for c in ("tipo", "categoria", "data") if c in df.columns]
        df = df.drop_duplicates(subset=chaves, keep="last")
        duplicados = total - len(df)

        df["ano"] = df["data"].dt.year
        self.__df_limpo = df.sort_values(chaves).reset_index(drop=True)
        log.info("Dados limpos: %d linhas (%d inválidas e %d duplicadas removidas).",
                 len(self.__df_limpo), invalidos, duplicados)

    def filtrar_dados(self, coluna, valor, df=None):
        return self.filtrar_varios({coluna: valor}, df)

    def filtrar_varios(self, criterios, df=None):
        df = self._base(df)
        for coluna, valor in criterios.items():
            if coluna not in df.columns:
                log.warning("Coluna '%s' não encontrada para filtro.", coluna)
                return df.iloc[0:0]
            if pd.api.types.is_list_like(valor):
                df = df[df[coluna].isin(valor)]
            else:
                df = df[df[coluna] == valor]
        return df
    
    def ordenar_dados(self, coluna, ascending=True, df=None):
        df = self._base(df)
        if coluna in df.columns:
            return df.sort_values(by=coluna, ascending=ascending)
        print(f"Coluna '{coluna}' não encontrada para ordenação.")
        return pd.DataFrame()


    def restringir_periodo_comum(self, df=None, coluna_serie="categoria"):
        df = self._base(df)
        if df.empty or coluna_serie not in df.columns:
            return df
        series_por_data = df.groupby("data")[coluna_serie].nunique()
        datas_completas = series_por_data[series_por_data == df[coluna_serie].nunique()].index
        return df[df["data"].isin(datas_completas)]        

        
    def agrupar_dados(self, coluna_agrupamento, coluna_agrupada, func_agrupamento= "mean", df=None):
        if func_agrupamento not in self.FUNCOES_AGRUPAMENTO:
            raise ValueError(f"Função '{func_agrupamento}' não suportada. ", f"Use uma de {self.FUNCOES_AGRUPAMENTO}.")
        df = self._base(df)
        for coluna in (coluna_agrupamento, coluna_agrupada):
            if coluna not in df.columns:
                log.warning("Coluna '%s' não encontrada para agrupamento.", coluna)
                return pd.DataFrame()
        return (df.groupby(coluna_agrupamento)[coluna_agrupada].agg(func_agrupamento).reset_index())

    def calcular_estatisticas(self, coluna):
        df = self._base(df)
        if coluna not in df.columns:
            return {}
        return df[coluna].describe().to_dict()

    def calcular_indicadores(self, coluna="valor", df=None):
        df = self._base(df)
        if coluna not in df.columns:
            return {}
        serie = df[coluna]
        return {
            "media": serie.mean(),
            "mediana": serie.median(),
            "desvio_padrao": serie.std(),
            "minimo": serie.min(),
            "maximo": serie.max(),
        }

    def calcular_pico(self, coluna="valor", df=None):
        df = self._base(df)
        if coluna not in df.columns or "data" not in df.columns or df[coluna].dropna().empty:
            return None
        linha = df.iloc[df[coluna].reset_index(drop=True).idxmax()]
        return linha[coluna], linha["data"]

    def calcular_variacao_anual(self, coluna="valor", df=None):
        df = self._base(df)
        if df.empty or coluna not in df.columns or "ano" not in df.columns:
            return None
        fim_de_ano = df.sort_values("data").groupby("ano")[coluna].last()
        if len(fim_de_ano) < 2 or (fim_de_ano <= 0).any():
            return None
        return fim_de_ano.pct_change().dropna().mean() * 100

    def _base(self, df):
        return df if df is not None else self.get_df_limpo()