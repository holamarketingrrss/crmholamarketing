"""Cálculos sobre las publicaciones: formatos, mejores posteos, frecuencia y horarios.

Los números se calculan acá (en Python) y no los inventa el modelo: Claude
recibe este resumen ya hecho y se encarga de interpretarlo y proponer ideas.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# "Comentá KIT", "comenta \"GUIA\"", "Comentá la palabra PLAN"...
RE_COMENTA_PALABRA = re.compile(
    r"coment[aá](?:\s+la\s+palabra)?\s*[\"“'«]?([A-ZÁÉÍÓÚÑ0-9]{2,})", re.IGNORECASE
)


def formato_de(media: dict) -> str:
    if media.get("media_product_type") == "REELS":
        return "Reel"
    if media.get("media_product_type") == "STORY":
        return "Stories"
    return {"CAROUSEL_ALBUM": "Carrusel", "IMAGE": "Foto", "VIDEO": "Reel"}.get(
        media.get("media_type", ""), "Foto"
    )


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


def normalizar(media: dict, tz: ZoneInfo) -> dict:
    ins = media.get("insights", {})
    fecha = datetime.strptime(media["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz)
    caption = (media.get("caption") or "").strip()
    likes = ins.get("likes", media.get("like_count"))
    comentarios = ins.get("comments", media.get("comments_count"))
    p = {
        "id": media["id"],
        "fecha": fecha.isoformat(timespec="minutes"),
        "dia": DIAS[fecha.weekday()],
        "hora": fecha.hour,
        "formato": formato_de(media),
        "titulo": _primera_linea(caption),
        "caption": caption,
        "link": media.get("permalink"),
        "alcance": _num(ins.get("reach")),
        "vistas": _num(ins.get("views")),
        "guardados": _num(ins.get("saved")),
        "compartidos": _num(ins.get("shares")),
        "likes": _num(likes),
        "comentarios": _num(comentarios),
        "seguidores_ganados": ins.get("follows"),
        "visitas_perfil": ins.get("profile_visits"),
        "respuestas": _num(ins.get("replies")),
        "tiempo_medio_visualizacion_s": _ms_a_s(ins.get("ig_reels_avg_watch_time")),
    }
    interacciones = p["guardados"] + p["compartidos"] + p["likes"] + p["comentarios"]
    p["tasa_interaccion"] = round(interacciones / p["alcance"], 4) if p["alcance"] else 0.0
    palabra = RE_COMENTA_PALABRA.search(caption)
    p["cta_comenta_palabra"] = palabra.group(1).upper() if palabra else None
    return p


def _ms_a_s(v):
    return round(v / 1000, 1) if isinstance(v, (int, float)) else None


def _primera_linea(texto: str, largo: int = 90) -> str:
    linea = next((l.strip() for l in texto.splitlines() if l.strip()), "(sin texto)")
    return linea if len(linea) <= largo else linea[: largo - 1] + "…"


def _stats(valores: list[float]) -> dict:
    if not valores:
        return {"promedio": 0, "mediana": 0}
    return {
        "promedio": round(statistics.mean(valores), 1),
        "mediana": round(statistics.median(valores), 1),
    }


def _resumen_grupo(posts: list[dict]) -> dict:
    return {
        "cantidad": len(posts),
        "alcance": _stats([p["alcance"] for p in posts]),
        "guardados": _stats([p["guardados"] for p in posts]),
        "compartidos": _stats([p["compartidos"] for p in posts]),
        "comentarios": _stats([p["comentarios"] for p in posts]),
        "tasa_interaccion": _stats([p["tasa_interaccion"] for p in posts]),
    }


def _compacto(p: dict) -> dict:
    return {
        k: p[k]
        for k in (
            "fecha", "formato", "titulo", "alcance", "guardados", "compartidos",
            "comentarios", "tiempo_medio_visualizacion_s", "link",
        )
        if p.get(k) is not None
    }


def analizar(publicaciones: list[dict], historias: list[dict], zona_horaria: str) -> dict:
    tz = ZoneInfo(zona_horaria)
    posts = sorted((normalizar(m, tz) for m in publicaciones), key=lambda p: p["fecha"])
    stories = sorted((normalizar(h, tz) for h in historias), key=lambda p: p["fecha"])

    por_formato = defaultdict(list)
    for p in posts:
        por_formato[p["formato"]].append(p)

    por_mes = defaultdict(int)
    for p in posts:
        por_mes[p["fecha"][:7]] += 1

    por_dia = defaultdict(list)
    por_franja = defaultdict(list)
    for p in posts:
        por_dia[p["dia"]].append(p["alcance"])
        por_franja[_franja(p["hora"])].append(p["alcance"])

    con_cta = [p for p in posts if p["cta_comenta_palabra"]]
    sin_cta = [p for p in posts if not p["cta_comenta_palabra"]]

    seguidores = [p["seguidores_ganados"] for p in posts if p["seguidores_ganados"] is not None]
    seguidores_confiable = bool(seguidores) and sum(1 for s in seguidores if s) >= len(seguidores) / 3

    reels = por_formato.get("Reel", [])
    tiempos = [p["tiempo_medio_visualizacion_s"] for p in reels if p["tiempo_medio_visualizacion_s"]]

    return {
        "zona_horaria": zona_horaria,
        "total_publicaciones": len(posts),
        "periodo_real": {
            "primera": posts[0]["fecha"] if posts else None,
            "ultima": posts[-1]["fecha"] if posts else None,
        },
        "por_formato": {f: _resumen_grupo(ps) for f, ps in por_formato.items()},
        "top_alcance": [_compacto(p) for p in sorted(posts, key=lambda p: -p["alcance"])[:5]],
        "top_guardados": [_compacto(p) for p in sorted(posts, key=lambda p: -p["guardados"])[:5]],
        "top_comentarios": [_compacto(p) for p in sorted(posts, key=lambda p: -p["comentarios"])[:3]],
        "peores_alcance": [_compacto(p) for p in sorted(posts, key=lambda p: p["alcance"])[:3]],
        "frecuencia_por_mes": dict(sorted(por_mes.items())),
        "alcance_mediano_por_dia": _ordenar_dias({d: _stats(v)["mediana"] for d, v in por_dia.items()}),
        "publicaciones_por_dia": _ordenar_dias({d: len(v) for d, v in por_dia.items()}),
        "alcance_mediano_por_franja": {f: {"mediana": _stats(v)["mediana"], "publicaciones": len(v)} for f, v in sorted(por_franja.items())},
        "cta_comenta_palabra": {
            "posts_con_cta": len(con_cta),
            "comentarios_promedio_con_cta": _stats([p["comentarios"] for p in con_cta])["promedio"],
            "comentarios_promedio_sin_cta": _stats([p["comentarios"] for p in sin_cta])["promedio"],
            "palabras_usadas": sorted({p["cta_comenta_palabra"] for p in con_cta}),
        },
        "reels_tiempo_medio_visualizacion_s": _stats(tiempos) if tiempos else None,
        "seguidores_ganados": {
            "dato_confiable": seguidores_confiable,
            "total": sum(s for s in seguidores if isinstance(s, (int, float))),
        },
        "historias": _resumen_historias(stories),
        "publicaciones": [
            {**_compacto(p), "caption": p["caption"][:400], "dia": p["dia"], "hora": p["hora"]}
            for p in posts
        ],
    }


def _resumen_historias(stories: list[dict]) -> dict:
    if not stories:
        return {
            "cantidad": 0,
            "nota": "Sin historias capturadas en el período (la API solo da las últimas 24 h; "
            "hay que correr `snapshot-historias` todos los días).",
        }
    dias = {s["fecha"][:10] for s in stories}
    return {
        "cantidad": len(stories),
        "dias_con_historias": len(dias),
        "historias_por_dia_activo": round(len(stories) / len(dias), 1),
        "alcance": _stats([s["alcance"] for s in stories]),
        "respuestas": _stats([s["respuestas"] for s in stories]),
        "top_alcance": [
            {"fecha": s["fecha"], "texto": s["titulo"], "alcance": s["alcance"], "respuestas": s["respuestas"]}
            for s in sorted(stories, key=lambda s: -s["alcance"])[:5]
        ],
    }


def _franja(hora: int) -> str:
    if hora < 9:
        return "00-09"
    if hora < 12:
        return "09-12"
    if hora < 15:
        return "12-15"
    if hora < 18:
        return "15-18"
    if hora < 21:
        return "18-21"
    return "21-24"


def _ordenar_dias(d: dict) -> dict:
    return {dia: d[dia] for dia in DIAS if dia in d}
