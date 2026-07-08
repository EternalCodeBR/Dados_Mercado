"""Orquestrador: atualiza o workbook de mercado (`mercado.xlsx`) a partir das APIs.

- `atualizar()` (padrão diário): busca uma **janela recente** e faz *upsert* idempotente
  na planilha existente — só adiciona o que falta, **não** regenera/rebusca o histórico.
- `seed()`: monta o histórico completo do zero (uma vez, para criar o arquivo).

Workbook: aba `INDICES` (legenda) + **uma aba por índice** (nome = nome do índice):
diárias `CDI`, `FATOR_DIARIO_CDI`, `PTAX`, `EURO`, `CHF`, `CAD`, `JPY` e a mensal `IPCA`.
"""
from __future__ import annotations

import csv
import datetime

from . import feriados, paths, planilha, schema
from .append import delta_idempotente, merge_idempotente
from .aquisicao import cdi, ipca, moedas, sgs

INICIO_SEED = datetime.date(2019, 1, 1)
ANO_INICIO_MENSAL = 2019  # corta o histórico mensal (IPCA) a partir deste ano
JANELA_DIARIA_DIAS = 30

ABA_INDICES = "INDICES"
COL_VAR_MENSAL = "VARIAÇÃO MENSAL"
FMT_VAR_MENSAL = "0.00000000"  # 8 casas decimais (display)
COLS_SERIE = ["COD_SERIE", "DATA", "VALOR"]
COLS_MENSAL = ["COD_INDICE_MENSAL", "ANO", "MES", "VALOR", COL_VAR_MENSAL]
COLS_INDICES = ["TIPO", "COD", "NOME", "FONTE", "DATA REFERÊNCIA"]
COLS_HISTORICO = ["Índice", "Data", "Valor"]
CHAVE_SERIE = ("COD_SERIE", "DATA")
CHAVE_MENSAL = ("COD_INDICE_MENSAL", "ANO", "MES")


def montar_serie_valor(cdi_diaria, moedas_por_cod, corte=None) -> list[dict]:
    """Linhas diárias combinadas (puro): CDI (séries 2 e 3) + moedas, pela própria data.

    `corte` (D-1 útil): se dado, **CDI e moedas** descartam datas posteriores a ele —
    nunca coletam D-0 (dado do próprio dia). Ambos gravam pelo seu próprio dia.
    """
    if corte is not None:
        cdi_diaria = {d: v for d, v in cdi_diaria.items() if d <= corte}
    linhas = cdi.linhas_cdi(cdi_diaria)
    for cod, serie in moedas_por_cod.items():
        linhas.extend(moedas.linhas_moeda(cod, serie, corte=corte))
    return sorted(linhas, key=lambda r: (r["DATA"], r["COD_SERIE"]))


def montar_indice_mensal(ipca_parsed) -> list[dict]:
    """Linhas mensais (puro): IPCA a partir de ANO_INICIO_MENSAL, ordenadas."""
    parsed = [(ano, mes, val) for (ano, mes, val) in ipca_parsed if ano >= ANO_INICIO_MENSAL]
    linhas = ipca.linhas_indice_mensal(ipca.COD_INDICE_MENSAL_IPCA, parsed)
    return sorted(linhas, key=lambda r: (r["ANO"], r["MES"], r["COD_INDICE_MENSAL"]))


def _coletar_serie_valor(inicio: datetime.date) -> list[dict]:
    # CDI e moedas nunca em D-0: cortam no dia útil anterior (BVMF).
    corte = feriados.dia_util_anterior(datetime.date.today())
    cdi_diaria = cdi.obter_cdi_diario(inicio, corte)
    moedas_por_cod = {
        cod: sgs.obter_serie(sgs_cod, inicio, corte)
        for cod, sgs_cod in moedas.SGS_POR_COD_SERIE.items()
    }
    return montar_serie_valor(cdi_diaria, moedas_por_cod, corte=corte)


def _coletar_indice_mensal() -> list[dict]:
    return montar_indice_mensal(ipca.parse_valores_mensais(ipca.obter_valores_ipeadata()))


def _abas_series(serie_rows: list[dict]) -> list[tuple[str, list[str], list[dict]]]:
    """Uma aba por série diária ATIVA (nome = nome do índice), em COLS_SERIE."""
    por_cod: dict[int, list[dict]] = {}
    for r in serie_rows:
        por_cod.setdefault(r["COD_SERIE"], []).append(r)
    abas = []
    for s in schema.SERIES_DIARIAS:
        if not s.ativo:
            continue
        rows = sorted(por_cod.get(s.cod, []), key=lambda r: r["DATA"])
        abas.append((schema.aba_nome(s), COLS_SERIE, rows))
    return abas


