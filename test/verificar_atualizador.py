"""Verificação do atualizador SEM usar a internet.

Rode a partir da raiz:   python tests/verificar_atualizador.py

Monta um "Banco Central falso" a partir dos CSVs reais do projeto: cada série volta com um mês novo,
o último mês revisado e pequenas revisões antigas, e as séries ainda não confirmadas ficam escondidas
em códigos embaralhados, no meio de séries "isca" parecidas. Em seguida confere que o atualizador:
descobre os códigos certos, não troca séries, não perde dados e se comporta bem quando tudo dá errado.
"""
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atualizador_dados import (AtualizadorDados, ErroDownload, STATUS_ATUALIZADA, STATUS_EM_DIA, STATUS_MANTIDA)
from config import CODIGOS_SGS, PASTA_DADOS, POOLS_SGS, SERIES
from fonte_dados import FonteDados


def ok(condicao, mensagem):
    print(("  OK   " if condicao else "  FALHA"), mensagem)
    assert condicao, mensagem


def csv_texto(df):
    """DataFrame -> texto no formato do BCB: "01/12/2001";"51,49" (aspas, duas casas, vírgula)."""
    linhas = ['"data";"valor"']
    for data, valor in zip(df["data"], df["valor"]):
        linhas.append('"{}";"{}"'.format(f"{data:%d/%m/%Y}", f"{valor:.2f}".replace(".", ",")))
    return "\n".join(linhas) + "\n"


