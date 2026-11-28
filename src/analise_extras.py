"""Análise do CUSTO da dívida e da dívida BRUTA: usa as séries extras (IPCA, Selic e DBGG).

Complementa a AnaliseDivida (dívida líquida por setor) com quatro ideias:

* Acumulado em 12 meses: taxas mensais se compõem, não se somam. 12 meses de 1% ao mês valem
  (1,01)^12 − 1 = 12,68%, e não 12%.
* Juro real ex-post: o quanto os juros superaram a inflação *depois* de observados os dois:
  (1 + Selic) ÷ (1 + IPCA) − 1.
* Dívida em termos reais: o saldo em R$ de cada mês, corrigido pelo IPCA para os preços do último mês,
  separa o que é só inflação do que é crescimento de verdade.
      (1 + crescimento nominal) = (1 + inflação) × (1 + crescimento real)
* Selic x PIB nominal: se o custo da dívida (a Selic, como aproximação) supera o crescimento do PIB
  nominal, a dívida tende a crescer em proporção do PIB, salvo superávit primário.

Todas as séries são limitadas ao mesmo horizonte da dívida líquida (o último mês com todos os dados);
por isso o mês corrente da Selic, que ainda está incompleto, nunca entra.
"""
import numpy as np
import pandas as pd

from analise_divida import AnaliseDivida, Janela, _do
from config import TIPO_PORCENTAGEM, TIPO_REAL
from indicador import formatar_mes, formatar_percentual, formatar_pp

SELIC12, IPCA12, JURO_REAL = "Selic (12 meses)", "IPCA (12 meses)", "Juro real (Selic − IPCA)"
PIB12 = "PIB nominal (12 meses)"


