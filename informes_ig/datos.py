"""Trae los datos de Instagram de una cuenta y calcula las métricas, sin Notion ni Claude API.

Pensado para las rutinas de Claude: la rutina corre esto, lee el JSON y escribe
el informe y las ideas en Notion con el conector.

    python -m informes_ig.datos --ig-id 17841449615689473 --dias 90
    python -m informes_ig.datos --ig-id 17841449615689473 --desde 2026-06-01 --hasta 2026-09-30

    # Cuenta conectada por inicio de sesión de Instagram, con su propio token:
    python -m informes_ig.datos --ig-id 17841468353440281 --instagram-login --token-env IG_TOKEN_LUJIS

Por defecto lee el token de META_ACCESS_TOKEN.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone

import requests

from . import instagram, instagram_login, metricas


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="informes_ig.datos", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ig-id", required=True, help="ID de la cuenta de Instagram")
    ap.add_argument("--dias", type=int, default=90, help="Días hacia atrás (default 90)")
    ap.add_argument("--desde", type=date.fromisoformat, help="AAAA-MM-DD (pisa --dias)")
    ap.add_argument("--hasta", type=date.fromisoformat, help="AAAA-MM-DD (default hoy)")
    ap.add_argument("--zona-horaria", default="America/Argentina/Buenos_Aires")
    ap.add_argument("--version", default=os.environ.get("META_API_VERSION", "v23.0"))
    ap.add_argument("--token-env", default="META_ACCESS_TOKEN",
                    help="Variable con el token (default META_ACCESS_TOKEN)")
    ap.add_argument("--instagram-login", action="store_true",
                    help="Cuenta conectada por inicio de sesión de Instagram (graph.instagram.com)")
    args = ap.parse_args(argv)

    token = os.environ.get(args.token_env)
    if not token:
        sys.exit(f"Falta la variable {args.token_env}")

    aviso_token = None
    if args.instagram_login:
        token, aviso_token = _renovar_token_instagram(token, args.token_env)

    hasta = args.hasta or date.today()
    desde = args.desde or hasta - timedelta(days=args.dias)
    inicio = datetime.combine(desde, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(hasta, time.max, tzinfo=timezone.utc)

    host = instagram_login.GRAPH_IG if args.instagram_login else instagram.GRAPH
    api = instagram.InstagramAPI(token, args.version, host=host)
    perfil = api.perfil(args.ig_id)
    publicaciones = api.publicaciones(args.ig_id, inicio, fin)
    resultado = {
        "perfil": perfil,
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "metricas": metricas.analizar(publicaciones, [], args.zona_horaria),
    }
    if aviso_token:
        resultado["aviso_token"] = aviso_token
    json.dump(resultado, sys.stdout, ensure_ascii=False, indent=2, default=str)
    print()


def _renovar_token_instagram(token: str, variable: str) -> tuple[str, str | None]:
    """Extiende el token de Instagram otros 60 días. Si Meta devuelve uno distinto, avisa."""
    r = requests.get(f"{instagram_login.GRAPH_IG}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=60)
    datos = r.json() if r.content else {}
    if r.status_code >= 400 or "access_token" not in datos:
        error = datos.get("error", {}).get("message", r.text[:200])
        return token, f"No se pudo renovar {variable}: {error}. Si venció, hay que generar uno nuevo."
    dias = int(datos.get("expires_in", 0)) // 86400
    if datos["access_token"] != token:
        return datos["access_token"], (
            f"Meta devolvió un token nuevo para {variable} (vence en {dias} días): "
            "hay que reemplazarlo en la configuración del entorno."
        )
    return token, None


if __name__ == "__main__":
    main()
