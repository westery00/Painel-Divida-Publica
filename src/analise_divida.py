"""Análise de domínio: responde às três perguntas do projeto.

    1. De onde vem a dívida?        -> composição por setor (origem)
    2. Qual setor mais contribui?   -> ranking e participação no total
    3. Por que a dívida aumentou?   -> variação, contribuição de cada setor, ritmo vs. PIB

Esta classe NÃO desenha nada nem conhece o Streamlit: recebe o AnalisadorDados
(que limpa e filtra os dados) e devolve tabelas e textos prontos. O Dashboard só
precisa apresentá-los.

Conceitos usados (explicados também na aba "Dados e Metodologia" do painel):

* Tabela "larga" (pivot): uma linha por mês e uma coluna por categoria. Facilita
  somar setores, calcular participações e diferenças entre datas.
* Período comum: só entram os meses em que TODAS as séries existem, nas duas
  medidas. Assim, % do PIB e R$ falam do mesmo intervalo e as partes fecham com o total.
* Janela de análise: a variação de um período é medida a partir do último mês do
  ano anterior ao primeiro ano escolhido (ex.: "2014 a 2016" = dez/2013 -> dez/2016).
  É como o mercado mede "variação no ano": compara fim de ano com fim de ano.
* PIB implícito: como a dívida está em R$ e em % do PIB, PIB = R$ / (% / 100).
* Crescimento composto (CAGR): taxa anual constante que leva do valor inicial ao final.
"""
from dataclasses import dataclass
from functools import reduce

import pandas as pd

from analisador_dados import AnalisadorDados
from config import (COMPONENTES, ESTATAIS_DETALHE, GOVERNOS, ROTULOS_CURTOS, SERIE_PRINCIPAL,
                    SERIES, TIPO_PORCENTAGEM, TIPO_REAL)
from indicador import (formatar_medida, formatar_mes, formatar_percentual, formatar_pp,
                       formatar_variacao)

TOTAL = SERIE_PRINCIPAL
COLUNAS = [TOTAL] + COMPONENTES + ESTATAIS_DETALHE


@dataclass(frozen=True)
class Janela:
    """Intervalo de análise: d0 (data-base) e d1 (posição atual)."""
    d0: pd.Timestamp
    d1: pd.Timestamp
    ano_ini: int
    ano_fim: int

    @property
    def meses(self) -> int:
        return (self.d1.year - self.d0.year) * 12 + (self.d1.month - self.d0.month)

    @property
    def texto(self) -> str:
        return f"{formatar_mes(self.d0)} → {formatar_mes(self.d1)}"


