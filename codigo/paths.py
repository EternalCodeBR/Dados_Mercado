from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OUTPUT = RAIZ / "output"
MERCADO_XLSX = OUTPUT / "mercado.xlsx"  # planilha de produção (histórico completo)
HISTORICO = OUTPUT / "historico"        # output/historico/<ANO>/Dadosmercado_ddmmyy.csv (delta do dia)
TEAMS_WEBHOOK_FILE = RAIZ / "teams_webhook.url"  # segredo (fora do git); alt.: env TEAMS_WEBHOOK_URL
