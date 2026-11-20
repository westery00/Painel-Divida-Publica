import os
from fonte_dados import FonteDados
from analisador_dados import analisador_dados
from visualizador import Visualizador
from dashboard import Dashboard

def main():
    # 1. Gerenciar origem dos dados (FonteDados)
    caminho_arquivo = os.path.join("dados", "divida_liquida_geral.csv")
    fonte = FonteDados("divida_liquida_geral.csv", caminho_arquivo)
    df_bruto = fonte.carregar_dados()

    # 2. Processar e analisar (AnalisadorDados)
    analisador = analisador_dados(df_bruto)
    df_tratado = analisador.get_df_limpo()

    # 3. Gerar visualizações (Visualizador)
    visualizador = Visualizador()

    # 4. Organizar o painel e iniciar o Dashboard (Dashboard)
    app = Dashboard(df_tratado, visualizador, analisador)
    app.executar()

if __name__ == "__main__":
    main()