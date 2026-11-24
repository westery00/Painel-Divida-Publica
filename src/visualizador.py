"""Camada de gráficos: transforma dados já preparados em figuras Plotly.

Não faz cálculos de negócio. Todos os gráficos passam por ``_estilizar``, que
aplica o mesmo visual (fundo transparente sobre o cartão, grade suave, fonte).
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import tema


class Visualizador:
    TIPOS_GRAFICO = ("linha", "barra", "pizza", "box")
    ROTULOS_PADRAO = {"data": "Data", "valor": "Valor", "categoria": "Categoria", "ano": "Ano"}

    def __init__(self, template="plotly_dark"):
        self.template = template

    # ------------------------------------------------------------ estilo comum
    def _estilizar(self, fig, rotulo_y=None, altura=360, titulo=None, legenda=True):
        fig.update_layout(
            template=self.template,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=tema.FONTE, color=tema.TEXTO, size=12),
            height=altura,
            margin=dict(l=8, r=8, t=48 if (legenda or titulo) else 12, b=8),
            showlegend=legenda,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        title_text="", bgcolor="rgba(0,0,0,0)"),
            hoverlabel=dict(bgcolor=tema.FUNDO_CARD_2, font_color=tema.TEXTO, bordercolor=tema.BORDA),
        )
        if titulo:
            fig.update_layout(title=dict(text=titulo, x=0.01, xanchor="left", font=dict(size=15)))
        fig.update_xaxes(gridcolor=tema.GRADE, zeroline=False, linecolor=tema.GRADE, title_text="")
        fig.update_yaxes(gridcolor=tema.GRADE, zeroline=False, linecolor=tema.GRADE)
        if rotulo_y:
            fig.update_yaxes(title_text=rotulo_y)
        return fig

    def _bandas(self, fig, bandas, inicio, fim):
        """Faixas verticais de contexto (ex.: recessão), recortadas ao intervalo exibido."""
        for faixa_ini, faixa_fim, rotulo in bandas:
            a, b = pd.Timestamp(faixa_ini), pd.Timestamp(faixa_fim)
            if b < inicio or a > fim:
                continue
            a, b = max(a, inicio), min(b, fim)
            meio = a + (b - a) / 2
            fig.add_shape(type="rect", xref="x", yref="paper", y0=0, y1=1,
                          x0=a.strftime("%Y-%m-%d"), x1=b.strftime("%Y-%m-%d"),
                          fillcolor="rgba(255,255,255,0.07)", line=dict(width=0), layer="below")
            fig.add_annotation(x=meio.strftime("%Y-%m-%d"), y=0.02, xref="x", yref="paper",
                               text=rotulo, showarrow=False, yanchor="bottom",
                               font=dict(size=10, color=tema.TEXTO_SUAVE))

    # ------------------------------------------------------- gráfico genérico
    def plotar_grafico(self, df, x_coluna, y_coluna, titulo=None, tipo_grafico="linha",
                       cor=None, rotulo_y=None, cores=None, bandas=None, altura=360):
        """Gráfico a partir de um DataFrame em formato longo.

        cor:     coluna usada para separar séries por cor (ex.: 'categoria').
        rotulo_y: texto do eixo Y (ex.: '% do PIB').
        cores:   dicionário {valor da coluna 'cor': cor}, para fixar a cor de cada grupo.
        bandas:  lista de (início, fim, rótulo) desenhadas atrás de gráficos de linha.
        """
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
        base = dict(labels=rotulos)
        if cor is not None and cores:
            base["color_discrete_map"] = cores

        if tipo_grafico == "linha":
            fig = px.line(df, x=x_coluna, y=y_coluna, color=cor, **base)
            fig.update_traces(line=dict(width=2.4))
            fig.update_layout(hovermode="x unified")
        elif tipo_grafico == "barra":
            # Mantém as barras na ordem em que aparecem no DataFrame.
            ordem = {x_coluna: list(dict.fromkeys(df[x_coluna]))}
            fig = px.bar(df, x=x_coluna, y=y_coluna, color=cor, text_auto=True,
                         category_orders=ordem, **base)
        elif tipo_grafico == "pizza":
            fig = px.pie(df, values=y_coluna, names=x_coluna, hole=0.3, **base)
        else:
            fig = px.box(df, x=x_coluna, y=y_coluna, color=cor, **base)

        self._estilizar(fig, rotulo_y, altura, titulo, legenda=cor is not None)
        if bandas and tipo_grafico == "linha":
            self._bandas(fig, bandas, df[x_coluna].min(), df[x_coluna].max())
        return fig

    # ----------------------------------------------------- gráficos especiais
    def cascata(self, rotulos, valores, medidas, textos, rotulo_y=None, altura=370,
                cor_alta=tema.AZUL, cor_baixa=tema.VERDE, cor_total=tema.LARANJA):
        """Cascata (waterfall): cada barra sobe ou desce a partir da anterior.

        medidas: 'relative' (soma à barra anterior), 'absolute' (começa do zero no
                 valor dado) ou 'total' (mostra a soma acumulada até ali).
        """
        fig = go.Figure(go.Waterfall(
            x=list(rotulos), y=[float(v) for v in valores], measure=list(medidas), text=list(textos),
            textposition="outside", cliponaxis=False,
            connector=dict(line=dict(color=tema.TEXTO_SUAVE, width=1)),
            increasing=dict(marker=dict(color=cor_alta)),
            decreasing=dict(marker=dict(color=cor_baixa)),
            totals=dict(marker=dict(color=cor_total)),
            hovertemplate="%{x}: %{text}<extra></extra>"))
        return self._estilizar(fig, rotulo_y, altura, legenda=False)

    def barras_empilhadas(self, df, cores, linha=None, nome_linha="Total", rotulo_y=None, altura=390):
        """Barras empilhadas por categoria (colunas do df); valores negativos descem do zero."""
        fig = go.Figure()
        x = [str(i) for i in df.index]
        for coluna in df.columns:
            fig.add_trace(go.Bar(x=x, y=[float(v) for v in df[coluna]], name=str(coluna),
                                 marker_color=cores.get(coluna)))
        if linha is not None:
            fig.add_trace(go.Scatter(x=x, y=[float(v) for v in linha], name=nome_linha,
                                     mode="lines+markers", marker=dict(size=6),
                                     line=dict(color=tema.BRANCO, width=2)))
        fig.update_layout(barmode="relative", hovermode="x unified")
        self._estilizar(fig, rotulo_y, altura)
        fig.update_xaxes(type="category")
        return fig

    def rosca(self, rotulos, valores, cores, texto_central="", altura=370):
        """Rosca (donut) com um texto no centro."""
        fig = go.Figure(go.Pie(
            labels=list(rotulos), values=[float(v) for v in valores], hole=0.62, sort=False,
            direction="clockwise", textinfo="percent", textposition="outside",
            marker=dict(colors=list(cores), line=dict(color=tema.FUNDO_CARD, width=3)),
            hovertemplate="%{label}: %{percent}<extra></extra>"))
        self._estilizar(fig, None, altura)
        fig.update_layout(margin=dict(l=30, r=30, t=24, b=44),
                          legend=dict(orientation="h", y=-0.04, x=0.5, xanchor="center"))
        if texto_central:
            fig.add_annotation(text=texto_central, x=0.5, y=0.5, xref="paper", yref="paper",
                               showarrow=False, font=dict(size=14, color=tema.TEXTO))
        return fig

    def barras_horizontais(self, rotulos, valores, cores, textos, rotulo_x=None, altura=370):
        """Ranking em barras horizontais; a primeira categoria fica no topo."""
        fig = go.Figure(go.Bar(
            x=[float(v) for v in valores], y=list(rotulos), orientation="h",
            marker_color=list(cores), text=list(textos), textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>"))
        self._estilizar(fig, None, altura, legenda=False)
        fig.update_layout(margin=dict(l=8, r=110, t=12, b=8))
        fig.update_yaxes(autorange="reversed")
        if rotulo_x:
            fig.update_xaxes(title_text=rotulo_x)
        return fig

    def mapa_calor(self, matriz, textos, rotulo_cor, altura=390):
        """Mapa de calor: vermelho = a dívida subiu, verde = desceu, centro neutro no zero."""
        fig = go.Figure(go.Heatmap(
            z=matriz.values, x=[str(c) for c in matriz.columns], y=[str(i) for i in matriz.index],
            text=textos.values, texttemplate="%{text}", textfont=dict(size=11),
            colorscale=tema.ESCALA_DIVERGENTE, zmid=0, xgap=3, ygap=3,
            colorbar=dict(title=dict(text=rotulo_cor), thickness=12, len=0.9),
            hovertemplate="%{y} · %{x}: %{text}<extra></extra>"))
        self._estilizar(fig, None, altura, legenda=False)
        fig.update_yaxes(type="category", autorange="reversed")
        fig.update_xaxes(type="category", side="top")
        return fig

    def barras_sinal(self, x, y, rotulo_y=None, altura=350):
        """Barras coloridas pelo sinal: vermelho (alta) e verde (queda)."""
        y = [float(v) for v in y]
        fig = go.Figure(go.Bar(
            x=list(x), y=y, marker_color=[tema.VERMELHO if v > 0 else tema.VERDE for v in y],
            hovertemplate="%{x|%m/%Y}: %{y:.1f}<extra></extra>"))
        return self._estilizar(fig, rotulo_y, altura, legenda=False)
