# Trabalho-final — Painel da Dívida Pública Líquida

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

## Atualização automática dos dados

A cada inicialização, o painel baixa as séries do Banco Central e atualiza os CSVs de `dados/`
(`src/atualizador_dados.py`). O endereço usado é o que o próprio portal publica:
`https://api.bcb.gov.br/dados/serie/bcdata.sgs.<código>/dados?formato=csv`.

- **Uma vez por inicialização.** O Streamlit reexecuta o código a cada clique, mas a atualização usa
  `st.cache_resource`, que só roda de novo após reiniciar o servidor ou clicar em **Atualizar dados agora**
  (barra lateral). A barra lateral mostra o resultado e, em "Detalhes da atualização", o estado de cada série.
- **Nunca piora os dados.** Um arquivo só é substituído se o baixado tiver todas as datas do atual e os valores
  coincidirem (com tolerância, pois o BCB revisa valores passados, por exemplo o último mês). Sem internet,
  com erro ou com série suspeita, o arquivo local fica como está e o painel avisa.
- **Sem rede?** `PAINEL_OFFLINE=1 streamlit run src/main.py` abre direto com os dados salvos.
- Como os CSVs são regravados, o Git mostrará arquivos modificados quando o BCB publicar dados novos.

## Como executar

```bash
pip install -r requirements.txt
streamlit run src/main.py
```

Execute a partir da raiz do projeto. Para conferir: `python tests/verificar_analise.py` (cálculos) e `python tests/verificar_atualizador.py` (atualização, sem internet).

## Estrutura

```
dados/
  porcentagem/   10 séries mensais (CSV: data;valor), em % do PIB
  real/           9 séries mensais (CSV: data;valor), em R$ milhões
src/
  config.py           caminhos, nome de cada série, unidades, estrutura da dívida, focos e eventos de contexto
  fonte_dados.py      FonteDados      lê os CSVs e devolve um único DataFrame
  atualizador_dados.py AtualizadorDados baixa as séries do Banco Central, valida e atualiza os CSVs
  analisador_dados.py AnalisadorDados limpeza e ferramentas gerais (filtros, agrupamentos, indicadores)
  analise_divida.py   AnaliseDivida   responde às 3 perguntas, para o Geral e para cada setor
  indicador.py        formatadores pt-BR (R$ 9,38 tri, +39,5 p.p.) e classes Indicador
  tema.py             paleta, CSS e blocos de HTML (cartões, cabeçalho, legenda)
  visualizador.py     Visualizador    cria os gráficos Plotly
  dashboard.py        Dashboard       monta as abas usando as classes acima
  main.py             ponto de entrada
tests/
  verificar_analise.py      confere os números da análise com os CSVs reais
  verificar_atualizador.py  testa a atualização com um Banco Central falso (sem internet)
.streamlit/config.toml   tema escuro nativo do Streamlit
```

```
AtualizadorDados ──► FonteDados ──► AnalisadorDados ──► AnaliseDivida ──► Dashboard ──► Visualizador (gráficos)
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

Todos no Portal de Dados Abertos do Banco Central (https://dadosabertos.bcb.gov.br): use a busca por título.
Cada página tem o link de download; para baixar direto, use o endereço de CSV acima trocando `<código>`.
"Confirmado" significa que o título e o código foram vistos no próprio portal.

| Dado | Código / onde achar | Situação |
|---|---|---|
| Fatores condicionantes da DLSP (resultado primário, juros, câmbio, efeito do PIB) | busque "fatores condicionantes"; família NFSP, ex.: **5750** (NFSP sem desvalorização cambial, % PIB, fluxo em 12 meses, juros nominais, total) | 5750 confirmado; os demais fatores, a localizar |
| Dívida Bruta do Governo Geral (DBGG) | **13762** (% do PIB, metodologia a partir de 2008) | confirmado |
| Composição por indexador e detentor | Tesouro Nacional, "Relatório Mensal da Dívida Pública Federal" (tesourotransparente.gov.br) | fonte indicada; dataset exato a localizar |
| Dívida interna x externa | no mesmo relatório do Tesouro (DPMFi e DPFe), ou séries da DLSP no BCB | a localizar |
| Selic | **4390** (acumulada no mês) | confirmado |
| IPCA | **433** (variação mensal; vem do IBGE) | não confirmado nesta pesquisa |
