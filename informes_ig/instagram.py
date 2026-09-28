"""Cliente mínimo de la Instagram Graph API (Instagram API con Facebook Login).

Trae las publicaciones de un período con sus métricas, y guarda "fotos" de las
historias activas (la API solo devuelve historias de las últimas 24 horas, por
eso hay que capturarlas todos los días y acumularlas).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com"

CAMPOS_MEDIA = (
    "id,caption,media_type,media_product_type,timestamp,permalink,"
    "like_count,comments_count"
)

# Métricas por tipo. Si Meta rechaza alguna (cambian seguido), se reintenta
# con el conjunto mínimo.
METRICAS_FEED = [
    "reach", "saved", "shares", "views", "likes", "comments",
    "total_interactions", "follows", "profile_visits",
]
METRICAS_REEL = [
    "reach", "saved", "shares", "views", "likes", "comments",
    "total_interactions", "ig_reels_avg_watch_time", "ig_reels_video_view_total_time",
]
METRICAS_STORY = [
    "reach", "views", "replies", "shares", "total_interactions",
    "follows", "profile_visits", "navigation",
]
METRICAS_MINIMAS = ["reach", "saved", "shares"]
METRICAS_MINIMAS_STORY = ["reach", "replies"]


class ErrorMeta(RuntimeError):
    pass


class InstagramAPI:
    def __init__(self, token: str, version: str = "v23.0", sesion: requests.Session | None = None,
                 host: str = GRAPH):
        self.token = token
        self.base = f"{host}/{version}"
        self.http = sesion or requests.Session()

    # -- HTTP -----------------------------------------------------------------
    def _get(self, url: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        if "access_token=" not in url:
            params["access_token"] = self.token
        for intento in range(4):
            r = self.http.get(url, params=params, timeout=60)
            if r.status_code in (429, 500, 502, 503) and intento < 3:
                time.sleep(2 ** (intento + 1))
                continue
            datos = r.json() if r.content else {}
            if r.status_code >= 400 or "error" in datos:
                err = datos.get("error", {})
                raise ErrorMeta(f"{err.get('code')} {err.get('message', r.text)}")
            return datos
        raise ErrorMeta("Meta no respondió después de varios intentos")

    def _paginar(self, url: str, params: dict) -> list[dict]:
        items: list[dict] = []
        datos = self._get(url, params)
        while True:
            items.extend(datos.get("data", []))
            siguiente = datos.get("paging", {}).get("next")
            if not siguiente:
                return items
            datos = self._get(siguiente)

    # -- Cuenta ---------------------------------------------------------------
    def cuentas_disponibles(self) -> list[dict]:
        """Lista las páginas de Facebook del token con su cuenta de IG vinculada."""
        paginas = self._paginar(
            f"{self.base}/me/accounts",
            {"fields": "name,instagram_business_account{id,username,followers_count}", "limit": 100},
        )
        return [
            {
                "pagina": p.get("name"),
                "ig_user_id": p["instagram_business_account"]["id"],
                "usuario": p["instagram_business_account"].get("username"),
                "seguidores": p["instagram_business_account"].get("followers_count"),
            }
            for p in paginas
            if p.get("instagram_business_account")
        ]

    def perfil(self, ig_user_id: str) -> dict:
        return self._get(
            f"{self.base}/{ig_user_id}",
            {"fields": "username,name,followers_count,follows_count,media_count"},
        )

    # -- Publicaciones --------------------------------------------------------
    def publicaciones(self, ig_user_id: str, desde: datetime, hasta: datetime) -> list[dict]:
        """Publicaciones del feed (carruseles, fotos y reels) con sus métricas."""
        crudas = self._paginar(
            f"{self.base}/{ig_user_id}/media",
            {
                "fields": CAMPOS_MEDIA,
                "since": int(desde.timestamp()),
                "until": int(hasta.timestamp()),
                "limit": 50,
            },
        )
        resultado = []
        for m in crudas:
            fecha = _parse_fecha(m["timestamp"])
            if not (desde <= fecha <= hasta):
                continue
            es_reel = m.get("media_product_type") == "REELS"
            m["insights"] = self.insights(
                m["id"], METRICAS_REEL if es_reel else METRICAS_FEED, METRICAS_MINIMAS
            )
            resultado.append(m)
        return resultado

    def insights(self, media_id: str, metricas: list[str], minimas: list[str]) -> dict:
        for conjunto in (metricas, minimas):
            try:
                datos = self._get(
                    f"{self.base}/{media_id}/insights", {"metric": ",".join(conjunto)}
                )
                return {d["name"]: _valor_metrica(d) for d in datos.get("data", [])}
            except ErrorMeta:
                continue
        return {}

    # -- Historias ------------------------------------------------------------
    def historias_activas(self, ig_user_id: str) -> list[dict]:
        crudas = self._paginar(
            f"{self.base}/{ig_user_id}/stories",
            {"fields": "id,caption,media_type,timestamp,permalink", "limit": 50},
        )
        for h in crudas:
            h["insights"] = self.insights(h["id"], METRICAS_STORY, METRICAS_MINIMAS_STORY)
        return crudas


def _valor_metrica(dato: dict):
    if "total_value" in dato:
        tv = dato["total_value"]
        if "breakdowns" in tv:
            return {
                r["dimension_values"][0]: r["value"]
                for b in tv["breakdowns"]
                for r in b.get("results", [])
            }
        return tv.get("value")
    valores = dato.get("values") or [{}]
    return valores[0].get("value")


def _parse_fecha(texto: str) -> datetime:
    # Meta devuelve "2025-11-14T13:00:00+0000"
    return datetime.strptime(texto, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)


# -- Almacenamiento local de historias ----------------------------------------
def guardar_historias(ruta: Path, historias: list[dict]) -> int:
    """Agrega/actualiza historias en un .jsonl (se queda con la captura más nueva)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    existentes = {h["id"]: h for h in leer_historias(ruta)}
    ahora = datetime.now(timezone.utc).isoformat()
    for h in historias:
        h["capturado"] = ahora
        existentes[h["id"]] = h
    with ruta.open("w", encoding="utf-8") as f:
        for h in sorted(existentes.values(), key=lambda x: x["timestamp"]):
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    return len(historias)


def leer_historias(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
