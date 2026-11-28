"""Verificação do painel inteiro, sem Streamlit nem Plotly instalados.

Rode a partir da raiz:   python test/verificar_painel.py

O Streamlit e o Plotly são SUBSTITUÍDOS por versões simuladas que registram tudo o que o painel desenha
e validam o que a API real aceitaria (nomes de propriedades, tamanhos dos vetores, colunas existentes,
chaves únicas). Isso pega erros de lógica e de integração, mas NÃO substitui abrir o painel de verdade:
rode `streamlit run src/main.py` para ver o resultado visual.
"""
import sys, types, math, re
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ======================= Plotly falso, com validação do que a API aceita =======================
VALIDOS = {
 "Bar": {"x","y","base","name","marker_color","orientation","marker","text","textposition","cliponaxis","hovertemplate"},
 "Scatter": {"x","y","name","mode","marker","line"},
 "Pie": {"labels","values","hole","sort","direction","textinfo","textposition","pull","marker","hovertemplate"},
 "Heatmap": {"z","x","y","text","texttemplate","textfont","colorscale","zmid","xgap","ygap","colorbar","hovertemplate"},
}
LAYOUT = {"template","paper_bgcolor","plot_bgcolor","font","height","margin","showlegend","separators","legend","hoverlabel","title","hovermode","barmode"}
SUB = {"legend": {"orientation","yanchor","y","xanchor","x","title_text","bgcolor"}, "margin": {"l","r","t","b"},
       "font": {"family","color","size"}, "hoverlabel": {"bgcolor","font_color","bordercolor"}, "title": {"text","x","xanchor","font"}}
EIXO = {"gridcolor","zeroline","linecolor","title_text","type","autorange","side"}
SHAPE = {"type","xref","yref","x0","x1","y0","y1","fillcolor","line","layer"}
ANOT = {"x","y","xref","yref","text","showarrow","yanchor","font"}
def chk(nome, usados, validos):
    ruim = set(usados) - validos
    assert not ruim, f"{nome}: propriedade(s) inexistente(s) {ruim}"

class Traco:
    def __init__(self, tipo, **kw):
        chk(f"go.{tipo}", kw, VALIDOS[tipo]); self.tipo, self.kw = tipo, kw
        n = None
        for k in ("x","y","labels","values","text","base","pull"):
            if k in kw and kw[k] is not None and tipo != "Heatmap":
                m = len(list(kw[k])); n = n or m
                assert m == n, f"go.{tipo}: tamanhos diferentes ({k}={m} vs {n})"
        mc = kw.get("marker_color")
        if isinstance(mc, list): assert len(mc) == n, "marker_color com tamanho diferente"
        if tipo == "Pie": assert len(kw["marker"]["colors"]) == n, "cores da rosca != fatias"
        if tipo == "Heatmap":
            z = kw["z"]; assert len(z) == len(kw["y"]) and len(z[0]) == len(kw["x"]), "z != (len(y), len(x))"
            assert len(kw["text"]) == len(z) and len(kw["text"][0]) == len(z[0]), "text != z"
        eixo_valor = "x" if kw.get("orientation") == "h" else "y"
        for k in (eixo_valor, "z", "base"):
            if k in kw and tipo in ("Bar","Scatter"):
                assert all(isinstance(v, float) and not math.isnan(v) for v in kw[k]), f"go.{tipo}.{k} com NaN/não-float"

class TracoPx:
    def __init__(self, nome): self.name = nome; self.opacity = None; self.largura = None
    def update(self, **kw):
        chk("trace.update", kw, {"opacity", "line"}); self.opacity = kw.get("opacity", self.opacity)
        if "line" in kw: chk("trace.line", kw["line"], {"width"}); self.largura = kw["line"]["width"]

