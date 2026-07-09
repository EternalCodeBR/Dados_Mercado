# Base de Dados de Mercado

Rotina em Python que automatiza a coleta diária de indicadores do mercado financeiro
brasileiro a partir de fontes oficiais, mantendo um histórico consolidado e confiável
para uso por outras rotinas/calculadoras.

## Problema
A atualização dos **8 indicadores de mercado** (CDI e seu fator diário, PTAX/USD,
EUR, CHF, CAD, JPY e IPCA) usados pelas calculadoras de ativos era feita manualmente
em uma planilha (`BaseDadosMercado.xlsm`): alguém precisava consultar cada fonte,
copiar o valor do dia e colar na aba certa — **5 a 10 minutos de digitação por dia
útil**, com risco de erro a cada valor copiado. Não havia notificação automática de
que a base tinha (ou não) sido atualizada — falhas silenciosas só eram percebidas
quando alguém ia usar o dado.

## Solução
Rotina em Python (`python -m codigo.orquestrador`) que:
- **Coleta os indicadores direto nas fontes oficiais** (sem intervenção manual):

  | Indicador | Fonte |
  |---|---|
  | CDI (a.a.) e Fator diário do CDI | BACEN/SGS 12 |
  | PTAX / USD | BACEN/SGS 1 |
  | EURO / CHF / CAD / JPY | BACEN/SGS 21619 / 21625 / 21635 / 21621 |
  | IPCA (mensal) | IPEADATA `PRECOS12_IPCA12` |

- **Respeita o calendário de mercado**: dias úteis e feriados via biblioteca `holidays`
  (mercado BVMF/B3); a coleta sempre busca até **D-1 útil**, nunca o dia corrente.
- **Atualiza de forma incremental e idempotente**: upsert por índice/data, então rodar
  de novo no mesmo dia não duplica nem corrompe o histórico.
- **Gera saída padronizada e auditável**:
  - `output/mercado.xlsx` — histórico completo, uma aba por índice, estilizado;
  - `output/historico/<ano>/Dadosmercado_<ddmmyy>.csv` — apenas o delta do dia.
- **Notifica a equipe no Microsoft Teams** ao final (sucesso em verde, falha em vermelho),
  incluindo o CSV do dia como anexo — eliminando a checagem manual de "a base foi
  atualizada hoje?".
- **Tem 49 testes automatizados** (`pytest`) cobrindo aquisição, cálculo de dias úteis,
  montagem da planilha e notificação.

## Resultado
- **Zero digitação manual**: os 8 indicadores, que exigiam 5–10 minutos de consulta
  e cópia por dia, passaram a ser coletados sozinhos, todo dia útil, via agendamento
  (Windows Task Scheduler) — direto de 2 fontes oficiais (BACEN e IPEADATA).
- Histórico auditável e reconstruível do zero a qualquer momento
  (`python -m codigo.orquestrador seed`).
- Falhas deixaram de ser silenciosas: a equipe é avisada no Teams no mesmo dia,
  com o arquivo já em anexo.

## Como rodar
```bash
pip install -r requirements.txt

# Atualização diária (padrão): coleta o dia novo, atualiza a planilha e gera o CSV do dia
python -m codigo.orquestrador

# Carga completa do histórico (criar do zero ou reconstruir)
python -m codigo.orquestrador seed
```
> Rode com o `mercado.xlsx` **fechado** no Excel.

## Notificação no Teams
Ao final, a rotina posta um cartão no Teams (verde em sucesso, vermelho em falha).
A URL do webhook é resolvida nesta ordem: variável de ambiente `TEAMS_WEBHOOK_URL` →
arquivo `teams_webhook.url` (na raiz, fora do git, veja `teams_webhook.url.example`).
Sem nenhuma das duas, a notificação é apenas pulada.

Quando há arquivo do dia, o payload inclui o CSV (base64); um fluxo do **Power Automate**
pode salvar o arquivo no SharePoint e o cartão exibe o botão **Abrir Dadosmercado_<dia>.csv**
se a variável de ambiente `SHAREPOINT_HISTORICO_URL` estiver definida.

## Estrutura do projeto
```
codigo/
  orquestrador.py   # seed() / atualizar() + ponto de entrada (python -m codigo.orquestrador)
  aquisicao/        # clientes das APIs: cdi, moedas (sgs), ipca
  feriados.py       # dias úteis e feriados (BVMF)
  schema.py         # catálogo de séries e índices
  planilha.py       # escrita do mercado.xlsx
  notificador.py    # notificação no Teams
  paths.py          # caminhos de saída
  append.py         # upsert idempotente e delta
tests/              # testes (pytest)
output/             # gerado pela rotina (ignorado no git)
docs/apresentacao/  # one-pager de apresentação do projeto
```

## Testes
```bash
python -m pytest
```

## Agendamento
Agende `python -m codigo.orquestrador` no Windows Task Scheduler para rodar todo dia útil.
