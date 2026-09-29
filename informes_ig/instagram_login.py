"""Conexión de cuentas que solo tienen Instagram (sin Business Manager ni página de Facebook).

Usa la "Instagram API con inicio de sesión de Instagram":
1. `url_autorizacion()` arma el link que se le manda al cliente.
2. El cliente entra con su Instagram, acepta, y termina en la redirect URI con `?code=...`.
3. `canjear_codigo()` cambia ese código por un token de larga duración (60 días).
4. `token_vigente()` lo renueva solo cuando le quedan menos de 30 días.

Los tokens se guardan en datos/tokens/<cliente>.json (fuera del repo).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

GRAPH_IG = "https://graph.instagram.com"
AUTORIZAR = "https://www.instagram.com/oauth/authorize"
CANJE = "https://api.instagram.com/oauth/access_token"
PERMISOS = "instagram_business_basic,instagram_business_manage_insights"
RENOVAR_SI_QUEDAN = timedelta(days=30)


class ErrorLogin(RuntimeError):
    pass


def _app() -> tuple[str, str, str]:
    faltan = [v for v in ("INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET", "INSTAGRAM_REDIRECT_URI")
              if not os.environ.get(v)]
    if faltan:
        raise SystemExit(f"Faltan variables en .env: {', '.join(faltan)}")
    return (os.environ["INSTAGRAM_APP_ID"], os.environ["INSTAGRAM_APP_SECRET"],
            os.environ["INSTAGRAM_REDIRECT_URI"])


def url_autorizacion(estado: str = "") -> str:
    app_id, _, redirect = _app()
    params = {"client_id": app_id, "redirect_uri": redirect, "response_type": "code",
              "scope": PERMISOS, "enable_fb_login": "0"}
    if estado:
        params["state"] = estado
    return f"{AUTORIZAR}?{urlencode(params)}"


def extraer_codigo(texto: str) -> str:
    """Acepta el código solo o la URL completa a la que llegó el cliente."""
    texto = texto.strip()
    if "code=" in texto:
        texto = parse_qs(urlparse(texto).query).get("code", [texto])[0]
    return texto.split("#")[0]


def _json(r: requests.Response) -> dict:
    datos = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in datos or "error_type" in datos:
        err = datos.get("error", datos)
        mensaje = err.get("message") or err.get("error_message") if isinstance(err, dict) else err
        raise ErrorLogin(f"Instagram rechazó el pedido: {mensaje or r.text[:300]}")
    return datos


def canjear_codigo(codigo: str, http: requests.Session | None = None) -> dict:
    http = http or requests.Session()
    app_id, secreto, redirect = _app()
    corto = _json(http.post(CANJE, data={
        "client_id": app_id, "client_secret": secreto, "grant_type": "authorization_code",
        "redirect_uri": redirect, "code": extraer_codigo(codigo),
    }, timeout=60))
    largo = _json(http.get(f"{GRAPH_IG}/access_token", params={
        "grant_type": "ig_exchange_token", "client_secret": secreto,
        "access_token": corto["access_token"],
    }, timeout=60))
    perfil = _json(http.get(f"{GRAPH_IG}/me", params={
        "fields": "user_id,username", "access_token": largo["access_token"],
    }, timeout=60))
    return _registro(largo, perfil.get("user_id") or str(corto.get("user_id", "")),
                     perfil.get("username", ""))


def _registro(respuesta: dict, user_id: str, usuario: str) -> dict:
    ahora = datetime.now(timezone.utc)
    return {
        "access_token": respuesta["access_token"],
        "ig_user_id": str(user_id),
        "usuario": usuario,
        "obtenido": ahora.isoformat(),
        "vence": (ahora + timedelta(seconds=int(respuesta.get("expires_in", 5184000)))).isoformat(),
    }


def ruta_token(dir_datos: Path, slug: str) -> Path:
    return dir_datos / "tokens" / f"{slug}.json"


def guardar(ruta: Path, registro: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(registro, indent=2), encoding="utf-8")
    try:
        ruta.chmod(0o600)
    except OSError:
        pass


def leer(ruta: Path) -> dict | None:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def token_vigente(ruta: Path, nombre: str, http: requests.Session | None = None,
                  ahora: datetime | None = None) -> dict:
    """Devuelve el registro del token, renovándolo si le quedan menos de 30 días."""
    registro = leer(ruta)
    if not registro:
        raise SystemExit(f"{nombre} no está conectado. Corré: python -m informes_ig conectar --cliente \"{nombre}\"")
    ahora = ahora or datetime.now(timezone.utc)
    vence = datetime.fromisoformat(registro["vence"])
    if vence <= ahora:
        raise SystemExit(f"El permiso de {nombre} venció el {vence:%d/%m/%Y}. "
                         f"Hay que volver a conectarlo con `conectar`.")
    obtenido = datetime.fromisoformat(registro["obtenido"])
    # Meta solo deja renovar tokens con más de 24 h.
    if vence - ahora < RENOVAR_SI_QUEDAN and ahora - obtenido > timedelta(hours=24):
        http = http or requests.Session()
        nuevo = _json(http.get(f"{GRAPH_IG}/refresh_access_token", params={
            "grant_type": "ig_refresh_token", "access_token": registro["access_token"],
        }, timeout=60))
        registro = _registro(nuevo, registro["ig_user_id"], registro.get("usuario", ""))
        guardar(ruta, registro)
    return registro
