import pandas as pd
import plotly.express as px

class Visualizador:
    def __init__(self, tema='plotly_dark'):
        self.tema = tema

    def plotar_grafico(self, df, x_coluna, y_coluna, titulo, tipo_grafico='linha'):
        if tipo_grafico == 'linha':
            fig = px.line(df, x=x_coluna, y=y_coluna, title=titulo, template=self.tema, markers=True)
        elif tipo_grafico == 'barra':
            fig = px.bar(df, x=x_coluna, y=y_coluna, title=titulo, template=self.tema, text_auto=True)
        elif tipo_grafico == 'pizza':
            fig = px.pie(df, values=y_coluna, names=x_coluna, title=titulo, template=self.tema, hole=0.3)
        elif tipo_grafico == 'box':
            fig = px.box(df, x=x_coluna, y=y_coluna, title=titulo, template=self.tema)    
        else:
            raise ValueError("Tipo de gráfico não suportado. Use 'linha' ou 'barra'.")

        return fig
