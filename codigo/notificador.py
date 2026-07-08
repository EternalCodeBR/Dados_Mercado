"""Notificação no Microsoft Teams ao fim da rotina (best-effort, nunca derruba).

A URL do webhook é resolvida nesta ordem (a 1ª que existir vence):
  1. variável de ambiente `TEAMS_WEBHOOK_URL`;
  2. arquivo `teams_webhook.url` na raiz do projeto (1ª linha não-comentada, fora do git).

Sem nenhuma das duas, a notificação é apenas pulada (best-effort).

Suporta os dois tipos de webhook, detectados pela URL:
  - Incoming Webhook clássico (`*.webhook.office.com` / `outlook.office.com`) -> MessageCard.
  - Power Automate Workflow (demais, ex.: `*.logic.azure.com`) -> Adaptive Card.

Anexo (Power Automate): quando `notificar(..., arquivo=...)` recebe um caminho, o
payload ganha `arquivo_nome` e `arquivo_base64` (conteúdo do arquivo em base64). O
fluxo do Power Automate deve: (1) Parse JSON; (2) "Criar arquivo" no SharePoint com
`base64ToBinary(arquivo_base64)`; (3) postar o card com um botão "Abrir" para o link.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from . import paths

_VERDE = "2EB67D"
_VERMELHO = "D1242F"

# Pasta do SharePoint onde o fluxo salva o CSV do dia (a MESMA do Create file).
# Usada para montar o botão "Abrir <arquivo>" no card. Defina via env var para
# habilitar o botão; sem ela, o card é postado sem o botão "Abrir".
SHAREPOINT_HISTORICO_URL = os.environ.get("SHAREPOINT_HISTORICO_URL", "")


def _ler_arquivo(p) -> str | None:
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            return linha
    return None


def _url() -> str | None:
    env = os.environ.get("TEAMS_WEBHOOK_URL")
    if env and env.strip():
        return env.strip()
    if paths.TEAMS_WEBHOOK_FILE.exists():
        do_arquivo = _ler_arquivo(paths.TEAMS_WEBHOOK_FILE)
        if do_arquivo:
            return do_arquivo
    return None


def _eh_classico(url: str) -> bool:
    return "webhook.office.com" in url or "outlook.office.com" in url


def _payload(url: str, titulo: str, texto: str, sucesso: bool, arquivo_nome=None) -> dict:
    if _eh_classico(url):
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": _VERDE if sucesso else _VERMELHO,
            "summary": titulo,
            "title": titulo,
            "text": texto,
        }
    content = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "color": "Good" if sucesso else "Attention",
                "text": titulo,
                "wrap": True,
            },
            {"type": "TextBlock", "text": texto, "wrap": True},
        ],
    }
    if arquivo_nome and SHAREPOINT_HISTORICO_URL:
        # botão "Abrir" já pronto (URL = pasta do SharePoint + nome do arquivo)
        content["actions"] = [
            {
                "type": "Action.OpenUrl",
                "title": f"Abrir {arquivo_nome}",
                "url": SHAREPOINT_HISTORICO_URL + arquivo_nome,
            }
        ]
    payload = {
        "type": "message",
        # campos no topo p/ o fluxo ler direto (e subir o arquivo no SharePoint)
        "titulo": titulo,
        "texto": texto,
        "sucesso": sucesso,
        "attachments": [
            {"contentType": "application/vnd.microsoft.card.adaptive", "content": content}
        ],
    }
    if arquivo_nome:
        payload["arquivo_nome"] = arquivo_nome
    return payload


def notificar(titulo: str, texto: str, sucesso: bool = True, arquivo=None, timeout: int = 30) -> bool:
    """Posta no Teams. Best-effort: nunca levanta — devolve True/False e loga.

    `arquivo` (caminho opcional): se existir e o webhook for Power Automate, inclui
    `arquivo_nome` e `arquivo_base64` no payload para o fluxo anexar/subir no SharePoint.
    """
    url = _url()
    if not url:
        print("[teams] sem webhook (TEAMS_WEBHOOK_URL ou teams_webhook.url) — notificação pulada.")
        return False
    arquivo_nome, arquivo_b64 = None, None
    if arquivo is not None and not _eh_classico(url):
        p = Path(arquivo)
        if p.exists():
            arquivo_nome = p.name
            arquivo_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    payload = _payload(url, titulo, texto, sucesso, arquivo_nome)
    if arquivo_b64 is not None:
        payload["arquivo_base64"] = arquivo_b64
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return True
    except requests.RequestException as erro:
        print(f"[teams] falha ao notificar: {erro}")
        return False
