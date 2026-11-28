"""Verificação do atualizador SEM usar a internet.

Rode a partir da raiz:   python test/verificar_atualizador.py

Monta um "Banco Central falso" a partir dos CSVs reais do projeto: cada série volta com um mês novo, o
último mês revisado e pequenas revisões antigas, no meio de séries "isca" parecidas. Confere que o
atualizador: atualiza sem trocar séries, descobre códigos quando um deles falha, não perde dados e se
comporta bem quando tudo dá errado, inclusive com as séries extras (IPCA, Selic, dívida bruta).
"""
import contextlib
import dataclasses
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import atualizador_dados as ad
from atualizador_dados import AtualizadorDados, ErroDownload, STATUS_ATUALIZADA, STATUS_EM_DIA, STATUS_MANTIDA
from config import CODIGOS_SGS, EXTRAS, PASTA_DADOS, PASTA_EXTRA, POOLS_SGS, SERIES
from fonte_dados import FonteDados

TOTAL_SERIES = sum(len(v) for v in SERIES.values()) + len(EXTRAS)   # 19 de dívida líquida + 4 extras
# Os 5 códigos que foram confirmados no portal; os demais, nos testes de descoberta, viram "desconhecidos".
MINIMOS = {"porcentagem": {"divida_liquida_setor_publico_consolidado.csv": 4513, "divida_liquida_governo_federal.csv": 4504,
                           "divida_liquida_banco.csv": 4505, "divida_liquida_governo_estaduais.csv": 4507},
           "real": {"divida_liquida_consolidada_real.csv": 4478}}


def ok(condicao, mensagem):
    print(("  OK   " if condicao else "  FALHA"), mensagem)
    assert condicao, mensagem


@contextlib.contextmanager
def com_config(**trocas):
    """Troca temporariamente nomes de config dentro do atualizador (ex.: CODIGOS_SGS=MINIMOS)."""
    antigos = {k: getattr(ad, k) for k in trocas}
    for k, v in trocas.items():
        setattr(ad, k, v)
    try:
        yield
    finally:
        for k, v in antigos.items():
            setattr(ad, k, v)


def csv_texto(df):
    """DataFrame -> texto no formato do BCB: "01/12/2001";"51,49" (aspas, duas casas, vírgula)."""
    linhas = ['"data";"valor"']
    for data, valor in zip(df["data"], df["valor"]):
        linhas.append('"{}";"{}"'.format(f"{data:%d/%m/%Y}", f"{valor:.2f}".replace(".", ",")))
    return "\n".join(linhas) + "\n"


