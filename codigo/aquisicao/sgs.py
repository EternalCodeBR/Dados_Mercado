"""Cliente da API SGS do Banco Central (séries diárias) — fonte única de fetch.

Usado pelo CDI (série 12) e pelas moedas (1, 21619, ...). Mantém o acesso ao
BACEN em um só lugar (DRY): timeout, tratamento de erro HTTP e descarte de vazios.
"""
from __future__ import annotations

import datetime
import time

import requests

_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def obter_serie(
    codigo_sgs: int,
    data_inicial: datetime.date | None = None,
    data_final: datetime.date | None = None,
    timeout: int = 60,
    tentativas: int = 4,
) -> dict[datetime.date, float]:
    """Baixa a série SGS `codigo_sgs` e devolve {data: valor} (float).

    Pula registros com `valor` nulo/vazio. Faz `tentativas` com backoff: a API do
    BACEN devolve 5xx/timeout intermitente em ranges longos. Levanta a última
    exceção se todas as tentativas falharem.
    """
    url = _URL.format(codigo=codigo_sgs)
    if data_inicial:
        url += "&dataInicial=" + data_inicial.strftime("%d/%m/%Y")
    if data_final:
        url += "&dataFinal=" + data_final.strftime("%d/%m/%Y")

    ultimo_erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return {
                datetime.datetime.strptime(item["data"], "%d/%m/%Y").date(): float(
                    item["valor"]
                )
                for item in resp.json()
                if item.get("valor") not in (None, "")
            }
        except requests.RequestException as erro:
            ultimo_erro = erro
            if tentativa < tentativas - 1:
                time.sleep(2 * (tentativa + 1))  # 2s, 4s, 6s
    raise ultimo_erro