class Fig:
    def __init__(self, tracos=None, origem="go"): self.tracos = tracos or []; self.origem = origem; self.layout = {}; self.formas = []; self.anots = 0; self.px_tracos = []
    def update_layout(self, **kw):
        chk("layout", kw, LAYOUT)
        for k, v in kw.items():
            if k in SUB and isinstance(v, dict): chk(f"layout.{k}", v, SUB[k])
        self.layout.update(kw); return self
    def update_traces(self, **kw): return self
    def for_each_trace(self, fn): [fn(t) for t in self.px_tracos]; return self
    def update_xaxes(self, **kw): chk("xaxis", kw, EIXO); return self
    def update_yaxes(self, **kw): chk("yaxis", kw, EIXO); return self
    def add_trace(self, t): assert isinstance(t, Traco); self.tracos.append(t); return self
    def add_shape(self, **kw): chk("shape", kw, SHAPE); self.formas.append(kw); return self
    def add_annotation(self, **kw): chk("annotation", kw, ANOT); self.anots += 1; return self

go = types.ModuleType("plotly.graph_objects")
go.Figure = lambda *t: Fig(list(t))
for nome in VALIDOS: setattr(go, nome, (lambda n: lambda **kw: Traco(n, **kw))(nome))

px = types.ModuleType("plotly.express")
def _px(nome, df, **cols):
    for arg, col in cols.items():
        if col is not None and arg in ("x","y","color","values","names"):
            assert col in df.columns, f"px.{nome}: coluna '{col}' ({arg}) não existe em {list(df.columns)}"
    f = Fig(origem="px"); f.df = df; f.cols = cols
    if cols.get("color"): f.px_tracos = [TracoPx(n) for n in dict.fromkeys(df[cols["color"]])]
    return f
for nome in ("line","bar","pie","box"):
    setattr(px, nome, (lambda n: lambda df, **kw: _px(n, df, **{k: v for k, v in kw.items() if k in ("x","y","color","values","names")}))(nome))
pl = types.ModuleType("plotly"); pl.express, pl.graph_objects = px, go
sys.modules.update({"plotly": pl, "plotly.express": px, "plotly.graph_objects": go})

# ============================== Streamlit falso ==============================
rec = {"abas": [], "laterais": [], "botoes": [], "markdown": [], "graficos": [], "chaves": [], "infos": [], "erros": [], "avisos": [], "tabelas": [], "chamadas": [], "legendas": [], "defaults": {}}
resp = {}
class Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def markdown(self, t, **k): rec["markdown"].append(t)
st = types.ModuleType("streamlit")
st.set_page_config = lambda **k: rec["chamadas"].append("set_page_config")
st.markdown = lambda t, **k: rec["markdown"].append(t)
st.write = lambda *a, **k: None
st.caption = lambda t, **k: rec["legendas"].append(t)
st.info = lambda t, **k: rec["infos"].append(t)
st.warning = lambda t, **k: rec["avisos"].append(t)
st.error = lambda t, **k: rec["erros"].append(t)
def _container(border=False, key=None):
    assert key is None or key not in rec["chaves"], f"chave de cartão duplicada: {key}"
    rec["chaves"].append(key); return Ctx()
st.container = _container
st.columns = lambda spec: [Ctx() for _ in range(spec if isinstance(spec, int) else len(spec))]
st.tabs = lambda nomes: (rec["abas"].append(list(nomes)), [Ctx() for _ in nomes])[1]
st.expander = lambda *a, **k: Ctx()
def _multi(label, options, default=None, key=None, **k):
    assert all(d in options for d in (default or [])), "default fora das opções"
    rec["defaults"][key] = list(default or []); return resp.get(key, default or [])
st.multiselect = _multi
st.toggle = lambda label, key=None, value=False, **k: resp.get(key, value)
def _plotly(fig, key=None, theme="x", config=None, **k):
    assert isinstance(fig, Fig); assert theme is None; assert key and key not in [g[0] for g in rec["graficos"]], f"key de gráfico duplicada: {key}"
    assert not k.get("use_container_width"); rec["graficos"].append((key, fig))
st.plotly_chart = _plotly
def _df(df, hide_index=None, column_config=None, **k):
    assert not k.get("use_container_width"); rec["tabelas"].append((df, column_config))
