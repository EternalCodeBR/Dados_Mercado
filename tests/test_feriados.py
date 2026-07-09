import datetime

from codigo.feriados import (
    dia_util_anterior,
    dias_uteis_entre,
    eh_dia_util,
    eh_feriado,
    feriados_b3,
)


def test_feriados_conhecidos_2026():
    assert eh_feriado(datetime.date(2026, 1, 1))   # Confraternização Universal
    assert eh_feriado(datetime.date(2026, 2, 16))  # Carnaval


def test_dia_util_vs_fim_de_semana_e_feriado():
    assert eh_dia_util(datetime.date(2026, 1, 2))       # sexta, dia útil
    assert not eh_dia_util(datetime.date(2026, 1, 3))   # sábado
    assert not eh_dia_util(datetime.date(2026, 1, 1))   # feriado


def test_feriados_b3_intervalo():
    fs = feriados_b3(2026, 2026)
    assert datetime.date(2026, 1, 1) in fs
    assert len(fs) >= 10


def test_dias_uteis_entre_pula_fds_e_feriado():
    # 01/01 (feriado) a 05/01/2026: úteis = 02 (sex), 05 (seg)
    uteis = dias_uteis_entre(datetime.date(2026, 1, 1), datetime.date(2026, 1, 5))
    assert uteis == [datetime.date(2026, 1, 2), datetime.date(2026, 1, 5)]


def test_dia_util_anterior():
    # segunda 05/01 -> sexta 02/01
    assert dia_util_anterior(datetime.date(2026, 1, 5)) == datetime.date(2026, 1, 2)
    # anterior a 02/01 (sexta): pula 01/01 (feriado) e o fim de semana
    r = dia_util_anterior(datetime.date(2026, 1, 2))
    assert eh_dia_util(r) and r < datetime.date(2026, 1, 1)
