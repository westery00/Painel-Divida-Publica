import plotly.express as px

class Visualizador:
    TIPOS_GRAFICO = ("linha", "barra", "pizza", "box")
    ROTULOS_PADRAO = {"data": "Data", "valor": "Valor", "categoria": "Categoria", "ano": "Ano"}

    def __init__(self, tema="plotly_dark"):
        self.tema = tema

    def plotar_grafico(self, df, x_coluna, y_coluna, titulo, tipo_grafico='linha', cor=None, rotulo_y=None, cores=None):
        if tipo_grafico not in self.TIPOS_GRAFICO:
            raise ValueError(f"Tipo de gráfico não suportado: '{tipo_grafico}'. "
                             f"Use um de {self.TIPOS_GRAFICO}.")
        colunas = [c for c in (x_coluna, y_coluna, cor) if c is not None]
        faltando = [c for c in colunas if c not in df.columns]
        if faltando:
            raise ValueError(f"Colunas não encontradas no DataFrame: {faltando}")

        rotulos = dict(self.ROTULOS_PADRAO)
        if rotulo_y:
            rotulos[y_coluna] = rotulo_y

        base = dict(title=titulo, template=self.tema, labels=rotulos)

        if cor is not None and cores:
            base["color_discrete_map"] = cores

        if tipo_grafico == "linha":
            return px.line(df, x=x_coluna, y=y_coluna, color=cor, **base)
        if tipo_grafico == "barra":
            # Mantém as barras na ordem em que aparecem no DataFrame.
            ordem = {x_coluna: list(dict.fromkeys(df[x_coluna]))}
            return px.bar(df, x=x_coluna, y=y_coluna, color=cor, text_auto=True,
                          category_orders=ordem, **base)
        if tipo_grafico == "pizza":
            return px.pie(df, values=y_coluna, names=x_coluna, hole=0.3, **base)
        return px.box(df, x=x_coluna, y=y_coluna, color=cor, **base)
