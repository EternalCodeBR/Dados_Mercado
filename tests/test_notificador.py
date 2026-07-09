from codigo import notificador


def test_eh_classico_detecta_pelo_dominio():
    assert notificador._eh_classico("https://x.webhook.office.com/webhookb2/abc")
    assert notificador._eh_classico("https://outlook.office.com/webhook/abc")
    assert not notificador._eh_classico(
        "https://prod-00.brazilsouth.logic.azure.com:443/workflows/abc/triggers/manual"
    )


def test_payload_classico_eh_messagecard():
    p = notificador._payload("https://x.webhook.office.com/w", "T", "corpo", sucesso=True)
    assert p["@type"] == "MessageCard"
    assert p["title"] == "T" and p["text"] == "corpo"
    assert p["themeColor"] == notificador._VERDE


def test_payload_workflow_eh_adaptive_card_e_cor_de_falha():
    p = notificador._payload("https://x.logic.azure.com/w", "T", "corpo", sucesso=False)
    card = p["attachments"][0]["content"]
    assert p["type"] == "message"
    assert card["type"] == "AdaptiveCard"
    assert card["body"][0]["color"] == "Attention"  # falha -> vermelho
    assert card["body"][1]["text"] == "corpo"
    # campos no topo p/ o fluxo ler direto
    assert p["titulo"] == "T" and p["texto"] == "corpo" and p["sucesso"] is False


def test_payload_com_arquivo_monta_botao_abrir(monkeypatch):
    monkeypatch.setattr(
        notificador, "SHAREPOINT_HISTORICO_URL", "https://x.sharepoint.com/historico/"
    )
    p = notificador._payload(
        "https://x.logic.azure.com/w", "T", "corpo", True, "Dadosmercado_230626.csv"
    )
    acao = p["attachments"][0]["content"]["actions"][0]
    assert acao["type"] == "Action.OpenUrl"
    assert acao["title"] == "Abrir Dadosmercado_230626.csv"
    assert acao["url"].endswith("Dadosmercado_230626.csv")
    assert acao["url"].startswith("https://x.sharepoint.com/")
    assert p["arquivo_nome"] == "Dadosmercado_230626.csv"


def test_payload_sem_arquivo_nao_tem_acoes():
    p = notificador._payload("https://x.logic.azure.com/w", "T", "corpo", True)
    assert "actions" not in p["attachments"][0]["content"]
    assert "arquivo_nome" not in p


def test_url_cai_no_padrao_do_codigo(monkeypatch, tmp_path):
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(notificador.paths, "TEAMS_WEBHOOK_FILE", tmp_path / "nao_existe.url")
    monkeypatch.setattr(notificador, "WEBHOOK_PADRAO", "https://x.logic.azure.com/padrao")
    assert notificador._url() == "https://x.logic.azure.com/padrao"


def test_env_e_arquivo_tem_prioridade_sobre_padrao(monkeypatch, tmp_path):
    f = tmp_path / "teams_webhook.url"
    f.write_text("https://x.logic.azure.com/do-arquivo", encoding="utf-8")
    monkeypatch.setattr(notificador.paths, "TEAMS_WEBHOOK_FILE", f)
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    assert notificador._url() == "https://x.logic.azure.com/do-arquivo"  # arquivo > padrão
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://x.logic.azure.com/do-env")
    assert notificador._url() == "https://x.logic.azure.com/do-env"      # env > arquivo


def test_notificar_sem_url_retorna_false(monkeypatch, tmp_path):
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(notificador.paths, "TEAMS_WEBHOOK_FILE", tmp_path / "nao_existe.url")
    monkeypatch.setattr(notificador, "WEBHOOK_PADRAO", "")  # sem padrão -> sem URL
    assert notificador.notificar("t", "x") is False


def test_notificar_posta_quando_ha_url(monkeypatch):
    enviados = {}

    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_post(url, json, timeout):
        enviados["url"] = url
        enviados["json"] = json
        return _Resp()

    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://x.logic.azure.com/w")
    monkeypatch.setattr(notificador.requests, "post", _fake_post)
    assert notificador.notificar("T", "corpo", sucesso=True) is True
    assert enviados["url"] == "https://x.logic.azure.com/w"
    assert enviados["json"]["type"] == "message"  # workflow -> adaptive card


def _captura_post(monkeypatch, destino):
    class _Resp:
        def raise_for_status(self):
            pass

    def _fake_post(url, json, timeout):
        destino["json"] = json
        return _Resp()

    monkeypatch.setattr(notificador.requests, "post", _fake_post)


def test_notificar_anexa_arquivo_base64_no_workflow(monkeypatch, tmp_path):
    import base64

    enviados = {}
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://x.logic.azure.com/w")
    _captura_post(monkeypatch, enviados)
    f = tmp_path / "Dadosmercado_230626.csv"
    f.write_text("Índice;Data;Valor\nCDI;2026-06-23;14,65\n", encoding="utf-8-sig")
    assert notificador.notificar("T", "corpo", arquivo=f) is True
    assert enviados["json"]["arquivo_nome"] == "Dadosmercado_230626.csv"
    assert base64.b64decode(enviados["json"]["arquivo_base64"]) == f.read_bytes()


def test_classico_nao_anexa_arquivo(monkeypatch, tmp_path):
    enviados = {}
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://x.webhook.office.com/w")
    _captura_post(monkeypatch, enviados)
    f = tmp_path / "Dadosmercado_230626.csv"
    f.write_text("x", encoding="utf-8")
    notificador.notificar("T", "corpo", arquivo=f)
    assert "arquivo_base64" not in enviados["json"]


def test_arquivo_webhook_ignora_comentarios(monkeypatch, tmp_path):
    f = tmp_path / "teams_webhook.url"
    f.write_text("# comentário\n\nhttps://x.webhook.office.com/w\n", encoding="utf-8")
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(notificador.paths, "TEAMS_WEBHOOK_FILE", f)
    assert notificador._url() == "https://x.webhook.office.com/w"
