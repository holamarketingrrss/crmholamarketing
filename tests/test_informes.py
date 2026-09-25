import json
from datetime import date

import pytest

from informes_ig import analisis, cli, metricas, notion


def media(id_, fecha, tipo="CAROUSEL_ALBUM", producto="FEED", caption="", **ins):
    return {
        "id": id_,
        "timestamp": fecha,
        "media_type": tipo,
        "media_product_type": producto,
        "caption": caption,
        "permalink": f"https://instagram.com/p/{id_}",
        "insights": ins,
    }


PUBLICACIONES = [
    media("1", "2026-03-04T13:00:00+0000", caption="Ideas de reels en MARZO\nGuardalo",
          reach=23668, saved=1415, shares=1021, likes=900, comments=40, follows=0),
    media("2", "2026-03-11T21:00:00+0000", caption="Nuevo kit! Comentá KIT y te lo mando",
          reach=2900, saved=75, shares=20, likes=100, comments=35, follows=0),
    media("3", "2026-04-02T13:00:00+0000", tipo="VIDEO", producto="REELS", caption="Recap evento",
          reach=2200, saved=16, shares=5, likes=80, comments=3, ig_reels_avg_watch_time=6500),
]


def test_metricas_formatos_top_y_cta():
    m = metricas.analizar(PUBLICACIONES, [], "America/Argentina/Buenos_Aires")
    assert m["total_publicaciones"] == 3
    assert m["por_formato"]["Carrusel"]["cantidad"] == 2
    assert m["por_formato"]["Reel"]["alcance"]["mediana"] == 2200
    assert m["top_alcance"][0]["titulo"] == "Ideas de reels en MARZO"
    assert m["frecuencia_por_mes"] == {"2026-03": 2, "2026-04": 1}
    assert m["cta_comenta_palabra"]["palabras_usadas"] == ["KIT"]
    assert m["cta_comenta_palabra"]["comentarios_promedio_con_cta"] == 35
    assert m["reels_tiempo_medio_visualizacion_s"]["mediana"] == 6.5
    # 13:00 UTC = 10:00 en Buenos Aires, un miércoles
    assert m["publicaciones"][0]["hora"] == 10 and m["publicaciones"][0]["dia"] == "miércoles"
    # seguidores ganados en 0 casi siempre → se marca como no confiable
    assert m["seguidores_ganados"]["dato_confiable"] is False
    assert m["historias"]["cantidad"] == 0


def test_metricas_historias():
    historias = [
        media("s1", "2026-03-04T13:00:00+0000", tipo="IMAGE", producto="STORY", reach=300, replies=4),
        media("s2", "2026-03-04T15:00:00+0000", tipo="IMAGE", producto="STORY", reach=250, replies=1),
    ]
    h = metricas.analizar([], historias, "UTC")["historias"]
    assert h["cantidad"] == 2 and h["dias_con_historias"] == 1
    assert h["alcance"]["promedio"] == 275


# -- Notion -------------------------------------------------------------------
def _opciones(*nombres):
    return {"options": [{"name": n} for n in nombres]}


# Esquemas reales: HOLAMARKETING (Estado + "Fecha de publicacion") y LUJIS (estado sin nombre).
ESQUEMA_HM = {
    "Name": {"id": "title", "type": "title"},
    "Estado": {"id": "est", "type": "status", "status": _opciones("Idea", "En guion", "Publicado")},
    "Formato": {"id": "fmt", "type": "select", "select": _opciones("Carrusel", "Reel", "Foto", "Stories")},
    "Pilar": {"id": "pil", "type": "select", "select": _opciones("Tendencia", "Clientes", "ClubHM")},
    "Fecha de publicacion": {"id": "fec", "type": "date", "date": {}},
    "Objetivo": {"id": "obj", "type": "rich_text", "rich_text": {}},
    "Desarrollo": {"id": "des", "type": "rich_text", "rich_text": {}},
    "Copy + CTA": {"id": "cop", "type": "rich_text", "rich_text": {}},
    "Hecho": {"id": "hec", "type": "url", "url": {}},
}
ESQUEMA_LUJIS = {
    "Name": {"id": "title", "type": "title"},
    "": {"id": "st2", "type": "status", "status": _opciones("Listo para Subir", "Idea", "Publicado")},
    "Formato": {"id": "fmt", "type": "select", "select": _opciones("Reel", "Carrusel", "Foto", "Stories")},
    "Pilar": {"id": "pil", "type": "select", "select": _opciones("Locacion", "Tendencia", "Producto")},
    "Fecha de publicación": {"id": "fec", "type": "date", "date": {}},
    "Desarrollo": {"id": "des", "type": "rich_text", "rich_text": {}},
}

