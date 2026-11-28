"""Configuração central do projeto.

Tudo o que os outros módulos precisam saber sobre *onde* estão os dados e
*o que* cada arquivo representa fica aqui, para não ser repetido (e
divergir) em vários lugares.
"""
from dataclasses import dataclass
from pathlib import Path

# --- Caminhos (relativos a este arquivo, então funcionam de qualquer pasta) ---
RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"

# --- Tipos de medida (cada um corresponde a uma subpasta de dados/) ---
TIPO_PORCENTAGEM = "porcentagem"
TIPO_REAL = "real"

# Rótulos exibidos na interface (unidades: % do PIB e R$ em milhões).
ROTULOS_TIPO = {
    TIPO_PORCENTAGEM: "Porcentagem (% do PIB)",
    TIPO_REAL: "Valores em R$ (milhões)",
}


@dataclass(frozen=True)
class Unidade:
    """Como exibir cada medida nos gráficos.

    Os CSVs em R$ estão em milhões; para os gráficos ficarem legíveis, os
    níveis (saldo da dívida) são mostrados em trilhões e as variações em bilhões.
    """
    rotulo_nivel: str
    fator_nivel: float
    rotulo_delta: str
    fator_delta: float


UNIDADES = {
    TIPO_PORCENTAGEM: Unidade("% do PIB", 1.0, "p.p. do PIB", 1.0),
    TIPO_REAL: Unidade("R$ trilhões", 1e-6, "R$ bilhões", 1e-3),
}


@dataclass(frozen=True)
class Serie:
    """Descreve uma série (um arquivo CSV).

    categoria: nome legível, igual nas duas pastas para permitir comparação.
    padrao:    se a categoria já vem marcada no filtro do dashboard.
    """
    categoria: str
    padrao: bool = False


# Categoria usada como referência nos KPIs (o total da dívida do setor público).
SERIE_PRINCIPAL = "Setor Público Consolidado"

# Relação entre as séries (verificada nos dados, diferença máxima de 0,02 p.p.):
#   Setor Público Consolidado = Governo Geral + Banco Central + Empresas Estatais
#   Governo Geral             = Federal + Estaduais + Municipais
#   Empresas Estatais         = Federais + Estaduais + Municipais
# Ou seja, os totais e as partes se sobrepõem: somar tudo contaria a dívida duas vezes.
# A ordem abaixo é a ordem em que as categorias aparecem nos filtros.
SERIES = {
    TIPO_PORCENTAGEM: {
        "divida_liquida_setor_publico_consolidado.csv": Serie("Setor Público Consolidado", True),
        "divida_liquida_geral.csv": Serie("Governo Geral"),
        "divida_liquida_governo_federal.csv": Serie("Governo Federal", True),
        "divida_liquida_governo_estaduais.csv": Serie("Governos Estaduais", True),
        "divida_liquida_governo_municipal.csv": Serie("Governos Municipais", True),
        "divida_liquida_banco.csv": Serie("Banco Central", True),
        "divida_liquida_empresas_estatais.csv": Serie("Empresas Estatais", True),
        "divida_liquida_empresas_estatais_federais.csv": Serie("Empresas Estatais Federais"),
        "divida_liquida_empresas_estatais_estaduais.csv": Serie("Empresas Estatais Estaduais"),
        "divida_liquida_empresas_estatais_municipais.csv": Serie("Empresas Estatais Municipais"),
    },
    TIPO_REAL: {
        "divida_liquida_consolidada_real.csv": Serie("Setor Público Consolidado", True),
        "divida_liquida_governos_federal_real.csv": Serie("Governo Federal", True),
        "divida_liquida_governos_estaduais_real.csv": Serie("Governos Estaduais", True),
        "divida_liquida_governos_municipais_real.csv": Serie("Governos Municipais", True),
        "divida_liquida_banco_central_real.csv": Serie("Banco Central", True),
        "divida_liquida_empresa_estatais_real.csv": Serie("Empresas Estatais", True),
        "divida_liquida_empresa_estatais_federais_real.csv": Serie("Empresas Estatais Federais"),
        "divida_liquida_empresa_estatais_estaduais_real.csv": Serie("Empresas Estatais Estaduais"),
        "divida_liquida_empresa_estatais_municipais_real.csv": Serie("Empresas Estatais Municipais"),
    },
}


# --- Estrutura da dívida usada nas análises ---------------------------------
# Os cinco blocos de primeiro nível: somados, formam o Setor Público Consolidado.
COMPONENTES = ["Governo Federal", "Governos Estaduais", "Governos Municipais",
               "Empresas Estatais", "Banco Central"]
ESTATAIS_DETALHE = ["Empresas Estatais Federais", "Empresas Estatais Estaduais",
                    "Empresas Estatais Municipais"]
GOVERNOS = ["Governo Federal", "Governos Estaduais", "Governos Municipais"]

ROTULOS_CURTOS = {
    "Setor Público Consolidado": "Total",
    "Governo Federal": "Federal",
    "Governos Estaduais": "Estados",
    "Governos Municipais": "Municípios",
    "Empresas Estatais": "Estatais",
    "Banco Central": "Banco Central",
    "Empresas Estatais Federais": "Estatais federais",
    "Empresas Estatais Estaduais": "Estatais estaduais",
    "Empresas Estatais Municipais": "Estatais municipais",
}

# Eventos de CONTEXTO desenhados como faixas nos gráficos de linha. Não fazem parte
# dos CSVs: são marcos amplamente conhecidos, apenas para situar o leitor no tempo.
EVENTOS = [
    ("2008-09-01", "2009-06-01", "Crise global"),
    ("2014-04-01", "2016-12-01", "Recessão"),
    ("2020-03-01", "2020-12-01", "Pandemia"),
]


