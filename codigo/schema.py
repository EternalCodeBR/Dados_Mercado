import re
from dataclasses import dataclass

_RE_ABA_ILEGAL = re.compile(r"[\\/?*\[\]:]")


@dataclass(frozen=True)
class Serie:
    cod: int
    nome: str
    fonte: str
    cadencia: str  # "diaria" | "mensal"
    ativo: bool = True  # False = no escopo do contrato, mas ainda não gerado


SERIES_DIARIAS = (
    Serie(2, "CDI", "BACEN/SGS 12", "diaria"),
    Serie(3, "FATOR_DIARIO_CDI", "Calculado do CDI", "diaria"),
    Serie(4, "PTAX/USD", "BACEN/SGS 1", "diaria"),
    Serie(5, "EURO", "BACEN/SGS 21619", "diaria"),
    Serie(8, "CHF", "BACEN/SGS 21625", "diaria"),
    Serie(9, "CAD", "BACEN/SGS 21635", "diaria"),
    Serie(10, "USD_CUPOM_LIMPO", "B3 (a definir)", "diaria", ativo=False),
    Serie(11, "JPY", "BACEN/SGS 21621", "diaria"),
)
INDICES_MENSAIS = (
    Serie(1, "IPCA", "IPEADATA PRECOS12_IPCA12", "mensal"),
    Serie(2, "IGP-M", "IPEADATA IGP12_IGPM12", "mensal", ativo=False),
)
COD_SERIES_DIARIAS = {s.cod for s in SERIES_DIARIAS}
COD_INDICES_MENSAIS = {s.cod for s in INDICES_MENSAIS}
NOME_POR_COD_DIARIA = {s.cod: s.nome for s in SERIES_DIARIAS}
NOME_POR_COD_MENSAL = {s.cod: s.nome for s in INDICES_MENSAIS}


def aba_nome(serie: Serie) -> str:
    """Nome de aba do Excel para a série (sem caracteres ilegais: \\ / ? * [ ] :).

    PTAX/USD vira "PTAX" (escolha do usuário); demais nomes ficam inalterados.
    """
    nome = serie.nome.split("/")[0]
    return _RE_ABA_ILEGAL.sub("_", nome)[:31]


def linhas_indices(ref_diaria=None, ref_mensal=None) -> list[dict]:
    """Linhas da aba INDICES (apenas séries ATIVAS): TIPO, COD, NOME, FONTE, DATA REFERÊNCIA.

    TIPO indica a defasagem: "D-1" (diária, dia útil anterior) ou "M-1" (mensal).
    DATA REFERÊNCIA = data do dado mais recente daquele índice (vinda de `ref_diaria`/
    `ref_mensal`, dicts cod->str). Sem mapa, fica em branco.
    """
    ref_diaria = ref_diaria or {}
    ref_mensal = ref_mensal or {}
    rows = []
    for s in SERIES_DIARIAS:
        if s.ativo:
            rows.append({"TIPO": "D-1", "COD": s.cod, "NOME": s.nome, "FONTE": s.fonte,
                         "DATA REFERÊNCIA": ref_diaria.get(s.cod, "")})
    for s in INDICES_MENSAIS:
        if s.ativo:
            rows.append({"TIPO": "M-1", "COD": s.cod, "NOME": s.nome, "FONTE": s.fonte,
                         "DATA REFERÊNCIA": ref_mensal.get(s.cod, "")})
    return rows