def _com_variacao_mensal(rows: list[dict]) -> list[dict]:
    """Anexa a coluna VARIAÇÃO MENSAL como fórmula Excel `=(Dn/D{n-1}-1)*100`.

    Linha 1 = cabeçalho; a 1ª linha de dados (linha 2) fica em branco (sem mês
    anterior). A fórmula referencia a coluna D (VALOR) — daí depender da posição.
    """
    out = []
    for i, r in enumerate(rows):
        novo = {k: v for k, v in r.items() if k != COL_VAR_MENSAL}
        linha = i + 2  # +1 cabeçalho, +1 base-1
        novo[COL_VAR_MENSAL] = None if i == 0 else f"=(D{linha}/D{linha - 1}-1)*100"
        out.append(novo)
    return out


def _abas_mensais(mensal_rows: list[dict]):
    """Uma aba por índice mensal ATIVO (ex.: `IPCA`), em COLS_MENSAL."""
    por_cod: dict[int, list[dict]] = {}
    for r in mensal_rows:
        por_cod.setdefault(r["COD_INDICE_MENSAL"], []).append(r)
    abas = []
    for s in schema.INDICES_MENSAIS:
        if not s.ativo:
            continue
        rows = sorted(por_cod.get(s.cod, []), key=lambda r: (r["ANO"], r["MES"]))
        rows = _com_variacao_mensal(rows)
        abas.append((schema.aba_nome(s), COLS_MENSAL, rows, {COL_VAR_MENSAL: FMT_VAR_MENSAL}))
    return abas


def _ler_serie_valor() -> list[dict]:
    """Lê todas as abas de séries diárias ativas e devolve as linhas combinadas."""
    rows = []
    for s in schema.SERIES_DIARIAS:
        if s.ativo:
            rows.extend(planilha.ler_rows(paths.MERCADO_XLSX, schema.aba_nome(s)))
    return rows


def _ler_indice_mensal() -> list[dict]:
    rows = []
    for s in schema.INDICES_MENSAIS:
        if s.ativo:
            rows.extend(planilha.ler_rows(paths.MERCADO_XLSX, schema.aba_nome(s)))
    return rows


def _datas_referencia(serie_rows: list[dict], mensal_rows: list[dict]):
    """(ref_diaria, ref_mensal): cod -> data do registro mais recente do índice.

    Diária: maior DATA (ISO). Mensal: "AAAA-MM" do maior (ANO, MES).
    """
    ref_d: dict[int, str] = {}
    for r in serie_rows:
        cod, d = r["COD_SERIE"], r["DATA"]
        if cod not in ref_d or d > ref_d[cod]:
            ref_d[cod] = d
    ref_m: dict[int, str] = {}
    melhor: dict[int, tuple] = {}
    for r in mensal_rows:
        cod, chave = r["COD_INDICE_MENSAL"], (int(r["ANO"]), int(r["MES"]))
        if cod not in melhor or chave > melhor[cod]:
            melhor[cod] = chave
            ref_m[cod] = f"{chave[0]:04d}-{chave[1]:02d}"
    return ref_d, ref_m


def _gravar(serie_rows: list[dict], mensal_rows: list[dict]) -> None:
    ref_d, ref_m = _datas_referencia(serie_rows, mensal_rows)
    abas = [(ABA_INDICES, COLS_INDICES, schema.linhas_indices(ref_d, ref_m))]
    abas += _abas_series(serie_rows)
    abas += _abas_mensais(mensal_rows)
    planilha.escrever_mercado(paths.MERCADO_XLSX, abas)


def _linhas_historico(delta_serie: list[dict], delta_mensal: list[dict]) -> list[dict]:
    """Delta do dia no formato do histórico: Índice (nome) | Data | Valor."""
    linhas = []
    for r in delta_serie:
        nome = schema.NOME_POR_COD_DIARIA.get(r["COD_SERIE"], str(r["COD_SERIE"]))
        linhas.append({"Índice": nome, "Data": r["DATA"], "Valor": r["VALOR"]})
    for r in delta_mensal:
        nome = schema.NOME_POR_COD_MENSAL.get(r["COD_INDICE_MENSAL"], str(r["COD_INDICE_MENSAL"]))
        linhas.append({"Índice": nome, "Data": f"{int(r['ANO']):04d}-{int(r['MES']):02d}",
                       "Valor": r["VALOR"]})
    return sorted(linhas, key=lambda x: (x["Data"], x["Índice"]))


