from abc import ABC, abstractmethod
import pandas as pd
from config import SUFIXO_REAL, TIPO_REAL

def _formato_brasileiro(texto: str) -> str:
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")

class Indicador(ABC):
    SEM_VALOR = "n/d"

    def __init__(self, nome, valor, descricao):
        self.nome = nome
        self.__valor = valor
        self.descricao = descricao

    def get_valor(self):
        return self.__valor
    
    def set_valor(self, valor):
        self.__valor = valor

    def formatar_valor(self):
        valor = self.__valor
        if valor is None or pd.isna(valor):
            return self.SEM_VALOR
        return self._formatar(valor)

    @abstractmethod
    def _formatar(self, valor):
        pass

    def __str__(self):
        return f"{self.nome}: {self.formatar_valor()}"

class IndicadorMonetario(Indicador):
    def __init__(self, nome, valor, descricao="", sufixo=""):
        super().__init__(nome, valor, descricao)
        self.sufixo = sufixo

    def _formatar(self, valor):
        texto = f"R$ {_formato_brasileiro(f'{valor:,.2f}')}"
        return f"{texto} {self.sufixo}" if self.sufixo else texto

class IndicadorPercentual(Indicador):
    def _formatar(self, valor):
        return f"{_formato_brasileiro(f'{valor:,.2f}')}%"

def criar_indicador(tipo, nome, valor, descricao="") -> Indicador:
    if tipo == TIPO_REAL:
        return IndicadorMonetario(nome, valor, descricao, sufixo=SUFIXO_REAL)
    return IndicadorPercentual(nome, valor, descricao)
