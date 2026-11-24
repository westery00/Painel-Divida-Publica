"""Identidade visual do painel: paleta, CSS e pequenos blocos de HTML.

Inspirado nas referências do projeto: fundo azul-marinho, cartões arredondados,
números grandes coloridos com a variação logo abaixo, e abas por assunto.
Tudo que é "aparência" fica aqui, para mudar o visual sem mexer na lógica.
"""
from string import Template

# --- Paleta -------------------------------------------------------------
FUNDO = "#0B1330"
FUNDO_CARD = "#141D45"
FUNDO_CARD_2 = "#1B2658"
BORDA = "#243263"
TEXTO = "#E8ECF8"
TEXTO_SUAVE = "#8F9AC2"
GRADE = "rgba(143,154,194,0.16)"

AZUL = "#4C9AFF"
CIANO = "#36CFC9"
ROXO = "#9B8CFF"
LARANJA = "#FFB454"
VERMELHO = "#FF5A6E"
VERDE = "#2ECC9A"
BRANCO = "#F5F7FF"

FONTE = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# Cor fixa de cada categoria: o mesmo setor tem a mesma cor em TODOS os gráficos.
CORES_CATEGORIA = {
    "Geral": BRANCO,
    "Setor Público Consolidado": BRANCO,
    "Governo Geral": "#B8C4FF",
    "Governo Federal": AZUL,
    "Governos Estaduais": CIANO,
    "Governos Municipais": ROXO,
    "Empresas Estatais": LARANJA,
    "Banco Central": "#FF7AA2",
    "Empresas Estatais Federais": "#FFD08A",
    "Empresas Estatais Estaduais": "#E69A3C",
    "Empresas Estatais Municipais": "#C77D1E",
}

# Dívida subindo = vermelho; descendo = verde (centro neutro na cor do cartão).
ESCALA_DIVERGENTE = [[0.0, VERDE], [0.5, FUNDO_CARD], [1.0, VERMELHO]]

_CSS = Template("""
<style>
.stApp { background: $fundo; color: $texto; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px; }

section[data-testid="stSidebar"] { background: #0F1840; border-right: 1px solid $borda; }

/* Cartões (st.container com key começando em 'card_') */
div[class*="st-key-card_"] {
    background: $card; border: 1px solid $borda !important; border-radius: 16px;
    padding: 0.35rem 0.6rem 0.2rem 0.6rem;
}

/* Cabeçalho */
.topo { display: flex; justify-content: space-between; align-items: flex-end;
        gap: 1rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.topo-titulo { font-size: 2rem; font-weight: 700; color: $branco; line-height: 1.15; }
.topo-sub { color: $suave; font-size: 0.95rem; margin-top: 0.25rem; }
.topo-data { color: $laranja; font-size: 0.95rem; font-weight: 600; }

.chip { display: inline-block; background: $card2; border: 1px solid $borda; color: $branco;
        border-radius: 999px; padding: 3px 12px; font-size: 0.82rem; font-weight: 600; margin-right: 10px; }

/* Legenda própria (usada na rosca, para não depender da legenda do Plotly) */
.legenda { display: flex; justify-content: center; flex-wrap: wrap; gap: 6px 18px;
           margin: 2px 0 8px 0; font-size: 0.85rem; color: $texto; }
.legenda .ponto { display: inline-block; width: 11px; height: 11px; border-radius: 3px;
                  margin-right: 6px; vertical-align: -1px; }

/* KPIs */
.kpi { background: linear-gradient(145deg, $card2, $card); border: 1px solid $borda;
       border-radius: 16px; padding: 16px 18px; text-align: center; box-sizing: border-box;
       min-height: 118px; }
.kpi-t { color: $texto; font-size: 0.9rem; font-weight: 600; opacity: 0.9; }
.kpi-v { font-size: 2.1rem; font-weight: 700; line-height: 1.25; margin: 4px 0 2px 0; }
.kpi-s { font-size: 0.8rem; font-weight: 500; }
.kpi.pequeno .kpi-v { font-size: 1.6rem; }

/* Respostas às três perguntas */
.resp { background: linear-gradient(160deg, $card2, $card); border: 1px solid $borda;
        border-radius: 16px; padding: 16px 18px; box-sizing: border-box; min-height: 215px; }
.resp-p { color: $suave; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em;
          text-transform: uppercase; }
.resp-d { font-size: 1.55rem; font-weight: 700; line-height: 1.2; margin: 6px 0 8px 0; }
.resp-t { color: $texto; font-size: 0.88rem; line-height: 1.5; opacity: 0.88; }

/* Títulos dentro dos cartões */
.card-t { color: $branco; font-size: 1.02rem; font-weight: 700; margin-top: 0.3rem; }
.card-s { color: $suave; font-size: 0.82rem; margin-bottom: 0.2rem; }

/* Abas */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid $borda; }
.stTabs [data-baseweb="tab"] { padding: 10px 18px; border-radius: 10px 10px 0 0; font-weight: 600; }
.stTabs [aria-selected="true"] { background: $card; color: $branco; }
</style>
""")


