"""Aquisição das moedas via API SGS do Banco Central — taxa de venda.

O fetch fica em `sgs.obter_serie`. Cada moeda é gravada pela SUA PRÓPRIA data de
cotação, até **D-1** (nunca D-0) — igual ao CDI. Só entram dias com cotação publicada
(sem fill); como cada moeda só publica nos seus dias, os buracos já refletem o feriado
próprio dela. A calculadora obtém o D-1 como a última cotação ≤ data de marcação.

Códigos SGS validados contra a BaseDadosMercado (batem ao centavo):

| COD_SERIE | moeda      | SGS   |
|-----------|------------|-------|
| 4         | PTAX (USD) | 1     |
| 5         | EURO       | 21619 |
| 8         | CHF        | 21625 |
| 9         | CAD        | 21635 |
| 11        | JPY        | 21621 |
"""
from __future__ import annotations

import datetime

# COD_SERIE (schema do projeto) -> código SGS do BACEN (taxa de venda)
SGS_POR_COD_SERIE = {4: 1, 5: 21619, 8: 21625, 9: 21635, 11: 21621}


def linhas_moeda(
    cod_serie: int,
    serie_por_data: dict[datetime.date, float],
    corte: datetime.date | None = None,
) -> list[dict]:
    """Linhas (COD_SERIE, DATA, VALOR) pela própria data, até `corte` (D-1; nunca D-0).

    Inclui apenas datas com cotação publicada. `corte`: descarta datas posteriores a
    ele (p.ex. o D-0). Não há deslocamento nem fill — cada data carrega o seu valor.
    """
    linhas = []
    for d in sorted(serie_por_data):
        if corte is not None and d > corte:
            continue
        linhas.append(
            {"COD_SERIE": cod_serie, "DATA": d.isoformat(), "VALOR": serie_por_data[d]}
        )
    return linhas
