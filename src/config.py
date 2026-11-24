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
