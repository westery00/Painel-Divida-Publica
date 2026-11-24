"""Ponto de entrada. Execute a partir da raiz do projeto com:

    streamlit run src/main.py
"""
from analise_divida import AnaliseDivida
from analisador_dados import AnalisadorDados
from dashboard import Dashboard
from fonte_dados import FonteDados
from visualizador import Visualizador


def main():
    Dashboard.configurar_pagina()  # precisa ser o primeiro comando do Streamlit

    # 1. Origem dos dados (FonteDados): lê e identifica todas as séries
    df_bruto = FonteDados().carregar_tudo()

    # 2. Limpeza e ferramentas gerais (AnalisadorDados)
    analisador = AnalisadorDados(df_bruto)

    # 3. Análise do tema: responde às três perguntas (AnaliseDivida)
    analise = AnaliseDivida(analisador)

    # 4. Painel (Dashboard): apresenta a análise usando o Visualizador
    Dashboard(analise, Visualizador()).executar()


if __name__ == "__main__":
    main()