st.dataframe = _df
st.column_config = types.SimpleNamespace(NumberColumn=lambda label, format=None: ("num", label, format))
def _radio(label, options, format_func=str, **k):
    [format_func(o) for o in options]; return resp.get("radio", options[0])
def _slider(label, mn, mx, value, **k):
    v = resp.get("slider", value); assert mn <= v[0] <= v[1] <= mx; return v
def _select(label, options, **k):
    assert list(options); return resp.get("foco", list(options)[0])
def _botao(label, on_click=None, **k): rec["botoes"].append((label, on_click)); return False
def _cache_resource(*a, **k):
    def decorador(f):
        f.clear = lambda: None
        return f
    return decorador
st.cache_resource = _cache_resource
st.sidebar = types.SimpleNamespace(markdown=lambda t, **k: rec["markdown"].append(t), caption=lambda t, **k: rec["legendas"].append(t),
                                   radio=_radio, slider=_slider, selectbox=_select, warning=lambda t, **k: rec["laterais"].append(t),
                                   button=_botao, expander=lambda *a, **k: Ctx())
sys.modules["streamlit"] = st

# ================================= testes =================================
import main
from atualizador_dados import RelatorioAtualizacao, ResultadoSerie, STATUS_EM_DIA, STATUS_MANTIDA, STATUS_ATUALIZADA
from config import SERIES as _SERIES, EXTRAS as _EXTRAS
from datetime import datetime

def relatorio(status=STATUS_EM_DIA, sem_conexao=False, mantidas=()):
    r = RelatorioAtualizacao(quando=datetime(2026, 11, 25, 14, 3), sem_conexao=sem_conexao)
    for t in _SERIES:
        for a, serie in _SERIES[t].items():
            st_ = STATUS_MANTIDA if a in mantidas or sem_conexao else status
            r.series.append(ResultadoSerie(t, a, serie.categoria, st_, "sem conexão com o Banco Central" if sem_conexao else
                                           ("série descartada: só 0% dos valores coincidem" if st_ == STATUS_MANTIDA else "em dia até set/2026"), 4513))
    for e in _EXTRAS.values():
        st_ = STATUS_MANTIDA if sem_conexao else status
        r.series.append(ResultadoSerie("extra", e.arquivo, e.nome, st_, "sem conexão com o Banco Central" if sem_conexao else "em dia até set/2026", e.codigo_sgs))
    return r
chamadas_atualizacao = []
class FakeCache:
    def __init__(self, r): self.r = r; self.limpou = 0
    def __call__(self): chamadas_atualizacao.append(1); return self.r
    def clear(self): self.limpou += 1
cache_falso = FakeCache(relatorio())
original_atualizar = main.atualizar_dados
main.atualizar_dados = cache_falso
from analisador_dados import AnalisadorDados
from analise_divida import AnaliseDivida, TOTAL
from config import COMPONENTES, FOCOS, GERAL, ESTATAIS_DETALHE
from dashboard import Dashboard
from fonte_dados import FonteDados
from visualizador import Visualizador
import tema

def zerar(**r):
    for v in rec.values(): v.clear()
    resp.clear(); resp.update(r)
def cen(n): print(f"\n== {n}")
def ok(c, m): print(("  OK   " if c else "  FALHA"), m); assert c, m
def graficos(): return {k[5:]: f for k, f in rec["graficos"]}
def htmls(): return [m for m in rec["markdown"] if "<div" in m]
def verificar_pagina():
    ok(all("\n" not in h for h in htmls()), f"{len(htmls())} blocos HTML em uma linha")
    ok(all("$" not in m for m in rec["markdown"]), "nenhum '$' sem escape no Markdown")
    ok(rec["chamadas"] and rec["chamadas"][0] == "set_page_config", "set_page_config é a primeira chamada")

