"""Camada de entrada: lê os CSVs e devolve os dados em formato único.

Formato de saída (um registro por série, por mês):

    data (datetime) | valor (float) | categoria (str) | tipo (str)
"""
import logging
from pathlib import Path

import pandas as pd

from config import PASTA_DADOS, SERIES

log = logging.getLogger(__name__)


class FonteDados:
    COLUNAS = ["data", "valor", "categoria", "tipo"]
    FORMATO_DATA = "%d/%m/%Y"

    def __init__(self, pasta_dados=PASTA_DADOS):
        self.__pasta_dados = Path(pasta_dados)

    def get_pasta_dados(self) -> Path:
        return self.__pasta_dados

    def carregar_arquivo(self, caminho) -> pd.DataFrame:
        """Lê um CSV no padrão do projeto (separador ';', decimal ',').

        Devolve colunas [data, valor] já convertidas para datetime e float.
        Em caso de erro, registra o problema e devolve um DataFrame vazio.
        """
        caminho = Path(caminho)
        try:
            df = pd.read_csv(caminho, sep=";", decimal=",", encoding="utf-8")
            df["data"] = pd.to_datetime(df["data"], format=self.FORMATO_DATA)
            df["valor"] = pd.to_numeric(df["valor"])
            return df[["data", "valor"]]
        except FileNotFoundError:
            log.error("O arquivo '%s' não foi encontrado.", caminho)
        except (OSError, ValueError, KeyError) as erro:
            # ValueError cobre CSV vazio/malformado, data e número inválidos;
            # KeyError cobre arquivo sem as colunas 'data' e 'valor'.
            log.error("Erro ao carregar '%s': %r", caminho.name, erro)
        return pd.DataFrame(columns=["data", "valor"])

    def carregar_tipo(self, tipo: str) -> pd.DataFrame:
        """Carrega todas as séries de um tipo ('porcentagem' ou 'real').

        Só lê os arquivos declarados em config.SERIES. Outros .csv que estejam
        na pasta (por exemplo, arquivos gerados) são ignorados, com um aviso.
        """
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

    def carregar_tudo(self) -> pd.DataFrame:
        """Carrega todos os tipos e junta em um único DataFrame."""
        partes = [self.carregar_tipo(tipo) for tipo in SERIES]
        partes = [p for p in partes if not p.empty]
        if not partes:
            return self._vazio()
        return pd.concat(partes, ignore_index=True)

    def _vazio(self) -> pd.DataFrame:
        return pd.DataFrame(columns=self.COLUNAS)
