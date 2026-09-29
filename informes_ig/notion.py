"""Cliente mínimo de la API de Notion (versión 2025-09-03, con data sources).

- Descubre, dentro de la página de cada cliente, las subpáginas "Estrategia" y
  "Planificación de contenido" y la base "Plan de publicaciones".
- Lee el texto de la estrategia (pilares, ritmo editorial, tono, objetivos).
- Crea filas en el plan con Estado = Idea y crea la página del informe.

Los esquemas de las bases no son idénticos entre clientes (por ejemplo, en
algunos la propiedad de estado no tiene nombre, o la fecha se llama "Fecha de
publicacion" sin tilde), así que las propiedades se detectan por tipo y por
nombre aproximado, y se escriben usando su id.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field

import requests

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"
MAX_TEXTO = 2000  # límite de caracteres por objeto rich_text
MAX_BLOQUES = 100  # límite de bloques por request


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).strip()


def id_desde_url(valor: str) -> str:
    """Acepta un id con o sin guiones, o una URL de Notion."""
    ruta = valor.split("?")[0].split("#")[0].replace("-", "")
    corridas = re.findall(r"[0-9a-fA-F]{32,}", ruta)
    return corridas[-1][-32:] if corridas else valor


class ErrorNotion(RuntimeError):
    pass


class NotionAPI:
    def __init__(self, token: str, sesion: requests.Session | None = None):
        if not token:
            raise SystemExit("Falta NOTION_TOKEN (token de la integración interna de Notion).")
        self.http = sesion or requests.Session()
        self.http.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": VERSION,
                "Content-Type": "application/json",
            }
        )

    def _req(self, metodo: str, ruta: str, **kwargs) -> dict:
        for intento in range(5):
            r = self.http.request(metodo, f"{API}{ruta}", timeout=60, **kwargs)
            if r.status_code in (429, 502, 503, 504) and intento < 4:
                time.sleep(float(r.headers.get("Retry-After", 2 ** intento)))
                continue
            if r.status_code >= 400:
                raise ErrorNotion(f"{metodo} {ruta} → {r.status_code}: {r.text[:500]}")
            return r.json()
        raise ErrorNotion(f"{metodo} {ruta}: demasiados reintentos")

    # -- Lectura ---------------------------------------------------------------
    def hijos(self, bloque_id: str) -> list[dict]:
        resultado, cursor = [], None
        while True:
            params = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
            datos = self._req("GET", f"/blocks/{bloque_id}/children", params=params)
            resultado.extend(datos["results"])
            if not datos.get("has_more"):
                return resultado
            cursor = datos["next_cursor"]

    def pagina(self, pagina_id: str) -> dict:
        return self._req("GET", f"/pages/{pagina_id}")

    def base(self, base_id: str) -> dict:
        return self._req("GET", f"/databases/{base_id}")

    def data_source(self, ds_id: str) -> dict:
        return self._req("GET", f"/data_sources/{ds_id}")

    def consultar(self, ds_id: str, cuerpo: dict | None = None, limite: int = 100) -> list[dict]:
        resultado, cursor = [], None
        while len(resultado) < limite:
            body = {"page_size": min(100, limite - len(resultado)), **(cuerpo or {})}
            if cursor:
                body["start_cursor"] = cursor
            datos = self._req("POST", f"/data_sources/{ds_id}/query", json=body)
            resultado.extend(datos["results"])
            if not datos.get("has_more"):
                break
            cursor = datos["next_cursor"]
        return resultado

    def recorrer(self, bloque_id: str, profundidad: int = 0, max_prof: int = 6):
        """Genera (bloque, profundidad) recorriendo columnas, callouts, toggles, etc.

        No entra en subpáginas ni bases (son contenido aparte)."""
        for b in self.hijos(bloque_id):
            yield b, profundidad
            if (
                b.get("has_children")
                and b["type"] not in ("child_page", "child_database")
                and profundidad < max_prof
            ):
                yield from self.recorrer(b["id"], profundidad + 1, max_prof)

    def texto_de_pagina(self, pagina_id: str) -> str:
        """Texto plano (markdown aproximado) de una página, incluyendo columnas y callouts."""
        lineas = []
        for b, _ in self.recorrer(pagina_id):
            t = b["type"]
            contenido = b.get(t, {})
            texto = "".join(rt.get("plain_text", "") for rt in contenido.get("rich_text", []))
            if t == "table_row":
                celdas = [
                    "".join(rt.get("plain_text", "") for rt in celda) for celda in contenido.get("cells", [])
                ]
                texto = " | ".join(celdas)
            if not texto.strip():
                continue
            prefijo = {
                "heading_1": "# ", "heading_2": "## ", "heading_3": "### ",
                "bulleted_list_item": "- ", "numbered_list_item": "1. ",
                "to_do": "- [ ] ", "quote": "> ",
            }.get(t, "")
            if t.startswith("heading"):
                lineas.append("")
            lineas.append(prefijo + texto)
        return "\n".join(lineas)

    # -- Escritura -------------------------------------------------------------
    def crear_pagina(self, padre: dict, propiedades: dict, bloques: list[dict] | None = None,
                     icono: str | None = None) -> dict:
        bloques = bloques or []
        cuerpo = {"parent": padre, "properties": propiedades, "children": bloques[:MAX_BLOQUES]}
        if icono:
            cuerpo["icon"] = {"type": "emoji", "emoji": icono}
        pagina = self._req("POST", "/pages", json=cuerpo)
        for i in range(MAX_BLOQUES, len(bloques), MAX_BLOQUES):
            self.agregar_bloques(pagina["id"], bloques[i : i + MAX_BLOQUES])
        return pagina

    def agregar_bloques(self, bloque_id: str, bloques: list[dict]) -> None:
        for i in range(0, len(bloques), MAX_BLOQUES):
            self._req("PATCH", f"/blocks/{bloque_id}/children", json={"children": bloques[i : i + MAX_BLOQUES]})


# ---------------------------------------------------------------------------
# Estructura del portal del cliente
# ---------------------------------------------------------------------------
@dataclass
class PortalCliente:
    pagina_cliente: str
    estrategia: str | None
    plan_data_source: str | None
    plan_base: str | None = None


def descubrir_portal(api: NotionAPI, pagina_cliente: str, estrategia: str | None = None,
                     plan_base: str | None = None) -> PortalCliente:
    pagina_cliente = id_desde_url(pagina_cliente)
    planificacion = None
    if not estrategia or not plan_base:
        for b, _ in api.recorrer(pagina_cliente, max_prof=4):
            titulo, pid = _titulo_y_id(api, b)
            if not pid:
                continue
            n = normalizar(titulo)
            if not estrategia and n.startswith("estrategia"):
                estrategia = pid
            elif not planificacion and n.startswith("planificacion"):
                planificacion = pid

    if not plan_base and planificacion:
        for b, _ in api.recorrer(planificacion, max_prof=3):
            if b["type"] == "child_database":
                plan_base = b["id"]
                break

    ds = None
    if plan_base:
        plan_base = id_desde_url(plan_base)
        fuentes = api.base(plan_base).get("data_sources", [])
        if fuentes:
            ds = fuentes[0]["id"]
    return PortalCliente(pagina_cliente, estrategia and id_desde_url(estrategia), ds, plan_base)


def _titulo_y_id(api: NotionAPI, bloque: dict) -> tuple[str, str | None]:
    if bloque["type"] == "child_page":
        return bloque["child_page"]["title"], bloque["id"]
    if bloque["type"] == "link_to_page" and bloque["link_to_page"].get("type") == "page_id":
        pid = bloque["link_to_page"]["page_id"]
        try:
            props = api.pagina(pid)["properties"]
        except ErrorNotion:
            return "", None
        titulo = next(
            ("".join(t["plain_text"] for t in p["title"]) for p in props.values() if p["type"] == "title"),
            "",
        )
        return titulo, pid
    return "", None


# ---------------------------------------------------------------------------
# Esquema del "Plan de publicaciones"
# ---------------------------------------------------------------------------
@dataclass
class EsquemaPlan:
    data_source_id: str
    titulo: str
    estado: dict | None = None  # {"id", "tipo", "opcion_idea"}
    formato: dict | None = None  # {"id", "opciones"}
    pilar: dict | None = None  # {"id", "opciones"}
    fecha: str | None = None
    textos: dict[str, str] = field(default_factory=dict)  # objetivo/desarrollo/copy → id

    @property
    def pilares(self) -> list[str]:
        return self.pilar["opciones"] if self.pilar else []


def leer_esquema(api: NotionAPI, ds_id: str) -> EsquemaPlan:
    props = api.data_source(ds_id)["properties"]
    return esquema_desde_propiedades(ds_id, props)


def esquema_desde_propiedades(ds_id: str, props: dict) -> EsquemaPlan:
    por_tipo: dict[str, list[dict]] = {}
    for nombre, p in props.items():
        por_tipo.setdefault(p["type"], []).append({**p, "name": nombre})

    titulo = por_tipo["title"][0]["id"]
    esquema = EsquemaPlan(ds_id, titulo)

    # Estado: la primera propiedad "status"; si no hay, un select llamado Estado.
    candidatos = por_tipo.get("status", []) + [
        p for p in por_tipo.get("select", []) if normalizar(p["name"]) == "estado"
    ]
    if candidatos:
        p = candidatos[0]
        opciones = [o["name"] for o in p[p["type"]].get("options", [])]
        idea = next((o for o in opciones if normalizar(o) == "idea"), None)
        esquema.estado = {"id": p["id"], "tipo": p["type"], "opcion_idea": idea}

    for p in por_tipo.get("select", []):
        n = normalizar(p["name"])
        opciones = [o["name"] for o in p["select"].get("options", [])]
        if n.startswith("formato") and not esquema.formato:
            esquema.formato = {"id": p["id"], "opciones": opciones}
        elif n.startswith("pilar") and not esquema.pilar:
            esquema.pilar = {"id": p["id"], "opciones": opciones}

    fechas = por_tipo.get("date", [])
    fecha = next((p for p in fechas if "publicacion" in normalizar(p["name"])), fechas[0] if fechas else None)
    esquema.fecha = fecha["id"] if fecha else None

    for p in por_tipo.get("rich_text", []):
        n = normalizar(p["name"])
        if n.startswith("objetivo"):
            esquema.textos.setdefault("objetivo", p["id"])
        elif n.startswith("desarrollo") or n.startswith("guion"):
            esquema.textos.setdefault("desarrollo", p["id"])
        elif n.startswith("copy"):
            esquema.textos.setdefault("copy_cta", p["id"])
    return esquema


SINONIMOS_FORMATO = {
    "carrusel": ["carrusel", "carousel", "carrousel"],
    "reel": ["reel", "reels", "video"],
    "stories": ["stories", "story", "historia", "historias"],
    "foto": ["foto", "imagen", "post", "estatico"],
}


def mapear_opcion(valor: str, opciones: list[str]) -> str | None:
    """Devuelve la opción existente que corresponde a `valor` (sin tildes/mayúsculas)."""
    if not valor:
        return None
    v = normalizar(valor)
    for o in opciones:
        if normalizar(o) == v:
            return o
    for grupo in SINONIMOS_FORMATO.values():
        if v in grupo:
            for o in opciones:
                if normalizar(o) in grupo:
                    return o
    return None


def propiedades_idea(esquema: EsquemaPlan, idea: dict) -> tuple[dict, list[dict]]:
    """Arma las propiedades de la fila (Estado = Idea) y los bloques de cuerpo.

    Lo que no tenga columna en la base del cliente va al cuerpo de la página."""
    props: dict = {esquema.titulo: {"title": texto_enriquecido(idea["titulo"])}}
    cuerpo_extra: list[tuple[str, str]] = []

    if esquema.estado and esquema.estado["opcion_idea"]:
        props[esquema.estado["id"]] = {esquema.estado["tipo"]: {"name": esquema.estado["opcion_idea"]}}

    if esquema.formato:
        opcion = mapear_opcion(idea.get("formato", ""), esquema.formato["opciones"])
        if opcion:
            props[esquema.formato["id"]] = {"select": {"name": opcion}}
        else:
            cuerpo_extra.append(("Formato", idea.get("formato", "")))

    if esquema.pilar and idea.get("pilar"):
        opcion = mapear_opcion(idea["pilar"], esquema.pilar["opciones"])
        if opcion:
            props[esquema.pilar["id"]] = {"select": {"name": opcion}}
        else:
            cuerpo_extra.append(("Pilar sugerido", idea["pilar"]))

    if esquema.fecha and idea.get("fecha_sugerida"):
        props[esquema.fecha] = {"date": {"start": idea["fecha_sugerida"]}}

    etiquetas = {"objetivo": "Objetivo", "desarrollo": "Desarrollo", "copy_cta": "Copy + CTA"}
    for clave, etiqueta in etiquetas.items():
        valor = idea.get(clave) or ""
        if not valor:
            continue
        if clave in esquema.textos:
            props[esquema.textos[clave]] = {"rich_text": texto_enriquecido(valor)}
        else:
            cuerpo_extra.append((etiqueta, valor))

    bloques: list[dict] = []
    if idea.get("basado_en"):
        bloques.append(_callout(f"Por qué esta idea: {idea['basado_en']}", "📊"))
    for etiqueta, valor in cuerpo_extra:
        bloques.append(_encabezado(etiqueta, 3))
        bloques.extend(markdown_a_bloques(valor))
    return props, bloques


# ---------------------------------------------------------------------------
# Texto enriquecido y markdown → bloques de Notion
# ---------------------------------------------------------------------------
RE_INLINE = re.compile(r"(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|(?<!\*)\*[^*\s][^*]*\*(?!\*))")


def texto_enriquecido(texto: str) -> list[dict]:
    """Convierte **negrita**, *itálica* y [links](url) en rich_text, respetando el límite de 2000."""
    partes: list[dict] = []
    for trozo in RE_INLINE.split(texto or ""):
        if not trozo:
            continue
        anot, link = {}, None
        if trozo.startswith("**") and trozo.endswith("**"):
            trozo, anot = trozo[2:-2], {"bold": True}
        elif trozo.startswith("[") and "](" in trozo and trozo.endswith(")"):
            trozo, link = trozo[1:].split("](", 1)
            link = link[:-1]
        elif trozo.startswith("*") and trozo.endswith("*") and len(trozo) > 2:
            trozo, anot = trozo[1:-1], {"italic": True}
        for i in range(0, len(trozo), MAX_TEXTO):
            item: dict = {"type": "text", "text": {"content": trozo[i : i + MAX_TEXTO]}}
            if link and link.startswith("http"):
                item["text"]["link"] = {"url": link}
            if anot:
                item["annotations"] = anot
            partes.append(item)
    return partes[:100]


def _bloque(tipo: str, texto: str, **extra) -> dict:
    return {"object": "block", "type": tipo, tipo: {"rich_text": texto_enriquecido(texto), **extra}}


def _encabezado(texto: str, nivel: int) -> dict:
    return _bloque(f"heading_{nivel}", texto)


def _callout(texto: str, emoji: str) -> dict:
    return _bloque("callout", texto, icon={"type": "emoji", "emoji": emoji}, color="gray_background")


def _tabla(filas: list[list[str]]) -> dict:
    ancho = max(len(f) for f in filas)
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": ancho,
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {"cells": [texto_enriquecido(c) for c in f + [""] * (ancho - len(f))]},
                }
                for f in filas
            ],
        },
    }


def markdown_a_bloques(md: str) -> list[dict]:
    bloques: list[dict] = []
    tabla: list[list[str]] = []
    parrafo: list[str] = []

    def cerrar_parrafo():
        if parrafo:
            bloques.append(_bloque("paragraph", " ".join(parrafo)))
            parrafo.clear()

    def cerrar_tabla():
        if tabla:
            bloques.append(_tabla(tabla))
            tabla.clear()

    for cruda in (md or "").splitlines():
        linea = cruda.strip()
        if linea.startswith("|") and linea.endswith("|"):
            cerrar_parrafo()
            celdas = [c.strip() for c in linea.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in celdas):
                tabla.append(celdas)
            continue
        cerrar_tabla()
        if not linea:
            cerrar_parrafo()
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", linea)
        if m:
            cerrar_parrafo()
            bloques.append(_encabezado(m.group(2), len(m.group(1))))
        elif re.fullmatch(r"-{3,}|\*{3,}", linea):
            cerrar_parrafo()
            bloques.append({"object": "block", "type": "divider", "divider": {}})
        elif re.match(r"^[-*•]\s+", linea):
            cerrar_parrafo()
            bloques.append(_bloque("bulleted_list_item", re.sub(r"^[-*•]\s+", "", linea)))
        elif re.match(r"^\d+[.)]\s+", linea):
            cerrar_parrafo()
            bloques.append(_bloque("numbered_list_item", re.sub(r"^\d+[.)]\s+", "", linea)))
        elif linea.startswith(">"):
            cerrar_parrafo()
            bloques.append(_bloque("quote", linea.lstrip("> ")))
        else:
            parrafo.append(linea)
    cerrar_parrafo()
    cerrar_tabla()
    return bloques