IDEA = {
    "titulo": "5 ideas de reels para Halloween",
    "formato": "Carrusel",
    "pilar": "tendencia",
    "objetivo": "Guardados",
    "desarrollo": "Slide 1: ...\nSlide 2: ...",
    "copy_cta": "Guardalo y comentá IDEAS",
    "fecha_sugerida": "2026-10-08",
    "basado_en": "Los carruseles de ideas promedian 8.500 de alcance",
}


def test_esquema_holamarketing():
    e = notion.esquema_desde_propiedades("ds", ESQUEMA_HM)
    assert e.estado == {"id": "est", "tipo": "status", "opcion_idea": "Idea"}
    assert e.pilares == ["Tendencia", "Clientes", "ClubHM"]
    assert e.fecha == "fec"
    assert e.textos == {"objetivo": "obj", "desarrollo": "des", "copy_cta": "cop"}

    props, cuerpo = notion.propiedades_idea(e, IDEA)
    assert props["est"] == {"status": {"name": "Idea"}}
    assert props["fmt"] == {"select": {"name": "Carrusel"}}
    assert props["pil"] == {"select": {"name": "Tendencia"}}  # mapea sin mayúsculas
    assert props["fec"] == {"date": {"start": "2026-10-08"}}
    assert props["cop"]["rich_text"][0]["text"]["content"] == IDEA["copy_cta"]
    assert cuerpo[0]["type"] == "callout"


def test_esquema_lujis_estado_sin_nombre_y_columnas_faltantes():
    e = notion.esquema_desde_propiedades("ds", ESQUEMA_LUJIS)
    assert e.estado["id"] == "st2" and e.estado["opcion_idea"] == "Idea"
    props, cuerpo = notion.propiedades_idea(e, {**IDEA, "formato": "Historia", "pilar": "Branding nuevo"})
    assert props["st2"] == {"status": {"name": "Idea"}}
    assert props["fmt"] == {"select": {"name": "Stories"}}  # sinónimo
    assert "pil" not in props  # pilar inexistente → va al cuerpo
    textos = json.dumps(cuerpo, ensure_ascii=False)
    assert "Pilar sugerido" in textos and "Copy + CTA" in textos and "Objetivo" in textos


def test_texto_enriquecido_limites_y_formato():
    rt = notion.texto_enriquecido("Hola **negrita** y [link](https://x.com) " + "a" * 4500)
    assert rt[1]["annotations"] == {"bold": True}
    assert rt[3]["text"]["link"] == {"url": "https://x.com"}
    assert all(len(r["text"]["content"]) <= 2000 for r in rt)


def test_markdown_a_bloques():
    md = "## Título\nPárrafo uno\nsigue\n\n- viñeta\n1. número\n---\n| a | b |\n|---|---|\n| 1 | 2 |\n> cita"
    tipos = [b["type"] for b in notion.markdown_a_bloques(md)]
    assert tipos == ["heading_2", "paragraph", "bulleted_list_item", "numbered_list_item",
                     "divider", "table", "quote"]
    tabla = notion.markdown_a_bloques("| a | b |\n|---|---|\n| 1 | 2 |")[0]
    assert len(tabla["table"]["children"]) == 2


@pytest.mark.parametrize("valor", [
    "https://app.notion.com/p/300ed8741abb8040a062db7b645ed97f?pvs=204",
    "https://www.notion.so/HOLAMARKETING-300ed8741abb8040a062db7b645ed97f",
    "300ed874-1abb-8040-a062-db7b645ed97f",
])
def test_id_desde_url(valor):
    assert notion.id_desde_url(valor) == "300ed8741abb8040a062db7b645ed97f"


# -- Claude ---------------------------------------------------------------------
def test_esquema_claude_cerrado_y_con_enums():
    esquema = analisis._esquema(["Tendencia", "ClubHM"])
    idea = esquema["$defs"]["Idea"]
    assert idea["additionalProperties"] is False
    assert esquema["additionalProperties"] is False
    assert idea["properties"]["pilar"]["enum"] == ["Tendencia", "ClubHM"]
    assert idea["properties"]["formato"]["enum"] == ["Carrusel", "Reel", "Foto", "Stories"]


def test_prompt_incluye_estrategia_y_metricas():
    prompt = analisis.armar_prompt(
        "HM", "Ritmo editorial: 2 a 3 posteos semanales", {"total_publicaciones": 3}, {},
        {"posteos_mes": None}, [{"titulo": "Ya existe"}], (date(2026, 6, 1), date(2026, 9, 1)),
        "octubre 2026", ["Tendencia"],
    )
    assert "2 a 3 posteos semanales" in prompt and "Ya existe" in prompt
    assert "deducilo" in prompt and "octubre 2026" in prompt


def test_mes_siguiente():
    assert cli._mes_siguiente(date(2026, 12, 3)) == "2027-01"
    assert cli._mes_siguiente(date(2026, 9, 25)) == "2026-10"
    assert cli._mes_legible("2026-10") == "octubre 2026"