cen("A. Geral (todos os dados), % do PIB")
zerar(); main.main(); verificar_pagina(); g = graficos()
ok(len(g) == 15 and not rec["erros"] and not rec["avisos"], f"15 gráficos: {sorted(g)}")
ok(rec["defaults"]["evo_categorias_Geral"] == [TOTAL] + COMPONENTES, "evolução: padrão = total + 5 setores")
ok(not any("Foco:" in h for h in htmls() if "topo" in h) or any("Foco: Geral" in h for h in htmls()), "chip do foco no cabeçalho")
ok(any("Foco: Geral" in h for h in htmls()), "cabeçalho mostra 'Foco: Geral'")
ok(any(f.px_tracos == [] or all(t.opacity is None for t in f.px_tracos) for f in [g["evolucao"]]), "Geral: nenhuma linha apagada")
ok(g["rosca_grupo"].tracos[0].kw["pull"] == [0, 0, 0], "rosca do governo geral sem fatia em destaque")
ok(g["rosca_grupo"].layout["showlegend"] is False, "rosca SEM legenda interna do Plotly")
ok(any('class="legenda"' in m and "Federal" in m and "Estados" in m for m in rec["markdown"]), "legenda da rosca em HTML (Federal, Estados, Municípios)")
ok(all(f.layout.get("separators") == ",." for f in g.values()), "todos os gráficos com separadores brasileiros (decimal ',' e milhar '.')")

cen("B. cada setor em foco, nas duas medidas")
esperado = {"Governo Federal": 15, "Governos Estaduais": 15, "Governos Municipais": 15, "Empresas Estatais": 15, "Banco Central": 12}
for tipo in ("porcentagem", "real"):
    for foco in FOCOS[1:]:
        zerar(foco=foco, radio=tipo); main.main(); verificar_pagina() if tipo == "porcentagem" and foco == "Banco Central" else None
        g = graficos(); ok(not rec["erros"] and not rec["avisos"], f"[{tipo}] {foco}: {len(g)} gráficos")
        assert len(g) == esperado[foco], (foco, tipo, sorted(g))
        assert any(f"Foco: {foco}" in h for h in htmls() if "topo" in h)
print("      (Banco Central tem 12: sem rosca, sem crescimento 12m e sem crescimento real; os demais, 15)")

cen("C. gráficos que não se aplicam somem (e o vizinho ocupa a linha)")
zerar(foco="Banco Central"); main.main(); g = graficos()
ok("rosca_grupo" not in g and "estatais_esfera" not in g, "Banco Central: sem rosca")
ok("crescimento_12m" not in g, "Banco Central: sem crescimento percentual (série negativa)")
ok(not rec["infos"], "e SEM mensagens de aviso no lugar (os cartões simplesmente não aparecem)")
zerar(foco="Empresas Estatais"); main.main(); g = graficos()
ok("estatais_esfera" in g and "rosca_grupo" not in g, "Empresas Estatais: rosca trocada por barras por esfera (há valor negativo)")
ok(g["estatais_esfera"].tracos[0].kw["orientation"] == "h" and len(g["estatais_esfera"].tracos[0].kw["y"]) == 3, "barras das 3 esferas")
zerar(foco="Governos Estaduais"); main.main(); g = graficos()
ok(g["rosca_grupo"].tracos[0].kw["pull"] == [0, 1 and 0.07, 0], f"Estados: fatia do setor puxada para fora {g['rosca_grupo'].tracos[0].kw['pull']}")
cores = g["rosca_grupo"].tracos[0].kw["marker"]["colors"]
ok(cores[1] == tema.CORES_CATEGORIA["Governos Estaduais"] and cores[0].startswith("rgba") and cores[2].startswith("rgba"), "demais fatias apagadas (rgba)")
ok(sum(1 for m in rec["markdown"] if "legenda" in m and "rgba" in m) == 1, "legenda HTML usa as mesmas cores apagadas")

