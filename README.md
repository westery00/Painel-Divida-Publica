# Trabalho-final — Painel da Dívida Pública Líquida

Dashboard interativo (Python, Pandas, Plotly e Streamlit) para analisar a dívida
líquida do setor público brasileiro, por categoria (governo federal, estados,
municípios, Banco Central e empresas estatais), em duas medidas: porcentagem e
valores em R$.

## Como executar

```bash
pip install -r requirements.txt
streamlit run src/main.py
```

Execute a partir da raiz do projeto. Os caminhos dos dados são calculados a
partir da localização dos arquivos, então não dependem da pasta atual.

## Estrutura

```
dados/
  porcentagem/   10 séries mensais (CSV: data;valor)
  real/           9 séries mensais (CSV: data;valor)
src/
  config.py          caminhos, nome legível de cada série e rótulos da interface
  fonte_dados.py     FonteDados       lê os CSVs e devolve um único DataFrame
  analisador_dados.py AnalisadorDados limpa os dados; filtros, agrupamentos e indicadores
  indicador.py       Indicador*       guarda e formata valores (padrão brasileiro)
  visualizador.py    Visualizador     cria os gráficos Plotly
  dashboard.py       Dashboard        monta a interface usando as classes acima
  main.py            ponto de entrada
```

## Como as partes se conectam

```
FonteDados ──► AnalisadorDados ──► Dashboard ──► Visualizador (gráficos)
 (CSV → df)    (limpa, filtra,       (tela)  └──► Indicador   (formata KPIs)
                calcula)
```

Os dados circulam num formato único, um registro por série e por mês:

| data       | valor | categoria                 | tipo        |
|------------|-------|---------------------------|-------------|
| 2002-01-01 | 52.28 | Setor Público Consolidado | porcentagem |

## Sobre os dados

As séries se sobrepõem — os totais contêm as partes (diferença máxima de 0,02
ponto percentual nos dados):

- Setor Público Consolidado = Governo Geral + Banco Central + Empresas Estatais
- Governo Geral = Federal + Estaduais + Municipais
- Empresas Estatais = Federais + Estaduais + Municipais

Por isso, somar todas as categorias contaria a dívida duas vezes. O painel trata isso assim:

- **Indicadores (KPIs):** você escolhe uma das categorias selecionadas e os quatro
  indicadores (registros, média, maior pico e variação anual média) refletem
  somente a série dessa categoria.
- **Comparativo Total x Componentes:** o gráfico de barras mostra a média de cada
  categoria selecionada ao lado do Setor Público Consolidado, que é sempre
  exibido como referência. As médias usam apenas os meses em que todas as barras
  têm dados; sem isso, séries que começam em datas diferentes (na pasta `real`,
  1998 contra 2001) não fechariam com o total.

Para incluir um novo CSV, adicione-o em `SERIES` no arquivo `src/config.py`.
