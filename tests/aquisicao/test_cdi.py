import datetime

from codigo.aquisicao.cdi import (
    DIAS_UTEIS_ANO,
    anualizar,
    linhas_cdi,
)


def test_anualiza_bate_com_a_base():
    # par real da base: CDI diário 0,0534% -> fator 1,000534 -> 14,40% a.a. (série 2)
    fator, cdi_aa = anualizar(0.0534)
    assert round(fator, 6) == 1.000534
    assert cdi_aa == 14.4


def test_convencao_252():
    assert DIAS_UTEIS_ANO == 252


def test_linhas_cdi_gera_serie_2_e_3():
    serie = {datetime.date(2026, 6, 17): 0.0534}
    assert linhas_cdi(serie) == [
        {"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4},       # CDI a.a.
        {"COD_SERIE": 3, "DATA": "2026-06-17", "VALOR": 1.000534},   # FATOR diário
    ]