cen("D. destaque do dado em foco")
zerar(foco="Governo Federal"); main.main(); g = graficos()
tr = {t.name: t for t in g["participacao_tempo"].px_tracos}
ok(tr["Governo Federal"].opacity == 1.0 and tr["Governo Federal"].largura == 4 and all(t.opacity == 0.3 and t.largura == 1.6 for n, t in tr.items() if n != "Governo Federal"), "participação: setor em foco grosso, demais apagados")
ev = {t.name: t for t in g["evolucao"].px_tracos}
ok(set(ev) == {"Governo Federal", TOTAL} and ev["Governo Federal"].opacity == 1.0 and ev[TOTAL].opacity == 0.3, "evolução: padrão = [setor, total]; setor em destaque")
ok(rec["defaults"]["evo_categorias_Governo Federal"] == ["Governo Federal", TOTAL], "padrão da evolução muda com o foco (key por foco)")
cc = g["cascata_composicao"].tracos[0].kw["marker_color"]
ok(cc[0] == tema.CORES_CATEGORIA["Governo Federal"] and all(c.startswith("rgba") for c in cc[1:5]) and cc[5] == tema.LARANJA, "cascata: setor em cor cheia, outros apagados, total em âmbar")
ok(g["mapa_calor"].formas and g["mapa_calor"].formas[0]["x0"] == 0.5, f"mapa de calor: contorno na coluna 'Federal' (x0={g['mapa_calor'].formas[0]['x0']})")
zerar(); main.main(); g = graficos()
ok(g["mapa_calor"].formas[0]["x0"] == -0.5, "Geral: contorno na coluna 'Total'")
ok(sorted(set(g["ranking"].tracos[0].kw["marker_color"])) == sorted(set(tema.CORES_CATEGORIA[c] for c in COMPONENTES)), "Geral: ranking com todas as cores cheias")
zerar(foco="Banco Central"); main.main(); rk = graficos()["ranking"].tracos[0].kw
ok(rk["marker_color"][-1] == tema.CORES_CATEGORIA["Banco Central"] and rk["marker_color"][0].startswith("rgba"), "ranking do Banco Central: só a barra dele em cor cheia")
zerar(foco="Empresas Estatais"); main.main(); rk = graficos()["ranking"].tracos[0].kw
cheias = [c for c in rk["marker_color"] if not c.startswith("rgba")]
ok(len(rk["y"]) == 7 and len(cheias) == 3, f"Estatais em foco: ranking já vem detalhado (7 barras) e só as 3 esferas das estatais em cor cheia ({len(cheias)})")

cen("E. textos e KPIs seguem o foco")
zerar(foco="Governos Estaduais"); main.main()
pagina = " ".join(rec["markdown"])
ok("Governos Estaduais" in " ".join(h for h in htmls() if 'class="resp"' in h) and "Por que diminuiu" in pagina, "cartões de resposta falam do setor ('Por que diminuiu · Governos Estaduais')")
kp = [re.sub(r"<[^>]+>", "|", h) for h in htmls() if 'class="kpi' in h]
ok("Dívida líquida · Governos Estaduais" in kp[0] and "7,51%" in kp[0], "KPI do topo: Dívida líquida · Governos Estaduais = 7,51%")
ok(any("Contribuição à variação total" in k for k in kp) and any("Variação · Governos Estaduais" in k for k in kp), "KPIs da aba 'Por que aumentou' viram os do setor")
ok(any("Posição no ranking" in k and "2º de 5" in k for k in kp), "aba Setores: 'Posição no ranking: 2º de 5'")
tab = rec["tabelas"][0][0]; ok(list(tab.columns)[:3] == ["Data", "Governos Estaduais", TOTAL], f"tabela: setor em foco e total vêm primeiro: {list(tab.columns)[:3]}")
zerar(); main.main(); ok(any("Maior contribuinte" in re.sub(r"<[^>]+>", "|", h) for h in htmls()), "Geral mantém os KPIs de visão geral (Maior contribuinte)")

cen("F. períodos diferentes x focos (nada pode quebrar)")
casos = {"2014–2020": (2014, 2020), "um ano (2020)": (2020, 2020), "só 2026 (9 meses)": (2026, 2026), "1º ano (2002)": (2002, 2002), "2003–2013": (2003, 2013)}
for nome, per in casos.items():
    for foco in FOCOS:
        for tipo in ("porcentagem", "real"):
            zerar(slider=per, radio=tipo, foco=foco); main.main()
            assert not rec["erros"], (nome, foco, tipo)
    print(f"  OK   {nome}: 6 focos x 2 medidas sem erro")
