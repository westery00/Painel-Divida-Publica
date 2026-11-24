"""Camada de interface (Streamlit).

O Dashboard só apresenta: pede os números e textos à AnaliseDivida, os gráficos
ao Visualizador, o visual ao módulo ``tema`` e a formatação aos ``formatar_*``.

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
from config import (COMPONENTES, EVENTOS, ROTULOS_CURTOS, ROTULOS_TIPO, TIPO_PORCENTAGEM, UNIDADES)
from indicador import (criar_indicador, formatar_medida, formatar_mes, formatar_numero,
                       formatar_percentual, formatar_pp, formatar_variacao)
from visualizador import Visualizador

METODOLOGIA = """
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
cresce mais rápido que o PIB, a razão dívida/PIB sobe. Só é calculado para períodos de 12 meses ou mais.

**Como ler os gráficos.**
**Cascata:** cada barra soma (ou subtrai) à anterior até chegar ao total. **Mapa de calor:** cada célula é a
variação de um fim de ano ao seguinte; vermelho = a dívida subiu, verde = caiu. **Faixas sombreadas:**
eventos de contexto (não fazem parte dos CSVs). **\\***: ano em andamento, com o dado mais recente.

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


class Dashboard:
    ABAS = ["📊 Visão geral", "🧭 De onde vem", "🏛️ Qual setor contribui",
            "📈 Por que aumentou", "🗂️ Dados e metodologia"]

    def __init__(self, analise: AnaliseDivida, visualizador: Visualizador):
        self.analise = analise
        self.visualizador = visualizador

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

    # =============================================================== cabeçalho
    def render_cabecalho(self, ultima_data=None):
        atualizado = f"Dados até {formatar_mes(ultima_data)}" if ultima_data is not None else ""
        st.markdown(tema.html_cabecalho(
            "📊 Painel da Dívida Pública Líquida",
            "De onde vem, quem mais contribui e por que aumentou", atualizado), unsafe_allow_html=True)

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

        foco = st.sidebar.selectbox("Categoria em foco (indicadores do topo)", COLUNAS)

        janela = self.analise.janela(tipo, ano_ini, ano_fim)
        if janela is None:
            return None
        st.sidebar.markdown("---")
        st.sidebar.caption(f"As variações comparam **{formatar_mes(janela.d0)}** com "
                           f"**{formatar_mes(janela.d1)}** (fim de ano contra fim de ano).")
        return Selecao(tipo, ano_ini, ano_fim, foco, janela)

    # ===================================================================== KPIs
    def render_kpis(self, sel: Selecao):
        """Quatro indicadores da categoria em foco (todos refletem só essa série)."""
        t, j = sel.tipo, sel.janela
        k = self.analise.kpis_foco(t, sel.foco, j)
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

    # ===================================================================== abas
    def aba_visao_geral(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        respostas = self.analise.respostas(t, j)
        cores = [tema.AZUL, tema.LARANJA, self._cor_variacao(
            self.analise.kpis_foco(t, TOTAL, j)["variacao"])]
        for coluna, r, cor in zip(st.columns(3), respostas, cores):
            coluna.markdown(tema.html_resposta(r["pergunta"], r["destaque"], r["texto"], cor),
                            unsafe_allow_html=True)
        st.write("")

        with self._cartao("evolucao"):
            self._titulo("Evolução da dívida líquida", "Escolha as categorias para comparar")
            padrao = [TOTAL] + COMPONENTES
            categorias = st.multiselect("Categorias", COLUNAS, default=padrao, key="evo_categorias",
                                        label_visibility="collapsed")
            if not categorias:
                st.info("Selecione ao menos uma categoria.")
            else:
                df = self.analise.evolucao(t, categorias, sel.ano_ini, sel.ano_fim)
                df["valor"] = df["valor"] * u.fator_nivel
                fig = self.visualizador.plotar_grafico(
                    df, "data", "valor", None, "linha", cor="categoria", rotulo_y=u.rotulo_nivel,
                    cores=tema.CORES_CATEGORIA, bandas=EVENTOS, altura=420)
                self._grafico(fig, "evolucao")
            st.caption("Faixas sombreadas: eventos de contexto (não fazem parte dos dados).")

        with self._cartao("conclusoes"):
            self._titulo("Outras constatações do período")
            self._texto("\n".join(f"- {c}" for c in self.analise.conclusoes(t, j)))

    def aba_origem(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        esquerda, direita = st.columns([3, 2])

        with esquerda, self._cartao("cascata_composicao"):
            self._titulo(f"Como a dívida se forma · {formatar_mes(j.d1)}",
                         "Cada setor soma (ou subtrai) até o total consolidado")
            c = self.analise.cascata_composicao(t, j)
            textos = [formatar_medida(t, v, sinal=(m == "relative")) for v, m in zip(c["exibir"], c["medida"])]
            fig = self.visualizador.cascata(c["rotulo"], c["valor"] * u.fator_nivel, c["medida"],
                                            textos, u.rotulo_nivel)
            self._grafico(fig, "cascata_composicao")

        with direita, self._cartao("rosca_governo"):
            self._titulo("Dentro do governo geral", f"Federal, estados e municípios · {formatar_mes(j.d1)}")
            df, soma = self.analise.divisao_governo_geral(t, j)
            fig = self.visualizador.rosca(
                [ROTULOS_CURTOS[c] for c in df["categoria"]], df["valor"],
                [tema.CORES_CATEGORIA[c] for c in df["categoria"]],
                texto_central=f"Governo geral<br><b>{formatar_medida(t, soma)}</b>")
            self._grafico(fig, "rosca_governo")

        with self._cartao("composicao_anual"):
            self._titulo("Composição ao longo dos anos", "Saldo de cada setor no fim de cada ano; a linha é o total")
            anual, nota = self.analise.composicao_anual(t, sel.ano_ini, sel.ano_fim)
            partes = anual[COMPONENTES] * u.fator_nivel
            partes.columns = [ROTULOS_CURTOS[c] for c in COMPONENTES]
            cores = {ROTULOS_CURTOS[c]: tema.CORES_CATEGORIA[c] for c in COMPONENTES}
            fig = self.visualizador.barras_empilhadas(partes, cores, linha=anual[TOTAL] * u.fator_nivel,
                                                      rotulo_y=u.rotulo_nivel)
            self._grafico(fig, "composicao_anual")
            legenda = "Barras abaixo de zero: setor com posição credora líquida (reduz o total)."
            st.caption(f"{legenda} {nota}" if nota else legenda)

    def aba_setores(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
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
        for coluna, html in zip(st.columns(3), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")

        esquerda, direita = st.columns(2)
        with esquerda, self._cartao("ranking"):
            self._titulo(f"Ranking de contribuição · {formatar_mes(j.d1)}",
                         f"Barras em {u.rotulo_nivel}; rótulos mostram a participação no total")
            detalhar = st.toggle("Detalhar empresas estatais", key="detalhar_estatais")
            rk = self.analise.ranking(t, j, detalhar)
            fig = self.visualizador.barras_horizontais(
                [ROTULOS_CURTOS[c] for c in rk["categoria"]], rk["valor"] * u.fator_nivel,
                [tema.CORES_CATEGORIA[c] for c in rk["categoria"]],
                [formatar_percentual(p, 1) for p in rk["participacao"]], u.rotulo_nivel)
            self._grafico(fig, "ranking")

        with direita, self._cartao("participacao_tempo"):
            self._titulo("Participação no total ao longo do tempo",
                         "Quanto cada setor representa da dívida consolidada, mês a mês")
            df = self.analise.participacoes(t, sel.ano_ini, sel.ano_fim)
            fig = self.visualizador.plotar_grafico(
                df, "data", "valor", None, "linha", cor="categoria", rotulo_y="% do total",
                cores=tema.CORES_CATEGORIA, bandas=EVENTOS, altura=400)
            self._grafico(fig, "participacao_tempo")

    def aba_aumento(self, sel: Selecao):
        t, j, u = sel.tipo, sel.janela, sel.unidade
        total = self.analise.kpis_foco(t, TOTAL, j)
        cagr = self.analise.crescimento_composto(j)
        ext = self.analise.extremos(j)

        if cagr:
            c_div, c_pib = formatar_percentual(cagr["divida"], 1) + " a.a.", formatar_percentual(cagr["pib"], 1) + " a.a."
            s_div, s_pib = "crescimento composto, em R$", "PIB nominal, 12 meses"
        else:
            c_div = c_pib = "n/d"
            s_div = s_pib = "disponível para períodos de 12 meses ou mais"
        if ext and ext["alta_12m"]:
            alta, data_alta = ext["alta_12m"]
            k4 = tema.html_kpi("Maior alta em 12 meses", formatar_pp(alta), f"até {formatar_mes(data_alta)}",
                               tema.VERMELHO, pequeno=True)
        else:
            k4 = tema.html_kpi("Maior alta em 12 meses", "n/d", "período curto", tema.TEXTO_SUAVE, pequeno=True)
        cartoes = [
            tema.html_kpi("Variação da dívida total", formatar_variacao(t, total["variacao"]), j.texto,
                          self._cor_variacao(total["variacao"]), pequeno=True),
            tema.html_kpi("Crescimento médio da dívida", c_div, s_div, tema.LARANJA, pequeno=True),
            tema.html_kpi("Crescimento médio do PIB", c_pib, s_pib, tema.CIANO, pequeno=True),
            k4,
        ]
        for coluna, html in zip(st.columns(4), cartoes):
            coluna.markdown(html, unsafe_allow_html=True)
        st.write("")

        esquerda, direita = st.columns(2)
        with esquerda, self._cartao("cascata_aumento"):
            self._titulo("Quem puxou a variação", f"Contribuição de cada setor · {j.texto}")
            c = self.analise.cascata_aumento(t, j)
            textos = [formatar_variacao(t, v) if m == "relative" else formatar_medida(t, v)
                      for v, m in zip(c["exibir"], c["medida"])]
            fig = self.visualizador.cascata(c["rotulo"], c["valor"] * u.fator_nivel, c["medida"], textos,
                                            u.rotulo_nivel, cor_alta=tema.VERMELHO, cor_baixa=tema.VERDE)
            self._grafico(fig, "cascata_aumento")

        with direita, self._cartao("crescimento_12m"):
            self._titulo("Dívida x PIB: crescimento em 12 meses",
                         "Quando a dívida cresce mais que o PIB, a razão dívida/PIB sobe")
            df = self.analise.crescimento_12m(sel.ano_ini, sel.ano_fim)
            if df is None or df.empty:
                st.info("Disponível quando as duas medidas (% do PIB e R$) estão nos dados.")
            else:
                fig = self.visualizador.plotar_grafico(
                    df, "data", "valor", None, "linha", cor="serie", rotulo_y="% em 12 meses",
                    cores={"Dívida líquida (R$)": tema.VERMELHO, "PIB nominal": tema.CIANO},
                    bandas=EVENTOS, altura=370)
                self._grafico(fig, "crescimento_12m")

        esquerda, direita = st.columns(2)
        with esquerda, self._cartao("variacao_12m"):
            self._titulo("Variação em 12 meses da dívida total", "Vermelho: alta · Verde: queda")
            serie = self.analise.variacao_12m(t, sel.ano_ini, sel.ano_fim)
            if serie.empty:
                st.info("Sem dados suficientes no período.")
            else:
                fig = self.visualizador.barras_sinal(serie.index, serie.values * u.fator_delta, u.rotulo_delta)
                self._grafico(fig, "variacao_12m")

        with direita, self._cartao("mapa_calor"):
            self._titulo("Variação anual por setor", f"Fim de ano contra fim de ano ({u.rotulo_delta})")
            matriz = self.analise.variacao_anual(t, sel.ano_ini, sel.ano_fim) * u.fator_delta
            if matriz.empty:
                st.info("Sem dados suficientes no período.")
            else:
                casas = 1 if t == TIPO_PORCENTAGEM else 0
                textos = pd.DataFrame([[formatar_numero(v, casas, sinal=True) for v in linha]
                                       for linha in matriz.values], index=matriz.index, columns=matriz.columns)
                fig = self.visualizador.mapa_calor(matriz, textos, u.rotulo_delta)
                self._grafico(fig, "mapa_calor")

    def aba_dados(self, sel: Selecao):
        with self._cartao("tabela"):
            self._titulo("Dados do período", f"{ROTULOS_TIPO[sel.tipo]} · mais recentes primeiro")
            tabela = self.analise.periodo(sel.tipo, sel.ano_ini, sel.ano_fim).sort_index(ascending=False).copy()
            tabela.insert(0, "Data", tabela.index.date)
            tabela = tabela.reset_index(drop=True)
            formato = "%.2f" if sel.tipo == TIPO_PORCENTAGEM else "%.0f"
            colunas = {c: st.column_config.NumberColumn(c, format=formato) for c in tabela.columns if c != "Data"}
            st.dataframe(tabela, hide_index=True, column_config=colunas)
        with st.expander("Metodologia: como ler este painel e de onde vêm os números"):
            self._texto(METODOLOGIA)

    # ============================================================== orquestração
    def executar(self):
        """Monta a página completa."""
        if self.analise.vazio():
            self.render_cabecalho()
            st.error("Não foi possível carregar os dados. Verifique a pasta 'dados/' "
                     "e as mensagens no terminal.")
            return

        self.render_cabecalho(self.analise.ultima_data())
        sel = self.filtros()
        if sel is None:
            st.warning("Não há dados nos anos selecionados.")
            return

        self.render_kpis(sel)
        abas = st.tabs(self.ABAS)
        for aba, metodo in zip(abas, (self.aba_visao_geral, self.aba_origem, self.aba_setores,
                                      self.aba_aumento, self.aba_dados)):
            with aba:
                metodo(sel)
