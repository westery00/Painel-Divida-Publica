"""Camada de interface (Streamlit).

O Dashboard só apresenta: pede os números e textos à AnaliseDivida, os gráficos
ao Visualizador, o visual ao módulo ``tema`` e a formatação aos ``formatar_*``.

DADO EM FOCO. O usuário escolhe na barra lateral:
    Geral  -> usa todos os dados (o consolidado e todos os setores);
    setor  -> mostra só uma parte dos dados: todos os indicadores, textos e gráficos
              passam a falar desse setor, que aparece em destaque (os demais ficam apagados).

Cada gráfico é montado por um método ``_c_*`` que devolve um ``Cartao`` pronto, ou
``None`` quando o gráfico não faz sentido para o dado em foco (ex.: crescimento
percentual do Banco Central, cuja dívida é negativa). Cartões ``None`` somem da tela e
os vizinhos ocupam o espaço (veja ``_linha``).

Abas (cada uma responde a uma pergunta do projeto):
    Visão geral          -> resumo das três respostas e evolução no tempo
    De onde vem          -> composição da dívida por setor (origem)
    Qual setor contribui -> ranking e participação no total
    Por que aumentou     -> variação, quem puxou e ritmo da dívida vs. PIB
    Dados e metodologia  -> tabela e explicação dos conceitos
"""
from dataclasses import dataclass

import pandas as pd
import streamlit as st

import tema
from analise_divida import COLUNAS, TOTAL, AnaliseDivida, Janela
from analise_extras import IPCA12, JURO_REAL, PIB12, SELIC12, AnaliseExtras
from atualizador_dados import STATUS_MANTIDA, RelatorioAtualizacao
from config import (COMPONENTES, ESTATAIS_DETALHE, EVENTOS, FOCOS, GERAL, ROTULOS_CURTOS,
                    ROTULOS_TIPO, TIPO_PORCENTAGEM, TIPO_REAL, UNIDADES, serie_do_foco)
from indicador import (criar_indicador, formatar_medida, formatar_mes, formatar_numero,
                       formatar_percentual, formatar_pp, formatar_variacao)
from visualizador import Visualizador

METODOLOGIA = """
**Fonte dos dados.** Banco Central do Brasil (Portal de Dados Abertos, dadosabertos.bcb.gov.br): dívida líquida, dívida bruta e Selic. IBGE: IPCA.

**Dado em foco.** *Geral* usa todos os dados: o consolidado e todos os setores. Cada setor escolhido mostra
apenas uma parte dos dados, e todo o painel passa a falar dele: os indicadores, os textos e os gráficos,
nos quais o setor aparece em destaque e os demais ficam apagados. Gráficos que não fazem sentido para o setor
escolhido são escondidos (por exemplo, o crescimento percentual da dívida do Banco Central, que é negativa).

**O que é a dívida líquida.** É o saldo das dívidas das entidades públicas menos os seus ativos
financeiros (créditos). Como os ativos são descontados, o valor pode ser **negativo**: é o que
acontece com o Banco Central em boa parte do período (posição credora líquida).

**Como os setores se somam.** Setor público consolidado = governo federal + governos estaduais +
governos municipais + empresas estatais + Banco Central. Conferimos nos dados: a soma dos cinco
componentes reproduz o total, com diferenças apenas de arredondamento. O *governo geral* (federal +
estados + municípios) é uma soma intermediária. Por isso totais e partes nunca devem ser somados juntos.

**Duas medidas.** *% do PIB* (a dívida dividida pelo PIB dos últimos 12 meses) e *R$* (os CSVs trazem
milhões de reais; o painel abrevia para mi, bi e tri). Todas as análises usam apenas os meses em que
**todas** as séries existem nas duas medidas, para que as partes fechem com o total.

**Período e variação.** A variação de um período compara o último mês do ano anterior ao primeiro ano
escolhido com o último mês do último ano escolhido. Ex.: "2014 a 2026" mede de dez/2013 a set/2026. É a
mesma lógica de "variação no ano" (fim de ano contra fim de ano).

**PIB implícito.** Como temos a dívida em R$ e em % do PIB, o PIB sai da divisão: PIB = dívida em R$ ÷
(dívida em % do PIB ÷ 100). O resultado é compatível com o PIB nominal anual divulgado (por exemplo,
cerca de R$ 5,78 tri em dez/2014 e R$ 7,39 tri em dez/2019), o que confirma as unidades dos CSVs.

**Crescimento médio anual (CAGR).** É a taxa anual constante que levaria do valor inicial ao final:
`(final ÷ inicial) ^ (12 ÷ meses) − 1`. Compara-se o ritmo da dívida com o do PIB nominal: quando a dívida
cresce mais rápido que o PIB, a razão dívida/PIB sobe. Só é calculado para períodos de 12 meses ou mais e
para séries positivas.

**Juros e inflação.** Taxas mensais se *compõem*: 12 meses de 1% ao mês valem 12,68%, e não 12%. O *juro real
ex-post* é (1 + Selic) ÷ (1 + IPCA) − 1, com os dois acumulados em 12 meses. A *dívida em termos reais* corrige o saldo
de cada mês pelo IPCA para os preços do último mês, e separa inflação de crescimento de verdade: (1 + nominal) = (1 + inflação)
× (1 + real). A comparação *Selic × PIB nominal* usa a Selic só como aproximação do custo da dívida: quando ela supera o
crescimento do PIB nominal, a dívida tende a crescer em proporção do PIB, salvo superávit primário. O mês corrente da
Selic, ainda incompleto, não entra: todas as séries terminam no último mês da dívida líquida.

**Dívida bruta.** O painel mostra a dívida bruta do governo geral por duas metodologias do Banco Central, ao lado da dívida
líquida do mesmo conjunto (federal, estados e municípios). A bruta não desconta os ativos; a líquida desconta. As duas
metodologias da bruta medem de formas diferentes e não são trechos de uma mesma série; consulte a nota do Banco Central
na página de cada série para o detalhe da diferença.

**Como ler os gráficos.**
**Cascata:** cada barra soma (ou subtrai) à anterior até chegar ao total. **Mapa de calor:** cada célula é a
variação de um fim de ano ao seguinte; vermelho = a dívida subiu, verde = caiu; o contorno branco marca o
dado em foco. **Faixas sombreadas:** eventos de contexto (não fazem parte dos dados). **\\***: ano em
andamento, com o dado mais recente.

**Limitações.** O painel usa só a *dívida líquida* por setor. Ele mostra *quem* deve e *quanto cresceu*,
mas não decompõe o crescimento por fluxos (resultado primário, juros, câmbio), não separa dívida interna e
externa e não detalha por indexador ou detentor. Para isso seriam necessárias outras bases (veja o README).
"""


