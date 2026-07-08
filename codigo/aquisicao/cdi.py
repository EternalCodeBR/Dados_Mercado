"""Aquisição do CDI via API SGS do Banco Central (série 12 — CDI diário, % a.d.).

Fonte: BACEN/SGS série 12 (mesma API das moedas, via `sgs.obter_serie`). Substitui
o IPEADATA. A base guarda, derivadas do diário `d`:

- série 3 (FATOR_DIARIO_CDI) = ``1 + d/100``
- série 2 (CDI, % a.a.)      = ``((1 + d/100) ** 252 - 1) * 100``  (arred. 2 casas)

Validado contra a base: d = 0,0534 → fator 1,000534 → 14,40 % a.a. (= série 2).
"""
from __future__ import annotations

import datetime

from . import sgs

SERIE_CDI_SGS = 12
COD_SERIE_CDI = 2
COD_SERIE_FATOR = 3
DIAS_UTEIS_ANO = 252


def anualizar(cdi_diario_pct: float) -> tuple[float, float]:
    """Converte o CDI diário (% a.d.) no fator diário e no CDI anual (% a.a.).

    Retorna ``(fator_diario, cdi_aa)`` com o anual arredondado a 2 casas (como na base).
    """
    fator = 1 + cdi_diario_pct / 100
    cdi_aa = round((fator ** DIAS_UTEIS_ANO - 1) * 100, 2)
    return fator, cdi_aa


def obter_cdi_diario(
    data_inicial: datetime.date | None = None,
    data_final: datetime.date | None = None,
) -> dict[datetime.date, float]:
    """Histórico do CDI diário (% a.d.) da série SGS 12 -> {data: valor}."""
    return sgs.obter_serie(SERIE_CDI_SGS, data_inicial, data_final)


def linhas_cdi(serie_diaria: dict[datetime.date, float]) -> list[dict]:
    """Linhas (COD_SERIE, DATA, VALOR) das séries 2 (CDI a.a.) e 3 (FATOR), por data."""
    linhas = []
    for d in sorted(serie_diaria):
        fator, cdi_aa = anualizar(serie_diaria[d])
        iso = d.isoformat()
        linhas.append({"COD_SERIE": COD_SERIE_CDI, "DATA": iso, "VALOR": cdi_aa})
        linhas.append({"COD_SERIE": COD_SERIE_FATOR, "DATA": iso, "VALOR": fator})
    return linhas


if __name__ == "__main__":
    serie = obter_cdi_diario(datetime.date(2026, 6, 1))
    print(f"CDI (SGS 12) — {len(serie)} dias. Últimos 5:")
    for d in sorted(serie)[-5:]:
        fator, cdi_aa = anualizar(serie[d])
        print(f"  {d}: diário {serie[d]:.4f}% | fator {fator:.8f} | a.a. {cdi_aa:.2f}%")
