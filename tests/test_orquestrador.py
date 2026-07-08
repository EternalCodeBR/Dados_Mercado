import datetime

from codigo import paths
from codigo.orquestrador import (
    _abas_mensais,
    _abas_series,
    _datas_referencia,
    _gravar_historico,
    _linhas_historico,
    _referencia_do_dia,
    montar_indice_mensal,
    montar_serie_valor,
)


def test_montar_serie_valor_cdi_e_moedas_propria_data_ordenado():
    cdi_diaria = {datetime.date(2026, 6, 17): 0.0534}
    moedas_por_cod = {
        4: {datetime.date(2026, 6, 16): 5.078, datetime.date(2026, 6, 17): 5.0641}
    }
    linhas = montar_serie_valor(cdi_diaria, moedas_por_cod)
    assert {"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4} in linhas
    assert {"COD_SERIE": 3, "DATA": "2026-06-17", "VALOR": 1.000534} in linhas
    # moedas pela própria data (sem deslocamento)
    assert {"COD_SERIE": 4, "DATA": "2026-06-16", "VALOR": 5.078} in linhas
    assert {"COD_SERIE": 4, "DATA": "2026-06-17", "VALOR": 5.0641} in linhas
    chaves = [(r["DATA"], r["COD_SERIE"]) for r in linhas]
    assert chaves == sorted(chaves)


def test_cdi_e_moedas_nunca_coletam_d0():
    # 19/06 = D-0; corte = 18/06 (D-1). Nem CDI nem moeda pegam o 19; 18 com valor próprio.
    cdi_diaria = {datetime.date(2026, 6, 18): 0.0525, datetime.date(2026, 6, 19): 0.0525}
    moedas_por_cod = {
        4: {datetime.date(2026, 6, 18): 1.10, datetime.date(2026, 6, 19): 1.20}
    }
    linhas = montar_serie_valor(cdi_diaria, moedas_por_cod, corte=datetime.date(2026, 6, 18))
    assert "2026-06-19" not in [r["DATA"] for r in linhas]      # ninguém pega D-0
    cdi_datas = [r["DATA"] for r in linhas if r["COD_SERIE"] == 2]
    assert cdi_datas == ["2026-06-18"]                          # CDI só D-1
    assert {"COD_SERIE": 4, "DATA": "2026-06-18", "VALOR": 1.10} in linhas  # moeda D-1, valor próprio


def test_abas_series_uma_por_indice():
    serie_rows = [
        {"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4},
        {"COD_SERIE": 3, "DATA": "2026-06-17", "VALOR": 1.000534},
        {"COD_SERIE": 4, "DATA": "2026-06-17", "VALOR": 5.0641},
    ]
    abas = {nome: (cols, rows) for nome, cols, rows in _abas_series(serie_rows)}
    # nome da aba = nome do índice (PTAX/USD vira PTAX); colunas COD|DATA|VALOR
    assert "CDI" in abas and "FATOR_DIARIO_CDI" in abas and "PTAX" in abas
    assert abas["CDI"][0] == ["COD_SERIE", "DATA", "VALOR"]
    assert abas["CDI"][1] == [{"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4}]
    # USD_CUPOM_LIMPO (inativo) não vira aba
    assert "USD_CUPOM_LIMPO" not in abas


def test_abas_mensais_ipca():
    abas = {a[0]: a for a in _abas_mensais([
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 4, "VALOR": 7617.34},
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 7640.15},
    ])}
    assert "IPCA" in abas and "IGP-M" not in abas
    nome, cols, rows, formatos = abas["IPCA"]
    assert cols == ["COD_INDICE_MENSAL", "ANO", "MES", "VALOR", "VARIAÇÃO MENSAL"]
    # 1ª linha de dados (linha 2) sem variação; 2ª linha (linha 3) com fórmula referenciando D
    assert rows[0]["VARIAÇÃO MENSAL"] is None
    assert rows[1]["VARIAÇÃO MENSAL"] == "=(D3/D2-1)*100"
    assert formatos == {"VARIAÇÃO MENSAL": "0.00000000"}


def test_montar_indice_mensal_ipca():
    assert montar_indice_mensal([(2026, 5, 7640.15)]) == [
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 7640.15}
    ]


def test_montar_indice_mensal_corta_antes_de_2019():
    parsed = [(2018, 12, 1.0), (2019, 1, 2.0), (2026, 5, 7640.15)]
    anos = [r["ANO"] for r in montar_indice_mensal(parsed)]
    assert 2018 not in anos
    assert anos == [2019, 2026]


def test_datas_referencia_pega_o_mais_recente():
    serie = [
        {"COD_SERIE": 2, "DATA": "2026-06-18", "VALOR": 14.4},
        {"COD_SERIE": 2, "DATA": "2026-06-20", "VALOR": 14.5},
        {"COD_SERIE": 4, "DATA": "2026-06-19", "VALOR": 5.06},
    ]
    mensal = [
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 4, "VALOR": 1.0},
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 2.0},
    ]
    ref_d, ref_m = _datas_referencia(serie, mensal)
    assert ref_d == {2: "2026-06-20", 4: "2026-06-19"}
    assert ref_m == {1: "2026-05"}


def test_linhas_historico_usa_nome_e_data():
    delta_serie = [{"COD_SERIE": 2, "DATA": "2026-06-20", "VALOR": 14.5}]
    delta_mensal = [{"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 7640.15}]
    linhas = _linhas_historico(delta_serie, delta_mensal)
    assert {"Índice": "CDI", "Data": "2026-06-20", "Valor": 14.5} in linhas
    assert {"Índice": "IPCA", "Data": "2026-05", "Valor": 7640.15} in linhas


def test_gravar_historico_csv_delta_do_dia(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "HISTORICO", tmp_path / "historico")
    dia = datetime.date(2026, 6, 23)
    caminho = _gravar_historico(
        [{"COD_SERIE": 4, "DATA": "2026-06-22", "VALOR": 5.0641}], [], dia=dia
    )
    assert caminho.name == "Dadosmercado_230626.csv"
    assert caminho.parent.name == "2026"  # dividido por ano
    conteudo = caminho.read_text(encoding="utf-8-sig")
    assert conteudo.splitlines()[0] == "Índice;Data;Valor"      # separador ; (colunas no Excel)
    assert "PTAX/USD;2026-06-22;5,0641" in conteudo             # decimal vírgula (pt-BR)


def test_gravar_historico_vazio_nao_cria_arquivo(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "HISTORICO", tmp_path / "historico")
    assert _gravar_historico([], [], dia=datetime.date(2026, 6, 23)) is None
    assert not (tmp_path / "historico").exists()


def test_referencia_do_dia_filtra_d1_e_ultimo_mes():
    sv = [
        {"COD_SERIE": 2, "DATA": "2026-06-19", "VALOR": 14.1},
        {"COD_SERIE": 2, "DATA": "2026-06-22", "VALOR": 14.4},
        {"COD_SERIE": 4, "DATA": "2026-06-22", "VALOR": 5.06},
    ]
    im = [
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 4, "VALOR": 1.0},
        {"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 2.0},
    ]
    d_sv, d_im = _referencia_do_dia(sv, im, datetime.date(2026, 6, 22))
    assert {r["DATA"] for r in d_sv} == {"2026-06-22"}            # só o D-1
    assert d_im == [{"COD_INDICE_MENSAL": 1, "ANO": 2026, "MES": 5, "VALOR": 2.0}]  # último mês