class AnaliseDivida:
    def __init__(self, analisador: AnalisadorDados):
        self.analisador = analisador
        self.__tabelas = {}
        self.__completas = {}

    # ================================================================== base
    def tipos(self) -> list[str]:
        df = self.analisador.get_df_limpo()
        if df.empty or "tipo" not in df.columns:
            return []
        presentes = set(df["tipo"])
        return [t for t in SERIES if t in presentes]

    def tabela(self, tipo: str) -> pd.DataFrame:
        """Tabela larga com todas as categorias do tipo (índice: data)."""
        if tipo not in self.__tabelas:
            if tipo not in self.tipos():
                return pd.DataFrame()
            df = self.analisador.filtrar_dados("tipo", tipo)
            tabela = df.pivot(index="data", columns="categoria", values="valor").sort_index()
            tabela.index.name = "data"
            self.__tabelas[tipo] = tabela
        return self.__tabelas[tipo]

    def completa(self, tipo: str) -> pd.DataFrame:
        """Tabela larga restrita ao período comum (total + componentes + estatais detalhadas)."""
        if tipo not in self.__completas:
            self.__completas[tipo] = self._calcular_completa(tipo)
        return self.__completas[tipo]

    def _calcular_completa(self, tipo: str) -> pd.DataFrame:
        if tipo not in self.tipos():
            return pd.DataFrame()
        indices = []
        for t in self.tipos():
            tabela = self.tabela(t)
            if not set(COLUNAS) <= set(tabela.columns):
                return pd.DataFrame()
            indices.append(tabela[COLUNAS].dropna().index)
        comum = reduce(lambda a, b: a.intersection(b), indices)
        return self.tabela(tipo).loc[comum, COLUNAS]

    def vazio(self) -> bool:
        tipos = self.tipos()
        return not tipos or any(self.completa(t).empty for t in tipos)

    def anos(self) -> tuple[int, int]:
        indice = self.completa(self.tipos()[0]).index
        return int(indice.year.min()), int(indice.year.max())

    def ultima_data(self) -> pd.Timestamp:
        return self.completa(self.tipos()[0]).index.max()

    def janela(self, tipo: str, ano_ini: int, ano_fim: int):
        """Janela de análise para os anos escolhidos (None se não houver dados neles)."""
        indice = self.completa(tipo).index
        dentro = indice[(indice.year >= ano_ini) & (indice.year <= ano_fim)]
        if dentro.empty:
            return None
        antes = indice[indice < pd.Timestamp(year=ano_ini, month=1, day=1)]
        d0 = antes[-1] if len(antes) else dentro[0]
        return Janela(d0, dentro[-1], ano_ini, ano_fim)

    def periodo(self, tipo: str, ano_ini: int, ano_fim: int) -> pd.DataFrame:
        """Tabela larga restrita aos anos escolhidos (todas as categorias)."""
        tabela = self.completa(tipo)
        return tabela[(tabela.index.year >= ano_ini) & (tabela.index.year <= ano_fim)]

    @staticmethod
    def _rotulos_de_ano(indice_datas: pd.DatetimeIndex, anos) -> list[str]:
        """'2026*' para o ano cujo último dado não é dezembro (ano em andamento)."""
        ultimo = indice_datas.to_series().groupby(indice_datas.year).max()
        return [f"{a}*" if ultimo[a].month != 12 else str(a) for a in anos]

    def evolucao(self, tipo: str, categorias: list[str], ano_ini: int, ano_fim: int) -> pd.DataFrame:
        """Série mensal das categorias escolhidas, em formato longo (data, categoria, valor)."""
        ordenadas = [c for c in COLUNAS if c in categorias]
        selecao = self.periodo(tipo, ano_ini, ano_fim)[ordenadas].copy()
        selecao.index.name = "data"
        return selecao.reset_index().melt(id_vars="data", var_name="categoria", value_name="valor")

    # =============================================================== KPIs
    def kpis_foco(self, tipo: str, categoria: str, j: Janela) -> dict:
        """Indicadores de UMA categoria: nível, variação, participação e extremos."""
        tabela = self.completa(tipo)
        serie = tabela[categoria]
        v0, v1 = float(serie[j.d0]), float(serie[j.d1])
        ha_12m = serie.get(j.d1 - pd.DateOffset(months=12))

        longo = self.analisador.filtrar_varios({
            "tipo": tipo, "categoria": categoria,
            "ano": list(range(j.ano_ini, j.ano_fim + 1))})
        pico, data_pico = self.analisador.calcular_pico("valor", longo)
        minimo = self.analisador.calcular_indicadores("valor", longo)["minimo"]

        return {
            "nivel": v1, "nivel0": v0,
            "delta_12m": None if ha_12m is None else v1 - float(ha_12m),
            "variacao": v1 - v0,
            "participacao": v1 / float(tabela.loc[j.d1, TOTAL]) * 100,
            "participacao0": v0 / float(tabela.loc[j.d0, TOTAL]) * 100,
            "pico": float(pico), "pico_data": data_pico, "minimo": float(minimo),
        }

    # ===================================================== 1. de onde vem
    def ranking(self, tipo: str, j: Janela, detalhar_estatais: bool = False) -> pd.DataFrame:
        """Valor e participação (% do total) de cada componente em d1, do maior ao menor."""
        linha = self.completa(tipo).loc[j.d1]
        nomes = []
        for c in COMPONENTES:
            nomes += ESTATAIS_DETALHE if (detalhar_estatais and c == "Empresas Estatais") else [c]
        df = pd.DataFrame({"categoria": nomes, "valor": [float(linha[n]) for n in nomes]})
        df["participacao"] = df["valor"] / float(linha[TOTAL]) * 100
        return df.sort_values("valor", ascending=False).reset_index(drop=True)

    def cascata_composicao(self, tipo: str, j: Janela) -> pd.DataFrame:
        """Dados do gráfico em cascata (waterfall): cada setor soma (ou subtrai) até o total.

        Colunas: rotulo, valor (altura da barra), medida ('relative' | 'total'),
        exibir (número a mostrar no rótulo da barra).
        """
        ordem = self.ranking(tipo, j)
        total = float(self.completa(tipo).loc[j.d1, TOTAL])
        return pd.DataFrame({
            "rotulo": [ROTULOS_CURTOS[c] for c in ordem["categoria"]] + [ROTULOS_CURTOS[TOTAL]],
            "valor": list(ordem["valor"]) + [0.0],  # o total é calculado pelo próprio gráfico
            "medida": ["relative"] * len(ordem) + ["total"],
            "exibir": list(ordem["valor"]) + [total],
        })

    def divisao_governo_geral(self, tipo: str, j: Janela):
        """Federal x estados x municípios dentro do governo geral. Devolve (df, soma)."""
        linha = self.completa(tipo).loc[j.d1]
        df = pd.DataFrame({"categoria": GOVERNOS, "valor": [float(linha[g]) for g in GOVERNOS]})
        soma = float(df["valor"].sum())
        df["participacao"] = df["valor"] / soma * 100
        return df, soma

    def composicao_anual(self, tipo: str, ano_ini: int, ano_fim: int):
        """Saldo de cada componente no fim de cada ano. Devolve (df, nota sobre ano parcial)."""
        selecao = self.periodo(tipo, ano_ini, ano_fim)
        anual = selecao.groupby(selecao.index.year).last()[[TOTAL] + COMPONENTES]
        rotulos = self._rotulos_de_ano(selecao.index, anual.index)
        nota = None
        parcial = [r for r in rotulos if r.endswith("*")]
        if parcial:
            nota = f"{parcial[-1]}: dado mais recente do ano ({formatar_mes(selecao.index.max())})."
        anual.index = rotulos
        return anual, nota

    # ================================================ 2. qual setor contribui
    def participacoes(self, tipo: str, ano_ini: int, ano_fim: int) -> pd.DataFrame:
        """Participação de cada componente no total, mês a mês (formato longo, em %)."""
        selecao = self.periodo(tipo, ano_ini, ano_fim)
        partes = selecao[COMPONENTES].div(selecao[TOTAL], axis=0) * 100
        partes.index.name = "data"
        return partes.reset_index().melt(id_vars="data", var_name="categoria", value_name="valor")

    def destaque_setores(self, tipo: str, j: Janela) -> dict:
        """Maior contribuinte, e quem mais ganhou/perdeu participação entre d0 e d1."""
        tabela = self.completa(tipo)
        p0 = tabela.loc[j.d0, COMPONENTES] / tabela.loc[j.d0, TOTAL] * 100
        p1 = tabela.loc[j.d1, COMPONENTES] / tabela.loc[j.d1, TOTAL] * 100
        mudanca = (p1 - p0).astype(float)
        lider = p1.astype(float).idxmax()
        return {"lider": lider, "participacao": float(p1[lider]), "participacao0": float(p0[lider]),
                "maior_ganho": (mudanca.idxmax(), float(mudanca.max())),
                "maior_perda": (mudanca.idxmin(), float(mudanca.min()))}

    # ============================================== 3. por que aumentou
    def cascata_aumento(self, tipo: str, j: Janela) -> pd.DataFrame:
        """Cascata da variação: dívida em d0 + contribuição de cada setor = dívida em d1."""
        tabela = self.completa(tipo)
        t0, t1 = tabela.loc[j.d0], tabela.loc[j.d1]
        deltas = (t1[COMPONENTES] - t0[COMPONENTES]).astype(float).sort_values(ascending=False)
        return pd.DataFrame({
            "rotulo": [f"Dívida {formatar_mes(j.d0)}"] + [ROTULOS_CURTOS[c] for c in deltas.index]
                      + [f"Dívida {formatar_mes(j.d1)}"],
            "valor": [float(t0[TOTAL])] + list(deltas) + [0.0],
            "medida": ["absolute"] + ["relative"] * len(deltas) + ["total"],
            "exibir": [float(t0[TOTAL])] + list(deltas) + [float(t1[TOTAL])],
        })

    def variacao_anual(self, tipo: str, ano_ini: int, ano_fim: int) -> pd.DataFrame:
        """Variação de cada setor de um fim de ano ao seguinte (linhas: anos; colunas: setores)."""
        tabela = self.completa(tipo)
        anual = tabela[[TOTAL] + COMPONENTES].groupby(tabela.index.year).last()
        delta = anual.diff().loc[ano_ini:ano_fim].dropna(how="all")
        delta.index = self._rotulos_de_ano(tabela.index, delta.index)
        delta.columns = [ROTULOS_CURTOS[c] for c in delta.columns]
        return delta

    def variacao_12m(self, tipo: str, ano_ini: int, ano_fim: int) -> pd.Series:
        """Variação da dívida total em 12 meses, mês a mês."""
        serie = self.completa(tipo)[TOTAL].diff(12)
        return serie[(serie.index.year >= ano_ini) & (serie.index.year <= ano_fim)].dropna()

    def pib_implicito(self):
        """PIB acumulado em 12 meses (R$ milhões) = dívida em R$ / (dívida em % do PIB / 100).

        Usa o total consolidado: por ser um número grande, o arredondamento dos
        CSVs (duas casas) causa erro desprezível (< 0,02%).
        """
        if not {TIPO_PORCENTAGEM, TIPO_REAL} <= set(self.tipos()):
            return None
        pct = self.completa(TIPO_PORCENTAGEM)[TOTAL]
        real = self.completa(TIPO_REAL)[TOTAL]
        return real / (pct / 100)

    def crescimento_12m(self, ano_ini: int, ano_fim: int):
        """Crescimento em 12 meses da dívida (R$) e do PIB nominal, em % (formato longo)."""
        pib = self.pib_implicito()
        if pib is None:
            return None
        divida = self.completa(TIPO_REAL)[TOTAL]
        df = pd.DataFrame({
            "Dívida líquida (R$)": (divida / divida.shift(12) - 1) * 100,
            "PIB nominal": (pib / pib.shift(12) - 1) * 100,
        })
        df = df[(df.index.year >= ano_ini) & (df.index.year <= ano_fim)].dropna()
        df.index.name = "data"
        return df.reset_index().melt(id_vars="data", var_name="serie", value_name="valor")

    def crescimento_composto(self, j: Janela):
        """Crescimento médio ANUAL composto da dívida e do PIB nominal na janela, em %.

        CAGR = (valor_final / valor_inicial) ** (12 / meses) - 1.
        None se a janela tiver menos de 12 meses (anualizar um período curto engana).
        """
        pib = self.pib_implicito()
        if pib is None or j.meses < 12:
            return None
        divida = self.completa(TIPO_REAL)[TOTAL]
        d0, d1, p0, p1 = divida[j.d0], divida[j.d1], pib[j.d0], pib[j.d1]
        if d0 <= 0 or p0 <= 0:
            return None
        expoente = 12 / j.meses
        return {"divida": ((d1 / d0) ** expoente - 1) * 100,
                "pib": ((p1 / p0) ** expoente - 1) * 100}

    def extremos(self, j: Janela):
        """Menor/maior nível e maior alta/queda em 12 meses da dívida total, em % do PIB."""
        if TIPO_PORCENTAGEM not in self.tipos():
            return None
        serie = self.completa(TIPO_PORCENTAGEM)[TOTAL]
        no_periodo = serie[(serie.index.year >= j.ano_ini) & (serie.index.year <= j.ano_fim)]
        d12 = serie.diff(12)
        d12 = d12[(d12.index.year >= j.ano_ini) & (d12.index.year <= j.ano_fim)].dropna()
        resultado = {"minimo": (float(no_periodo.min()), no_periodo.idxmin()),
                     "maximo": (float(no_periodo.max()), no_periodo.idxmax()),
                     "alta_12m": None, "queda_12m": None}
        if not d12.empty:
            resultado["alta_12m"] = (float(d12.max()), d12.idxmax())
            resultado["queda_12m"] = (float(d12.min()), d12.idxmin())
        return resultado

    # ========================================================== textos
    def respostas(self, tipo: str, j: Janela) -> list[dict]:
        """As três respostas curtas (pergunta, destaque, texto), calculadas dos dados."""
        tabela = self.completa(tipo)
        l0, l1 = tabela.loc[j.d0], tabela.loc[j.d1]
        t0, t1 = float(l0[TOTAL]), float(l1[TOTAL])
        mes1, mes0 = formatar_mes(j.d1), formatar_mes(j.d0)
        parte = lambda v: formatar_percentual(float(v) / t1 * 100, 1)
        nivel = lambda v: formatar_medida(tipo, v) + (" do PIB" if tipo == TIPO_PORCENTAGEM else "")

        # 1. De onde vem
        governo = float(l1[GOVERNOS].sum())
        credora = ""
        if float(l1["Banco Central"]) < 0:
            credora = " (sinal negativo: posição credora líquida"
            credora += ", por isso o governo geral passa de 100%)" if governo / t1 > 1.0005 else ")"
        q1 = {
            "pergunta": "De onde vem a dívida?",
            "destaque": f"{formatar_percentual(governo / t1 * 100, 0)} no governo geral",
            "texto": (f"Em {mes1}, a dívida líquida consolidada é de {nivel(t1)}. Federal, estados e "
                      f"municípios respondem por {formatar_percentual(governo / t1 * 100, 1)} desse total; "
                      f"as empresas estatais, por {parte(l1['Empresas Estatais'])}, e o Banco Central, "
                      f"por {parte(l1['Banco Central'])}{credora}."),
        }

        # 2. Qual setor mais contribui
        rk = self.ranking(tipo, j)
        top, seg, ter = rk.iloc[0], rk.iloc[1], rk.iloc[2]
        part0 = float(l0[top["categoria"]]) / t0 * 100
        q2 = {
            "pergunta": "Qual setor mais contribui?",
            "destaque": f"{top['categoria']}: {formatar_percentual(top['participacao'], 1)}",
            "texto": (f"Em {mes1}, {top['categoria']} responde por {formatar_percentual(top['participacao'], 1)} "
                      f"do total ({nivel(top['valor'])}); em {mes0}, eram {formatar_percentual(part0, 1)}. "
                      f"Em seguida vêm {seg['categoria']} ({formatar_percentual(seg['participacao'], 1)} do total) "
                      f"e {ter['categoria']} ({formatar_percentual(ter['participacao'], 1)})."),
        }

        # 3. Por que aumentou
        delta = t1 - t0
        deltas = (l1[COMPONENTES] - l0[COMPONENTES]).astype(float)
        nome = deltas.idxmax() if delta >= 0 else deltas.idxmin()
        verbo = "subiu" if delta > 0 else "caiu" if delta < 0 else "ficou estável"
        texto = (f"Entre {mes0} e {mes1} a dívida {verbo}, de {formatar_medida(tipo, t0)} para "
                 f"{nivel(t1)}. {nome} contribuiu com {formatar_variacao(tipo, deltas[nome])}")
        if abs(delta) > 0.001 * abs(t0):
            participacao = deltas[nome] / delta * 100
            texto += f", {formatar_percentual(participacao, 0)} da variação"
            if participacao > 100:
                texto += " (mais que o total, pois outros setores recuaram)"
        texto += "."
        cagr = self.crescimento_composto(j)
        if cagr:
            texto += (f" Em média, a dívida cresceu {formatar_percentual(cagr['divida'], 1)} ao ano, "
                      f"contra {formatar_percentual(cagr['pib'], 1)} ao ano do PIB nominal.")
        q3 = {"pergunta": "Por que a dívida aumentou?" if delta >= 0 else "Por que a dívida diminuiu?",
              "destaque": formatar_variacao(tipo, delta), "texto": texto}
        return [q1, q2, q3]

    def conclusoes(self, tipo: str, j: Janela) -> list[str]:
        """Outras constatações do período (extremos, Banco Central, mudança de participação)."""
        itens = []
        ext = self.extremos(j)
        if ext:
            (vmin, dmin), (vmax, dmax) = ext["minimo"], ext["maximo"]
            itens.append(f"A dívida consolidada teve seu menor nível em {formatar_mes(dmin)} "
                         f"({formatar_percentual(vmin, 1)} do PIB) e o maior em {formatar_mes(dmax)} "
                         f"({formatar_percentual(vmax, 1)} do PIB).")
            if ext["alta_12m"]:
                (alta, d_alta), (queda, d_queda) = ext["alta_12m"], ext["queda_12m"]
                itens.append(f"A maior alta em 12 meses foi de {formatar_pp(alta)} (até {formatar_mes(d_alta)}) "
                             f"e a maior queda, de {formatar_pp(queda)} (até {formatar_mes(d_queda)}).")

        selecao = self.periodo(tipo, j.ano_ini, j.ano_fim)
        if not selecao.empty:
            negativos = int((selecao["Banco Central"] < 0).sum())
            itens.append(f"O Banco Central ficou com dívida líquida negativa (posição credora) em "
                         f"{negativos} dos {len(selecao)} meses do período, o que reduz o total consolidado.")

        d = self.destaque_setores(tipo, j)
        (ganha, v_ganho), (perde, v_perda) = d["maior_ganho"], d["maior_perda"]
        itens.append(f"Entre {formatar_mes(j.d0)} e {formatar_mes(j.d1)}, quem mais ganhou participação no "
                     f"total foi {ganha} ({formatar_pp(v_ganho)}); quem mais perdeu foi {perde} "
                     f"({formatar_pp(v_perda)}).")
        return itens
