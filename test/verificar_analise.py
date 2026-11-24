"""Verificação da camada de análise com os CSVs reais do projeto.

Rode a partir da raiz:   python tests/verificar_analise.py

Confere os números das três perguntas contra identidades matemáticas (partes que
somam o total, soma das variações anuais = variação total) e contra valores
calculados à parte. Usa só pandas: não precisa de Streamlit nem de Plotly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import math, logging
import pandas as pd
logging.basicConfig(level=logging.ERROR)
from fonte_dados import FonteDados
from analisador_dados import AnalisadorDados
from analise_divida import AnaliseDivida, TOTAL
from config import COMPONENTES, GOVERNOS, TIPO_PORCENTAGEM as P, TIPO_REAL as R
from indicador import *

def ok(c, m): print(("  OK   " if c else "  FALHA"), m); assert c, m
an = AnaliseDivida(AnalisadorDados(FonteDados().carregar_tudo()))

print("== base")
ok(an.tipos() == [P, R] and not an.vazio(), "dois tipos; não vazio")
ok(an.completa(P).index.equals(an.completa(R).index), "período comum idêntico nas duas medidas")
print("      anos:", an.anos(), "| última data:", formatar_mes(an.ultima_data()), "| meses:", len(an.completa(P)))
ok(an.anos() == (2002, 2026), "2002–2026")

print("== janela")
j = an.janela(P, 2014, 2026)
ok(formatar_mes(j.d0) == "dez/2013" and formatar_mes(j.d1) == "set/2026", f"2014–2026 parte de {j.texto}")
j0 = an.janela(P, 2002, 2026); ok(formatar_mes(j0.d0) == "jan/2002", f"2002–2026 parte do 1º mês disponível ({j0.texto})")
ok(an.janela(P, 1990, 1995) is None, "anos sem dados -> None")
j1 = an.janela(P, 2026, 2026); ok(j1.meses == 9, f"só 2026: {j1.meses} meses")

print("== KPIs do foco")
k = an.kpis_foco(P, TOTAL, j)
ok(math.isclose(k["nivel"], 69.98, abs_tol=.01) and math.isclose(k["nivel0"], 30.5, abs_tol=.1), f"consolidado: {k['nivel0']:.2f} -> {k['nivel']:.2f}")
ok(math.isclose(k["variacao"], 39.48, abs_tol=.02), f"variação {k['variacao']:.2f} p.p. (esperado 39,48 da exploração)")
ok(k["pico_data"] == pd.Timestamp("2026-09-01") and math.isclose(k["minimo"], 30.01, abs_tol=.01), f"pico {k['pico']:.2f} em {formatar_mes(k['pico_data'])}; mínimo {k['minimo']:.2f}")
ok(math.isclose(k["participacao"], 100), "participação do total = 100%")
kf = an.kpis_foco(P, "Governo Federal", j)
ok(math.isclose(kf["participacao"], 88.5, abs_tol=.1) and kf["delta_12m"] is not None, f"federal: {kf['participacao']:.1f}% do total; Δ12m {kf['delta_12m']:+.2f}")
ok(an.kpis_foco(P, TOTAL, an.janela(P, 2002, 2002))["delta_12m"] is None, "sem 12 meses anteriores -> delta None")
kb = an.kpis_foco(P, "Banco Central", j); ok(kb["participacao"] < 0, f"Banco Central: participação negativa ({kb['participacao']:.2f}%)")

print("== 1. De onde vem")
rk = an.ranking(P, j)
ok(rk.iloc[0]["categoria"] == "Governo Federal" and rk.iloc[-1]["categoria"] == "Banco Central", f"ranking: {list(rk.categoria)}")
ok(math.isclose(rk["participacao"].sum(), 100, abs_tol=.1), f"participações somam {rk['participacao'].sum():.2f}%")
rd = an.ranking(P, j, detalhar_estatais=True); ok(len(rd) == 7 and "Empresas Estatais" not in set(rd.categoria), "detalhar estatais: 7 linhas (3 em vez de 1)")
ok(math.isclose(rd["valor"].sum(), rk["valor"].sum(), abs_tol=.05), "detalhado soma o mesmo")
for tipo in (P, R):
    c = an.cascata_composicao(tipo, j)
    soma = c[c.medida == "relative"]["valor"].sum(); total = c.iloc[-1]["exibir"]
    ok(c.iloc[-1]["medida"] == "total" and math.isclose(soma, total, rel_tol=1e-3), f"[{tipo}] cascata: soma das partes {soma:,.2f} = total {total:,.2f}")
dg = an.divisao_grupo(P, j); g, soma = dg["df"], dg["soma"]
ok(math.isclose(g["participacao"].sum(), 100) and math.isclose(soma, 70.06, abs_tol=.1), f"governo geral = {soma:.2f}; shares {g.participacao.round(1).tolist()}")
ca, nota = an.composicao_anual(P, 2002, 2026)
ok(list(ca.index)[0] == "2002" and list(ca.index)[-1] == "2026*" and "set/2026" in nota, f"anual: {ca.index[0]}…{ca.index[-1]} | nota: {nota}")
ok(math.isclose(ca.loc["2013", TOTAL], 30.5, abs_tol=.1) and math.isclose(ca.loc["2002", TOTAL], 59.9, abs_tol=.1), "valores de fim de ano batem (2013=30,5; 2002=59,9)")
ok(math.isclose(ca.loc["2013", COMPONENTES].sum(), ca.loc["2013", TOTAL], abs_tol=.05), "componentes somam o total em 2013")

print("== 2. Qual setor")
pt = an.participacoes(P, 2002, 2026)
ok(set(pt.columns) == {"data", "categoria", "valor"} and pt["categoria"].nunique() == 5, "participações em formato longo, 5 setores")
s = pt[pt.data == pt.data.max()].set_index("categoria")["valor"]; ok(math.isclose(s.sum(), 100, abs_tol=.1), "somam 100% no último mês")
d = an.destaque_setores(P, j)
ok(d["lider"] == "Governo Federal" and d["maior_ganho"][0] == "Governo Federal" and d["maior_perda"][0] == "Governos Estaduais", f"líder {d['lider']}; ganho {d['maior_ganho']}; perda {d['maior_perda']}")

print("== 3. Por que aumentou")
ca_ = an.cascata_aumento(P, j)
ok(math.isclose(ca_.iloc[0]["exibir"] + ca_[ca_.medida == "relative"]["exibir"].sum(), ca_.iloc[-1]["exibir"], abs_tol=.05), "início + contribuições = fim")
ok(ca_.iloc[1]["rotulo"] == "Federal" and math.isclose(ca_.iloc[1]["exibir"], 41.47, abs_tol=.02), f"1ª barra: {ca_.iloc[1]['rotulo']} {ca_.iloc[1]['exibir']:+.2f} (esperado +41,47)")
va = an.variacao_anual(P, 2014, 2026)
ok(list(va.columns) == ["Total", "Federal", "Estados", "Municípios", "Estatais", "Banco Central"] and va.index[0] == "2014" and va.index[-1] == "2026*", f"heatmap: {va.shape}, {va.index[0]}…{va.index[-1]}")
ok(math.isclose(va.loc["2020", "Total"], 61.4 - 54.7, abs_tol=.15), f"variação 2020: {va.loc['2020','Total']:+.2f} (≈ 61,4 − 54,7)")
ok(math.isclose(va["Total"].sum(), 69.98 - 30.5, abs_tol=.1), "soma das variações anuais = variação total (2014→2026)")
v12 = an.variacao_12m(P, 2002, 2026); ok(math.isclose(v12.max(), 11.61, abs_tol=.02) and v12.idxmax() == pd.Timestamp("2016-09-01"), f"maior alta 12m {v12.max():.2f} em {formatar_mes(v12.idxmax())}")
ok(math.isclose(v12.min(), -7.72, abs_tol=.02), f"maior queda 12m {v12.min():.2f}")
pib = an.pib_implicito()
ok(math.isclose(pib["2014-12-01"] / 1e6, 5.78, abs_tol=.02) and math.isclose(pib["2019-12-01"] / 1e6, 7.39, abs_tol=.02), f"PIB implícito 2014: R$ {pib['2014-12-01']/1e6:.2f} tri | 2019: R$ {pib['2019-12-01']/1e6:.2f} tri (oficial: 5,78 e 7,39)")
cg = an.crescimento_composto(j); ok(math.isclose(cg["divida"], 14.73, abs_tol=.02) and math.isclose(cg["pib"], 7.5, abs_tol=.05), f"CAGR dívida {cg['divida']:.2f}% | PIB {cg['pib']:.2f}% (esperado 14,73 / 7,5)")
ok(an.crescimento_composto(j1) is None, "janela < 12 meses -> None")
c12 = an.crescimento_12m(2002, 2026); ok(set(c12.serie) == {"Dívida líquida (R$)", "PIB nominal"} and set(c12.columns) == {"data", "serie", "valor"}, "crescimento 12m: 2 séries, formato longo")
ex = an.extremos(j); ok(math.isclose(ex["minimo"][0], 30.01, abs_tol=.01) and ex["minimo"][1] == pd.Timestamp("2014-01-01") and ex["maximo"][1] == pd.Timestamp("2026-09-01"), f"extremos 2014–2026: mín {ex['minimo'][0]:.2f} ({formatar_mes(ex['minimo'][1])}), máx {ex['maximo'][0]:.2f} ({formatar_mes(ex['maximo'][1])})")

print("== textos (inspeção)")
for r in an.respostas(P, j): print(f"   [{r['pergunta']}] {r['destaque']}\n      {r['texto']}")
for t in an.conclusoes(P, j): print("   •", t)
print("   --- medida em R$:"); print("     ", an.respostas(R, j)[2]["texto"])
print("   --- janela em QUEDA (2003–2013):"); r = an.respostas(P, an.janela(P, 2003, 2013)); print("     ", r[2]["pergunta"], "|", r[2]["destaque"], "\n     ", r[2]["texto"])
print("   --- janela curta (2026):"); print("     ", an.respostas(P, j1)[2]["texto"])

print("== formatadores")
tests = [(formatar_reais(9379279), "R$ 9,38 tri"), (formatar_reais(842310.5), "R$ 842,31 bi"), (formatar_reais(1250), "R$ 1,25 bi"), (formatar_reais(500), "R$ 500,00 mi"),
         (formatar_reais(-740528.4), "-R$ 740,53 bi"), (formatar_reais(7380000, sinal=True), "+R$ 7,38 tri"), (formatar_pp(39.48), "+39,5 p.p."), (formatar_pp(-7.72), "-7,7 p.p."),
         (formatar_percentual(70.056, 2), "70,06%"), (formatar_percentual(1234.5, 1), "1.234,5%"), (formatar_variacao(R, 7380000), "+R$ 7,38 tri"), (formatar_variacao(P, 3.2), "+3,2 p.p."),
         (formatar_mes(pd.Timestamp("2026-09-01")), "set/2026"), (IndicadorMonetario("x", 9379279.0).formatar_valor(), "R$ 9,38 tri"), (IndicadorPercentual("x", None).formatar_valor(), "n/d")]
for got, want in tests: ok(got == want, f"{got!r}")

print("== Dado em foco (Geral x setores)")
from config import FOCOS, GERAL, ESTATAIS_DETALHE
setores = [f for f in FOCOS if f != GERAL]
pos = {f: an.posicao_foco(P, j, f) for f in setores}
ok(sorted(v["posicao"] for v in pos.values()) == [1, 2, 3, 4, 5], f"posições 1 a 5 sem repetir: {[(f.split()[-1], v['posicao']) for f, v in pos.items()]}")
ok(math.isclose(sum(v["participacao"] for v in pos.values()), 100, abs_tol=.1), "participações dos 5 setores somam 100%")
for tipo in (P, R):
    jj = an.janela(tipo, 2014, 2026); pp = {f: an.posicao_foco(tipo, jj, f) for f in setores}
    dt = pp[setores[0]]["variacao_total"]
    ok(math.isclose(sum(v["variacao"] for v in pp.values()), dt, rel_tol=2e-3, abs_tol=.05), f"[{tipo}] contribuições dos 5 setores somam a variação total ({dt:,.2f})")
    ok(math.isclose(sum(v["pct_da_variacao"] for v in pp.values()), 100, abs_tol=.5), f"[{tipo}] % da variação soma 100%")
ok(pos["Governo Federal"]["posicao"] == 1 and math.isclose(pos["Governo Federal"]["pct_da_variacao"], 105.0, abs_tol=.3), f"Federal: 1º, {pos['Governo Federal']['pct_da_variacao']:.1f}% da variação (41,47 ÷ 39,48)")
ok(pos["Governos Estaduais"]["pct_da_variacao"] < 0, f"Estados contribuíram no sentido oposto ({pos['Governos Estaduais']['pct_da_variacao']:.1f}%)")

print("== divisao_grupo / crescimento / extremos por setor")
ok(an.divisao_grupo(P, j, "Banco Central") is None, "Banco Central: sem rosca (não pertence a nenhum grupo)")
for f in ("Governo Federal", "Governos Estaduais", "Governos Municipais"):
    d = an.divisao_grupo(P, j, f); ok(d["destaque"] == f and d["curto"] == "Governo geral", f"{f}: rosca do governo geral com destaque")
de = an.divisao_grupo(P, j, "Empresas Estatais")
print("      estatais por esfera (% PIB):", an.completa(P).loc[j.d1, ESTATAIS_DETALHE].round(2).to_dict(), "->", "rosca aplicável" if de else "rosca omitida (há valor <= 0)")
ok(an.divisao_grupo(P, j, GERAL)["destaque"] is None, "Geral: rosca do governo geral sem destaque")
ok(an.crescimento_12m(2002, 2026, "Banco Central") is None, "crescimento 12m do Banco Central -> None (série ≤ 0)")
ok(set(an.crescimento_12m(2002, 2026)["serie"]) == {"Dívida líquida (R$)", "PIB nominal"}, "Geral: 2 linhas (dívida e PIB)")
c = an.crescimento_12m(2002, 2026, "Governo Federal"); ok(set(c["serie"]) == {"Governo Federal (R$)", "Dívida total (R$)", "PIB nominal"}, "Federal: 3 linhas (setor, total e PIB)")
cf = an.crescimento_composto(j, "Governo Federal"); r_ = an.completa(R)["Governo Federal"]; m = j.meses
ok(math.isclose(cf["divida"], ((r_[j.d1] / r_[j.d0]) ** (12 / m) - 1) * 100), f"CAGR do federal: {cf['divida']:.2f}% a.a. (confere com o cálculo manual)")
ok(an.crescimento_composto(j, "Banco Central") is None, "CAGR do Banco Central -> None")
ef = an.extremos(j, "Governo Federal"); ok(ef["maximo"][1] == pd.Timestamp("2026-09-01") and ef["minimo"][0] > 0, f"extremos do federal: máx {ef['maximo'][0]:.1f} ({formatar_mes(ef['maximo'][1])})")
ok(len(an.variacao_12m(P, 2002, 2026, "Banco Central")) > 0, "variação 12m do Banco Central existe (barras funcionam com negativos)")

print("== textos por setor")
for tipo in (P, R):
    for f in FOCOS:
        for jj in (j, an.janela(tipo, 2003, 2013), an.janela(tipo, 2026, 2026), an.janela(tipo, 2002, 2002)):
            rs = an.respostas(tipo, jj, f); cs = an.conclusoes(tipo, jj, f)
            ok(len(rs) == 3 and all(r["pergunta"] and r["destaque"] and r["texto"] for r in rs) and cs, "") if False else None
            assert len(rs) == 3 and all(r["pergunta"] and r["destaque"] and r["texto"] for r in rs) and cs, (tipo, f, jj)
            assert not any("nan" in r["texto"].lower().split() or "None" in r["texto"] for r in rs + [{"texto": c} for c in cs]), (tipo, f)
print("  OK   respostas e conclusões para 6 focos x 2 medidas x 4 janelas (sem erro, sem 'nan'/'None')")
for f in ("Banco Central", "Governos Estaduais", "Empresas Estatais"):
    print(f"   ── {f}")
    for r in an.respostas(P, j, f): print(f"     [{r['pergunta']}] {r['destaque']}\n        {r['texto']}")
    for t_ in an.conclusoes(P, j, f): print("      •", t_)

print("\nTODOS OS TESTES DA ANÁLISE PASSARAM")