def montar_remoto(semente=7):
    """Devolve ({código: texto CSV}, {(tipo, arquivo): código verdadeiro}, {código: 'isca'})."""
    sorteio = random.Random(semente)
    original = {t: {a: FonteDados(PASTA_DADOS).carregar_arquivo(PASTA_DADOS / t / a) for a in SERIES[t]} for t in SERIES}

    def novo_mes(df, fator_revisao):
        df = df.copy()
        ultimo = df.iloc[-1]
        df.loc[df.index[-1], "valor"] = ultimo["valor"] * fator_revisao + (0.02 if abs(ultimo["valor"]) < 1000 else 0)  # revisão do último mês
        proxima = ultimo["data"] + pd.DateOffset(months=1)
        df.loc[len(df)] = [proxima, df.iloc[-1]["valor"] * 1.003 + (0.01 if abs(ultimo["valor"]) < 1000 else 0)]       # mês novo
        for i in sorteio.sample(range(len(df) - 2), k=len(df) // 10):                                                  # revisões antigas pequenas
            df.loc[i, "valor"] *= 1 + sorteio.uniform(-0.004, 0.004)
        return df

    verdadeiros, remoto, iscas = {}, {}, {}
    for tipo in SERIES:
        confirmados = CODIGOS_SGS.get(tipo, {})
        livres = [c for c in POOLS_SGS[tipo] if c not in confirmados.values()]
        sorteio.shuffle(livres)
        desconhecidos = [a for a in SERIES[tipo] if a not in confirmados]
        for arquivo in SERIES[tipo]:
            codigo = confirmados.get(arquivo) or livres.pop()
            verdadeiros[(tipo, arquivo)] = codigo
            remoto[codigo] = csv_texto(novo_mes(original[tipo][arquivo], 1.0003))
        # iscas nos códigos que sobraram: cópias deformadas e somas de séries reais
        arquivos = list(SERIES[tipo])
        for codigo in livres:
            a, b = sorteio.sample(arquivos, 2)
            forma = sorteio.choice(["escala", "soma", "deslocada"])
            base, outra = original[tipo][a].copy(), original[tipo][b]
            if forma == "escala":
                base["valor"] *= 0.5
            elif forma == "soma":
                base = base.merge(outra, on="data", suffixes=("", "_b")); base["valor"] += base["valor_b"]; base = base[["data", "valor"]]
            else:
                base["valor"] += 5 if tipo == "porcentagem" else 500000
            remoto[codigo] = csv_texto(base)
            iscas[codigo] = forma
    return remoto, verdadeiros, iscas


class BCFalso:
    """Substitui a internet: serve os textos CSV e registra quantos downloads foram feitos."""
    def __init__(self, remoto):
        self.remoto, self.chamadas, self.falhas = dict(remoto), [], {}

    def __call__(self, codigo):
        self.chamadas.append(codigo)
        if codigo in self.falhas:
            raise self.falhas[codigo]
        return self.remoto[codigo]


def copia_dos_dados():
    pasta = Path(tempfile.mkdtemp()) / "dados"
    shutil.copytree(PASTA_DADOS, pasta)
    return pasta


def arquivos_bytes(pasta):
    return {str(p.relative_to(pasta)): p.read_bytes() for p in sorted(pasta.rglob("*.csv"))}


remoto, verdadeiros, iscas = montar_remoto()
print(f"Banco Central falso: {len(remoto)} séries ({len(verdadeiros)} reais + {len(iscas)} iscas)")

print("\n== 1. primeira execução: descobre os códigos, atualiza e não troca nenhuma série")
pasta = copia_dos_dados(); bc = BCFalso(remoto)
rel = AtualizadorDados(pasta, baixar=bc, simultaneos=3).atualizar()
ok(len(rel.series) == 19 and rel.atualizadas == 19 and not rel.mantidas, f"19 séries atualizadas ({rel.resumo()})")
mapa = json.loads((pasta / "fontes_sgs.json").read_text(encoding="utf-8"))
descobertos = {(t, a): c for t, d in mapa.items() for a, c in d.items()}
ok(len(descobertos) == 14, f"14 códigos descobertos e guardados em fontes_sgs.json (os 5 confirmados ficam no config)")
ok(all(verdadeiros[k] == c for k, c in descobertos.items()), "TODOS os códigos descobertos são os verdadeiros (nenhuma série trocada)")
ok(all(r.codigo == verdadeiros[(r.tipo, r.arquivo)] for r in rel.series), "relatório mostra o código certo de cada uma das 19")
novos = FonteDados(pasta).carregar_tudo()
ok(novos["data"].max() == pd.Timestamp("2026-10-01") and novos.groupby(["tipo", "categoria"])["data"].max().eq(pd.Timestamp("2026-10-01")).all(),
   "as 19 séries ganharam o mês novo (out/2026) e carregam normalmente")
ok(not list(pasta.rglob("*.tmp")), "nenhum arquivo temporário sobrando")

print("== 2. segunda execução: usa o mapa guardado e só baixa os 19 códigos")
bc2 = BCFalso(remoto)
rel2 = AtualizadorDados(pasta, baixar=bc2).atualizar()
ok(len(set(bc2.chamadas)) == 19, f"{len(set(bc2.chamadas))} downloads (sem nova descoberta)")
ok(rel2.em_dia == 19 and rel2.atualizadas == 0 and rel2.tudo_certo, "tudo 'em dia' (nada regravado)")

print("== 3. sem internet: nada é alterado")
pasta3 = copia_dos_dados(); antes = arquivos_bytes(pasta3)
def sem_rede(codigo): raise OSError("Network is unreachable")
rel3 = AtualizadorDados(pasta3, baixar=sem_rede).atualizar()
ok(rel3.sem_conexao and len(rel3.mantidas) == 19 and "Sem conexão" in rel3.resumo(), f"relatório: {rel3.resumo()}")
ok(arquivos_bytes(pasta3) == antes and not (pasta3 / "fontes_sgs.json").exists(), "arquivos idênticos byte a byte; nenhum mapa criado")

print("== 4. código confirmado devolvendo a série ERRADA: o arquivo não pode ser sobrescrito")
pasta4 = copia_dos_dados(); antes = arquivos_bytes(pasta4)
errado = dict(remoto); errado[4513] = remoto[4504]      # o consolidado passa a vir como se fosse o federal
rel4 = AtualizadorDados(pasta4, baixar=BCFalso(errado)).atualizar()
arq = "porcentagem/divida_liquida_setor_publico_consolidado.csv"
depois = arquivos_bytes(pasta4)
ok(depois[arq] == antes[arq], "consolidado % intacto (o federal NÃO foi gravado no lugar dele)")
cons = next(r for r in rel4.series if r.arquivo.endswith("setor_publico_consolidado.csv"))
ok(cons.status == STATUS_MANTIDA, f"relatório: mantida ({cons.detalhe[:90]}...)")
ok(sum(r.status == STATUS_ATUALIZADA for r in rel4.series) == 18, "as outras 18 seguem atualizadas")

print("== 5. série truncada (só 60 meses) é rejeitada: histórico não se perde")
pasta5 = copia_dos_dados(); antes = arquivos_bytes(pasta5)
linhas = remoto[4513].splitlines(); curta = dict(remoto); curta[4513] = "\n".join([linhas[0]] + linhas[-60:]) + "\n"
rel5 = AtualizadorDados(pasta5, baixar=BCFalso(curta)).atualizar()
ok(arquivos_bytes(pasta5)[arq] == antes[arq], "arquivo com 298 meses não foi trocado por um de 60")
ok("cobre só" in next(r for r in rel5.series if r.arquivo.endswith("setor_publico_consolidado.csv")).detalhe, "motivo registrado: cobertura insuficiente")

print("== 6. conteúdo estranho e falhas parciais")
pasta6 = copia_dos_dados(); antes = arquivos_bytes(pasta6)
estranho = dict(remoto); estranho[4504] = '{"error": "serie nao encontrada"}'
bc6 = BCFalso(estranho); bc6.falhas[4505] = ErroDownload("HTTP 500")
rel6 = AtualizadorDados(pasta6, baixar=bc6, tentativas=1).atualizar()
mantidas = {r.arquivo for r in rel6.mantidas}
ok({"divida_liquida_governo_federal.csv", "divida_liquida_banco.csv"} <= mantidas, "JSON de erro e HTTP 500: só essas duas ficam como estavam")
depois = arquivos_bytes(pasta6)
ok(depois["porcentagem/divida_liquida_governo_federal.csv"] == antes["porcentagem/divida_liquida_governo_federal.csv"], "federal intacto")
ok(not rel6.sem_conexao and rel6.atualizadas >= 15, f"as demais seguem ({rel6.atualizadas} atualizadas); não é 'sem conexão'")

print("== 7. duas séries idênticas escondidas: ambiguidade não é adivinhada")
pasta7 = copia_dos_dados()
alvo = ("porcentagem", "divida_liquida_empresas_estatais.csv"); cod = verdadeiros[alvo]
isca = next(c for c in POOLS_SGS["porcentagem"] if c in iscas)          # um código de isca qualquer do % PIB
gemeo = dict(remoto); gemeo[isca] = remoto[cod]                         # vira uma cópia exata do alvo
rel7 = AtualizadorDados(pasta7, baixar=BCFalso(gemeo)).atualizar()
r = next(x for x in rel7.series if x.arquivo == alvo[1])
ok(r.status == STATUS_MANTIDA and "inequivocamente" in r.detalhe, "série com gêmea exata: mantida, sem chute")
ok(sum(x.status == STATUS_ATUALIZADA for x in rel7.series) == 18, "as outras 18 não são afetadas")

print("== 8. comparação: revisão pequena passa; série diferente, não")
comparar = AtualizadorDados._comparar
base = pd.DataFrame({"data": pd.date_range("2002-01-01", periods=120, freq="MS"), "valor": [50 + i * 0.1 for i in range(120)]})
rev = base.copy(); rev["valor"] *= 1.01
ok(comparar("porcentagem", base, rev)[0], "revisão de 1% em todos os pontos: aceita")
rev2 = base.copy(); rev2.loc[100:, "valor"] += 0.8
ok(comparar("porcentagem", base, rev2)[0], "20 pontos recentes diferentes (17% do total, mas dentro de 3%/0,05): aceita")
diferente = base.copy(); diferente["valor"] *= 0.5
ok(not comparar("porcentagem", base, diferente)[0], "série com metade do valor: rejeitada")
ok(not comparar("porcentagem", base, base.iloc[20:])[0], "série que perdeu 20 meses do início: rejeitada")
ok(comparar("porcentagem", base.iloc[0:0], diferente)[0], "sem arquivo local, não há o que comparar: aceita")
print("\nTODOS OS TESTES DO ATUALIZADOR PASSARAM")
