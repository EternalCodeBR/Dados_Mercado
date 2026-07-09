from codigo import schema

def test_series_diarias_em_escopo():
    assert schema.COD_SERIES_DIARIAS == {2, 3, 4, 5, 8, 9, 10, 11}

def test_indices_mensais_em_escopo():
    assert schema.COD_INDICES_MENSAIS == {1, 2}

def test_fora_de_escopo_ausente():
    # IBOV(1 diária), EGAF11(6), SEQL3(7) não entram nas diárias
    assert 6 not in schema.COD_SERIES_DIARIAS
    assert 7 not in schema.COD_SERIES_DIARIAS


def test_linhas_indices_lista_so_ativos():
    rows = schema.linhas_indices()
    nomes = {r["NOME"] for r in rows}
    assert {"CDI", "FATOR_DIARIO_CDI", "IPCA"} <= nomes
    assert "IGP-M" not in nomes            # adiado
    assert "USD_CUPOM_LIMPO" not in nomes  # adiado
    cdi_row = next(r for r in rows if r["NOME"] == "CDI")
    assert "BACEN" in cdi_row["FONTE"]


def test_tipo_indica_defasagem_d1_m1():
    rows = schema.linhas_indices()
    diaria = next(r for r in rows if r["NOME"] == "CDI")
    mensal = next(r for r in rows if r["NOME"] == "IPCA")
    assert diaria["TIPO"] == "D-1"
    assert mensal["TIPO"] == "M-1"


def test_fator_fonte_capitalizado():
    fator = next(s for s in schema.SERIES_DIARIAS if s.nome == "FATOR_DIARIO_CDI")
    assert fator.fonte == "Calculado do CDI"


def test_aba_nome_sem_caractere_ilegal():
    ptax = next(s for s in schema.SERIES_DIARIAS if s.cod == 4)
    cdi = next(s for s in schema.SERIES_DIARIAS if s.cod == 2)
    assert schema.aba_nome(ptax) == "PTAX"   # PTAX/USD sem a barra
    assert schema.aba_nome(cdi) == "CDI"


def test_linhas_indices_tem_data_referencia():
    rows = schema.linhas_indices(ref_diaria={2: "2026-06-20"}, ref_mensal={1: "2026-05"})
    cdi = next(r for r in rows if r["NOME"] == "CDI")
    ipca = next(r for r in rows if r["NOME"] == "IPCA")
    assert cdi["DATA REFERÊNCIA"] == "2026-06-20"
    assert ipca["DATA REFERÊNCIA"] == "2026-05"
    # sem mapa -> coluna existe, em branco
    assert all("DATA REFERÊNCIA" in r for r in schema.linhas_indices())
