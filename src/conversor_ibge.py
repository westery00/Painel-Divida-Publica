"""Converte o IPCA baixado do IBGE para o formato dos demais CSVs do projeto.

O IBGE entrega a série "na horizontal": uma linha de cabeçalho com os meses por extenso
("julho 1994;agosto 1994;...") e uma linha "Brasil;6.84;1.86;...", com ponto decimal e textos de título
e rodapé. O painel lê o formato do Banco Central ("data";"valor", vírgula decimal), então este módulo
faz a conversão. Uso, a partir da raiz do projeto:

    python src/conversor_ibge.py                       # dados/extra/IPCA.csv -> ipca_variacao_mensal.csv
    python src/conversor_ibge.py origem.csv destino.csv

Rode de novo sempre que baixar um IPCA mais recente do IBGE.
"""
import re
import sys
from pathlib import Path

import pandas as pd

from config import PASTA_DADOS, PASTA_EXTRA, EXTRAS

MESES_PT = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_ROTULO_MES = re.compile(r"^\s*([A-Za-zçÇãÃ]+)\s+(\d{4})\s*$")


def ler_ipca_ibge(caminho) -> pd.DataFrame:
    """Lê o arquivo do IBGE e devolve [data, valor]. Levanta ValueError se o formato não for o esperado."""
    linhas = Path(caminho).read_text(encoding="utf-8-sig").splitlines()

    cabecalho = next((l.split(";")[1:] for l in linhas
                      if len(l.split(";")) > 12 and all(_ROTULO_MES.match(c) for c in l.split(";")[1:] if c.strip())), None)
    valores = next((l.split(";")[1:] for l in linhas if l.lstrip().startswith("Brasil")), None)
    if cabecalho is None or valores is None:
        raise ValueError("Não encontrei a linha de meses e a linha 'Brasil' no arquivo do IBGE.")
    cabecalho = [c for c in cabecalho if c.strip()]
    valores = [v for v in valores[:len(cabecalho)]]
    if len(valores) != len(cabecalho) or any(not v.strip() for v in valores):
        raise ValueError(f"Meses ({len(cabecalho)}) e valores ({len(valores)}) não conferem, ou há valores vazios.")

    datas = []
    for rotulo in cabecalho:
        nome, ano = _ROTULO_MES.match(rotulo).groups()
        mes = MESES_PT.get(nome.lower())
        if mes is None:
            raise ValueError(f"Mês desconhecido no cabeçalho: '{rotulo}'")
        datas.append(pd.Timestamp(year=int(ano), month=mes, day=1))
    df = pd.DataFrame({"data": datas, "valor": [float(v.replace(",", ".")) for v in valores]})

    esperado = (df["data"].max().year - df["data"].min().year) * 12 + df["data"].max().month - df["data"].min().month + 1
    if df["data"].duplicated().any() or len(df) != esperado:
        raise ValueError("A série do IBGE tem meses repetidos ou faltando.")
    return df.sort_values("data").reset_index(drop=True)


def converter_ipca(origem, destino) -> pd.DataFrame:
    """IPCA do IBGE -> CSV no formato do projeto. Devolve o DataFrame gravado."""
    df = ler_ipca_ibge(origem)
    linhas = ['"data";"valor"'] + ['"{}";"{}"'.format(f"{d:%d/%m/%Y}", f"{v:.2f}".replace(".", ","))
                                   for d, v in zip(df["data"], df["valor"])]
    Path(destino).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return df


if __name__ == "__main__":
    pasta = PASTA_DADOS / PASTA_EXTRA
    origem = Path(sys.argv[1]) if len(sys.argv) > 1 else pasta / "IPCA.csv"
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else pasta / EXTRAS["ipca"].arquivo
    gravado = converter_ipca(origem, destino)
    print(f"{len(gravado)} meses ({gravado['data'].min():%m/%Y} a {gravado['data'].max():%m/%Y}) gravados em {destino}")
