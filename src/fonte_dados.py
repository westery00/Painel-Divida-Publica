import pandas as pd

class FonteDados:
    def __init__(self, nome_arquivo, caminho):
        self.nome_arquivo = nome_arquivo
        self.__caminho = caminho
        self.df = None

    def get_caminho(self):
        return self.__caminho

    def carregar_dados(self):
            try:
                self.df = pd.read_csv(self.__caminho, sep=';', decimal=',')
                print("Dados carregados com sucesso!")
                return self.df
            except FileNotFoundError:
                print(f"Erro: O arquivo '{self.nome_arquivo}' não foi encontrado.")
                return pd.DataFrame()
            except Exception as e:
                print(f"Erro ao carregar os dados do arquivo '{self.nome_arquivo}': {e}")
                return pd.DataFrame()
    