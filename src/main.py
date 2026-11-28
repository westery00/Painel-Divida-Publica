"""Ponto de entrada. Execute a partir da raiz do projeto com:

    streamlit run src/main.py
"""
import os

import streamlit as st

from analise_divida import AnaliseDivida
from analise_extras import AnaliseExtras
from analisador_dados import AnalisadorDados
from atualizador_dados import AtualizadorDados, RelatorioAtualizacao
from dashboard import Dashboard
from fonte_dados import FonteDados
from visualizador import Visualizador


@st.cache_resource(show_spinner="Atualizando os dados com o Banco Central (acontece uma vez a cada inicialização)...")
def atualizar_dados() -> RelatorioAtualizacao | None:
    """Baixa as séries do Banco Central. O cache_resource faz isto UMA vez por inicialização do servidor
    (o Streamlit reexecuta main() a cada clique, mas esta função só roda de novo após `.clear()`).

    Para abrir o painel sem tentar a internet (ex.: apresentação sem rede), defina PAINEL_OFFLINE=1.
    """
    if os.environ.get("PAINEL_OFFLINE") == "1":
        return None
    return AtualizadorDados().atualizar()


def main(atualizador=None):
    Dashboard.configurar_pagina()  # precisa ser o primeiro comando do Streamlit

    # 0. Atualização dos CSVs (uma vez por inicialização); sem internet, segue com os dados salvos
    relatorio = atualizar_dados() if atualizador is None else atualizador.atualizar()

    # 1. Origem dos dados (FonteDados): lê e identifica todas as séries
    df_bruto = FonteDados().carregar_tudo()

    # 2. Limpeza e ferramentas gerais (AnalisadorDados)
    analisador = AnalisadorDados(df_bruto)

    # 3. Análise do tema: responde às três perguntas (AnaliseDivida)
    analise = AnaliseDivida(analisador)

    # 4. Séries extras: IPCA, Selic e dívida bruta (a aba 'Juros e inflação' e a dívida bruta x líquida)
    extras = AnaliseExtras(analise, FonteDados().carregar_extras())

    # 5. Painel (Dashboard): apresenta a análise usando o Visualizador
    Dashboard(analise, Visualizador(), relatorio, ao_atualizar=atualizar_dados.clear, extras=extras).executar()


if __name__ == "__main__":
    main()