def _gravar_historico(delta_serie: list[dict], delta_mensal: list[dict], dia=None):
    """Grava `output/historico/<ANO>/Dadosmercado_ddmmyy.csv` só com o delta do dia.

    `dia` = data de REFERÊNCIA (D-1 útil) — usada no nome do arquivo e na pasta do
    ano, pois reflete o período que os dados cobrem (não a data de geração).
    Excel pt-BR: separador `;` e decimal `,` (cada valor em sua coluna). Não cria
    arquivo quando nada foi atualizado. Devolve o caminho gravado (ou None).
    """
    dia = dia or datetime.date.today()
    linhas = _linhas_historico(delta_serie, delta_mensal)
    if not linhas:
        return None
    pasta = paths.HISTORICO / f"{dia.year:04d}"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"Dadosmercado_{dia.strftime('%d%m%y')}.csv"
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLS_HISTORICO)
        for r in linhas:
            w.writerow([r["Índice"], r["Data"], str(r["Valor"]).replace(".", ",")])
    return caminho


def _referencia_do_dia(serie_rows, mensal_rows, ref):
    """Subconjunto do dia de referência (D-1): linhas diárias com DATA==ref + o mês
    mais recente do índice mensal. Usado pelo seed para gravar o histórico do dia."""
    iso = ref.isoformat()
    diarias = [r for r in serie_rows if r["DATA"] == iso]
    mensais = []
    if mensal_rows:
        ultimo = max((int(r["ANO"]), int(r["MES"])) for r in mensal_rows)
        mensais = [r for r in mensal_rows if (int(r["ANO"]), int(r["MES"])) == ultimo]
    return diarias, mensais


def seed(inicio: datetime.date = INICIO_SEED):
    """Monta o histórico completo do zero e grava o CSV do dia de referência (D-1)."""
    sv, im = _coletar_serie_valor(inicio), _coletar_indice_mensal()
    _gravar(sv, im)
    ref = feriados.dia_util_anterior(datetime.date.today())
    d_sv, d_im = _referencia_do_dia(sv, im, ref)
    caminho_hist = _gravar_historico(d_sv, d_im, dia=ref)
    return len(sv), len(im), caminho_hist


def atualizar(janela_dias: int = JANELA_DIARIA_DIAS) -> tuple[int, int]:
    """Diário: busca a janela recente, faz upsert na planilha e grava o delta do dia.

    Atualiza `mercado.xlsx` (histórico completo) e, em paralelo, escreve um CSV só
    com o que foi adicionado hoje em `output/historico/<ANO>/`.
    """
    inicio = datetime.date.today() - datetime.timedelta(days=janela_dias)
    existentes_sv, novos_sv = _ler_serie_valor(), _coletar_serie_valor(inicio)
    existentes_im, novos_im = _ler_indice_mensal(), _coletar_indice_mensal()

    delta_sv = delta_idempotente(existentes_sv, novos_sv, CHAVE_SERIE)
    delta_im = delta_idempotente(existentes_im, novos_im, CHAVE_MENSAL)

    sv = merge_idempotente(existentes_sv, novos_sv, CHAVE_SERIE)
    im = merge_idempotente(existentes_im, novos_im, CHAVE_MENSAL)
    _gravar(sv, im)
    # nome do arquivo = data de REFERÊNCIA (D-1 útil, período que os dados cobrem),
    # não a data de geração.
    ref = feriados.dia_util_anterior(datetime.date.today())
    caminho_hist = _gravar_historico(delta_sv, delta_im, dia=ref)
    return len(sv), len(im), caminho_hist


if __name__ == "__main__":
    import sys
    import warnings

    from . import notificador

    warnings.filterwarnings("ignore")  # silencia aviso de verify=False (IPEADATA)
    modo = "seed" if (len(sys.argv) > 1 and sys.argv[1] == "seed") else "atualizar"
    hoje = datetime.date.today().isoformat()
    try:
        _, _, caminho_hist = seed() if modo == "seed" else atualizar()
    except Exception as erro:
        titulo = "❌ Base de Dados — rotina FALHOU"
        corpo = f"Rotina `{modo}` falhou em {hoje}.\n\n{type(erro).__name__}: {erro}"
        print(f"{titulo}\n{corpo}")
        notificador.notificar(titulo, corpo, sucesso=False)
        raise
    if modo == "seed":
        corpo = f"Carga completa (seed) concluída em {hoje}.\n\n- Planilha: `{paths.MERCADO_XLSX.name}`"
        if caminho_hist:
            corpo += f"\n- Arquivo do dia: `{caminho_hist.name}`"
    elif caminho_hist:
        corpo = f"Atualização concluída em {hoje}.\n\n- Arquivo do dia: `{caminho_hist.name}`"
    else:
        corpo = f"Atualização concluída em {hoje}.\n\n- Nenhum dado novo hoje."
    # terminal mostra a MESMA mensagem enviada ao Teams
    titulo = "✅ Base de Dados — atualizada"
    print(f"{titulo}\n{corpo}")
    notificador.notificar(titulo, corpo, sucesso=True, arquivo=caminho_hist)
