from fonte_dados import FonteDados
from analisador_dados import analisador_dados

# 1. Carrega os dados
fonte = FonteDados("divida_liquida_geral.csv", "data/divida_liquida_geral.csv")
df_bruto = fonte.carregar_dados()

# 2. Analisa e trata os dados
analisador = analisador_dados(df_bruto)
indicadores = analisador.calcular_5_indicadores("valor") # Substitua "Valor" pelo nome real da coluna numérica do seu CSV

print("Indicadores calculados:", indicadores)