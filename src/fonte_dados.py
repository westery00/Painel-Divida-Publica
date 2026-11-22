import pandas as pd
import os
class FonteDados:
    def __init__(self, nome_arquivo, caminho):
        self.nome_arquivo = nome_arquivo
        self.__caminho = caminho

    def get_caminho(self):
        return self.__caminho

    def carregar_dados(self):
            try:
                self.df = pd.read_csv(self.__caminho, sep=';', decimal=',')
                return self.df
            except FileNotFoundError:
                print(f"Erro: O arquivo '{self.nome_arquivo}' não foi encontrado.")
                return pd.DataFrame()
            except Exception as e:
                print(f"Erro ao carregar os dados do arquivo '{self.nome_arquivo}': {e}")
                return pd.DataFrame()

    def juntar_multiplos_csv(self, pasta, arquivo_saida="dados_juntados.csv"):
        caminho=os.path.join(pasta)
        arquivos_csv = [f for f in os.listdir(caminho) if f.endswith('.csv')]
        if not arquivos_csv:
            print(f"Nenhum arquivo CSV encontrado na pasta '{pasta}'.")
            return pd.DataFrame()

        df_list = []
        for arquivo in arquivos_csv:
            caminho_arquivo = os.path.join(caminho, arquivo)
            try:
                df_temp = pd.read_csv(caminho_arquivo, sep=';', decimal=',')
                df_list.append(df_temp["valor"])
            except Exception as e:
                    print(f"Erro ao ler o arquivo '{arquivo}': {e}")

        if df_list:
            df_juntado = pd.concat(df_list, ignore_index=True)
            caminho_saida = os.path.join(pasta, arquivo_saida)
            df_juntado.to_csv(caminho_saida, index=False, sep=';', decimal=',')
            print(f"Arquivos CSV juntados com sucesso em '{caminho_saida}'.")
            return df_juntado
        else:
            print("Nenhum dado foi carregado para juntar.")
            return pd.DataFrame()