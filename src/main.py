from analisador_dados import AnalisadorDados
from dashboard import Dashboard
from fonte_dados import FonteDados
from visualizador import Visualizador

def main():
    Dashboard.configurar_pagina()

    df_bruto = FonteDados().carregar_tudo()
    analisador = AnalisadorDados(df_bruto)
    visualizador = Visualizador()
    Dashboard(analisador, visualizador).executar()

if __name__ == "__main__":
    main()