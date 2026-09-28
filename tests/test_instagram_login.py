"""Conexión de clientes que solo tienen Instagram."""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from informes_ig import cli, instagram, instagram_login
from informes_ig.config import cargar_config


@pytest.fixture(autouse=True)
def app_instagram(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_ID", "123")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "secreto")
    monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://holamarketing.com.ar/")


class Resp:
    def __init__(self, datos, status=200):
        self._datos, self.status_code, self.content = datos, status, b"x"
        self.text = json.dumps(datos)

    def json(self):
        return self._datos


class SesionFalsa:
    def __init__(self):
        self.pedidos = []

    def post(self, url, data=None, timeout=None):
        self.pedidos.append(("POST", url, data))
        return Resp({"access_token": "corto", "user_id": 999})

    def get(self, url, params=None, timeout=None):
        self.pedidos.append(("GET", url, params))
        if url.endswith("/access_token"):
            return Resp({"access_token": "largo", "expires_in": 5184000})
        if url.endswith("/refresh_access_token"):
            return Resp({"access_token": "renovado", "expires_in": 5184000})
        return Resp({"user_id": "17841", "username": "lujis"})


def test_url_autorizacion():
    q = parse_qs(urlparse(instagram_login.url_autorizacion("lujis")).query)
    assert q["client_id"] == ["123"]
    assert q["redirect_uri"] == ["https://holamarketing.com.ar/"]
    assert q["scope"] == ["instagram_business_basic,instagram_business_manage_insights"]
    assert q["state"] == ["lujis"]


@pytest.mark.parametrize("texto", [
    "https://holamarketing.com.ar/?code=ABC123&state=lujis#_",
    "ABC123#_",
    "  ABC123 ",
])
def test_extraer_codigo(texto):
    assert instagram_login.extraer_codigo(texto) == "ABC123"


def test_canjear_codigo():
    http = SesionFalsa()
    reg = instagram_login.canjear_codigo("https://holamarketing.com.ar/?code=ABC#_", http)
    assert http.pedidos[0][2]["code"] == "ABC"
    assert reg["access_token"] == "largo" and reg["ig_user_id"] == "17841" and reg["usuario"] == "lujis"


def test_error_de_instagram():
    class Mala(SesionFalsa):
        def post(self, *a, **k):
            return Resp({"error_type": "OAuthException", "error_message": "code ya usado"}, 400)

    with pytest.raises(instagram_login.ErrorLogin, match="code ya usado"):
        instagram_login.canjear_codigo("X", Mala())


def _registro(obtenido, vence):
    return {"access_token": "viejo", "ig_user_id": "1", "usuario": "u",
            "obtenido": obtenido.isoformat(), "vence": vence.isoformat()}


def test_token_se_renueva_cuando_faltan_menos_de_30_dias(tmp_path):
    ahora = datetime(2026, 10, 1, tzinfo=timezone.utc)
    ruta = tmp_path / "t.json"
    http = SesionFalsa()

    instagram_login.guardar(ruta, _registro(ahora - timedelta(days=40), ahora + timedelta(days=50)))
    assert instagram_login.token_vigente(ruta, "X", http, ahora)["access_token"] == "viejo"
    assert http.pedidos == []

    instagram_login.guardar(ruta, _registro(ahora - timedelta(days=40), ahora + timedelta(days=10)))
    assert instagram_login.token_vigente(ruta, "X", http, ahora)["access_token"] == "renovado"
    assert instagram_login.leer(ruta)["access_token"] == "renovado"


def test_token_vencido_o_inexistente(tmp_path):
    ahora = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with pytest.raises(SystemExit, match="no está conectado"):
        instagram_login.token_vigente(tmp_path / "no.json", "X")
    ruta = tmp_path / "t.json"
    instagram_login.guardar(ruta, _registro(ahora - timedelta(days=70), ahora - timedelta(days=1)))
    with pytest.raises(SystemExit, match="venció"):
        instagram_login.token_vigente(ruta, "X", ahora=ahora)


def test_cliente_instagram_usa_graph_instagram(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clientes.yaml").write_text(
        "clientes:\n  - nombre: LUJIS\n    conexion: instagram\n    notion_pagina_cliente: x\n",
        encoding="utf-8",
    )
    cfg = cargar_config()
    c = cfg.cliente("lujis")
    ahora = datetime.now(timezone.utc)
    instagram_login.guardar(instagram_login.ruta_token(cfg.dir_datos, c.slug),
                            {**_registro(ahora, ahora + timedelta(days=60)), "ig_user_id": "17841"})
    api, ig_id = cli._api_instagram(cfg, c)
    assert ig_id == "17841"
    assert api.base.startswith("https://graph.instagram.com/") and api.token == "viejo"


def test_cliente_facebook_sin_ig_user_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clientes.yaml").write_text(
        "clientes:\n  - nombre: HM\n    notion_pagina_cliente: x\n", encoding="utf-8")
    cfg = cargar_config()
    with pytest.raises(SystemExit, match="Falta ig_user_id"):
        cli._api_instagram(cfg, cfg.cliente("HM"))
    assert isinstance(instagram.InstagramAPI("t").base, str)
