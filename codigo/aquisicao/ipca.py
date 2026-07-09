"""Aquisição do IPCA (índice mensal) via OData do IPEADATA.

Série `PRECOS12_IPCA12` (índice-número mensal do IPCA), endpoint OData4
`ValoresSerie` — campos `VALDATA` (ISO) e `VALVALOR`. Validado contra a base:
2026-05 = 7640.15. Vai para a tabela mensal `COD_INDICE_MENSAL=1`.

Usa `requests` direto (a lib `ipeadatapy` quebra no Python 3.14). IO separado da
transformação pura para permitir teste sem rede.
"""
from __future__ import annotations

import datetime

import requests

SERIE_IPCA = "PRECOS12_IPCA12"
COD_INDICE_MENSAL_IPCA = 1

_URL = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{sercodigo}')"


def obter_valores_ipeadata(sercodigo: str = SERIE_IPCA, timeout: int = 60) -> list[dict]:
    """Baixa os pontos da série (lista de dicts do OData `value`)."""
    resp = requests.get(_URL.format(sercodigo=sercodigo), timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.json()["value"]


def parse_valores_mensais(valores: list[dict]) -> list[tuple[int, int, float]]:
    """OData `ValoresSerie` -> [(ano, mes, valor)], pulando VALVALOR nulo/vazio."""
    out = []
    for v in valores:
        if v.get("VALVALOR") in (None, ""):
            continue
        d = datetime.date.fromisoformat(v["VALDATA"][:10])
        out.append((d.year, d.month, float(v["VALVALOR"])))
    return out


def linhas_indice_mensal(
    cod_indice: int, parsed: list[tuple[int, int, float]]
) -> list[dict]:
    """Linhas (COD_INDICE_MENSAL, ANO, MES, VALOR) para `indice_mensal_valor.csv`."""
    return [
        {"COD_INDICE_MENSAL": cod_indice, "ANO": ano, "MES": mes, "VALOR": valor}
        for (ano, mes, valor) in parsed
    ]


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore")  # silencia aviso de verify=False
    pontos = parse_valores_mensais(obter_valores_ipeadata())
    print(f"IPCA ({SERIE_IPCA}) — {len(pontos)} pontos mensais. Últimos 6:")
    for ano, mes, valor in pontos[-6:]:
        print(f"  {ano}-{mes:02d}: {valor}")
