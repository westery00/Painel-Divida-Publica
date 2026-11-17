import pandas as pd
class analisador_dados:
    def __init__(self, df: pd.DataFrame):
        self.df = df 
        self.__df_limpo = None

    def get_df_limpo(self):
        if self.__df_limpo is None:
            self.limpar_dados()
        return self.__df_limpo

    def limpar_dados(self):
        if self.df is None:
            self.__df_limpo = pd.DataFrame()
        else:
            dftemp = self.df.copy()
            dftemp = dftemp.fillna(0)
            dftemp = dftemp.drop_duplicates()
            self.__df_limpo = dftemp
            print("Dados limpos com sucesso (duplicidades e ausentes tratados)!")

    def filtrar_dados(self, coluna, valor):
        df = self.get_df_limpo()
        if coluna in df.columns:
            return df[df[coluna] == valor]
        print(f"Coluna '{coluna}' não encontrada para filtro.")
        return pd.DataFrame()

    def ordenar_dados(self, coluna, ascending=True):
        df = self.get_df_limpo()
        if coluna in df.columns:
            return df.sort_values(by=coluna, ascending=ascending)
        print(f"Coluna '{coluna}' não encontrada para ordenação.")
        return pd.DataFrame()

    def agrupar_dados(self, coluna_agrupamento, coluna_agrupada, func_agrupamento= "mean"):
        df = self.get_df_limpo()
        if coluna_agrupamento in df.columns and coluna_agrupada in df.columns:
            if func_agrupamento == 'sum':
                return df.groupby(coluna_agrupamento)[coluna_agrupada].sum().reset_index()
            elif func_agrupamento == 'mean':
                return df.groupby(coluna_agrupamento)[coluna_agrupada].mean().reset_index()
            elif func_agrupamento == 'max':
                return df.groupby(coluna_agrupamento)[coluna_agrupada].max().reset_index()
        return pd.DataFrame()

    def calcular_estatisticas(self, coluna):
        df= self.get_df_limpo()
        if coluna in df.columns:
            desc = df[coluna].describe()
            return desc.to_dict()
        return {}

    def calcular_5_indicador(self, coluna):
        df = self.get_df_limpo()
        if coluna in df.columns:
            media = df[coluna].mean()
            mediana = df[coluna].median()
            desvio_padrao = df[coluna].std()
            minimo = df[coluna].min()
            maximo = df[coluna].max()
            return {
                'media': media,
                'mediana': mediana,
                'desvio_padrao': desvio_padrao,
                'minimo': minimo,
                'maximo': maximo
            }
        return {}