"""Atualização dos CSVs a partir do Banco Central (SGS), a cada inicialização do painel.

Regra de ouro: NUNCA piorar os dados. O arquivo local só é substituído quando o que foi baixado
passa em duas verificações contra o histórico que já existe:
  1. cobertura: contém (quase) todas as datas do arquivo atual (senão pode estar truncado ou ser outra série);
  2. valores: 95% dos pontos coincidem dentro de uma tolerância (o BCB revisa valores passados).
Qualquer falha (sem internet, série inválida, arquivo estranho) mantém o arquivo local intacto
e fica registrada no relatório, que o painel mostra na barra lateral.

Descoberta de códigos. Só alguns códigos SGS foram confirmados no portal do BCB (config.CODIGOS_SGS).
Para os demais arquivos, o atualizador baixa as séries candidatas (config.POOLS_SGS) e escolhe, para
cada arquivo, a que reproduz o seu histórico; uma escolha só é aceita se for inequívoca. O resultado
é guardado em dados/fontes_sgs.json, e nas próximas execuções só se baixa o necessário.
"""
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config import (CODIGOS_SGS, PASTA_DADOS, PISO_TOLERANCIA_SGS, POOLS_SGS, SERIES, URL_SGS)
from fonte_dados import FonteDados
from indicador import formatar_mes

log = logging.getLogger(__name__)

STATUS_ATUALIZADA = "atualizada"   # arquivo novo gravado
STATUS_EM_DIA = "em_dia"           # baixado e idêntico ao que já existia
STATUS_MANTIDA = "mantida"         # não foi possível atualizar; arquivo local intacto


class ErroDownload(Exception):
    """Falha ao obter a série. ``rede`` indica problema de conexão (e não de conteúdo)."""

    def __init__(self, mensagem: str, rede: bool = False):
        super().__init__(mensagem)
        self.rede = rede


@dataclass
class ResultadoSerie:
    tipo: str
    arquivo: str
    categoria: str
    status: str
    detalhe: str = ""
    codigo: int | None = None
    ultima_data: pd.Timestamp | None = None


@dataclass
class RelatorioAtualizacao:
    quando: datetime
    series: list = field(default_factory=list)
    sem_conexao: bool = False

    def _contar(self, status: str) -> int:
        return sum(1 for s in self.series if s.status == status)

    @property
    def atualizadas(self) -> int:
        return self._contar(STATUS_ATUALIZADA)

    @property
    def em_dia(self) -> int:
        return self._contar(STATUS_EM_DIA)

    @property
    def mantidas(self) -> list:
        return [s for s in self.series if s.status == STATUS_MANTIDA]

    @property
    def tudo_certo(self) -> bool:
        return bool(self.series) and not self.mantidas

    def resumo(self) -> str:
        quando = self.quando.strftime("%d/%m/%Y %H:%M")
        if self.sem_conexao:
            return f"Sem conexão com o Banco Central ({quando}). Usando os dados salvos."
        verificadas = len(self.series) - len(self.mantidas)
        return (f"{verificadas} de {len(self.series)} séries verificadas no Banco Central em {quando} "
                f"({self.atualizadas} com dados novos).")