# --- Dado em foco ---------------------------------------------------------
# "Geral" usa todos os dados (o consolidado e todos os setores). Cada setor, quando
# escolhido, mostra apenas uma parte dos dados: o painel inteiro passa a falar dele.
GERAL = "Geral"
FOCOS = [GERAL] + COMPONENTES


def serie_do_foco(foco: str) -> str:
    """Série usada nos indicadores: o total para 'Geral', ou o próprio setor."""
    return SERIE_PRINCIPAL if foco == GERAL else foco


# --- Atualização automática (Banco Central, SGS) ---------------------------------
# Endereço oficial de download publicado no Portal de Dados Abertos do BCB; devolve o
# histórico completo no mesmo formato dos CSVs do projeto ("data";"valor", vírgula decimal).
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=csv"

# Códigos SGS das séries de dívida líquida por setor (um por arquivo). Se algum código estiver errado,
# o atualizador percebe (os dados baixados não batem com o histórico do arquivo), mantém o arquivo como
# está e tenta DESCOBRIR o código certo entre os candidatos de POOLS_SGS; o achado vai para
# dados/fontes_sgs.json.
CODIGOS_SGS = {
    TIPO_PORCENTAGEM: {
        "divida_liquida_setor_publico_consolidado.csv": 4513,
        "divida_liquida_governo_federal.csv": 4504,
        "divida_liquida_banco.csv": 4505,
        "divida_liquida_governo_estaduais.csv": 4507,
        "divida_liquida_geral.csv": 4536,
        "divida_liquida_governo_municipal.csv": 4508,
        "divida_liquida_empresas_estatais.csv": 4509,
        "divida_liquida_empresas_estatais_federais.csv": 4510,
        "divida_liquida_empresas_estatais_estaduais.csv": 4511,
        "divida_liquida_empresas_estatais_municipais.csv": 4512,
    },
    TIPO_REAL: {
        "divida_liquida_consolidada_real.csv": 4478,
        "divida_liquida_governos_federal_real.csv": 4469,
        "divida_liquida_governos_estaduais_real.csv": 4472,
        "divida_liquida_governos_municipais_real.csv": 4473,
        "divida_liquida_banco_central_real.csv": 4470,
        "divida_liquida_empresa_estatais_real.csv": 4474,
        "divida_liquida_empresa_estatais_federais_real.csv": 4475,
        "divida_liquida_empresa_estatais_estaduais_real.csv": 4476,
        "divida_liquida_empresa_estatais_municipais_real.csv": 4477
    },
}

# Candidatos para a descoberta (só usados se um código acima falhar na validação):
# % do PIB: 4503 a 4536; saldos em R$ milhões: 4469 a 4477.
POOLS_SGS = {
    TIPO_PORCENTAGEM: range(4503, 4537),
    TIPO_REAL: range(4469, 4478),
}

# Diferença tolerada ao comparar o histórico baixado com o local. O BCB revisa valores passados
# (ex.: o último mês), então a comparação não exige igualdade exata: vale o maior entre o piso
# abaixo e 3% do valor. O piso está na unidade da medida (p.p. do PIB ou R$ milhões).
PISO_TOLERANCIA_SGS = {TIPO_PORCENTAGEM: 0.05, TIPO_REAL: 100.0}

# A DESCOBERTA de códigos (que escolhe séries sem ninguém conferir) é mais rigorosa que a validação de
# um código já fixado: só aceita um candidato se pelo menos MIN_FRACAO_EXATA dos pontos forem IDÊNTICOS
# ao arquivo atual (diferença de até LIMITE_IGUALDADE_SGS, que é o arredondamento de duas casas). A série
# verdadeira é praticamente idêntica ao histórico; uma série "parecida" (soma com outra, por exemplo) não é.
LIMITE_IGUALDADE_SGS = {TIPO_PORCENTAGEM: 0.0051, TIPO_REAL: 0.51}
MIN_FRACAO_EXATA = 0.80


# --- Séries EXTRAS: inflação, juros e dívida bruta ---------------------------------
PASTA_EXTRA = "extra"   # dados/extra/


@dataclass(frozen=True)
class Extra:
    """Uma série fora da dívida líquida por setor.

    codigo_sgs:   código no SGS do Banco Central (o atualizador baixa e valida contra o arquivo local).
    piso/relativa: tolerância ao comparar o baixado com o arquivo local (veja PISO_TOLERANCIA_SGS).
                  Séries que o BCB/IBGE não revisam (IPCA, Selic) usam tolerância mínima, para que
                  uma série parecida (outro índice de preços, por exemplo) nunca seja aceita no lugar.
    """
    arquivo: str
    nome: str
    unidade: str
    codigo_sgs: int
    piso: float
    relativa: float


EXTRAS = {
    # IPCA do IBGE. O arquivo original (IPCA.csv) está no formato largo do IBGE; o painel lê a versão
    # convertida (python src/conversor_ibge.py). O código 433 NÃO foi confirmado no portal: a validação
    # estrita contra o histórico do IBGE protege o arquivo caso o código esteja errado.
    "ipca": Extra("ipca_variacao_mensal.csv", "IPCA (variação mensal)", "% a.m.", 433, 0.011, 0.0),
    "selic": Extra("selic_acumulada_no_mes.csv", "Selic acumulada no mês", "% a.m.", 4390, 0.011, 0.0),
    "dbgg_atual": Extra("divida_bruta_governo_geral_apartir_2008.csv",
                        "Dívida bruta do governo geral (metodologia a partir de 2008)", "% do PIB", 13762, 0.05, 0.03),
    "dbgg_antiga": Extra("divida_bruta_governo_geral_ate_2007.csv",
                         "Dívida bruta do governo geral (metodologia até 2007)", "% do PIB", 4537, 0.05, 0.03),
}