def novo_mes(df, sorteio):
    """Série como o BCB a devolveria depois: último mês revisado, um mês novo e revisões antigas pequenas."""
    df = df.copy()
    pequena = abs(df.iloc[-1]["valor"]) < 1000
    df.loc[df.index[-1], "valor"] = df.iloc[-1]["valor"] * 1.0003 + (0.02 if pequena else 0)
    df.loc[len(df)] = [df.iloc[-1]["data"] + pd.DateOffset(months=1), df.iloc[-1]["valor"] * 1.003 + (0.01 if pequena else 0)]
    for i in sorteio.sample(range(len(df) - 2), k=len(df) // 10):
        df.loc[i, "valor"] *= 1 + sorteio.uniform(-0.004, 0.004)
    return df


def montar_remoto(semente=7):
    """({código: texto CSV}, {(tipo, arquivo): código verdadeiro}, {código: forma da isca})."""
    sorteio, fonte = random.Random(semente), FonteDados(PASTA_DADOS)
    originais = {t: {a: fonte.carregar_arquivo(PASTA_DADOS / t / a) for a in SERIES[t]} for t in SERIES}
    remoto, verdadeiros, iscas = {}, {}, {}
    for t in SERIES:
        for a in SERIES[t]:
            verdadeiros[(t, a)] = CODIGOS_SGS[t][a]
            remoto[CODIGOS_SGS[t][a]] = csv_texto(novo_mes(originais[t][a], sorteio))
    for extra in EXTRAS.values():
        remoto[extra.codigo_sgs] = csv_texto(novo_mes(fonte.carregar_arquivo(PASTA_DADOS / PASTA_EXTRA / extra.arquivo), sorteio))
    for t in SERIES:   # iscas: cópias deformadas e somas de séries reais nos códigos candidatos que sobraram
        arquivos = list(SERIES[t])
        for codigo in POOLS_SGS[t]:
            if codigo in remoto:
                continue
            a, b = sorteio.sample(arquivos, 2)
            forma = sorteio.choice(["escala", "soma", "deslocada"])
            base, outra = originais[t][a].copy(), originais[t][b]
            if forma == "escala":
                base["valor"] *= 0.5
            elif forma == "soma":
                base = base.merge(outra, on="data", suffixes=("", "_b")); base["valor"] += base["valor_b"]; base = base[["data", "valor"]]
            else:
                base["valor"] += 5 if t == "porcentagem" else 500000
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
print(f"Banco Central falso: {len(remoto)} séries ({len(verdadeiros)} de dívida líquida + {len(EXTRAS)} extras + {len(iscas)} iscas)")
arq_consolidado = "porcentagem/divida_liquida_setor_publico_consolidado.csv"

print("\n== 1. códigos fixados no config: atualiza as 23 séries e baixa só o necessário")
pasta = copia_dos_dados(); bc = BCFalso(remoto)
rel = AtualizadorDados(pasta, baixar=bc, simultaneos=3).atualizar()
ok(len(rel.series) == TOTAL_SERIES == 23 and rel.atualizadas == 23 and not rel.mantidas, f"23 séries atualizadas ({rel.resumo()})")
ok(len(set(bc.chamadas)) == 23, "23 downloads: nenhum a mais (não há descoberta quando os códigos já bastam)")
ok(not (pasta / "fontes_sgs.json").exists() and not list(pasta.rglob("*.tmp")), "nenhum mapa criado e nenhum arquivo temporário sobrando")
ok(all(r.codigo == verdadeiros.get((r.tipo, r.arquivo), r.codigo) for r in rel.series), "cada série foi baixada do código certo")
novos = FonteDados(pasta).carregar_tudo()
ok(novos.groupby(["tipo", "categoria"])["data"].max().eq(pd.Timestamp("2026-10-01")).all(), "as 19 séries de dívida ganharam o mês novo (out/2026) e carregam normalmente")
ex_novas = FonteDados(pasta).carregar_extras()
ok(set(ex_novas) == set(EXTRAS) and all(len(df) > 0 for df in ex_novas.values()), "as 4 séries extras também carregam depois de atualizadas")

print("== 2. segunda execução: tudo em dia")
bc2 = BCFalso(remoto); rel2 = AtualizadorDados(pasta, baixar=bc2).atualizar()
ok(rel2.em_dia == 23 and rel2.atualizadas == 0 and rel2.tudo_certo, "23 'em dia' (nada regravado)")

print("== 3. descoberta: com só 5 códigos fixados, acha os outros 14 comparando com o histórico")
pasta3 = copia_dos_dados(); bc3 = BCFalso(remoto)
with com_config(CODIGOS_SGS=MINIMOS):
    rel3 = AtualizadorDados(pasta3, baixar=bc3, simultaneos=3).atualizar()
    mapa = json.loads((pasta3 / "fontes_sgs.json").read_text(encoding="utf-8"))
    descobertos = {(t, a): c for t, d in mapa.items() for a, c in d.items()}
    ok(len(descobertos) == 14 and all(verdadeiros[k] == c for k, c in descobertos.items()), "14 códigos descobertos, TODOS iguais aos que você fixou à mão (nenhuma série trocada)")
    ok(rel3.atualizadas == 23, "e as 23 séries foram atualizadas")
    bc3b = BCFalso(remoto); rel3b = AtualizadorDados(pasta3, baixar=bc3b).atualizar()
    ok(len(set(bc3b.chamadas)) == 23 and rel3b.em_dia == 23, "na execução seguinte usa o mapa guardado: 23 downloads, sem nova descoberta")

print("== 4. sem internet: nada é alterado")
pasta4 = copia_dos_dados(); antes = arquivos_bytes(pasta4)
def sem_rede(codigo): raise OSError("Network is unreachable")
rel4 = AtualizadorDados(pasta4, baixar=sem_rede).atualizar()
ok(rel4.sem_conexao and len(rel4.mantidas) == 23 and "Sem conexão" in rel4.resumo(), f"relatório: {rel4.resumo()}")
ok(arquivos_bytes(pasta4) == antes and not (pasta4 / "fontes_sgs.json").exists(), "arquivos idênticos byte a byte (inclusive os extras); nenhum mapa criado")

chamadas_sem_rede = []
def sem_rede_contando(codigo): chamadas_sem_rede.append(codigo); raise OSError("Connection timed out")
rel4b = AtualizadorDados(copia_dos_dados(), baixar=sem_rede_contando, simultaneos=4).atualizar()
ok(rel4b.sem_conexao and len(chamadas_sem_rede) == 4 and len(rel4b.series) == 23,
   f"rede que pendura: desiste depois do 1º lote ({len(chamadas_sem_rede)} tentativas, e não 23), e o relatório cobre as 23 séries")

print("== 5. código fixado devolvendo a série ERRADA: o arquivo não pode ser sobrescrito")
pasta5 = copia_dos_dados(); antes = arquivos_bytes(pasta5)
errado = dict(remoto); errado[4513] = remoto[4504]      # o consolidado passa a vir como se fosse o federal
rel5 = AtualizadorDados(pasta5, baixar=BCFalso(errado)).atualizar()
ok(arquivos_bytes(pasta5)[arq_consolidado] == antes[arq_consolidado], "consolidado % intacto (o federal NÃO foi gravado no lugar dele)")
r = next(x for x in rel5.series if x.arquivo.endswith("setor_publico_consolidado.csv"))
ok(r.status == STATUS_MANTIDA, f"relatório: mantida ({r.detalhe[:80]}...)")
ok(rel5.atualizadas == 22, "as outras 22 seguem atualizadas")

print("== 6. série truncada, conteúdo estranho e falhas parciais")
pasta6 = copia_dos_dados(); antes = arquivos_bytes(pasta6)
linhas = remoto[4513].splitlines(); curta = dict(remoto); curta[4513] = "\n".join([linhas[0]] + linhas[-60:]) + "\n"
rel6 = AtualizadorDados(pasta6, baixar=BCFalso(curta)).atualizar()
ok(arquivos_bytes(pasta6)[arq_consolidado] == antes[arq_consolidado], "série de 60 meses não substitui a de 298")
ok("cobre só" in next(x for x in rel6.series if x.arquivo.endswith("setor_publico_consolidado.csv")).detalhe, "motivo registrado: cobertura insuficiente")
pasta6b = copia_dos_dados(); antes = arquivos_bytes(pasta6b)
estranho = dict(remoto); estranho[4504] = '{"error": "serie nao encontrada"}'
bc6 = BCFalso(estranho); bc6.falhas[4505] = ErroDownload("HTTP 500")
rel6b = AtualizadorDados(pasta6b, baixar=bc6).atualizar()
ok({"divida_liquida_governo_federal.csv", "divida_liquida_banco.csv"} <= {x.arquivo for x in rel6b.mantidas}, "JSON de erro e HTTP 500: só essas duas ficam como estavam")
ok(arquivos_bytes(pasta6b)["porcentagem/divida_liquida_governo_federal.csv"] == antes["porcentagem/divida_liquida_governo_federal.csv"] and not rel6b.sem_conexao and rel6b.atualizadas == 21,
   "federal intacto; as outras 21 seguem; não é 'sem conexão'")

print("== 7. duas séries idênticas escondidas (na descoberta): ambiguidade não é adivinhada")
pasta7 = copia_dos_dados()
alvo = ("porcentagem", "divida_liquida_empresas_estatais.csv")
isca = next(c for c in POOLS_SGS["porcentagem"] if c in iscas)
gemeo = dict(remoto); gemeo[isca] = remoto[verdadeiros[alvo]]
with com_config(CODIGOS_SGS=MINIMOS):
    rel7 = AtualizadorDados(pasta7, baixar=BCFalso(gemeo)).atualizar()
r = next(x for x in rel7.series if x.arquivo == alvo[1])
ok(r.status == STATUS_MANTIDA and "inequivocamente" in r.detalhe, "série com gêmea exata: mantida, sem chute")
ok(rel7.atualizadas == 22, "as outras 22 não são afetadas")

print("== 8. séries extras: código errado do IPCA, arquivo ausente e revisão do mês corrente")
pasta8 = copia_dos_dados(); antes = arquivos_bytes(pasta8)
ipca_local = FonteDados(PASTA_DADOS).carregar_extra("ipca")
parecida = ipca_local.copy(); parecida["valor"] += [0.03 if i % 2 else -0.03 for i in range(len(parecida))]   # "outro índice": difere ±0,03
remoto8 = dict(remoto); remoto8[99001] = csv_texto(parecida)
with com_config(EXTRAS={**EXTRAS, "ipca": dataclasses.replace(EXTRAS["ipca"], codigo_sgs=99001)}):
    rel8 = AtualizadorDados(pasta8, baixar=BCFalso(remoto8)).atualizar()
ri = next(x for x in rel8.series if x.arquivo == EXTRAS["ipca"].arquivo)
ok(ri.status == STATUS_MANTIDA and "descartada" in ri.detalhe, f"IPCA com código errado (série parecida): rejeitado ({ri.detalhe[:70]}...)")
ok(arquivos_bytes(pasta8)[f"{PASTA_EXTRA}/{EXTRAS['ipca'].arquivo}"] == antes[f"{PASTA_EXTRA}/{EXTRAS['ipca'].arquivo}"], "arquivo do IPCA intacto")
ok(AtualizadorDados._comparar(ipca_local, parecida, 0.05, 0.03)[0] and not AtualizadorDados._comparar(ipca_local, parecida, 0.011, 0.0)[0],
   "a tolerância folgada aceitaria essa série parecida; a estrita do IPCA (0,011) não: por isso ela existe")
pasta8b = copia_dos_dados(); (pasta8b / PASTA_EXTRA / EXTRAS["ipca"].arquivo).unlink()
rel8b = AtualizadorDados(pasta8b, baixar=BCFalso(remoto)).atualizar()
ri = next(x for x in rel8b.series if x.arquivo == EXTRAS["ipca"].arquivo)
ok(ri.status == STATUS_MANTIDA and "não pôde ser conferida" in ri.detalhe and not (pasta8b / PASTA_EXTRA / EXTRAS["ipca"].arquivo).exists(),
   "sem arquivo local, o IPCA não é criado (não há com o que conferir o código)")
ok(rel8b.atualizadas == 22, "as outras 22 seguem")
selic_local = FonteDados(PASTA_DADOS).carregar_extra("selic")
ok(selic_local["data"].max() >= pd.Timestamp("2026-11-01"), "a Selic local tem o mês corrente (parcial)")
ok(next(x for x in rel.series if x.arquivo == EXTRAS["selic"].arquivo).status == STATUS_ATUALIZADA, "Selic aceita mesmo com o último mês revisado (1 ponto em 484 fora da tolerância)")

print("== 9. a descoberta não troca séries (15 sorteios de códigos e iscas)")
trocadas = nao_resolvidas = 0
with com_config(CODIGOS_SGS=MINIMOS):
    for semente in range(15):
        remoto_s, verd_s, _ = montar_remoto(semente)
        pasta_s = copia_dos_dados()
        rel_s = AtualizadorDados(pasta_s, baixar=BCFalso(remoto_s), simultaneos=3).atualizar()
        for r in rel_s.series:
            if r.tipo == "extra":
                continue
            if r.status == STATUS_MANTIDA:
                nao_resolvidas += 1
            elif r.codigo != verd_s[(r.tipo, r.arquivo)]:
                trocadas += 1
ok(trocadas == 0, f"15 sorteios x 19 séries: 0 trocadas ({15 * 19 - nao_resolvidas} corretas, {nao_resolvidas} mantidas por ambiguidade)")

print("== 10. comparação: revisão pequena passa; série diferente, não")
comparar = AtualizadorDados._comparar
base = pd.DataFrame({"data": pd.date_range("2002-01-01", periods=120, freq="MS"), "valor": [50 + i * 0.1 for i in range(120)]})
rev = base.copy(); rev["valor"] *= 1.01
ok(comparar(base, rev, 0.05)[0], "revisão de 1% em todos os pontos: aceita")
rev2 = base.copy(); rev2.loc[100:, "valor"] += 0.8
ok(comparar(base, rev2, 0.05)[0], "20 pontos recentes diferentes (dentro de 3%): aceita")
diferente = base.copy(); diferente["valor"] *= 0.5
ok(not comparar(base, diferente, 0.05)[0], "série com metade do valor: rejeitada")
ok(not comparar(base, base.iloc[20:], 0.05)[0], "série que perdeu 20 meses do início: rejeitada")
ok(comparar(base.iloc[0:0], diferente, 0.05)[0], "sem arquivo local, a comparação aceita (as extras é que exigem o arquivo)")

print("== 11. a descoberta recusa 'quase iguais': impostor (federal + série pequena) x série verdadeira revisada")
from config import LIMITE_IGUALDADE_SGS, MIN_FRACAO_EXATA
fonte_ = FonteDados(PASTA_DADOS)
fed = fonte_.carregar_arquivo(PASTA_DADOS / "porcentagem" / "divida_liquida_governo_federal.csv")
peq = fonte_.carregar_arquivo(PASTA_DADOS / "porcentagem" / "divida_liquida_empresas_estatais_municipais.csv")
impostor = fed.merge(peq, on="data", suffixes=("", "_b")); impostor["valor"] += impostor["valor_b"]; impostor = impostor[["data", "valor"]]
verdadeira = pd.read_csv(__import__("io").StringIO(remoto[CODIGOS_SGS["porcentagem"]["divida_liquida_governo_federal.csv"]]), sep=";", decimal=",")
verdadeira["data"] = pd.to_datetime(verdadeira["data"], format="%d/%m/%Y")
lim = LIMITE_IGUALDADE_SGS["porcentagem"]
f_imp, f_ver = AtualizadorDados._fracao_exata(fed, impostor, lim), AtualizadorDados._fracao_exata(fed, verdadeira, lim)
ok(AtualizadorDados._comparar(fed, impostor, 0.05)[0], "o impostor PASSARIA na validação por tolerância (por isso a descoberta precisa de mais rigor)")
ok(f_imp < MIN_FRACAO_EXATA, f"impostor: só {f_imp:.0%} dos pontos idênticos (< {MIN_FRACAO_EXATA:.0%}): recusado pela descoberta")
ok(f_ver >= MIN_FRACAO_EXATA, f"série verdadeira, mesmo com revisões e mês novo: {f_ver:.0%} idênticos (≥ {MIN_FRACAO_EXATA:.0%}): aceita")

print("\nTODOS OS TESTES DO ATUALIZADOR PASSARAM")