zerar(slider=(2026, 2026), foco="Governo Federal"); main.main()
ok(any("12 meses ou mais" in m for m in rec["markdown"]), "só 2026: CAGR vira 'n/d' com o motivo")
zerar(foco="Banco Central", radio="real"); main.main()
ok(any("zero ou negativo" in m for m in rec["markdown"]), "Banco Central em R$: CAGR 'n/d' com o motivo certo (série negativa)")
zerar(slider=(2002, 2002)); main.main(); ok("mapa_calor" not in graficos() and not rec["infos"], "2002: mapa de calor some sem aviso")

cen("G. interações")
zerar(evo_categorias_Geral=[]); main.main(); ok(any("ao menos uma categoria" in i for i in rec["infos"]), "evolução sem categorias -> aviso")
zerar(detalhar_Geral=True); main.main(); ok(len(graficos()["ranking"].tracos[0].kw["y"]) == 7, "Geral + detalhar estatais: 7 barras")

cen("H. cascata feita à mão: geometria")
v = Visualizador()
fig = v.cascata(["ini", "a", "b", "c", "fim"], [10.0, 5.0, -3.0, 2.0, 0.0], ["absolute", "relative", "relative", "relative", "total"], list("12345"), ["r"] * 5)
b = fig.tracos[0].kw; topos = [x + y for x, y in zip(b["base"], b["y"])]
ok(b["base"] == [0.0, 10.0, 12.0, 12.0, 0.0] and b["y"] == [10.0, 5.0, 3.0, 2.0, 14.0], f"base={b['base']} altura={b['y']}")
ok(topos[-1] == 14.0 and max(topos) == 15.0, "barra final = soma acumulada (10+5−3+2 = 14)")
fig = v.cascata(["x", "y", "fim"], [5.0, -8.0, 0.0], ["absolute", "relative", "total"], ["a", "b", "c"], ["r"] * 3)
b = fig.tracos[0].kw; ok(b["base"] == [0.0, -3.0, -3.0] and b["y"] == [5.0, 8.0, 3.0], f"cruzando o zero: base={b['base']} altura={b['y']} (barra de 5 a −3, total em −3)")

cen("I. dados indisponíveis e Visualizador")
zerar(); Dashboard(AnaliseDivida(AnalisadorDados(FonteDados("/nao/existe").carregar_tudo())), Visualizador()).executar()
ok(len(rec["erros"]) == 1 and not rec["graficos"], "st.error e nada desenhado")
df = pd.DataFrame({"a": ["x", "y"], "b": [3.0, 4.0], "c": ["p", "q"]})
for t in ("linha", "barra", "pizza", "box"): ok(v.plotar_grafico(df, "a", "b", None, t, cor="c", cores={"p": "red"}) is not None, f"plotar_grafico '{t}'")
f2 = v.plotar_grafico(df, "a", "b", None, "linha", cor="c", destaque="p"); ok([t.opacity for t in f2.px_tracos] == [1.0, 0.3], "destaque: série em foco opaca, outras 0,3")
for args, esp in ((("a","b",None,"radar"), "não suportado"), (("a","zzz",None,"linha"), "não encontradas")):
    try: v.plotar_grafico(df, *args); ok(False, "deveria falhar")
    except ValueError as e: ok(esp in str(e), f"ValueError: {e}")

