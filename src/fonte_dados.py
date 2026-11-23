import pandas as pd
from pathlib import Path
import logging
from config import PASTA_DADOS, SERIES

log = logging.getLogger(__name__)
class FonteDados:
    COLUNAS = ["data", "valor", "categoria", "tipo"]
    FORMATO_DATA = "%d/%m/%Y"

    def __init__(self, pasta_dados=PASTA_DADOS):
        self.__pasta_dados = Path(pasta_dados)

    def get_pasta_dados(self):
        return self.__pasta_dados

    def carregar_arquivo(self, caminho):
        caminho = Path(caminho)
        try:
            df = pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8")
            df["data"] = pd.to_datetime(df["data"], format=self.FORMATO_DATA)
            df["valor"] = pd.to_numeric(df["valor"])
            return df[["data", "valor"]]
        except FileNotFoundError:
            log.error("O arquivo '%s' não foi encontrado.", caminho)
        except (OSError, ValueError, KeyError) as erro:
            log.error("Erro ao carregar '%s': %r", caminho.name, erro)
        return pd.DataFrame(columns=["data", "valor"])

    def carregar_tipo(self, tipo):
        series = SERIES.get(tipo)
        if series is None:
            log.error("Tipo desconhecido: '%s'. Use um de %s.", tipo, list(SERIES))
            return self._vazio()

        pasta = self.__pasta_dados / tipo
        if not pasta.is_dir():
            log.error("Pasta '%s' não encontrada.", pasta)
            return self._vazio()

        partes = []
        for nome_arquivo, serie in series.items():
            df = self.carregar_arquivo(pasta / nome_arquivo)
            if df.empty:
                continue  # o motivo já foi registrado em carregar_arquivo
            df["categoria"] = serie.categoria
            df["tipo"] = tipo
            partes.append(df)

        ignorados = sorted({f.name for f in pasta.glob("*.csv")} - set(series))
        if ignorados:
            log.warning("Arquivos CSV ignorados em '%s' (não estão em config.SERIES): %s",
                        pasta, ignorados)

        if not partes:
            log.warning("Nenhum dado carregado para o tipo '%s'.", tipo)
            return self._vazio()
        return pd.concat(partes, ignore_index=True)[self.COLUNAS]        

    def carregar_tudo(self):
        partes = [self.carregar_tipo(tipo) for tipo in SERIES]
        partes = [p for p in partes if not p.empty]
        if not partes:
            return self._vazio()
        return pd.concat(partes, ignore_index=True)

    def _vazio(self):
        return pd.DataFrame(columns=self.COLUNAS)
