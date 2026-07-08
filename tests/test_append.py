from codigo.append import delta_idempotente, merge_idempotente


def test_nao_duplica_chave_existente():
    existentes = [{"COD_SERIE": 2, "DATA": "2026-06-01", "VALOR": 14.4}]
    novos = [
        {"COD_SERIE": 2, "DATA": "2026-06-01", "VALOR": 14.4},   # duplicata
        {"COD_SERIE": 2, "DATA": "2026-06-02", "VALOR": 14.5},   # nova
    ]
    out = merge_idempotente(existentes, novos, chave=("COD_SERIE", "DATA"))
    assert len(out) == 2
    assert {r["DATA"] for r in out} == {"2026-06-01", "2026-06-02"}


def test_delta_traz_so_as_chaves_novas():
    existentes = [{"COD_SERIE": 2, "DATA": "2026-06-01", "VALOR": 14.4}]
    novos = [
        {"COD_SERIE": 2, "DATA": "2026-06-01", "VALOR": 14.4},   # já existe
        {"COD_SERIE": 2, "DATA": "2026-06-02", "VALOR": 14.5},   # nova
    ]
    delta = delta_idempotente(existentes, novos, chave=("COD_SERIE", "DATA"))
    assert delta == [{"COD_SERIE": 2, "DATA": "2026-06-02", "VALOR": 14.5}]
