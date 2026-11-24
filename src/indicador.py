"""Formatação de valores no padrão brasileiro e classes de Indicador.

As funções ``formatar_*`` são usadas por todo o projeto, para que um número
apareça sempre igual (KPIs, gráficos e textos). Todos os valores em R$ chegam
em MILHÕES, como nos CSVs, e são abreviados para mi/bi/tri.
"""
from abc import ABC, abstractmethod

import pandas as pd

from config import TIPO_REAL

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _formato_brasileiro(texto: str) -> str:
    """Troca os separadores do padrão americano (1,234.56) para o brasileiro (1.234,56)."""
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def formatar_numero(valor: float, casas: int = 1, sinal: bool = False) -> str:
    texto = f"{valor:+,.{casas}f}" if sinal else f"{valor:,.{casas}f}"
    return _formato_brasileiro(texto)


def formatar_percentual(valor: float, casas: int = 1, sinal: bool = False) -> str:
    return formatar_numero(valor, casas, sinal) + "%"


def formatar_pp(valor: float, casas: int = 1) -> str:
    """Variação em pontos percentuais, sempre com sinal: '+3,2 p.p.'."""
    return formatar_numero(valor, casas, sinal=True) + " p.p."


def formatar_reais(valor_milhoes: float, casas: int = 2, sinal: bool = False) -> str:
    """Abrevia um valor em milhões de reais: 9379279 -> 'R$ 9,38 tri'."""
    absoluto = abs(valor_milhoes)
    if absoluto >= 1e6:
        numero, unidade = absoluto / 1e6, "tri"
    elif absoluto >= 1e3:
        numero, unidade = absoluto / 1e3, "bi"
    else:
        numero, unidade = absoluto, "mi"
    prefixo = ""
    if valor_milhoes < 0:
        prefixo = "-"
    elif sinal and valor_milhoes > 0:
        prefixo = "+"
    return f"{prefixo}R$ {formatar_numero(numero, casas)} {unidade}"


def formatar_medida(tipo: str, valor: float, sinal: bool = False, casas: int = 1) -> str:
    """Nível de uma série: percentual (% do PIB) ou reais, conforme o tipo."""
    if tipo == TIPO_REAL:
        return formatar_reais(valor, casas=2, sinal=sinal)
    return formatar_percentual(valor, casas, sinal)


def formatar_variacao(tipo: str, valor: float) -> str:
    """Variação entre duas datas, com sinal: '+39,5 p.p.' ou '+R$ 7,38 tri'."""
    if tipo == TIPO_REAL:
        return formatar_reais(valor, casas=2, sinal=True)
    return formatar_pp(valor)


def formatar_mes(data) -> str:
    """Timestamp -> 'set/2026'."""
    return f"{MESES[data.month - 1]}/{data.year}"


class Indicador(ABC):
    SEM_VALOR = "n/d"

    def __init__(self, nome, valor, descricao=""):
        self.nome = nome
        self.__valor = valor
        self.descricao = descricao

    def get_valor(self):
        return self.__valor

    def set_valor(self, valor):
        self.__valor = valor

    def formatar_valor(self) -> str:
        """Texto pronto para exibição; 'n/d' quando não há valor calculável."""
        valor = self.__valor
        if valor is None or pd.isna(valor):
            return self.SEM_VALOR
        return self._formatar(valor)

    @abstractmethod
    def _formatar(self, valor) -> str:
        """Formata um valor válido (nunca recebe None/NaN)."""

    def __str__(self):
        return f"{self.nome}: {self.formatar_valor()}"


class IndicadorMonetario(Indicador):
    """Valor em milhões de reais, exibido abreviado (mi, bi ou tri)."""

    def _formatar(self, valor) -> str:
        return formatar_reais(valor)


class IndicadorPercentual(Indicador):
    def _formatar(self, valor) -> str:
        return formatar_percentual(valor, casas=2)


def criar_indicador(tipo, nome, valor, descricao="") -> Indicador:
    """Escolhe a classe certa conforme o tipo de medida dos dados ('porcentagem' ou 'real')."""
    classe = IndicadorMonetario if tipo == TIPO_REAL else IndicadorPercentual
    return classe(nome, valor, descricao)