class AnaliseExtras:
    def __init__(self, analise: AnaliseDivida, extras: dict):
        self.analise = analise
        self._series = {chave: self._como_serie(df) for chave, df in extras.items()}

    @staticmethod
    def _como_serie(df: pd.DataFrame) -> pd.Series:
        serie = df.set_index("data")["valor"].sort_index()
        return serie[~serie.index.duplicated()]

    def tem(self, *chaves: str) -> bool:
        return all(c in self._series for c in chaves)

    def _horizonte(self, serie: pd.Series) -> pd.Series:
        """Corta no último mês da dívida líquida (o mês corrente da Selic ainda está incompleto)."""
        return serie[serie.index <= self.analise.ultima_data()]

    @staticmethod
    def _anos(obj, ano_ini: int, ano_fim: int):
        return obj[(obj.index.year >= ano_ini) & (obj.index.year <= ano_fim)]

    @staticmethod
    def _acumulado_12m(taxa_mensal: pd.Series) -> pd.Series:
        """Taxa mensal (%) -> acumulado composto em 12 meses (%). Meses faltando viram NaN."""
        mensal = taxa_mensal.asfreq("MS")
        return ((1 + mensal / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100

    @staticmethod
    def longo(df: pd.DataFrame) -> pd.DataFrame:
        """Tabela larga (índice = data) -> formato longo (data, serie, valor), sem os vazios."""
        largo = df.copy()
        largo.index.name = "data"
        return largo.reset_index().melt(id_vars="data", var_name="serie", value_name="valor").dropna()

    def indice_ipca(self) -> pd.Series:
        """Nível do IPCA (base 1 no primeiro mês): permite comparar preços de datas diferentes."""
        return (1 + self._series["ipca"].asfreq("MS") / 100).cumprod()

    # =================================================== juros e inflação
    def juros_inflacao(self, ano_ini: int, ano_fim: int):
        """Selic, IPCA e juro real, todos acumulados em 12 meses (colunas em %). None se faltar dado."""
        if not self.tem("ipca", "selic"):
            return None
        selic = self._acumulado_12m(self._horizonte(self._series["selic"]))
        ipca = self._acumulado_12m(self._horizonte(self._series["ipca"]))
        df = pd.DataFrame({SELIC12: selic, IPCA12: ipca}).dropna()
        df[JURO_REAL] = ((1 + df[SELIC12] / 100) / (1 + df[IPCA12] / 100) - 1) * 100
        df = self._anos(df, ano_ini, ano_fim)
        return None if df.empty else df

    def selic_pib(self, ano_ini: int, ano_fim: int):
        """Selic em 12 meses x crescimento do PIB nominal em 12 meses. None se faltar dado."""
        pib = self.analise.pib_implicito()
        if pib is None or not self.tem("selic"):
            return None
        pib = pib.asfreq("MS")
        selic = self._acumulado_12m(self._horizonte(self._series["selic"]))
        df = pd.DataFrame({SELIC12: selic, PIB12: (pib / pib.shift(12) - 1) * 100}).dropna()
        df = self._anos(df, ano_ini, ano_fim)
        return None if df.empty else df

    def kpis_juros(self, j: Janela) -> dict:
        """Valores em d1 (None quando não calculáveis)."""
        resultado = {"selic": None, "ipca": None, "juro_real": None, "selic_menos_pib": None}
        ji = self.juros_inflacao(j.ano_ini, j.ano_fim)
        if ji is not None and j.d1 in ji.index:
            linha = ji.loc[j.d1]
            resultado.update(selic=float(linha[SELIC12]), ipca=float(linha[IPCA12]), juro_real=float(linha[JURO_REAL]))
        sp = self.selic_pib(j.ano_ini, j.ano_fim)
        if sp is not None and j.d1 in sp.index:
            resultado["selic_menos_pib"] = float(sp.loc[j.d1, SELIC12] - sp.loc[j.d1, PIB12])
        return resultado

    # ====================================================== dívida em termos reais
    def divida_real(self, categoria: str, j: Janela):
        """Saldo em R$ nominal e corrigido pelo IPCA para os preços de d1 (formato longo, R$ milhões)."""
        if not self.tem("ipca"):
            return None
        nominal = self.analise.periodo(TIPO_REAL, j.ano_ini, j.ano_fim)[categoria]
        indice = self.indice_ipca()
        if nominal.empty or nominal.index.min() < indice.index.min() or j.d1 > indice.index.max():
            return None
        real = nominal * indice[j.d1] / indice.reindex(nominal.index)
        if real.isna().any():
            return None
        df = pd.DataFrame({"Nominal": nominal, f"Real (preços de {formatar_mes(j.d1)})": real})
        return self.longo(df)

    def crescimento_real(self, j: Janela, categoria: str):
        """Crescimento nominal, inflação e crescimento real entre d0 e d1 (em %).

        Devolve {'acumulado': {...}, 'anualizado': {...} | None}; 'anualizado' só existe com 12 meses ou mais.
        None se a dívida da categoria for zero/negativa numa das pontas (percentual sem sentido).
        """
        if not self.tem("ipca"):
            return None
        serie = self.analise.completa(TIPO_REAL)[categoria]
        d0, d1 = float(serie[j.d0]), float(serie[j.d1])
        indice = self.indice_ipca()
        if d0 <= 0 or d1 <= 0 or j.d0 < indice.index.min() or j.d1 > indice.index.max():
            return None
        nominal, inflacao = d1 / d0 - 1, indice[j.d1] / indice[j.d0] - 1
        fatores = {"nominal": nominal, "inflacao": inflacao, "real": (1 + nominal) / (1 + inflacao) - 1}
        anualizado = None
        if j.meses >= 12:
            anualizado = {k: ((1 + v) ** (12 / j.meses) - 1) * 100 for k, v in fatores.items()}
        return {"acumulado": {k: v * 100 for k, v in fatores.items()}, "anualizado": anualizado}

    # ================================================= dívida bruta x líquida
    def bruta_liquida(self, ano_ini: int, ano_fim: int):
        """Dívida bruta (duas metodologias) e líquida do governo geral, em % do PIB (formato longo)."""
        liquida = self.analise.tabela(TIPO_PORCENTAGEM).get("Governo Geral")
        if not self.tem("dbgg_atual") or liquida is None:
            return None
        colunas = {"Bruta (metodologia atual)": self._series["dbgg_atual"]}
        if self.tem("dbgg_antiga"):
            colunas["Bruta (metodologia até 2007)"] = self._series["dbgg_antiga"]
        colunas["Líquida (governo geral)"] = liquida
        df = pd.DataFrame(colunas)
        df = self._anos(df[df.index <= self.analise.ultima_data()], ano_ini, ano_fim)
        return None if df.dropna(how="all").empty else self.longo(df)

    def resumo_bruta_liquida(self, j: Janela):
        """Valores de d1 e diferença entre a bruta (metodologia atual) e a líquida. None se não houver."""
        liquida = self.analise.tabela(TIPO_PORCENTAGEM).get("Governo Geral")
        if not self.tem("dbgg_atual") or liquida is None or j.d1 not in self._series["dbgg_atual"].index:
            return None
        bruta, liq = float(self._series["dbgg_atual"][j.d1]), float(liquida[j.d1])
        antiga = self._series["dbgg_antiga"].get(j.d1) if self.tem("dbgg_antiga") else None
        return {"bruta": bruta, "liquida": liq, "diferenca": bruta - liq,
                "antiga": None if antiga is None else float(antiga)}

    # =============================================================== textos
    def frase_real(self, j: Janela, categoria: str):
        """Uma frase sobre o crescimento real, para somar à resposta 'por que aumentou'. None se não houver."""
        c = self.crescimento_real(j, categoria)
        if c is None:
            return None
        if c["anualizado"]:
            a = c["anualizado"]
            return (f"Descontada a inflação (IPCA), o crescimento real foi de {formatar_percentual(a['real'], 1)} ao ano "
                    f"(nominal: {formatar_percentual(a['nominal'], 1)}).")
        a = c["acumulado"]
        return (f"Descontada a inflação (IPCA), o crescimento real no período foi de "
                f"{formatar_percentual(a['real'], 1)} (nominal: {formatar_percentual(a['nominal'], 1)}).")

    def constatacoes_juros(self, j: Janela, categoria: str, foco: str):
        """Constatações da aba 'Juros e inflação', calculadas dos dados."""
        itens = []
        k = self.kpis_juros(j)
        mes1 = formatar_mes(j.d1)
        if k["selic"] is not None:
            itens.append(f"Em {mes1}, a Selic acumulada em 12 meses foi de {formatar_percentual(k['selic'], 1)} e o IPCA, de "
                         f"{formatar_percentual(k['ipca'], 1)}: um juro real ex-post de {formatar_percentual(k['juro_real'], 1)}.")
        sp = self.selic_pib(j.ano_ini, j.ano_fim)
        if sp is not None:
            acima = int((sp[SELIC12] > sp[PIB12]).sum())
            itens.append(f"Em {acima} dos {len(sp)} meses do período, a Selic acumulada em 12 meses superou o crescimento do PIB "
                         f"nominal; quando isso acontece, a dívida tende a crescer em proporção do PIB, salvo superávit primário "
                         f"(a Selic é só uma aproximação do custo médio da dívida).")
        quem = "a dívida total" if foco == "Geral" else f"a dívida {_do(foco)}"
        c = self.crescimento_real(j, categoria)
        if c is not None:
            if c["anualizado"]:
                a = c["anualizado"]
                itens.append(f"Entre {formatar_mes(j.d0)} e {mes1}, {quem} cresceu {formatar_percentual(a['nominal'], 1)} ao ano em valores "
                             f"nominais. Com a inflação (IPCA) de {formatar_percentual(a['inflacao'], 1)} ao ano, o crescimento real foi de "
                             f"{formatar_percentual(a['real'], 1)} ao ano.")
            else:
                a = c["acumulado"]
                itens.append(f"Entre {formatar_mes(j.d0)} e {mes1}, {quem} cresceu {formatar_percentual(a['nominal'], 1)} em valores nominais; "
                             f"com inflação (IPCA) de {formatar_percentual(a['inflacao'], 1)}, o crescimento real foi de "
                             f"{formatar_percentual(a['real'], 1)}.")
        return itens

    def texto_bruta_liquida(self, j: Janela):
        r = self.resumo_bruta_liquida(j)
        if r is None:
            return None
        texto = (f"Em {formatar_mes(j.d1)}, a dívida bruta do governo geral foi de {formatar_percentual(r['bruta'], 1)} do PIB "
                 f"(metodologia atual) e a líquida, de {formatar_percentual(r['liquida'], 1)} (diferença de {formatar_pp(r['diferenca'])}).")
        if r["antiga"] is not None:
            texto += f" Pela metodologia até 2007, a bruta seria {formatar_percentual(r['antiga'], 1)}."
        return texto + " As metodologias medem a dívida bruta de formas diferentes; consulte a nota do Banco Central na página da série."
