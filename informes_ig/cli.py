"""Línea de comandos.

    python -m informes_ig cuentas
    python -m informes_ig descubrir --cliente HOLAMARKETING
    python -m informes_ig snapshot-historias --todos
    python -m informes_ig informe --cliente HOLAMARKETING --dias 90 --mes 2026-10
    python -m informes_ig informe --todos --dry-run
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from . import analisis, instagram, metricas, notion
from .config import Cliente, Config, cargar_config

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="informes_ig", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clientes", default="clientes.yaml", help="Archivo de configuración")
    sub = ap.add_subparsers(dest="comando", required=True)

    sub.add_parser("cuentas", help="Lista las cuentas de IG a las que llega el token de Meta")

    for nombre, ayuda in (
        ("descubrir", "Muestra qué páginas y columnas de Notion detecta para el cliente"),
        ("snapshot-historias", "Guarda las historias activas (correr 1 o 2 veces por día)"),
        ("informe", "Genera el informe, lo sube a Notion y carga las ideas como 'Idea'"),
    ):
        p = sub.add_parser(nombre, help=ayuda)
        grupo = p.add_mutually_exclusive_group(required=True)
        grupo.add_argument("--cliente", help="Nombre del cliente en clientes.yaml")
        grupo.add_argument("--todos", action="store_true", help="Todos los clientes")
        if nombre == "informe":
            p.add_argument("--dias", type=int, default=90, help="Días hacia atrás (default 90)")
            p.add_argument("--desde", type=date.fromisoformat, help="AAAA-MM-DD (pisa --dias)")
            p.add_argument("--hasta", type=date.fromisoformat, help="AAAA-MM-DD (default hoy)")
            p.add_argument("--mes", help="Mes a planificar, AAAA-MM (default: el mes que viene)")
            p.add_argument("--dry-run", action="store_true",
                           help="No escribe en Notion; deja el informe y las ideas en datos/")
            p.add_argument("--sin-ideas", action="store_true", help="Solo el informe")

    args = ap.parse_args(argv)
    cfg = cargar_config(args.clientes)

    if args.comando == "cuentas":
        return cmd_cuentas(cfg)

    clientes = cfg.clientes if args.todos else [cfg.cliente(args.cliente)]
    for c in clientes:
        print(f"\n=== {c.nombre} ===")
        try:
            if args.comando == "descubrir":
                cmd_descubrir(cfg, c)
            elif args.comando == "snapshot-historias":
                cmd_snapshot(cfg, c)
            else:
                cmd_informe(cfg, c, args)
        except (instagram.ErrorMeta, notion.ErrorNotion, RuntimeError) as e:
            print(f"  ✗ Error con {c.nombre}: {e}")
            if not args.todos:
                raise SystemExit(1)


# ---------------------------------------------------------------------------
def cmd_cuentas(cfg: Config) -> None:
    import os

    api = instagram.InstagramAPI(os.environ.get("META_ACCESS_TOKEN", ""), cfg.meta_api_version)
    for cuenta in api.cuentas_disponibles():
        print(f"  {cuenta['usuario']:<30} ig_user_id={cuenta['ig_user_id']}  ({cuenta['pagina']}, "
              f"{cuenta['seguidores']} seguidores)")


def cmd_descubrir(cfg: Config, c: Cliente) -> None:
    api = notion.NotionAPI(cfg.notion_token)
    portal = notion.descubrir_portal(api, c.notion_pagina_cliente, c.notion_estrategia, c.notion_plan_base)
    print(f"  Estrategia:          {portal.estrategia or '✗ no encontrada'}")
    print(f"  Plan (base):         {portal.plan_base or '✗ no encontrada'}")
    print(f"  Plan (data source):  {portal.plan_data_source or '✗'}")
    if portal.plan_data_source:
        e = notion.leer_esquema(api, portal.plan_data_source)
        idea = e.estado and e.estado["opcion_idea"]
        print(f"  Estado 'Idea':       {'✓ ' + idea if idea else '✗ no existe la opción Idea'}")
        print(f"  Formatos:            {e.formato['opciones'] if e.formato else '✗'}")
        print(f"  Pilares:             {e.pilares or '✗'}")
        print(f"  Fecha:               {'✓' if e.fecha else '✗'}")
        print(f"  Columnas de texto:   {sorted(e.textos)}")
    if portal.estrategia:
        texto = api.texto_de_pagina(portal.estrategia)
        ritmo = texto.lower().find("ritmo editorial")
        print("  Ritmo editorial:    ", texto[ritmo : ritmo + 200].replace("\n", " | ") if ritmo >= 0 else "✗ no encontrado")


def cmd_snapshot(cfg: Config, c: Cliente) -> None:
    api = instagram.InstagramAPI(c.token_meta, cfg.meta_api_version)
    historias = api.historias_activas(c.ig_user_id)
    ruta = cfg.dir_datos / c.slug / "historias.jsonl"
    instagram.guardar_historias(ruta, historias)
    print(f"  ✓ {len(historias)} historias activas guardadas en {ruta}")


# ---------------------------------------------------------------------------
def cmd_informe(cfg: Config, c: Cliente, args) -> None:
    hasta = args.hasta or date.today()
    desde = args.desde or hasta - timedelta(days=args.dias)
    mes = args.mes or _mes_siguiente(date.today())
    mes_txt = _mes_legible(mes)
    salida = cfg.dir_datos / c.slug / f"informe-{hasta.isoformat()}"
    salida.mkdir(parents=True, exist_ok=True)

    # 1. Notion: estrategia, esquema del plan y lo ya planificado
    napi = notion.NotionAPI(cfg.notion_token)
    portal = notion.descubrir_portal(napi, c.notion_pagina_cliente, c.notion_estrategia, c.notion_plan_base)
    estrategia = napi.texto_de_pagina(portal.estrategia) if portal.estrategia else ""
    esquema = notion.leer_esquema(napi, portal.plan_data_source) if portal.plan_data_source else None
    if not args.sin_ideas and not esquema:
        raise RuntimeError("No encontré la base 'Plan de publicaciones'. Configurá notion_plan_base.")
    ya_planificado = _filas_recientes(napi, esquema) if esquema else []
    print(f"  ✓ Notion: estrategia {'ok' if estrategia else 'NO encontrada'}, "
          f"{len(ya_planificado)} filas recientes en el plan")

    # 2. Instagram
    iapi = instagram.InstagramAPI(c.token_meta, cfg.meta_api_version)
    inicio = datetime.combine(desde, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(hasta, time.max, tzinfo=timezone.utc)
    perfil = iapi.perfil(c.ig_user_id)
    publicaciones = iapi.publicaciones(c.ig_user_id, inicio, fin)
    historias = [
        h for h in instagram.leer_historias(cfg.dir_datos / c.slug / "historias.jsonl")
        if inicio <= instagram._parse_fecha(h["timestamp"]) <= fin
    ]
    print(f"  ✓ Instagram: {len(publicaciones)} publicaciones y {len(historias)} historias en el período")
    _guardar(salida / "crudo.json", {"perfil": perfil, "publicaciones": publicaciones, "historias": historias})

    # 3. Métricas + Claude
    datos = metricas.analizar(publicaciones, historias, c.zona_horaria)
    _guardar(salida / "metricas.json", datos)
    pilares = esquema.pilares if esquema else []
    prompt = analisis.armar_prompt(
        c.nombre, estrategia, datos, perfil, vars(c.pack), ya_planificado,
        (desde, hasta), mes_txt, pilares, c.notas,
    )
    print(f"  … analizando con {cfg.anthropic_model}")
    resultado = analisis.generar(prompt, pilares, cfg.anthropic_model)
    if args.sin_ideas:
        resultado.ideas = []
    _guardar(salida / "resultado.json", resultado.model_dump())
    (salida / "informe.md").write_text(_informe_md_local(c, resultado, desde, hasta), encoding="utf-8")
    print(f"  ✓ Informe e ideas guardados en {salida}")

    if args.dry_run:
        print(f"  (dry-run) {len(resultado.ideas)} ideas NO cargadas en Notion")
        return

    # 4. Ideas → Plan de publicaciones (Estado = Idea)
    creadas = []
    existentes = {notion.normalizar(f["titulo"]) for f in ya_planificado}
    for idea in resultado.ideas:
        if notion.normalizar(idea.titulo) in existentes:
            print(f"    · ya existía, se omite: {idea.titulo}")
            continue
        props, cuerpo = notion.propiedades_idea(esquema, idea.model_dump())
        pagina = napi.crear_pagina({"type": "data_source_id", "data_source_id": esquema.data_source_id},
                                   props, cuerpo)
        creadas.append((idea, pagina["url"]))
    if esquema and not (esquema.estado and esquema.estado["opcion_idea"]):
        print("  ⚠ La base no tiene la opción de estado 'Idea': las filas quedaron sin estado")
    print(f"  ✓ {len(creadas)} ideas cargadas en Planificación de contenido")

    # 5. Página del informe
    padre = notion.id_desde_url(c.notion_informes_padre or portal.pagina_cliente)
    bloques = _bloques_informe(resultado, creadas, datos, desde, hasta, mes_txt)
    titulo = f"Informe Instagram · {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}"
    pagina = napi.crear_pagina({"type": "page_id", "page_id": padre},
                               {"title": {"title": notion.texto_enriquecido(titulo)}}, bloques, icono="📊")
    print(f"  ✓ Informe en Notion: {pagina['url']}")


def _filas_recientes(api: notion.NotionAPI, esquema: notion.EsquemaPlan) -> list[dict]:
    filas = api.consultar(
        esquema.data_source_id,
        {"sorts": [{"timestamp": "created_time", "direction": "descending"}]},
        limite=80,
    )
    resultado = []
    for f in filas:
        props = {p["id"]: p for p in f["properties"].values()}
        titulo = "".join(t["plain_text"] for t in props.get(esquema.titulo, {}).get("title", []))
        fila = {"titulo": titulo}
        if esquema.estado:
            valor = props.get(esquema.estado["id"], {}).get(esquema.estado["tipo"])
            fila["estado"] = valor and valor.get("name")
        if esquema.formato:
            valor = props.get(esquema.formato["id"], {}).get("select")
            fila["formato"] = valor and valor.get("name")
        if esquema.fecha:
            valor = props.get(esquema.fecha, {}).get("date")
            fila["fecha"] = valor and valor.get("start")
        if titulo:
            resultado.append(fila)
    return resultado


def _bloques_informe(res: analisis.Resultado, creadas, datos: dict, desde: date, hasta: date,
                     mes_txt: str) -> list[dict]:
    b = [notion._callout(res.resumen, "💡")]
    b += notion.markdown_a_bloques(
        f"Período analizado: **{desde:%d/%m/%Y} al {hasta:%d/%m/%Y}** · "
        f"{datos['total_publicaciones']} publicaciones · "
        f"{datos['historias']['cantidad']} historias · horarios en {datos['zona_horaria']}"
    )
    b.append({"object": "block", "type": "divider", "divider": {}})
    b += notion.markdown_a_bloques(res.informe_markdown)

    r = res.ritmo
    b.append({"object": "block", "type": "divider", "divider": {}})
    b += notion.markdown_a_bloques(
        f"## Ritmo editorial usado para planificar {mes_txt}\n"
        f"- Feed: {r.posteos_feed_mes} por mes ({r.carruseles_mes} carruseles, {r.reels_mes} reels, "
        f"{r.fotos_mes} fotos)\n- Historias: {r.historias}\n- Fuente: {r.fuente}"
    )
    if creadas:
        b += notion.markdown_a_bloques(f"## Ideas cargadas en Planificación de contenido ({len(creadas)})")
        for idea, url in creadas:
            b += notion.markdown_a_bloques(f"- [{idea.titulo}]({url}) · {idea.formato} · {idea.fecha_sugerida}")

    filas = [["Posteo", "Formato", "Alcance", "Guardados", "Compartidos", "Comentarios"]]
    for p in datos["top_alcance"]:
        titulo = f"[{_corto(p.get('titulo', ''))}]({p['link']})" if p.get("link") else _corto(p.get("titulo", ""))
        filas.append([titulo, p["formato"], _n(p["alcance"]), _n(p["guardados"]),
                      _n(p["compartidos"]), _n(p["comentarios"])])
    if len(filas) > 1:
        b += notion.markdown_a_bloques("## Top 5 por alcance")
        b.append(notion._tabla(filas))
    return b


def _informe_md_local(c: Cliente, res: analisis.Resultado, desde: date, hasta: date) -> str:
    partes = [f"# Informe Instagram · {c.nombre} · {desde} al {hasta}", "", res.resumen, "",
              res.informe_markdown, "", "## Ideas", ""]
    for i in res.ideas:
        partes += [f"### {i.titulo}", f"- Formato: {i.formato} · Pilar: {i.pilar} · Fecha: {i.fecha_sugerida}",
                   f"- Objetivo: {i.objetivo}", f"- Basado en: {i.basado_en}", "", "**Desarrollo**", "",
                   i.desarrollo, "", "**Copy + CTA**", "", i.copy_cta, ""]
    return "\n".join(partes)


def _mes_siguiente(hoy: date) -> str:
    return f"{hoy.year + hoy.month // 12}-{hoy.month % 12 + 1:02d}"


def _mes_legible(aaaa_mm: str) -> str:
    anio, mes = aaaa_mm.split("-")
    return f"{MESES[int(mes) - 1]} {anio}"


def _corto(t: str, n: int = 60) -> str:
    return t if len(t) <= n else t[: n - 1] + "…"


def _n(v) -> str:
    return f"{int(v):,}".replace(",", ".")


def _guardar(ruta: Path, datos) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
