from abc import ABC, abstractmethod

class Indicador(ABC):
    def __init__(self, nome, valor, descricao):
        self.nome = nome
        self.__valor = valor
        self.descricao = descricao

    def get_valor(self):
        return self.__valor
    def set_valor(self, valor):
        self.__valor = valor

    @abstractmethod
    def formatar_valor(self):
        pass    

class IndicadorMonetario(Indicador):
    def formatar_valor(self):
        return f"R$ {self.get_valor():,.2f}"

class IndicadorPercentual(Indicador):
    def formatar_valor(self):
        return f"{self.get_valor():.2f}%"