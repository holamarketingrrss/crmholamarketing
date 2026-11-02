"""Revisa perfiles públicos de creadoras UGC con Business Discovery de Meta.

Pensado para la rutina de evaluación de UGC (ver UGC.md): la rutina corre esto con
los usuarios de Instagram de la base de Notion, lee el JSON y escribe el informe.

    python -m informes_ig.ugc --usuario lindatucasa --usuario _belenparedes_

Business Discovery solo ve cuentas de creador o de empresa. Las cuentas personales,
privadas o inexistentes vuelven con "visible": false y el motivo.
Usa META_ACCESS_TOKEN y la cuenta de @holamarketing como cuenta desde la que se consulta.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from statistics import median

from . import instagram

CUENTA_CONSULTA = "17841449615689473"  # @holamarketing

CAMPOS = (
    "business_discovery.username({u}){{username,name,biography,website,followers_count,"
    "media_count,media.limit(30){{timestamp,like_count,comments_count,media_type,"
    "media_product_type,permalink,caption}}}}"
)


def limpiar_usuario(texto: str) -> str | None:
    """Acepta @usuario, usuario o un link de Instagram y devuelve solo el usuario."""
    t = (texto or "").strip().replace("\\", "")
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", t)
    if m:
        t = m.group(1)
    t = t.lstrip("@").strip(".")
    return t if re.fullmatch(r"[A-Za-z0-9_.]{1,30}", t) else None


def evaluar(perfil: dict, ahora: datetime | None = None) -> dict:
    """Métricas de actividad e interacción a partir de la respuesta de Business Discovery."""
    ahora = ahora or datetime.now(timezone.utc)
    seguidores = perfil.get("followers_count") or 0
    posteos = perfil.get("media", {}).get("data", [])
    fechas = [_fecha(p["timestamp"]) for p in posteos if p.get("timestamp")]
    ultimo = max(fechas) if fechas else None
    dias_ultimo = (ahora - ultimo).days if ultimo else None
    en_30 = sum(1 for f in fechas if (ahora - f).days <= 30)
    en_90 = sum(1 for f in fechas if (ahora - f).days <= 90)

    recientes = posteos[:12]
    interacciones = [
        (p.get("like_count") or 0) + (p.get("comments_count") or 0)
        for p in recientes if p.get("like_count") is not None
    ]
    likes_ocultos = len(recientes) - len(interacciones)
    tasa = round(100 * median(interacciones) / seguidores, 2) if interacciones and seguidores else None
    reels = sum(1 for p in recientes if p.get("media_product_type") == "REELS")

    m = {
        "seguidores": seguidores,
        "publicaciones_totales": perfil.get("media_count"),
        "dias_desde_ultimo_posteo": dias_ultimo,
        "posteos_ultimos_30_dias": en_30,
        "posteos_ultimos_90_dias": en_90,
        "interacciones_mediana": median(interacciones) if interacciones else None,
        "tasa_interaccion_pct": tasa,
        "posteos_con_likes_ocultos": likes_ocultos,
        "porcentaje_reels": round(100 * reels / len(recientes)) if recientes else None,
        "mejores_posteos": [
            {"link": p.get("permalink"), "likes": p.get("like_count"), "comentarios": p.get("comments_count"),
             "tipo": p.get("media_product_type"), "texto": (p.get("caption") or "")[:120]}
            for p in sorted(recientes, key=lambda p: -((p.get("like_count") or 0) + (p.get("comments_count") or 0)))[:3]
        ],
    }
    m["sugerencia"] = sugerencia(m)
    return m


def sugerencia(m: dict) -> str:
    """Semáforo de base; la rutina lo puede ajustar mirando el contenido."""
    dias = m["dias_desde_ultimo_posteo"]
    if dias is None or dias > 60 or m["posteos_ultimos_90_dias"] == 0:
        return "🔴 No"
    tasa = m["tasa_interaccion_pct"]
    activa = dias <= 14 and m["posteos_ultimos_30_dias"] >= 4
    # Con muchos seguidores la tasa natural baja; 1% en cuentas grandes equivale a 2% en chicas.
    umbral = 1.0 if m["seguidores"] >= 50_000 else 2.0
    if activa and tasa is not None and tasa >= umbral:
        return "🟢 Recomendada"
    return "🟡 Revisar"


def revisar(api: instagram.InstagramAPI, usuario: str, cuenta: str = CUENTA_CONSULTA) -> dict:
    limpio = limpiar_usuario(usuario)
    if not limpio:
        return {"usuario": usuario, "visible": False, "motivo": "El usuario de Instagram no es válido"}
    try:
        datos = api._get(f"{api.base}/{cuenta}", {"fields": CAMPOS.format(u=limpio)})
    except instagram.ErrorMeta as e:
        motivo = "Cuenta personal, privada o inexistente (Meta no la muestra)" if "110" in str(e) or "find" in str(e).lower() else str(e)
        return {"usuario": limpio, "visible": False, "motivo": motivo}
    perfil = datos.get("business_discovery") or {}
    return {
        "usuario": limpio,
        "visible": True,
        "nombre": perfil.get("name"),
        "bio": perfil.get("biography"),
        "web": perfil.get("website"),
        "metricas": evaluar(perfil),
    }


def _fecha(texto: str) -> datetime:
    return datetime.strptime(texto, "%Y-%m-%dT%H:%M:%S%z")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="informes_ig.ugc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--usuario", action="append", required=True, help="Usuario o link de Instagram (repetible)")
    ap.add_argument("--cuenta", default=CUENTA_CONSULTA, help="IG ID desde el que se consulta")
    ap.add_argument("--version", default=os.environ.get("META_API_VERSION", "v23.0"))
    args = ap.parse_args(argv)

    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        sys.exit("Falta la variable META_ACCESS_TOKEN")
    api = instagram.InstagramAPI(token, args.version)
    json.dump([revisar(api, u, args.cuenta) for u in args.usuario], sys.stdout,
              ensure_ascii=False, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