cen("J. atualização na inicialização e estado dos dados")
zerar(); chamadas_atualizacao.clear(); main.main(); verificar_pagina()
ok(len(chamadas_atualizacao) == 1, "main() chama a atualização uma vez (cache_resource a repete só após .clear)")
ok(any("🟢" in m and "23 de 23 séries verificadas" in m and "25/11/2026 14:03" in m for m in rec["legendas"]), "tudo certo: selo verde com o resumo e a hora")
ok(not rec["laterais"], "sem aviso quando está tudo em dia")
ok(len(rec["botoes"]) == 1 and rec["botoes"][0][0].endswith("Atualizar dados agora") and rec["botoes"][0][1] == cache_falso.clear, "botão 'Atualizar dados agora' aciona o .clear do cache")
det = [m for m in rec["markdown"] if "Setor Público Consolidado" in m and m.startswith("- ")]
ok(len(det) == 1 and det[0].count("\n- ") + 1 == 23, "detalhes da atualização: uma linha por série (19 de dívida líquida + 4 extras)")
ok("dado extra" in det[0], "séries extras identificadas como 'dado extra'")
ok("&#36;" in det[0] and "R$" not in det[0], "cifrão do detalhe escapado (R&#36; nas séries em reais)")

zerar(); main.atualizar_dados = FakeCache(relatorio(sem_conexao=True)); main.main()
ok(len(rec["laterais"]) == 1 and "Sem conexão" in rec["laterais"][0], "sem internet: aviso na lateral")
ok(len(graficos()) == 15 and not rec["erros"], "e o painel funciona normalmente com os dados salvos")

zerar(); main.atualizar_dados = FakeCache(relatorio(mantidas=("divida_liquida_geral.csv", "divida_liquida_banco.csv"))); main.main()
ok(len(rec["laterais"]) == 1 and "2 série(s) mantida(s)" in rec["laterais"][0], "parcial: aviso diz quantas séries foram mantidas")
ok(any("⚠️" in m and "descartada" in m for m in rec["markdown"]), "detalhes marcam as séries mantidas com ⚠️ e o motivo")

zerar(); chamadas_atualizacao.clear(); main.atualizar_dados = cache_falso
class AtualizadorFalso:
    chamou = 0
    def atualizar(self): AtualizadorFalso.chamou += 1; return relatorio(STATUS_ATUALIZADA)
main.main(atualizador=AtualizadorFalso())
ok(AtualizadorFalso.chamou == 1 and not chamadas_atualizacao, "main(atualizador=...) usa o atualizador dado, sem passar pelo cache")

zerar(); Dashboard(AnaliseDivida(AnalisadorDados(FonteDados("/nao/existe").carregar_tudo())), Visualizador(), relatorio(sem_conexao=True), ao_atualizar=cache_falso.clear).executar()
ok(len(rec["erros"]) == 1 and len(rec["botoes"]) == 1, "sem dados: erro na tela, mas o botão de atualizar continua disponível")
zerar(); Dashboard(AnaliseDivida(AnalisadorDados(FonteDados().carregar_tudo())), Visualizador()).executar()
ok(not rec["botoes"] and any("Fonte: Banco Central" in l for l in rec["legendas"]), "sem relatório (uso direto): sem botão, só a fonte")


import os
os.environ["PAINEL_OFFLINE"] = "1"
ok(original_atualizar() is None, "PAINEL_OFFLINE=1: não tenta a internet (devolve None na hora)")
del os.environ["PAINEL_OFFLINE"]


