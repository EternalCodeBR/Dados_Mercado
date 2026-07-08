from codigo import planilha


def test_roundtrip_e_multiplas_abas(tmp_path):
    p = tmp_path / "mercado.xlsx"
    planilha.escrever_mercado(
        p,
        [
            ("SERIE_VALOR", ["COD_SERIE", "DATA", "VALOR"],
             [{"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4}]),
            ("INDICES", ["TIPO", "COD", "NOME", "FONTE"],
             [{"TIPO": "diária", "COD": 2, "NOME": "CDI", "FONTE": "BACEN/SGS 12"}]),
        ],
    )
    # cada campo numa coluna -> lido de volta como dict por cabeçalho
    assert planilha.ler_rows(p, "SERIE_VALOR") == [
        {"COD_SERIE": 2, "DATA": "2026-06-17", "VALOR": 14.4}
    ]
    assert planilha.ler_rows(p, "INDICES")[0]["NOME"] == "CDI"


def test_aba_inexistente_retorna_vazio(tmp_path):
    p = tmp_path / "m.xlsx"
    planilha.escrever_mercado(p, [("X", ["A"], [{"A": 1}])])
    assert planilha.ler_rows(p, "NAO_EXISTE") == []


def test_arquivo_inexistente_retorna_vazio(tmp_path):
    assert planilha.ler_rows(tmp_path / "nada.xlsx", "SERIE_VALOR") == []