def css() -> str:
    return _CSS.substitute(fundo=FUNDO, texto=TEXTO, card=FUNDO_CARD, card2=FUNDO_CARD_2,
                           borda=BORDA, suave=TEXTO_SUAVE, branco=BRANCO, laranja=LARANJA)


def esmaecer(cor_hex: str, alpha: float = 0.3) -> str:
    """'#4C9AFF' -> 'rgba(76,154,255,0.3)': a mesma cor, mais apagada (para o que não está em foco)."""
    h = cor_hex.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def escapar_cifrao(texto) -> str:
    """O Streamlit interpreta $...$ como fórmula matemática; '&#36;' mostra o cifrão normal."""
    return str(texto).replace("$", "&#36;")


# Os blocos abaixo são escritos em UMA linha de propósito: no Markdown, linhas
# indentadas ou em branco no meio do HTML fariam o Streamlit exibir o código na tela.
def html_cabecalho(titulo: str, subtitulo: str, atualizado: str, foco: str = "") -> str:
    chip = f'<span class="chip">Foco: {foco}</span>' if foco else ""
    return escapar_cifrao(
        f'<div class="topo"><div><div class="topo-titulo">{titulo}</div>'
        f'<div class="topo-sub">{subtitulo}</div></div>'
        f'<div class="topo-data">{chip}{atualizado}</div></div>')


def html_legenda(itens) -> str:
    """Legenda em HTML: itens = [(rótulo, cor), ...]."""
    pontos = "".join(f'<span><span class="ponto" style="background:{cor}"></span>{rotulo}</span>'
                     for rotulo, cor in itens)
    return f'<div class="legenda">{pontos}</div>'


def html_kpi(titulo: str, valor: str, sub: str, cor_valor: str, cor_sub: str = TEXTO_SUAVE,
             pequeno: bool = False) -> str:
    classe = "kpi pequeno" if pequeno else "kpi"
    return escapar_cifrao(
        f'<div class="{classe}"><div class="kpi-t">{titulo}</div>'
        f'<div class="kpi-v" style="color:{cor_valor}">{valor}</div>'
        f'<div class="kpi-s" style="color:{cor_sub}">{sub}</div></div>')


def html_resposta(pergunta: str, destaque: str, texto: str, cor: str) -> str:
    return escapar_cifrao(
        f'<div class="resp" style="border-top:3px solid {cor}"><div class="resp-p">{pergunta}</div>'
        f'<div class="resp-d" style="color:{cor}">{destaque}</div><div class="resp-t">{texto}</div></div>')


def html_titulo_cartao(titulo: str, subtitulo: str = "") -> str:
    sub = f'<div class="card-s">{subtitulo}</div>' if subtitulo else ""
    return escapar_cifrao(f'<div class="card-t">{titulo}</div>{sub}')
