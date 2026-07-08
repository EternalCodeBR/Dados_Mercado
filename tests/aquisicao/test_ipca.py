from codigo.aquisicao.ipca import (
    COD_INDICE_MENSAL_IPCA,
    linhas_indice_mensal,
    parse_valores_mensais,
)

# amostra real do OData (campos VALDATA/VALVALOR)
_VALORES = [
    {"SERCODIGO": "PRECOS12_IPCA12", "VALDATA": "2026-04-01T00:00:00-03:00", "VALVALOR": 7596.09},
    {"SERCODIGO": "PRECOS12_IPCA12", "VALDATA": "2026-05-01T00:00:00-03:00", "VALVALOR": 7640.15},
    {"SERCODIGO": "PRECOS12_IPCA12", "VALDATA": "2026-06-01T00:00:00-03:00", "VALVALOR": None},
]


def test_parse_extrai_ano_mes_valor_e_pula_nulo():
    assert parse_valores_mensais(_VALORES) == [(2026, 4, 7596.09), (2026, 5, 7640.15)]


def test_linhas_indice_mensal_formato_csv():
    parsed = [(2026, 5, 7640.15)]
    assert linhas_indice_mensal(COD_INDICE_MENSAL_IPCA, parsed) == [
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 7640.15}
    ]
