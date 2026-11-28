# Trabalho-final — Painel da Dívida Pública Líquida

Painel interativo (Python, Pandas, Plotly e Streamlit) que **destrincha a dívida pública líquida**
por setor e responde a três perguntas, agora com o contexto de juros, inflação e dívida bruta:

| Pergunta | Onde responde |
|---|---|
| **De onde vem a dívida?** | aba *De onde vem*: cascata da composição, rosca do grupo, evolução anual por setor e dívida bruta × líquida |
| **Qual setor mais contribui?** | aba *Qual setor contribui*: ranking, participação no total ao longo do tempo, quem ganhou/perdeu peso |
| **Por que a dívida aumentou?** | aba *Por que aumentou*: cascata da variação por setor, dívida × PIB, variação em 12 meses e mapa de calor anual |
| **E os juros e a inflação?** | aba *Juros e inflação*: Selic, IPCA e juro real; Selic × PIB nominal; dívida em valores reais |

A aba *Visão geral* resume as respostas em texto calculado dos dados e a aba *Dados e metodologia* traz a
tabela e a explicação dos conceitos.

**Fontes:** Banco Central do Brasil (Portal de Dados Abertos, https://dadosabertos.bcb.gov.br): dívida líquida,
dívida bruta e Selic. IBGE: IPCA.

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
- **Códigos.** Os 19 códigos da dívida líquida estão fixados em `CODIGOS_SGS` (`config.py`) e as séries extras em
  `EXTRAS`. Se um código fixado não bater com o histórico do arquivo, o atualizador tenta **descobrir** o certo entre
  os candidatos de `POOLS_SGS`, mas só aceita um candidato com pelo menos 80% dos pontos **idênticos** ao arquivo
  (uma série "parecida", como uma soma com outra, não passa). O que for descoberto fica em `dados/fontes_sgs.json`
  e aparece marcado nos detalhes ("código descoberto automaticamente"): confira.
- **Séries extras são sempre conferidas contra o arquivo local**, com tolerância mínima para IPCA e Selic (que não
  são revisados). Sem arquivo local para comparar, a série não é criada.
- **IPCA.** O código SGS **433** é uma *tentativa*: não foi confirmado no portal. Se não for o IPCA, a validação
  recusa a série e o arquivo fica como está; o painel avisa na lateral.
- **Sem rede?** `PAINEL_OFFLINE=1 streamlit run src/main.py` abre direto com os dados salvos.
- Como os CSVs são regravados, o Git mostrará arquivos modificados quando o BCB publicar dados novos.

## Como executar

```bash
pip install -r requirements.txt
streamlit run src/main.py
```

Execute a partir da raiz do projeto. Para conferir (nenhum usa internet):

```bash
python test/verificar_analise.py       # cálculos da dívida líquida
python test/verificar_extras.py        # IPCA, Selic e dívida bruta
python test/verificar_atualizador.py   # atualização, com um Banco Central falso
python test/verificar_painel.py        # painel inteiro, com Streamlit e Plotly simulados
```

Testado com Python 3 e pandas 3.0 (as quatro verificações passam com avisos tratados como erro). As
simulações do Streamlit e do Plotly pegam erros de lógica, mas não substituem abrir o painel de verdade.

## Estrutura

```
dados/
  porcentagem/   10 séries mensais de dívida líquida (CSV: data;valor), em % do PIB
  real/           9 séries mensais de dívida líquida (CSV: data;valor), em R$ milhões
  extra/          IPCA, Selic e dívida bruta do governo geral (duas metodologias)
    IPCA.csv                    original do IBGE (formato largo); o painel lê o convertido
    ipca_variacao_mensal.csv    IPCA convertido para o formato do projeto
src/
  config.py           caminhos, séries, unidades, códigos SGS, estrutura da dívida, focos e eventos de contexto
  fonte_dados.py      FonteDados       lê os CSVs e devolve DataFrames
  conversor_ibge.py   converte o IPCA do IBGE (python src/conversor_ibge.py)
  atualizador_dados.py AtualizadorDados baixa as séries do Banco Central, valida e atualiza os CSVs
  analisador_dados.py AnalisadorDados  limpeza e ferramentas gerais (filtros, agrupamentos, indicadores)
  analise_divida.py   AnaliseDivida    responde às 3 perguntas, para o Geral e para cada setor
  analise_extras.py   AnaliseExtras    juros, inflação, dívida em termos reais e dívida bruta x líquida
  indicador.py        formatadores pt-BR (R$ 9,38 tri, +39,5 p.p.) e classes Indicador
  tema.py             paleta, CSS e blocos de HTML (cartões, cabeçalho, legenda)
  visualizador.py     Visualizador     cria os gráficos Plotly
  dashboard.py        Dashboard        monta as abas usando as classes acima
  main.py             ponto de entrada
test/                 as quatro verificações acima
.streamlit/config.toml   tema escuro nativo do Streamlit
```

```
AtualizadorDados ──► FonteDados ──► AnalisadorDados ──► AnaliseDivida ──┬─► Dashboard ──► Visualizador (gráficos)
 (BCB → CSV)        (CSV → df)     (limpa, filtra)      (3 perguntas)   │      │  └──► tema, indicador (visual, formatos)
                         └────────────────────────────► AnaliseExtras ──┘      └─ usa as duas análises
```

Para atualizar o IPCA a partir do IBGE (se baixar um arquivo mais recente): substitua `dados/extra/IPCA.csv` e rode
`python src/conversor_ibge.py`.

## Conceitos usados

- **Tabela larga (pivot).** Uma linha por mês e uma coluna por setor. Facilita somar setores, calcular
  participações e diferenças entre datas.
- **Período comum.** Só entram os meses em que todas as séries existem, nas duas medidas; assim as partes
  fecham com o total e % do PIB e R$ falam do mesmo intervalo. As séries extras terminam no mesmo mês da dívida
  líquida (o mês corrente da Selic, ainda incompleto, não entra).
- **Janela de análise.** A variação de "2014 a 2026" é medida de dez/2013 a set/2026 (fim de ano contra
  fim de ano), a mesma lógica de "variação no ano".
- **Cascata (waterfall) com barras flutuantes.** Cada barra começa onde a anterior terminou (`base` + altura).
  Foi feita à mão, e não com `go.Waterfall`, para dar uma cor a cada barra e assim realçar o dado em foco.
- **PIB implícito.** PIB = dívida em R$ ÷ (dívida em % do PIB ÷ 100). Os valores obtidos (R$ 5,78 tri em
  dez/2014, R$ 7,39 tri em dez/2019) coincidem com o PIB nominal divulgado.
- **Crescimento composto (CAGR).** `(final ÷ inicial) ^ (12 ÷ meses) − 1`.
- **Acumulado em 12 meses.** Taxas mensais se compõem: 12 meses de 1% valem 12,68%, e não 12%.
- **Juro real ex-post.** `(1 + Selic) ÷ (1 + IPCA) − 1`, com os dois acumulados em 12 meses.
- **Dívida em termos reais.** O saldo de cada mês, corrigido pelo IPCA para os preços do último mês, separa
  inflação de crescimento real: `(1 + nominal) = (1 + inflação) × (1 + real)`.
- **Selic × PIB nominal.** A Selic (aproximação do custo da dívida) acima do crescimento do PIB nominal tende a
  elevar a dívida em proporção do PIB, salvo superávit primário.
- **Dívida bruta × líquida.** A bruta não desconta os ativos; a líquida desconta. As duas metodologias da bruta
  (até 2007 e a partir de 2008) medem de formas diferentes e não são trechos de uma mesma série: consulte a nota
  do Banco Central na página de cada série.
- **Cartões que podem não existir.** Cada gráfico é montado por um método `_c_*` que devolve um `Cartao`
  pronto ou `None` (quando não se aplica). Uma única função (`_linha`) descarta os `None` e reparte a largura.
- **Visual por CSS.** Os cartões usam `st.container(key="card_...")`: o Streamlit transforma a `key` numa classe
  CSS, estilizada em `tema.py`. O CSS não troca a fonte dos elementos do Streamlit (os ícones dele são uma fonte
  especial). Os blocos de HTML ficam em uma linha e o `$` é escapado (o Markdown trataria `$...$` como fórmula).

## Dados que ainda enriqueceriam o projeto

Já incluídos: **dívida bruta (DBGG)**, **Selic** e **IPCA**. Ainda não vieram:

| Dado | Onde achar | Para quê |
|---|---|---|
| Fatores condicionantes da DLSP (resultado primário, juros, câmbio, efeito do PIB) e NFSP | Portal do BCB, busca por "fatores condicionantes" e "NFSP"; ex.: SGS **5750** (juros nominais, % do PIB, fluxo em 12 meses) | explicar *por que* a dívida cresce em fluxos |
| Composição da dívida federal por indexador e por detentor | Tesouro Nacional, Relatório Mensal da Dívida (tesourotransparente.gov.br) | origem por tipo de título |
| Dívida externa líquida | Tesouro Transparente (planilha de dívida externa líquida) | interna × externa |
| Emissões diretas, Relatório Anual da Dívida | Tesouro Transparente | fluxo de emissões e visão anual |

Para incluir um novo CSV do BCB, registre-o em `EXTRAS` (ou em `SERIES`, se for dívida líquida por setor) no
`src/config.py`. O formato esperado é o dos arquivos atuais: separador `;`, colunas `data` e `valor`, datas
`dd/mm/aaaa` e decimal com vírgula.
