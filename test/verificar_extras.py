"""Verificação das séries extras (IPCA, Selic, dívida bruta) com os CSVs reais do projeto.

Rode a partir da raiz:   python test/verificar_extras.py

Cada cálculo é conferido por um caminho independente (laço mês a mês, fórmulas à mão e métodos que já
existiam), para não testar o código contra ele mesmo.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analise_divida import AnaliseDivida, TOTAL
from analise_extras import AnaliseExtras, IPCA12, JURO_REAL, PIB12, SELIC12
from analisador_dados import AnalisadorDados
from config import COMPONENTES, EXTRAS, FOCOS, GERAL, PASTA_DADOS, PASTA_EXTRA, TIPO_PORCENTAGEM as P, TIPO_REAL as R, serie_do_foco
from fonte_dados import FonteDados


def ok(c, m):
    print(("  OK   " if c else "  FALHA"), m)
    assert c, m


fonte = FonteDados()
base = AnaliseDivida(AnalisadorDados(fonte.carregar_tudo()))
extras_df = fonte.carregar_extras()
ex = AnaliseExtras(base, extras_df)
lido = lambda chave: extras_df[chave].set_index("data")["valor"]

print("== séries carregadas")
ok(set(extras_df) == set(EXTRAS), f"4 séries extras presentes: {sorted(extras_df)}")
ok(lido("ipca").index.max() == pd.Timestamp("2026-10-01") and lido("selic").index.max() >= pd.Timestamp("2026-11-01"), "IPCA vai a out/2026 e a Selic inclui o mês corrente")
ok(not AnaliseExtras(base, {}).tem("ipca"), "sem dados, tem() é falso (a aba avisa em vez de quebrar)")

j = base.janela(P, 2002, 2026)
print("== acumulado em 12 meses (conferido com laço independente)")
ji = ex.juros_inflacao(2002, 2026)
def acum(serie, fim, n=12):
    janela = serie[(serie.index > fim - pd.DateOffset(months=n)) & (serie.index <= fim)]
    assert len(janela) == n
    produto = 1.0
    for v in janela: produto *= 1 + v / 100
    return (produto - 1) * 100
fim = pd.Timestamp("2026-09-01")
ok(math.isclose(ji.loc[fim, IPCA12], acum(lido("ipca"), fim), abs_tol=1e-9), f"IPCA 12m set/2026 = {ji.loc[fim, IPCA12]:.4f}% (laço independente)")
ok(math.isclose(ji.loc[fim, SELIC12], acum(lido("selic"), fim), abs_tol=1e-9), f"Selic 12m set/2026 = {ji.loc[fim, SELIC12]:.4f}%")
ok(math.isclose(ji.loc[fim, JURO_REAL], ((1 + ji.loc[fim, SELIC12] / 100) / (1 + ji.loc[fim, IPCA12] / 100) - 1) * 100), f"juro real = {ji.loc[fim, JURO_REAL]:.4f}% (Selic e IPCA compostos)")
ok(ji.index.max() == fim, "horizonte: nunca passa de set/2026 (o mês corrente da Selic, incompleto, não entra)")
ok(math.isclose(acum(pd.Series([1.0] * 12, index=pd.date_range("2020-01-01", periods=12, freq="MS")), pd.Timestamp("2020-12-01")), 12.6825, abs_tol=1e-3), "12 meses de 1% compõem 12,68% (não 12%)")

print("== Selic x PIB nominal")
sp = ex.selic_pib(2002, 2026)
pib = base.pib_implicito()
ok(math.isclose(sp.loc[fim, PIB12], (pib[fim] / pib[fim - pd.DateOffset(months=12)] - 1) * 100), f"PIB nominal 12m = {sp.loc[fim, PIB12]:.2f}% (de dívida em R$ ÷ dívida em % do PIB)")
k = ex.kpis_juros(j)
ok(math.isclose(k["selic_menos_pib"], sp.loc[fim, SELIC12] - sp.loc[fim, PIB12]) and math.isclose(k["juro_real"], ji.loc[fim, JURO_REAL]), "KPIs de juros batem com as tabelas")

print("== dívida em termos reais")
dr = ex.divida_real(TOTAL, j)
nominal = base.completa(R)[TOTAL]
rotulo_real = next(s for s in dr["serie"].unique() if s.startswith("Real"))
real = dr[dr["serie"] == rotulo_real].set_index("data")["valor"]
ok("set/2026" in rotulo_real, f"rótulo explica a base de preços: '{rotulo_real}'")
ok(math.isclose(real[fim], nominal[fim]), "no último mês, real = nominal (os preços são os de d1)")
ipca = lido("ipca"); d0 = pd.Timestamp("2010-12-01")
inflacao_laco = 1.0
for v in ipca[(ipca.index > d0) & (ipca.index <= fim)]: inflacao_laco *= 1 + v / 100
ok(math.isclose(real[d0], nominal[d0] * inflacao_laco, rel_tol=1e-9), f"dez/2010: R$ {nominal[d0]/1e6:.2f} tri nominais valem R$ {real[d0]/1e6:.2f} tri de set/2026 (inflação acumulada {100*(inflacao_laco-1):.1f}%)")
ok(real[d0] > nominal[d0], "no passado, o valor real é maior que o nominal (a inflação corrói)")

print("== crescimento real (identidade e consistência com o método já existente)")
c = ex.crescimento_real(j, TOTAL); ac, an = c["acumulado"], c["anualizado"]
ok(math.isclose((1 + ac["nominal"] / 100), (1 + ac["inflacao"] / 100) * (1 + ac["real"] / 100)), f"(1+nominal) = (1+inflação)(1+real): {ac['nominal']:.1f}% = {ac['inflacao']:.1f}% e {ac['real']:.1f}%")
cagr = base.crescimento_composto(j)
ok(math.isclose(an["nominal"], cagr["divida"], rel_tol=1e-9), f"CAGR nominal ({an['nominal']:.2f}% a.a.) = crescimento_composto() que já existia")
ok(an["real"] < an["nominal"] and an["inflacao"] > 0, f"real {an['real']:.2f}% a.a. < nominal {an['nominal']:.2f}% a.a. (inflação {an['inflacao']:.2f}% a.a.)")
ok(ex.crescimento_real(j, "Banco Central") is None, "Banco Central (negativo): sem percentual (None)")
curta = ex.crescimento_real(base.janela(P, 2026, 2026), TOTAL)
ok(curta["anualizado"] is None and curta["acumulado"]["nominal"] > 0, "janela < 12 meses: só o acumulado, sem anualizar")

print("== dívida bruta x líquida")
bl = ex.bruta_liquida(2002, 2026)
ok(set(bl["serie"]) == {"Bruta (metodologia atual)", "Bruta (metodologia até 2007)", "Líquida (governo geral)"}, "3 séries")
r = ex.resumo_bruta_liquida(j)
atual = lido("dbgg_atual")[fim]; geral = base.tabela(P)["Governo Geral"][fim]
ok(math.isclose(r["bruta"], atual) and math.isclose(r["liquida"], geral) and math.isclose(r["diferenca"], atual - geral), f"set/2026: bruta {r['bruta']:.2f}% x líquida {r['liquida']:.2f}% = diferença {r['diferenca']:.2f} p.p.")
ok(r["antiga"] is not None and r["antiga"] > r["bruta"], f"metodologia antiga ({r['antiga']:.2f}%) acima da atual: são medidas diferentes, não trechos de uma série")
ok(bl[bl["serie"] == "Bruta (metodologia atual)"]["data"].min() == pd.Timestamp("2006-12-01"), "a bruta atual começa em dez/2006 (as linhas partem de datas diferentes)")
sem_dbgg = AnaliseExtras(base, {k: v for k, v in extras_df.items() if not k.startswith("dbgg")})
ok(sem_dbgg.bruta_liquida(2002, 2026) is None and sem_dbgg.texto_bruta_liquida(j) is None, "sem DBGG: None (o cartão some)")

print("== textos: todos os focos, medidas e janelas, sem 'nan' nem erro")
for foco in FOCOS:
    for janela in (j, base.janela(P, 2003, 2013), base.janela(P, 2026, 2026), base.janela(P, 2002, 2002), base.janela(P, 2014, 2020)):
        for t in (ex.constatacoes_juros(janela, serie_do_foco(foco), foco) + [ex.frase_real(janela, serie_do_foco(foco)) or "", ex.texto_bruta_liquida(janela) or ""]):
            assert "nan" not in t.lower().split() and "None" not in t, (foco, t)
print("  OK   6 focos x 5 janelas")
for t in ex.constatacoes_juros(j, TOTAL, GERAL) + [ex.frase_real(j, TOTAL), ex.texto_bruta_liquida(j)]: print("   •", t)
print("   -- Banco Central:", ex.constatacoes_juros(j, "Banco Central", "Banco Central")[-1][:90], "...")
ok(".." not in ex.texto_bruta_liquida(j) and all(".." not in s for s in ex.constatacoes_juros(j, TOTAL, GERAL)), "sem pontuação dupla ('p.p..') nos textos")
print("\nTODOS OS TESTES DAS SÉRIES EXTRAS PASSARAM")