@dataclass(frozen=True)
class Selecao:
    """O que o usuário escolheu nos filtros."""
    tipo: str
    ano_ini: int
    ano_fim: int
    foco: str
    janela: Janela

    @property
    def unidade(self):
        return UNIDADES[self.tipo]

    @property
    def serie(self) -> str:
        """Série usada nos indicadores: o total (se Geral) ou o próprio setor."""
        return serie_do_foco(self.foco)

    @property
    def em_foco(self) -> bool:
        return self.foco != GERAL

    def destacada(self, categoria: str) -> bool:
        """Esta categoria está em destaque? No Geral, todas; num setor, só ele (e suas subdivisões)."""
        if not self.em_foco:
            return True
        return categoria == self.foco or (self.foco == "Empresas Estatais" and categoria in ESTATAIS_DETALHE)


@dataclass
class Cartao:
    """Um gráfico já pronto, com seu título, para ser desenhado dentro de um cartão."""
    nome: str
    titulo: str
    subtitulo: str
    fig: object
    nota: str = ""
    legenda: str = ""


class Dashboard:
    ABAS = ["📊 Visão geral", "🧭 De onde vem", "🏛️ Qual setor contribui",
            "📈 Por que aumentou", "💸 Juros e inflação", "🗂️ Dados e metodologia"]

    def __init__(self, analise: AnaliseDivida, visualizador: Visualizador,
                 relatorio: RelatorioAtualizacao | None = None, ao_atualizar=None,
                 extras: AnaliseExtras | None = None):
        self.analise = analise
        self.visualizador = visualizador
        self.relatorio = relatorio          # resultado da atualização feita na inicialização
        self.ao_atualizar = ao_atualizar    # função chamada pelo botão "Atualizar dados agora"
        self.extras = extras                # IPCA, Selic e dívida bruta (opcional)

    @staticmethod
    def configurar_pagina():
        """Deve ser a primeira chamada ao Streamlit em cada execução."""
        st.set_page_config(page_title="Dívida Pública Líquida", page_icon="📊", layout="wide")
        st.markdown(tema.css(), unsafe_allow_html=True)

    # ============================================================= componentes
    @staticmethod
    def _cartao(nome: str):
        """Cartão arredondado. A key vira uma classe CSS (st-key-card_*) estilizada em tema.py."""
        return st.container(border=True, key=f"card_{nome}")

    @staticmethod
    def _titulo(titulo: str, subtitulo: str = ""):
        st.markdown(tema.html_titulo_cartao(titulo, subtitulo), unsafe_allow_html=True)

    @staticmethod
    def _grafico(fig, chave: str):
        st.plotly_chart(fig, key=f"graf_{chave}", theme=None, config={"displayModeBar": False})

    @staticmethod
    def _texto(markdown: str):
        st.markdown(tema.escapar_cifrao(markdown), unsafe_allow_html=True)

    @staticmethod
    def _cor_variacao(valor: float) -> str:
        """Dívida subindo é vermelho; descendo, verde."""
        return tema.VERMELHO if valor > 0 else tema.VERDE

    @staticmethod
    def _cor(sel: Selecao, categoria: str) -> str:
        """Cor da categoria; apagada se não for o dado em foco."""
        cor = tema.CORES_CATEGORIA[categoria]
        return cor if sel.destacada(categoria) else tema.esmaecer(cor)

    def _linha(self, cartoes: list, larguras: list | None = None):
        """Desenha uma linha de cartões, ignorando os None (gráficos que não se aplicam).

        Se sobrar só um, ele ocupa a largura toda; as proporções só valem quando todos aparecem.
        """
        cartoes = [c for c in cartoes if c is not None]
        if not cartoes:
            return
        proporcao = larguras if larguras and len(larguras) == len(cartoes) else len(cartoes)
        for coluna, c in zip(st.columns(proporcao), cartoes):
            with coluna, self._cartao(c.nome):
                self._titulo(c.titulo, c.subtitulo)
                self._grafico(c.fig, c.nome)
                if c.legenda:
                    st.markdown(c.legenda, unsafe_allow_html=True)
                if c.nota:
                    st.caption(c.nota)

    @staticmethod
    def _complemento(sel: Selecao) -> str:
        return f" · em destaque: {sel.foco}" if sel.em_foco else ""

    # =============================================================== cabeçalho
    def render_cabecalho(self, ultima_data=None, foco=None):
        atualizado = f"Dados até {formatar_mes(ultima_data)}" if ultima_data is not None else ""
        st.markdown(tema.html_cabecalho(
            "📊 Painel da Dívida Pública Líquida",
            "De onde vem, quem mais contribui e por que aumentou", atualizado, foco or ""),
            unsafe_allow_html=True)

    # ================================================================== filtros
    def filtros(self):
        """Barra lateral. Devolve a Selecao, ou None se não houver dados nos anos escolhidos."""
        st.sidebar.markdown("## Filtros")
        tipo = st.sidebar.radio("Medida", self.analise.tipos(), format_func=ROTULOS_TIPO.get)

        primeiro, ultimo = self.analise.anos()
        if primeiro == ultimo:
            ano_ini = ano_fim = primeiro
        else:
            ano_ini, ano_fim = st.sidebar.slider("Período (anos)", primeiro, ultimo, (primeiro, ultimo))

        foco = st.sidebar.selectbox(
            "Dado em foco", FOCOS,
            help="Geral usa todos os dados. Cada setor mostra só uma parte, e todo o painel passa a "
                 "falar dele.")

        janela = self.analise.janela(tipo, ano_ini, ano_fim)
        if janela is None:
            return None
        st.sidebar.markdown("---")
        st.sidebar.caption(f"As variações comparam **{formatar_mes(janela.d0)}** com "
                           f"**{formatar_mes(janela.d1)}** (fim de ano contra fim de ano).")
        return Selecao(tipo, ano_ini, ano_fim, foco, janela)

    # ===================================================================== KPIs
    def render_kpis(self, sel: Selecao):
        """Quatro indicadores do dado em foco (todos refletem só essa série)."""
        t, j = sel.tipo, sel.janela
        k = self.analise.kpis_foco(t, sel.serie, j)
        pequeno = len(sel.foco) > 18

        if k["delta_12m"] is None:
            sub1, cor1 = "sem 12 meses anteriores", tema.TEXTO_SUAVE
        else:
            sub1 = f"{formatar_variacao(t, k['delta_12m'])} em 12 meses"
            cor1 = self._cor_variacao(k["delta_12m"])

        cartoes = [
            tema.html_kpi(f"Dívida líquida · {sel.foco}",
                          criar_indicador(t, "Nível", k["nivel"]).formatar_valor(),
                          sub1, tema.LARANJA, cor1, pequeno),
            tema.html_kpi("Participação no total",
                          formatar_percentual(k["participacao"], 1),
                          f"era {formatar_percentual(k['participacao0'], 1)} em {formatar_mes(j.d0)}",
                          tema.AZUL, tema.TEXTO_SUAVE),
            tema.html_kpi("Variação no período",
                          formatar_variacao(t, k["variacao"]),
                          f"{formatar_medida(t, k['nivel0'])} → {formatar_medida(t, k['nivel'])}",
                          self._cor_variacao(k["variacao"]), tema.TEXTO_SUAVE),
            tema.html_kpi("Pico no período",
                          criar_indicador(t, "Pico", k["pico"]).formatar_valor(),
                          f"em {formatar_mes(k['pico_data'])} · mínimo {formatar_medida(t, k['minimo'])}",
                          tema.ROXO, tema.TEXTO_SUAVE),
        ]
        for coluna, html in zip(st.columns(4), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")

    # ============================================== cartões: de onde vem (Q1)
    def _c_cascata_composicao(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        c = self.analise.cascata_composicao(t, j)
        textos = [formatar_medida(t, v, sinal=(m == "relative")) for v, m in zip(c["exibir"], c["medida"])]
        cores = [tema.LARANJA if m == "total" else self._cor(sel, cat)
                 for cat, m in zip(c["categoria"], c["medida"])]
        fig = self.visualizador.cascata(c["rotulo"], c["valor"] * u.fator_nivel, c["medida"], textos,
                                        cores, u.rotulo_nivel)
        return Cartao("cascata_composicao", f"Como a dívida se forma · {formatar_mes(j.d1)}",
                      "Cada setor soma (ou subtrai) até o total consolidado" + self._complemento(sel), fig)

    def _c_rosca(self, sel: Selecao):
        """Divisão do grupo do dado em foco; None para o Banco Central (não pertence a um grupo)."""
        t, j, u = sel.tipo, sel.janela, sel.unidade
        info = self.analise.divisao_grupo(t, j, sel.foco)
        if info is None:
            return self._c_estatais_esfera(sel) if sel.foco == "Empresas Estatais" else None

        df, destaque = info["df"], info["destaque"]
        cores = [tema.CORES_CATEGORIA[c] if destaque in (None, c) else tema.esmaecer(tema.CORES_CATEGORIA[c])
                 for c in df["categoria"]]
        rotulos = [ROTULOS_CURTOS[c] for c in df["categoria"]]
        fig = self.visualizador.rosca(
            rotulos, df["valor"], cores,
            texto_central=f"{info['curto']}<br><b>{formatar_medida(t, info['soma'])}</b>",
            destacar=ROTULOS_CURTOS[destaque] if destaque else None)
        return Cartao("rosca_grupo", info["titulo"],
                      f"Federal, estados e municípios · {formatar_mes(j.d1)}" + self._complemento(sel), fig,
                      legenda=tema.html_legenda(list(zip(rotulos, cores))))

    def _c_estatais_esfera(self, sel: Selecao):
        """Empresas estatais por esfera, em barras (aceitam valores negativos, ao contrário da rosca)."""
        t, j, u = sel.tipo, sel.janela, sel.unidade
        rk = self.analise.ranking(t, j, detalhar_estatais=True)
        rk = rk[rk["categoria"].isin(ESTATAIS_DETALHE)]
        fig = self.visualizador.barras_horizontais(
            [ROTULOS_CURTOS[c] for c in rk["categoria"]], rk["valor"] * u.fator_nivel,
            [tema.CORES_CATEGORIA[c] for c in rk["categoria"]],
            [formatar_medida(t, v) for v in rk["valor"]], u.rotulo_nivel, altura=300)
        return Cartao("estatais_esfera", "Dentro das empresas estatais",
                      f"Por esfera · {formatar_mes(j.d1)} · valor negativo: posição credora líquida", fig)

    def _c_composicao_anual(self, sel: Selecao):
        t, u = sel.tipo, sel.unidade
        anual, nota = self.analise.composicao_anual(t, sel.ano_ini, sel.ano_fim)
        partes = anual[COMPONENTES] * u.fator_nivel
        partes.columns = [ROTULOS_CURTOS[c] for c in COMPONENTES]
        cores = {ROTULOS_CURTOS[c]: self._cor(sel, c) for c in COMPONENTES}
        fig = self.visualizador.barras_empilhadas(partes, cores, linha=anual[TOTAL] * u.fator_nivel,
                                                  rotulo_y=u.rotulo_nivel)
        legenda = "Barras abaixo de zero: setor com posição credora líquida (reduz o total)."
        return Cartao("composicao_anual", "Composição ao longo dos anos",
                      "Saldo de cada setor no fim de cada ano; a linha é o total" + self._complemento(sel),
                      fig, nota=f"{legenda} {nota}" if nota else legenda)

    # ============================================ cartões: qual setor contribui (Q2)
    def _c_ranking(self, sel: Selecao, detalhar: bool):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        rk = self.analise.ranking(t, j, detalhar)
        fig = self.visualizador.barras_horizontais(
            [ROTULOS_CURTOS[c] for c in rk["categoria"]], rk["valor"] * u.fator_nivel,
            [self._cor(sel, c) for c in rk["categoria"]],
            [formatar_percentual(p, 1) for p in rk["participacao"]], u.rotulo_nivel)
        return Cartao("ranking", f"Ranking de contribuição · {formatar_mes(j.d1)}",
                      f"Barras em {u.rotulo_nivel}; rótulos mostram a participação no total", fig)

    def _c_participacao(self, sel: Selecao):
        df = self.analise.participacoes(sel.tipo, sel.ano_ini, sel.ano_fim)
        fig = self.visualizador.plotar_grafico(
            df, "data", "valor", None, "linha", cor="categoria", rotulo_y="% do total",
            cores=tema.CORES_CATEGORIA, bandas=EVENTOS, altura=400,
            destaque=sel.foco if sel.em_foco else None)
        return Cartao("participacao_tempo", "Participação no total ao longo do tempo",
                      "Quanto cada setor representa da dívida consolidada, mês a mês" + self._complemento(sel), fig)

    # ================================================ cartões: por que aumentou (Q3)
    def _c_cascata_aumento(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        c = self.analise.cascata_aumento(t, j)
        textos = [formatar_variacao(t, v) if m == "relative" else formatar_medida(t, v)
                  for v, m in zip(c["exibir"], c["medida"])]
        cores = []
        for categoria, medida, valor in zip(c["categoria"], c["medida"], c["exibir"]):
            if medida != "relative":
                cores.append(tema.LARANJA)
                continue
            base = tema.VERMELHO if valor > 0 else tema.VERDE
            cores.append(base if sel.destacada(categoria) else tema.esmaecer(base))
        fig = self.visualizador.cascata(c["rotulo"], c["valor"] * u.fator_nivel, c["medida"], textos,
                                        cores, u.rotulo_nivel)
        return Cartao("cascata_aumento", "Quem puxou a variação",
                      f"Contribuição de cada setor · {j.texto}" + self._complemento(sel), fig)

    def _c_crescimento(self, sel: Selecao):
        """Crescimento em 12 meses do dado em foco x PIB; None se não for calculável."""
        df = self.analise.crescimento_12m(sel.ano_ini, sel.ano_fim, sel.serie)
        if df is None or df.empty:
            return None
        cores = {"Dívida líquida (R$)": tema.VERMELHO, "PIB nominal": tema.CIANO,
                 "Dívida total (R$)": tema.esmaecer(tema.BRANCO, 0.6)}
        if sel.em_foco:
            cores[f"{sel.foco} (R$)"] = tema.CORES_CATEGORIA[sel.foco]
        fig = self.visualizador.plotar_grafico(
            df, "data", "valor", None, "linha", cor="serie", rotulo_y="% em 12 meses",
            cores=cores, bandas=EVENTOS, altura=370)
        quem = sel.foco if sel.em_foco else "Dívida"
        return Cartao("crescimento_12m", f"{quem} x PIB: crescimento em 12 meses",
                      "Quando a dívida cresce mais que o PIB, a razão dívida/PIB sobe", fig)

    def _c_variacao_12m(self, sel: Selecao):
        u = sel.unidade
        serie = self.analise.variacao_12m(sel.tipo, sel.ano_ini, sel.ano_fim, sel.serie)
        if serie.empty:
            return None
        fig = self.visualizador.barras_sinal(serie.index, serie.values * u.fator_delta, u.rotulo_delta)
        titulo = f"Variação em 12 meses · {sel.foco}" if sel.em_foco else "Variação em 12 meses da dívida total"
        return Cartao("variacao_12m", titulo, "Vermelho: alta · Verde: queda", fig)

    def _c_mapa_calor(self, sel: Selecao):
        t, u = sel.tipo, sel.unidade
        matriz = self.analise.variacao_anual(t, sel.ano_ini, sel.ano_fim) * u.fator_delta
        if matriz.empty:
            return None
        casas = 1 if t == TIPO_PORCENTAGEM else 0
        textos = pd.DataFrame([[formatar_numero(v, casas, sinal=True) for v in linha] for linha in matriz.values],
                              index=matriz.index, columns=matriz.columns)
        fig = self.visualizador.mapa_calor(matriz, textos, u.rotulo_delta, destaque=ROTULOS_CURTOS[sel.serie])
        return Cartao("mapa_calor", "Variação anual por setor",
                      f"Fim de ano contra fim de ano ({u.rotulo_delta}) · contorno branco: {ROTULOS_CURTOS[sel.serie]}"
                      if sel.em_foco else f"Fim de ano contra fim de ano ({u.rotulo_delta})", fig)

    # ============================================ cartões: dívida bruta, juros e inflação
    def _c_bruta_liquida(self, sel: Selecao):
        if self.extras is None:
            return None
        df = self.extras.bruta_liquida(sel.ano_ini, sel.ano_fim)
        if df is None:
            return None
        cores = {"Bruta (metodologia atual)": tema.LARANJA,
                 "Bruta (metodologia até 2007)": tema.esmaecer(tema.LARANJA, 0.55),
                 "Líquida (governo geral)": tema.CORES_CATEGORIA["Governo Geral"]}
        fig = self.visualizador.plotar_grafico(df, "data", "valor", None, "linha", cor="serie", rotulo_y="% do PIB",
                                               cores=cores, bandas=EVENTOS, altura=380)
        return Cartao("bruta_liquida", "Dívida bruta × líquida do governo geral",
                      "Federal, estados e municípios · % do PIB · duas metodologias para a bruta", fig,
                      nota=self.extras.texto_bruta_liquida(sel.janela) or "")

    def _c_juros_inflacao(self, sel: Selecao):
        df = self.extras.juros_inflacao(sel.ano_ini, sel.ano_fim)
        if df is None:
            return None
        fig = self.visualizador.plotar_grafico(
            self.extras.longo(df), "data", "valor", None, "linha", cor="serie", rotulo_y="% em 12 meses",
            cores={SELIC12: tema.LARANJA, IPCA12: tema.CIANO, JURO_REAL: tema.ROXO}, bandas=EVENTOS, altura=370)
        return Cartao("juros_inflacao", "Selic, inflação e juro real", "Acumulados em 12 meses", fig)

    def _c_selic_pib(self, sel: Selecao):
        df = self.extras.selic_pib(sel.ano_ini, sel.ano_fim)
        if df is None:
            return None
        fig = self.visualizador.plotar_grafico(
            self.extras.longo(df), "data", "valor", None, "linha", cor="serie", rotulo_y="% em 12 meses",
            cores={SELIC12: tema.LARANJA, PIB12: tema.VERDE}, bandas=EVENTOS, altura=370)
        return Cartao("selic_pib", "Selic × crescimento do PIB nominal",
                      "Acumulados em 12 meses · a Selic é só uma aproximação do custo médio da dívida", fig)

    def _quem(self, sel: Selecao) -> str:
        return "Dívida total" if not sel.em_foco else f"Dívida · {sel.foco}"

    def _c_divida_real(self, sel: Selecao):
        df = self.extras.divida_real(sel.serie, sel.janela)
        if df is None:
            return None
        df["valor"] = df["valor"] * UNIDADES[TIPO_REAL].fator_nivel
        cores = {nome: (tema.LARANJA if nome == "Nominal" else tema.CIANO) for nome in df["serie"].unique()}
        fig = self.visualizador.plotar_grafico(df, "data", "valor", None, "linha", cor="serie",
                                               rotulo_y=UNIDADES[TIPO_REAL].rotulo_nivel, cores=cores,
                                               bandas=EVENTOS, altura=370)
        return Cartao("divida_real", f"{self._quem(sel)}: valores nominais × reais",
                      f"Real = corrigida pelo IPCA para os preços de {formatar_mes(sel.janela.d1)}", fig)

    def _c_crescimento_real(self, sel: Selecao):
        c = self.extras.crescimento_real(sel.janela, sel.serie)
        if c is None:
            return None
        anual = c["anualizado"] is not None
        valores = c["anualizado"] if anual else c["acumulado"]
        df = pd.DataFrame({"item": ["Nominal", "Inflação (IPCA)", "Real"],
                           "valor": [valores["nominal"], valores["inflacao"], valores["real"]]})
        fig = self.visualizador.plotar_grafico(
            df, "item", "valor", None, "barra", cor="item", rotulo_y="% ao ano" if anual else "% no período",
            cores={"Nominal": tema.LARANJA, "Inflação (IPCA)": tema.CIANO, "Real": tema.ROXO}, altura=340)
        return Cartao("crescimento_real", "Crescimento da dívida: nominal, inflação e real",
                      f"{sel.janela.texto} · (1 + nominal) = (1 + inflação) × (1 + real)", fig)

    # ===================================================================== abas
    def aba_visao_geral(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        respostas = self.analise.respostas(t, j, sel.foco)
        if self.extras is not None:  # soma à resposta 'por que aumentou' o crescimento descontada a inflação
            frase = self.extras.frase_real(j, sel.serie)
            if frase:
                respostas[2]["texto"] += " " + frase
        variacao = self.analise.kpis_foco(t, sel.serie, j)["variacao"]
        cores = [tema.AZUL, tema.LARANJA, self._cor_variacao(variacao)]
        for coluna, r, cor in zip(st.columns(3), respostas, cores):
            coluna.markdown(tema.html_resposta(r["pergunta"], r["destaque"], r["texto"], cor),
                            unsafe_allow_html=True)
        st.write("")

        with self._cartao("evolucao"):
            self._titulo("Evolução da dívida líquida", "Escolha as categorias para comparar")
            padrao = [TOTAL] + COMPONENTES if not sel.em_foco else [sel.foco, TOTAL]
            # a key inclui o foco: ao trocar o dado em foco, a seleção volta ao padrão daquele foco
            categorias = st.multiselect("Categorias", COLUNAS, default=padrao,
                                        key=f"evo_categorias_{sel.foco}", label_visibility="collapsed")
            if not categorias:
                st.info("Selecione ao menos uma categoria.")
            else:
                df = self.analise.evolucao(t, categorias, sel.ano_ini, sel.ano_fim)
                df["valor"] = df["valor"] * u.fator_nivel
                fig = self.visualizador.plotar_grafico(
                    df, "data", "valor", None, "linha", cor="categoria", rotulo_y=u.rotulo_nivel,
                    cores=tema.CORES_CATEGORIA, bandas=EVENTOS, altura=420,
                    destaque=sel.foco if sel.em_foco and sel.foco in categorias else None)
                self._grafico(fig, "evolucao")
            st.caption("Faixas sombreadas: eventos de contexto (não fazem parte dos dados).")

        with self._cartao("conclusoes"):
            self._titulo("Outras constatações do período", f"Sobre: {sel.foco}")
            self._texto("\n".join(f"- {c}" for c in self.analise.conclusoes(t, j, sel.foco)))

    def aba_origem(self, sel: Selecao):
        self._linha([self._c_cascata_composicao(sel), self._c_rosca(sel)], [3, 2])
        self._linha([self._c_composicao_anual(sel)])
        self._linha([self._c_bruta_liquida(sel)])

    def aba_setores(self, sel: Selecao):
        t, j = sel.tipo, sel.janela
        if not sel.em_foco:
            d = self.analise.destaque_setores(t, j)
            (ganha, v_ganho), (perde, v_perda) = d["maior_ganho"], d["maior_perda"]
            cartoes = [
                tema.html_kpi("Maior contribuinte", d["lider"],
                              f"{formatar_percentual(d['participacao'], 1)} do total · era "
                              f"{formatar_percentual(d['participacao0'], 1)} em {formatar_mes(j.d0)}",
                              tema.CORES_CATEGORIA[d["lider"]], pequeno=True),
                tema.html_kpi("Mais ganhou participação", ganha, f"{formatar_pp(v_ganho)} no total · {j.texto}",
                              tema.CORES_CATEGORIA[ganha], pequeno=True),
                tema.html_kpi("Mais perdeu participação", perde, f"{formatar_pp(v_perda)} no total · {j.texto}",
                              tema.CORES_CATEGORIA[perde], pequeno=True),
            ]
        else:
            p = self.analise.posicao_foco(t, j, sel.foco)
            cor = tema.CORES_CATEGORIA[sel.foco]
            if p["pct_da_variacao"] is None:
                sub3 = "a dívida total variou pouco no período"
            else:
                sub3 = f"{formatar_percentual(p['pct_da_variacao'], 0)} da variação total ({formatar_variacao(t, p['variacao_total'])})"
            cartoes = [
                tema.html_kpi("Posição no ranking", f"{p['posicao']}º de {p['de']}",
                              f"{formatar_percentual(p['participacao'], 1)} do total · {formatar_mes(j.d1)}",
                              cor, pequeno=True),
                tema.html_kpi("Variação da participação", formatar_pp(p["mudanca_pp"]),
                              f"de {formatar_percentual(p['participacao0'], 1)} para "
                              f"{formatar_percentual(p['participacao'], 1)} · {j.texto}", cor, pequeno=True),
                tema.html_kpi("Contribuição à variação total", formatar_variacao(t, p["variacao"]), sub3,
                              self._cor_variacao(p["variacao"]), pequeno=True),
            ]
        for coluna, html in zip(st.columns(3), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")

        detalhar = st.toggle("Detalhar empresas estatais no ranking", value=(sel.foco == "Empresas Estatais"),
                             key=f"detalhar_{sel.foco}")
        self._linha([self._c_ranking(sel, detalhar), self._c_participacao(sel)])

    def aba_aumento(self, sel: Selecao):
        t, j = sel.tipo, sel.janela
        pib = self.analise.crescimento_composto(j, sel.serie)
        c_pib = f"{formatar_percentual(pib['pib'], 1)} a.a." if pib else "n/d"
        s_pib = "PIB nominal, 12 meses" if pib else self._motivo_sem_cagr(sel)
        c_div = f"{formatar_percentual(pib['divida'], 1)} a.a." if pib else "n/d"
        s_div = "crescimento composto, em R$" if pib else self._motivo_sem_cagr(sel)

        k = self.analise.kpis_foco(t, sel.serie, j)
        if sel.em_foco:
            p = self.analise.posicao_foco(t, j, sel.foco)
            pct = p["pct_da_variacao"]
            cartoes = [
                tema.html_kpi(f"Variação · {sel.foco}", formatar_variacao(t, k["variacao"]), j.texto,
                              self._cor_variacao(k["variacao"]), pequeno=True),
                tema.html_kpi("Contribuição à variação total",
                              formatar_percentual(pct, 0) if pct is not None else "n/d",
                              f"total: {formatar_variacao(t, p['variacao_total'])}", tema.AZUL, pequeno=True),
                tema.html_kpi(f"Crescimento médio · {sel.foco}", c_div, s_div, tema.LARANJA, pequeno=True),
                tema.html_kpi("Crescimento médio do PIB", c_pib, s_pib, tema.CIANO, pequeno=True),
            ]
        else:
            ext = self.analise.extremos(j)
            if ext and ext["alta_12m"]:
                alta, data_alta = ext["alta_12m"]
                k4 = tema.html_kpi("Maior alta em 12 meses", formatar_pp(alta), f"até {formatar_mes(data_alta)}",
                                   tema.VERMELHO, pequeno=True)
            else:
                k4 = tema.html_kpi("Maior alta em 12 meses", "n/d", "período curto", tema.TEXTO_SUAVE, pequeno=True)
            cartoes = [
                tema.html_kpi("Variação da dívida total", formatar_variacao(t, k["variacao"]), j.texto,
                              self._cor_variacao(k["variacao"]), pequeno=True),
                tema.html_kpi("Crescimento médio da dívida", c_div, s_div, tema.LARANJA, pequeno=True),
                tema.html_kpi("Crescimento médio do PIB", c_pib, s_pib, tema.CIANO, pequeno=True),
                k4,
            ]
        for coluna, html in zip(st.columns(4), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")

        self._linha([self._c_cascata_aumento(sel), self._c_crescimento(sel)])
        self._linha([self._c_variacao_12m(sel), self._c_mapa_calor(sel)])

    @staticmethod
    def _motivo_sem_cagr(sel: Selecao) -> str:
        if sel.janela.meses < 12:
            return "disponível para períodos de 12 meses ou mais"
        return "não se aplica: série com valor zero ou negativo"

    def aba_juros(self, sel: Selecao):
        ex = self.extras
        if ex is None or not ex.tem("ipca", "selic"):
            st.info("Esta aba precisa do IPCA e da Selic em dados/extra/ (veja o README).")
            return
        j = sel.janela
        k = ex.kpis_juros(j)
        pct = lambda v: formatar_percentual(v, 1) if v is not None else "n/d"
        diferenca = k["selic_menos_pib"]
        cartoes = [
            tema.html_kpi("Selic em 12 meses", pct(k["selic"]), f"acumulada até {formatar_mes(j.d1)}", tema.LARANJA, pequeno=True),
            tema.html_kpi("IPCA em 12 meses", pct(k["ipca"]), f"acumulado até {formatar_mes(j.d1)}", tema.CIANO, pequeno=True),
            tema.html_kpi("Juro real (ex-post)", pct(k["juro_real"]), "Selic e IPCA acumulados, compostos", tema.ROXO, pequeno=True),
            tema.html_kpi("Selic menos PIB nominal", formatar_pp(diferenca) if diferenca is not None else "n/d",
                          "ambos em 12 meses", self._cor_variacao(diferenca) if diferenca is not None else tema.TEXTO_SUAVE,
                          pequeno=True),
        ]
        for coluna, html in zip(st.columns(4), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")
        self._linha([self._c_juros_inflacao(sel), self._c_selic_pib(sel)])
        self._linha([self._c_divida_real(sel), self._c_crescimento_real(sel)], [3, 2])
        with self._cartao("constatacoes_juros"):
            self._titulo("Constatações do período", f"Sobre: {sel.foco}")
            self._texto("\n".join(f"- {c}" for c in ex.constatacoes_juros(j, sel.serie, sel.foco)))

    def aba_dados(self, sel: Selecao):
        with self._cartao("tabela"):
            self._titulo("Dados do período", f"{ROTULOS_TIPO[sel.tipo]} · mais recentes primeiro")
            tabela = self.analise.periodo(sel.tipo, sel.ano_ini, sel.ano_fim).sort_index(ascending=False).copy()
            # o dado em foco (e o total) vêm primeiro
            ordem = list(dict.fromkeys([sel.serie, TOTAL] + list(tabela.columns)))
            tabela = tabela[ordem]
            tabela.insert(0, "Data", tabela.index.date)
            tabela = tabela.reset_index(drop=True)
            formato = "%.2f" if sel.tipo == TIPO_PORCENTAGEM else "%.0f"
            colunas = {c: st.column_config.NumberColumn(c, format=formato) for c in tabela.columns if c != "Data"}
            st.dataframe(tabela, hide_index=True, column_config=colunas)
        with st.expander("Metodologia: como ler este painel e de onde vêm os números"):
            self._texto(METODOLOGIA)

    # ===================================================== estado dos dados (lateral)
    def render_status_dados(self):
        """Mostra se os dados foram atualizados com o Banco Central e oferece atualizar na hora."""
        r = self.relatorio
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Dados**")
        if r is None:
            st.sidebar.caption("Fonte: Banco Central do Brasil (arquivos salvos no projeto).")
        else:
            texto = tema.escapar_cifrao(r.resumo())
            if r.sem_conexao:
                st.sidebar.warning(texto)
            elif r.mantidas:
                st.sidebar.warning(f"{texto} {len(r.mantidas)} série(s) mantida(s) como estavam.")
            else:
                st.sidebar.caption(f"🟢 {texto}")
            with st.sidebar.expander("Detalhes da atualização"):
                unidade = {TIPO_PORCENTAGEM: "% do PIB", TIPO_REAL: "R$", "extra": "dado extra"}
                self._texto("\n".join(
                    f"- {'⚠️' if s.status == STATUS_MANTIDA else '✅'} **{s.categoria}** ({unidade[s.tipo]}): {s.detalhe}"
                    for s in r.series))
        if self.ao_atualizar is not None:
            st.sidebar.button("🔄 Atualizar dados agora", on_click=self.ao_atualizar,
                              help="Baixa de novo as séries do Banco Central.")

    # ============================================================== orquestração
    def executar(self):
        """Monta a página completa."""
        if self.analise.vazio():
            self.render_cabecalho()
            st.error("Não foi possível carregar os dados. Verifique a pasta 'dados/' "
                     "e as mensagens no terminal.")
            self.render_status_dados()
            return

        # Os filtros ficam na barra lateral; precisam vir antes do cabeçalho, que mostra o foco.
        sel = self.filtros()
        self.render_status_dados()
        self.render_cabecalho(self.analise.ultima_data(), sel.foco if sel else None)
        if sel is None:
            st.warning("Não há dados nos anos selecionados.")
            return

        self.render_kpis(sel)
        abas = st.tabs(self.ABAS)
        for aba, metodo in zip(abas, (self.aba_visao_geral, self.aba_origem, self.aba_setores,
                                      self.aba_aumento, self.aba_juros, self.aba_dados)):
            with aba:
                metodo(sel)
