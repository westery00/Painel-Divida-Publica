# Painel da Dívida Pública Líquida

Painel interativo (Python, Pandas, Plotly e Streamlit) que **destrincha a dívida pública líquida**
por setor e responde a três perguntas:

| Pergunta | Onde responde |
|---|---|
| **De onde vem a dívida?** | aba *De onde vem*: cascata da composição, rosca do grupo e evolução anual por setor |
| **Qual setor mais contribui?** | aba *Qual setor contribui*: ranking, participação no total ao longo do tempo, quem ganhou/perdeu peso |
| **Por que a dívida aumentou?** | aba *Por que aumentou*: cascata da variação por setor, dívida × PIB, variação em 12 meses e mapa de calor anual |

A aba *Visão geral* resume as três respostas em texto calculado dos dados e a aba *Dados e metodologia* traz
a tabela e a explicação dos conceitos.

**Fonte dos dados:** Banco Central do Brasil (Portal de Dados Abertos, https://dadosabertos.bcb.gov.br).

## Dado em foco

Na barra lateral, **Dado em foco** controla o painel inteiro:

- **Geral** usa todos os dados: o consolidado e todos os setores.
- **Um setor** (Governo Federal, Governos Estaduais, Governos Municipais, Empresas Estatais ou Banco Central)
  mostra só uma parte dos dados. Indicadores, textos e gráficos passam a falar dele: o setor aparece em
  destaque e os demais ficam apagados.

Gráficos que não fazem sentido para o setor escolhido simplesmente não aparecem (por exemplo, o crescimento
percentual do Banco Central, cuja dívida é negativa); os vizinhos ocupam o espaço.

## Como executar

```bash
pip install -r requirements.txt
streamlit run src/main.py
```

Execute a partir da raiz do projeto. Para conferir os cálculos: `python tests/verificar_analise.py`.

## Estrutura

```
dados/
  porcentagem/   10 séries mensais (CSV: data;valor), em % do PIB
  real/           9 séries mensais (CSV: data;valor), em R$ milhões
src/
  config.py           caminhos, nome de cada série, unidades, estrutura da dívida, focos e eventos de contexto
  fonte_dados.py      FonteDados      lê os CSVs e devolve um único DataFrame
  analisador_dados.py AnalisadorDados limpeza e ferramentas gerais (filtros, agrupamentos, indicadores)
  analise_divida.py   AnaliseDivida   responde às 3 perguntas, para o Geral e para cada setor
  indicador.py        formatadores pt-BR (R$ 9,38 tri, +39,5 p.p.) e classes Indicador
  tema.py             paleta, CSS e blocos de HTML (cartões, cabeçalho, legenda)
  visualizador.py     Visualizador    cria os gráficos Plotly
  dashboard.py        Dashboard       monta as abas usando as classes acima
  main.py             ponto de entrada
tests/
  verificar_analise.py   confere os números da análise com os CSVs reais
.streamlit/config.toml   tema escuro nativo do Streamlit
```

```
FonteDados ──► AnalisadorDados ──► AnaliseDivida ──► Dashboard ──► Visualizador (gráficos)
 (CSV → df)    (limpa, filtra)     (3 perguntas)      (abas)   └──► tema, indicador (visual e formatos)
```

## Conceitos usados

- **Tabela larga (pivot).** Uma linha por mês e uma coluna por setor. Facilita somar setores, calcular
  participações e diferenças entre datas.
- **Período comum.** Só entram os meses em que todas as séries existem, nas duas medidas; assim as partes
  fecham com o total e % do PIB e R$ falam do mesmo intervalo.
- **Janela de análise.** A variação de "2014 a 2026" é medida de dez/2013 a set/2026 (fim de ano contra
  fim de ano), a mesma lógica de "variação no ano".
- **Cascata (waterfall) com barras flutuantes.** Cada barra começa onde a anterior terminou (`base` + altura).
  Foi feita à mão, e não com `go.Waterfall`, para dar uma cor a cada barra e assim realçar o dado em foco.
  É a escolha certa aqui porque o Banco Central tem dívida **negativa**, o que impede gráficos de fatias.
- **PIB implícito.** PIB = dívida em R$ ÷ (dívida em % do PIB ÷ 100). Os valores obtidos (R$ 5,78 tri em
  dez/2014, R$ 7,39 tri em dez/2019) coincidem com o PIB nominal divulgado, o que confirma as unidades.
- **Crescimento composto (CAGR).** `(final ÷ inicial) ^ (12 ÷ meses) − 1`: a taxa anual constante que
  leva do valor inicial ao final. Compara o ritmo da dívida com o do PIB nominal.
- **Cartões que podem não existir.** Cada gráfico é montado por um método `_c_*` que devolve um `Cartao`
  pronto ou `None` (quando não se aplica ao dado em foco). Uma única função (`_linha`) descarta os `None`
  e reparte a largura entre os que sobraram.
- **Template Method nos indicadores.** `Indicador.formatar_valor()` trata valores ausentes ("n/d") e delega
  a formatação às subclasses (`IndicadorMonetario`, `IndicadorPercentual`).
- **Visual por CSS.** Os cartões usam `st.container(key="card_...")`: o Streamlit transforma a `key` numa
  classe CSS (`st-key-card_...`), estilizada em `tema.py`. Os blocos de HTML são escritos em uma linha e o
  `$` é escapado, porque o Markdown do Streamlit trataria `$...$` como fórmula e linhas indentadas como código.
  O CSS não troca a fonte dos elementos do Streamlit, pois os ícones dele (setas, etc.) são uma fonte
  especial e mudar a fonte faz o nome do ícone aparecer como texto.
- **Legenda da rosca em HTML.** Em vez de depender do posicionamento da legenda do Plotly, a legenda é
  desenhada abaixo do gráfico, no cartão.
- **Números em português.** `separators=",."` no layout do Plotly: decimal com vírgula e milhar com ponto.

## Sobre os dados

As séries se sobrepõem (diferença máxima de 0,02 p.p. nos dados): Setor Público Consolidado = Governo Federal
+ Governos Estaduais + Governos Municipais + Empresas Estatais + Banco Central. Por isso totais e partes
nunca são somados juntos. As faixas de eventos nos gráficos de linha (crise global, recessão, pandemia) são
contexto e não fazem parte dos CSVs.

Para incluir um novo CSV, adicione-o em `SERIES` no arquivo `src/config.py`. O formato esperado é o dos
arquivos atuais: separador `;`, colunas `data` e `valor`, datas `dd/mm/aaaa` e decimal com vírgula.

## Dados que enriqueceriam o projeto

Podem ser buscados no Portal de Dados Abertos do Banco Central (https://dadosabertos.bcb.gov.br):

1. **Fatores condicionantes da dívida** (resultado primário, juros nominais, câmbio, efeito do PIB): responde
   *por que* a dívida cresce em termos de fluxos, o que hoje só é possível mostrar por setor.
2. **Dívida Bruta do Governo Geral (DBGG)**, a medida usada em comparações internacionais.
3. **Composição da dívida federal** por indexador (Selic, prefixado, inflação, câmbio) e por detentor.
4. **Dívida interna x externa.**
5. **Taxa Selic e inflação (IPCA)**, para relacionar o custo da dívida ao seu crescimento.
