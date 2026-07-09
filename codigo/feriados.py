"""Calendário de feriados do mercado financeiro brasileiro (B3 / BM&FBOVESPA).

Convenção do projeto (e de todos os projetos): feriados vêm SEMPRE da biblioteca
`holidays`, mercado financeiro **BVMF** (`holidays.financial_holidays("BVMF")`) —
nunca de planilha. Na lib o código válido é "BVMF" (BM&FBOVESPA/B3); "BMF"/"XBMF"
não existem (levantam NotImplementedError).
"""
from __future__ import annotations

import datetime

import holidays

MERCADO = "BVMF"


def feriados_b3(ano_ini: int, ano_fim: int) -> set[datetime.date]:
    """Conjunto de feriados B3/BVMF no intervalo de anos [ano_ini, ano_fim]."""
    anos = range(ano_ini, ano_fim + 1)
    return set(holidays.financial_holidays(MERCADO, years=anos).keys())


def eh_feriado(data: datetime.date) -> bool:
    """True se a data é feriado B3/BVMF."""
    return data in holidays.financial_holidays(MERCADO, years=data.year)


def eh_dia_util(data: datetime.date) -> bool:
    """True se é dia útil de mercado: não é fim de semana nem feriado B3/BVMF."""
    return data.weekday() < 5 and not eh_feriado(data)


def dias_uteis_entre(ini: datetime.date, fim: datetime.date) -> list[datetime.date]:
    """Lista de dias úteis (inclusive) entre ini e fim."""
    dias, d = [], ini
    um_dia = datetime.timedelta(days=1)
    while d <= fim:
        if eh_dia_util(d):
            dias.append(d)
        d += um_dia
    return dias


def dia_util_anterior(data: datetime.date) -> datetime.date:
    """Primeiro dia útil B3/BVMF estritamente anterior a `data`.

    Conceito do calendário brasileiro — usar para CDI / datas de marcação B3.
    Para escolher cotação de MOEDA, não use isto: use a última cotação publicada
    (data-driven), pois cada moeda tem o seu próprio feriado.
    """
    d = data - datetime.timedelta(days=1)
    while not eh_dia_util(d):
        d -= datetime.timedelta(days=1)
    return d