cen("K. séries extras: IPCA, Selic e dívida bruta")
zerar(); main.main(); g = graficos()
ok(len(rec["abas"][0]) == 6 and "💸 Juros e inflação" in rec["abas"][0], f"6 abas, com 'Juros e inflação': {rec['abas'][0]}")
ok({"bruta_liquida", "juros_inflacao", "selic_pib", "divida_real", "crescimento_real"} <= set(g), "cartões novos presentes (dívida bruta x líquida e os 4 da aba de juros)")
kp = [re.sub(r"<[^>]+>", "|", h) for h in htmls() if 'class="kpi' in h]
ok(any("Selic em 12 meses" in k and "14,5%" in k for k in kp) and any("IPCA em 12 meses" in k and "4,6%" in k for k in kp), "KPIs de juros: Selic 14,5% e IPCA 4,6% em 12 meses (set/2026)")
ok(any("Juro real" in k and "9,5%" in k for k in kp) and any("Selic menos PIB nominal" in k for k in kp), "juro real 9,5% e 'Selic menos PIB nominal'")
ok(any("Descontada a inflação (IPCA)" in h for h in htmls() if 'class="resp"' in h), "a resposta 'por que aumentou' ganhou a frase do crescimento real")
ok(any("dívida bruta do governo geral foi de 83,0%" in l for l in rec["legendas"]), "nota da dívida bruta x líquida sob o gráfico")
ok(all(".." not in m for m in rec["markdown"] if "p.p." in m) and all(".." not in l for l in rec["legendas"]), "sem pontuação dupla nos textos")
sr = g["divida_real"].px_tracos; ok(len(sr) == 2 and sr[0].name == "Nominal" and sr[1].name.startswith("Real (preços de set/2026)"), "dívida real: duas linhas (nominal e real em preços de set/2026)")
ok(g["divida_real"].df["valor"].max() < 20, "valores em R$ trilhões (escala 1e-6), não em milhões")
cr = g["crescimento_real"].df; ok(list(cr["item"]) == ["Nominal", "Inflação (IPCA)", "Real"], "crescimento real: 3 barras (nominal, inflação, real)")
ok(math.isclose((1 + cr["valor"][0] / 100), (1 + cr["valor"][1] / 100) * (1 + cr["valor"][2] / 100)), "e elas obedecem (1+nominal) = (1+inflação)(1+real)")
ok(set(g["juros_inflacao"].df["serie"]) == {"Selic (12 meses)", "IPCA (12 meses)", "Juro real (Selic − IPCA)"}, "juros e inflação: Selic, IPCA e juro real")
ok(g["juros_inflacao"].formas and g["selic_pib"].formas, "faixas de eventos também nos gráficos novos")

zerar(foco="Banco Central"); main.main(); g = graficos()
ok("crescimento_real" not in g and "divida_real" in g and not rec["infos"], "Banco Central: sem crescimento real (negativo), mas com dívida real; sem avisos no lugar")
zerar(foco="Governo Federal", radio="real"); main.main(); ok(len(graficos()) == 15 and not rec["erros"], "setor em foco, medida em R$: 15 gráficos")
zerar(slider=(2026, 2026)); main.main(); g = graficos()
ok("crescimento_real" in g and list(g["crescimento_real"].df["item"]) == ["Nominal", "Inflação (IPCA)", "Real"], "janela < 12 meses (só 2026): o cartão de crescimento real mostra o acumulado, sem anualizar")
ok(not rec["erros"], "janela de 2026 sem erro")

cen("L. sem as séries extras (arquivos ausentes): o painel continua funcionando")
from analise_extras import AnaliseExtras
analise_base = AnaliseDivida(AnalisadorDados(FonteDados().carregar_tudo())); extras_todas = FonteDados().carregar_extras()
zerar(); Dashboard(analise_base, Visualizador(), relatorio(), ao_atualizar=cache_falso.clear).executar()
g = graficos(); ok(len(g) == 10 and "bruta_liquida" not in g and not rec["erros"], "sem extras: 10 gráficos (os da dívida líquida), sem dívida bruta")
ok(any("precisa do IPCA e da Selic" in i for i in rec["infos"]), "aba de juros explica o que falta, em vez de quebrar")
sem_ipca = AnaliseExtras(analise_base, {k: v for k, v in extras_todas.items() if k != "ipca"})
zerar(); Dashboard(analise_base, Visualizador(), extras=sem_ipca).executar(); ok(any("precisa do IPCA e da Selic" in i for i in rec["infos"]) and not rec["erros"], "sem IPCA: mesmo aviso; dívida bruta continua")
sem_dbgg = AnaliseExtras(analise_base, {k: v for k, v in extras_todas.items() if not k.startswith("dbgg")})
zerar(); Dashboard(analise_base, Visualizador(), extras=sem_dbgg).executar(); g = graficos()
ok("bruta_liquida" not in g and "juros_inflacao" in g and not rec["erros"], "sem DBGG: some só o cartão da dívida bruta; a aba de juros segue")

print("\nTODOS OS TESTES DO PAINEL PASSARAM")