class AtualizadorDados:
    def __init__(self, pasta_dados=PASTA_DADOS, baixar=None, timeout: float = 10,
                 simultaneos: int = 4, tentativas: int = 2):
        self.pasta = Path(pasta_dados)
        self.timeout, self.simultaneos, self.tentativas = timeout, simultaneos, tentativas
        self._baixar_texto = baixar or self._baixar_http   # injetável (os testes não usam a internet)
        self._cache: dict = {}                              # código -> (texto, DataFrame) | ErroDownload
        self._arquivo_mapa = self.pasta / "fontes_sgs.json"
        self._fonte = FonteDados(self.pasta)

    # ============================================================== download
    def _baixar_http(self, codigo: int) -> str:
        pedido = urllib.request.Request(URL_SGS.format(codigo=codigo),
                                        headers={"User-Agent": "Mozilla/5.0 (painel-divida-publica)"})
        ultimo = None
        for tentativa in range(self.tentativas):
            try:
                with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                    return resposta.read().decode("utf-8-sig")
            except urllib.error.HTTPError as erro:
                if erro.code not in (429, 500, 502, 503, 504):
                    raise ErroDownload(f"HTTP {erro.code}") from erro      # código inexistente etc.: sem repetir
                ultimo = ErroDownload(f"HTTP {erro.code}")
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as erro:
                ultimo = ErroDownload(f"sem conexão ({erro})", rede=True)
            if tentativa + 1 < self.tentativas:
                time.sleep(1.0 * (tentativa + 1))
        raise ultimo

    @staticmethod
    def _interpretar(texto: str) -> pd.DataFrame:
        """CSV do BCB -> DataFrame [data, valor]. Levanta ErroDownload se o conteúdo for inválido."""
        try:
            df = pd.read_csv(io.StringIO(texto), sep=";", decimal=",")
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
            df["valor"] = pd.to_numeric(df["valor"])
        except (ValueError, KeyError) as erro:   # CSV vazio, JSON de erro, coluna ausente, número inválido...
            raise ErroDownload(f"conteúdo inesperado ({type(erro).__name__})") from erro
        if len(df) < 12 or df["valor"].isna().any() or df["data"].duplicated().any():
            raise ErroDownload("série vazia, curta demais ou inconsistente")
        return df[["data", "valor"]].sort_values("data").reset_index(drop=True)

    def _obter(self, codigo: int):
        """Texto e DataFrame da série (com cache nesta execução). Levanta ErroDownload."""
        if codigo not in self._cache:
            try:
                texto = self._baixar_texto(codigo)
                self._cache[codigo] = (texto, self._interpretar(texto))
            except ErroDownload as erro:
                self._cache[codigo] = erro
            except Exception as erro:  # a função injetada (ou algo inesperado) pode lançar qualquer coisa
                self._cache[codigo] = ErroDownload(f"{type(erro).__name__}: {erro}", rede=isinstance(erro, OSError))
        resultado = self._cache[codigo]
        if isinstance(resultado, ErroDownload):
            raise resultado
        return resultado

    def _pre_baixar(self, codigos):
        """Baixa vários códigos ao mesmo tempo, só para aquecer o cache."""
        pendentes = [c for c in dict.fromkeys(codigos) if c not in self._cache]
        with ThreadPoolExecutor(max_workers=self.simultaneos) as pool:
            list(pool.map(lambda c: self._tentar(c), pendentes))

    def _tentar(self, codigo):
        try:
            return self._obter(codigo)
        except ErroDownload:
            return None

    # ========================================================== comparação
    @staticmethod
    def _comparar(tipo: str, local: pd.DataFrame, remoto: pd.DataFrame):
        """(compatível?, erro médio, motivo). Sem arquivo local, não há o que comparar: aceita."""
        if local.empty:
            return True, 0.0, ""
        juntos = local.merge(remoto, on="data", how="left", suffixes=("_local", "_remoto"))
        cobertura = juntos["valor_remoto"].notna().mean()
        if cobertura < 0.99:
            return False, np.inf, f"cobre só {cobertura:.0%} das datas do arquivo atual"
        juntos = juntos.dropna()
        diferenca = (juntos["valor_remoto"] - juntos["valor_local"]).abs()
        tolerancia = np.maximum(PISO_TOLERANCIA_SGS[tipo], 0.03 * juntos["valor_local"].abs())
        dentro = float((diferenca <= tolerancia).mean())
        if dentro < 0.95:
            return False, float(diferenca.mean()), f"só {dentro:.0%} dos valores coincidem com o arquivo atual"
        return True, float(diferenca.mean()), ""

    # =========================================================== descoberta
    def _descobrir(self, tipo: str, pendentes: dict, ocupados: set) -> dict:
        """Para cada arquivo pendente (nome -> DataFrame local), acha o código cujo histórico o reproduz.

        Devolve {arquivo: código} só das escolhas inequívocas: o melhor candidato precisa ser claramente
        mais parecido que o segundo (senão, duas séries quase iguais poderiam ser trocadas).
        """
        pool = [c for c in POOLS_SGS[tipo] if c not in ocupados]
        self._pre_baixar(pool)
        remotos = {c: self._tentar(c) for c in pool}
        remotos = {c: r[1] for c, r in remotos.items() if r is not None}

        candidatos = {}
        for arquivo, local in pendentes.items():
            if local.empty:
                continue
            validos = sorted((erro, c) for c, rem in remotos.items()
                             for ok, erro, _ in [self._comparar(tipo, local, rem)] if ok)
            if validos:
                candidatos[arquivo] = validos

        escolhidos, usados = {}, set()
        for arquivo, validos in sorted(candidatos.items(), key=lambda kv: kv[1][0][0]):
            livres = [(erro, c) for erro, c in validos if c not in usados]
            if not livres:
                continue
            if len(livres) > 1 and livres[1][0] <= 3 * livres[0][0] + 1e-9:
                continue  # ambíguo: há outra série quase tão parecida
            escolhidos[arquivo] = livres[0][1]
            usados.add(livres[0][1])
        return escolhidos

    # ============================================================== mapa
    def _ler_mapa(self) -> dict:
        try:
            bruto = json.loads(self._arquivo_mapa.read_text(encoding="utf-8"))
            return {t: {a: int(c) for a, c in d.items()} for t, d in bruto.items()}
        except (OSError, ValueError, AttributeError):
            return {}

    def _salvar_mapa(self, mapa: dict):
        try:
            self._gravar(self._arquivo_mapa, json.dumps(mapa, indent=2, ensure_ascii=False) + "\n")
        except OSError as erro:
            log.warning("Não foi possível salvar %s: %r", self._arquivo_mapa.name, erro)

    @staticmethod
    def _gravar(caminho: Path, texto: str):
        """Gravação atômica: escreve num arquivo temporário e troca, para nunca deixar um CSV pela metade."""
        temporario = caminho.with_suffix(caminho.suffix + ".tmp")
        temporario.write_text(texto, encoding="utf-8")
        os.replace(temporario, caminho)

    # ============================================================ principal
    def atualizar(self) -> RelatorioAtualizacao:
        """Atualiza todos os CSVs possíveis e devolve o relatório. Nunca levanta exceção de rede."""
        relatorio = RelatorioAtualizacao(quando=datetime.now())
        mapa_salvo = self._ler_mapa()
        mapa = {t: {**mapa_salvo.get(t, {}), **CODIGOS_SGS.get(t, {})} for t in SERIES}  # os confirmados prevalecem
        locais = {(t, a): self._fonte.carregar_arquivo(self.pasta / t / a) for t in SERIES for a in SERIES[t]}

        self._pre_baixar(c for t in SERIES for c in mapa[t].values())
        if self._cache and all(isinstance(v, ErroDownload) and v.rede for v in self._cache.values()):
            # Nenhum download funcionou por falta de conexão: não adianta tentar a descoberta.
            relatorio.sem_conexao = True
            relatorio.series = [ResultadoSerie(t, a, serie.categoria, STATUS_MANTIDA,
                                               "sem conexão com o Banco Central", mapa[t].get(a))
                                for t in SERIES for a, serie in SERIES[t].items()]
            return relatorio
        resultados, pendentes = {}, {t: {} for t in SERIES}

        for tipo in SERIES:
            for arquivo, serie in SERIES[tipo].items():
                codigo = mapa[tipo].get(arquivo)
                motivo = "código ainda não descoberto"
                if codigo is not None:
                    try:
                        resultados[(tipo, arquivo)] = self._aplicar(tipo, arquivo, codigo, locais[(tipo, arquivo)])
                        continue
                    except ErroDownload as erro:
                        motivo = str(erro)
                        if erro.rede:
                            resultados[(tipo, arquivo)] = (STATUS_MANTIDA, codigo, f"sem conexão: {motivo}", None)
                            continue
                    mapa[tipo].pop(arquivo, None)  # código que não bate: será redescoberto
                pendentes[tipo][arquivo] = (locais[(tipo, arquivo)], motivo)

        for tipo in SERIES:
            if not pendentes[tipo]:
                continue
            achados = self._descobrir(tipo, {a: l for a, (l, _) in pendentes[tipo].items()},
                                      ocupados=set(mapa[tipo].values()))
            for arquivo, (local, motivo) in pendentes[tipo].items():
                codigo = achados.get(arquivo)
                if codigo is None:
                    resultados[(tipo, arquivo)] = (
                        STATUS_MANTIDA, None, f"{motivo}; nenhuma série candidata do Banco Central correspondeu "
                                              f"inequivocamente ao arquivo atual", None)
                    continue
                try:
                    resultados[(tipo, arquivo)] = self._aplicar(tipo, arquivo, codigo, local)
                    mapa[tipo][arquivo] = codigo
                except ErroDownload as erro:
                    resultados[(tipo, arquivo)] = (STATUS_MANTIDA, codigo, str(erro), None)

        descobertos = {t: {a: c for a, c in mapa[t].items() if a not in CODIGOS_SGS.get(t, {})} for t in SERIES}
        if descobertos != {t: mapa_salvo.get(t, {}) for t in SERIES} and any(descobertos.values()):
            self._salvar_mapa(descobertos)

        for tipo in SERIES:
            for arquivo, serie in SERIES[tipo].items():
                status, codigo, detalhe, ultima = resultados[(tipo, arquivo)]
                relatorio.series.append(ResultadoSerie(tipo, arquivo, serie.categoria, status, detalhe, codigo, ultima))
        return relatorio

    def _aplicar(self, tipo: str, arquivo: str, codigo: int, local: pd.DataFrame):
        """Baixa, valida contra o arquivo local e grava se houver novidade. Levanta ErroDownload se não servir."""
        texto, remoto = self._obter(codigo)
        compativel, _, motivo = self._comparar(tipo, local, remoto)
        if not compativel:
            raise ErroDownload(f"série {codigo} descartada: {motivo}")
        ultima = remoto["data"].max()
        if not local.empty and local.equals(remoto):
            return STATUS_EM_DIA, codigo, f"em dia até {formatar_mes(ultima)}", ultima
        self._gravar(self.pasta / tipo / arquivo, texto)
        return STATUS_ATUALIZADA, codigo, f"atualizada até {formatar_mes(ultima)}", ultima
