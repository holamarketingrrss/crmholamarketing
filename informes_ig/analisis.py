"""Análisis con Claude: interpreta las métricas y propone ideas de contenido.

Claude recibe los números ya calculados (metricas.py), la estrategia del
cliente tal como está en Notion y lo que ya hay planificado. Devuelve un JSON
validado con el informe y las ideas.
"""

from __future__ import annotations

import json
from datetime import date

import anthropic
from pydantic import BaseModel, Field

SISTEMA = """Sos estratega de contenido de HOLA MARKETING, una agencia argentina de redes sociales.
Tu trabajo es leer el rendimiento de Instagram de un cliente y convertirlo en decisiones de contenido.

Cómo escribís el informe:
- Español rioplatense, claro y directo, sin jerga de marketing ni frases de gurú.
- Siempre con números concretos sacados de las métricas que te pasan. Nunca inventes datos:
  si algo no está en las métricas, no lo afirmes. Si un dato falta o no es confiable, decilo.
- Comparás formatos y temas ("los carruseles educativos llegan 3 veces más lejos que los de venta").
- Nombrás los posteos que mejor funcionaron por su título y explicás por qué creés que funcionaron.
- Separás lo que es dato de lo que es interpretación ("creo que es por el contenido, no por el formato").
- Marcás la frecuencia real contra el ritmo editorial contratado.
- Mejores días y franjas horarias según los datos propios del cliente (indicá la zona horaria).
- Cerrás con recomendaciones accionables para el próximo período.
- Usá markdown simple: encabezados ##, párrafos, viñetas y, si ayuda, una tabla chica.

Cómo proponés ideas:
- Respetá la estrategia del cliente: pilares, tono, público, objetivos del trimestre y límites.
- Cantidad: exactamente lo que marca el pack/ritmo editorial para el mes objetivo (feed: carruseles,
  reels y fotos según el pack). Para historias, proponé una fila por semana del mes con la secuencia
  diaria desarrollada (formato "Stories").
- Cada idea se apoya en algo que funcionó (o corrige algo que no), y lo explicás en "basado_en".
- Aprovechá fechas especiales del mes objetivo relevantes para el público (Argentina salvo que la
  estrategia diga otra cosa).
- No repitas ideas que ya están en el plan.
- "desarrollo": guion del reel (gancho + escenas + cierre), texto slide por slide del carrusel, o la
  secuencia de historias día por día (con encuestas, cajas de preguntas, etc.).
- "copy_cta": el copy listo para publicar con su llamado a la acción.
- "fecha_sugerida": dentro del mes objetivo, en los mejores días que muestran los datos, en formato AAAA-MM-DD.
"""


class Ritmo(BaseModel):
    posteos_feed_mes: int = Field(description="Publicaciones de feed por mes según el pack")
    reels_mes: int
    carruseles_mes: int
    fotos_mes: int
    historias: str = Field(description="Ritmo de historias, p. ej. '1 diaria (L a D)'")
    fuente: str = Field(description="De dónde sale: 'pack configurado' o cita de la Estrategia")


class Idea(BaseModel):
    titulo: str
    formato: str = Field(description="Carrusel, Reel, Foto o Stories")
    pilar: str
    objetivo: str
    desarrollo: str
    copy_cta: str
    fecha_sugerida: str
    basado_en: str


class Resultado(BaseModel):
    resumen: str = Field(description="3 o 4 oraciones con lo más importante del período")
    ritmo: Ritmo
    informe_markdown: str
    ideas: list[Idea]


def _esquema(pilares: list[str]) -> dict:
    esquema = Resultado.model_json_schema()
    idea = esquema["$defs"]["Idea"]["properties"]
    idea["formato"]["enum"] = ["Carrusel", "Reel", "Foto", "Stories"]
    if pilares:
        idea["pilar"]["enum"] = pilares
    _cerrar(esquema)
    return esquema


def _cerrar(nodo):
    """Structured outputs requiere additionalProperties: false en cada objeto."""
    if isinstance(nodo, dict):
        if nodo.get("type") == "object":
            nodo["additionalProperties"] = False
        for v in nodo.values():
            _cerrar(v)
    elif isinstance(nodo, list):
        for v in nodo:
            _cerrar(v)


def armar_prompt(
    cliente: str,
    estrategia: str,
    metricas: dict,
    perfil: dict,
    pack: dict,
    ya_planificado: list[dict],
    periodo: tuple[date, date],
    mes_objetivo: str,
    pilares: list[str],
    notas: str = "",
) -> str:
    pack_txt = (
        json.dumps(pack, ensure_ascii=False)
        if any(v for v in pack.values())
        else "No configurado: deducilo de la sección 'Ritmo editorial' de la estrategia."
    )
    return f"""# Cliente: {cliente}

## Período analizado
Del {periodo[0].isoformat()} al {periodo[1].isoformat()}.

## Mes para el que hay que proponer ideas
{mes_objetivo}

## Perfil de Instagram
{json.dumps(perfil, ensure_ascii=False)}

## Pack contratado
{pack_txt}

## Pilares disponibles en el plan de publicaciones
{", ".join(pilares) if pilares else "(la base no tiene pilares definidos: usá los de la estrategia)"}

## Estrategia y ritmo editorial (copiado de Notion)
<estrategia>
{estrategia or "(no se encontró la página de estrategia)"}
</estrategia>

## Ya planificado en Notion (no repetir)
{json.dumps(ya_planificado, ensure_ascii=False)}

## Métricas calculadas del período
<metricas>
{json.dumps(metricas, ensure_ascii=False)}
</metricas>

{f"## Notas del equipo{chr(10)}{notas}" if notas else ""}

Escribí el informe del período y las ideas para {mes_objetivo}.
"""


def generar(prompt: str, pilares: list[str], modelo: str) -> Resultado:
    cliente = anthropic.Anthropic()
    with cliente.beta.messages.stream(
        model=modelo,
        max_tokens=64000,
        system=SISTEMA,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": _esquema(pilares)},
        },
        # Si el modelo rechaza el pedido, la API lo reintenta en otro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        mensaje = stream.get_final_message()

    if mensaje.stop_reason == "refusal":
        raise RuntimeError(f"Claude no generó el informe (refusal): {mensaje.stop_details}")
    if mensaje.stop_reason == "max_tokens":
        raise RuntimeError("La respuesta se cortó por max_tokens; probá con un período más corto.")
    texto = next(b.text for b in mensaje.content if b.type == "text")
    return Resultado.model_validate_json(texto)
