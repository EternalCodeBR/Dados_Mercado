import datetime

from codigo.aquisicao.moedas import SGS_POR_COD_SERIE, linhas_moeda


def test_mapa_sgs_bate_com_schema():
    assert SGS_POR_COD_SERIE == {4: 1, 5: 21619, 8: 21625, 9: 21635, 11: 21621}


def test_linhas_moeda_propria_data_so_publicadas():
    serie = {
        datetime.date(2026, 6, 16): 1.0,
        datetime.date(2026, 6, 17): 1.1,
        datetime.date(2026, 6, 18): 1.2,
    }
    assert linhas_moeda(4, serie) == [
        {"COD_SERIE": 4, "DATA": "2026-06-16", "VALOR": 1.0},
        {"COD_SERIE": 4, "DATA": "2026-06-17", "VALOR": 1.1},
        {"COD_SERIE": 4, "DATA": "2026-06-18", "VALOR": 1.2},
    ]


def test_linhas_moeda_corta_d0():
    # hoje=19; corte=18 (D-1). O 19 (D-0) não entra; o 18 fica com o PRÓPRIO valor.
    serie = {datetime.date(2026, 6, 18): 1.10, datetime.date(2026, 6, 19): 1.20}
    linhas = linhas_moeda(4, serie, corte=datetime.date(2026, 6, 18))
    assert linhas == [{"COD_SERIE": 4, "DATA": "2026-06-18", "VALOR": 1.10}]
