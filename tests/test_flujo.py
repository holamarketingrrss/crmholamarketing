"""Flujo completo de `informe` con Meta, Notion y Claude simulados."""

from informes_ig import analisis, cli, instagram, notion
from tests.test_informes import ESQUEMA_LUJIS, PUBLICACIONES


class NotionFalso:
    def __init__(self, token):
        self.creadas = []

    def recorrer(self, bloque_id, profundidad=0, max_prof=6):
        arbol = {
            "cliente": [{"type": "column_list", "id": "cols", "has_children": True}],
            "cols": [{"type": "child_page", "id": "est", "child_page": {"title": "Estrategia"}},
                     {"type": "child_page", "id": "plan", "child_page": {"title": "Planificación de contenidos "}}],
            "plan": [{"type": "child_database", "id": "base", "has_children": False}],
        }
        for b in arbol.get(bloque_id, []):
            yield b, profundidad
            if b.get("has_children"):
                yield from self.recorrer(b["id"], profundidad + 1)

    def base(self, base_id):
        return {"data_sources": [{"id": "ds1"}]}

    def data_source(self, ds_id):
        return {"properties": ESQUEMA_LUJIS}

    def texto_de_pagina(self, pid):
        return "## Ritmo editorial\n- Feed: 3 posteos semanales"

    def consultar(self, ds_id, cuerpo=None, limite=100):
        return [{"properties": {"Name": {"id": "title", "type": "title",
                                         "title": [{"plain_text": "Idea repetida"}]}}}]

    def crear_pagina(self, padre, props, bloques=None, icono=None):
        self.creadas.append((padre, props, bloques))
        return {"id": f"p{len(self.creadas)}", "url": f"https://notion.so/p{len(self.creadas)}"}


class IGFalso:
    def __init__(self, token, version):
        pass

    def perfil(self, uid):
        return {"username": "lujis", "followers_count": 1000}

    def publicaciones(self, uid, desde, hasta):
        return PUBLICACIONES


def test_informe_completo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clientes.yaml").write_text(
        "clientes:\n  - nombre: LUJIS\n    ig_user_id: 123\n    notion_pagina_cliente: cliente\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("META_ACCESS_TOKEN", "x")
    monkeypatch.setenv("NOTION_TOKEN", "x")
    falso = NotionFalso("x")
    monkeypatch.setattr(notion, "NotionAPI", lambda token: falso)
    monkeypatch.setattr(notion, "id_desde_url", lambda v: v)
    monkeypatch.setattr(instagram, "InstagramAPI", IGFalso)

    visto = {}

    def generar(prompt, pilares, modelo):
        visto["prompt"], visto["pilares"] = prompt, pilares
        idea = dict(titulo="Nueva idea", formato="Reel", pilar="Tendencia", objetivo="Alcance",
                    desarrollo="Gancho...", copy_cta="Seguinos", fecha_sugerida="2026-10-07",
                    basado_en="Los reels educativos...")
        return analisis.Resultado(
            resumen="Resumen", informe_markdown="## Lo que dicen los números\nTexto",
            ritmo=dict(posteos_feed_mes=12, reels_mes=4, carruseles_mes=8, fotos_mes=0,
                       historias="1 diaria", fuente="Estrategia"),
            ideas=[analisis.Idea(**idea), analisis.Idea(**{**idea, "titulo": "Idea repetida"})],
        )

    monkeypatch.setattr(analisis, "generar", generar)
    cli.main(["informe", "--cliente", "LUJIS", "--mes", "2026-10"])

    assert "3 posteos semanales" in visto["prompt"]
    assert visto["pilares"] == ["Locacion", "Tendencia", "Producto"]
    # 1 idea nueva (la repetida se omite) + la página del informe
    assert len(falso.creadas) == 2
    padre, props, _ = falso.creadas[0]
    assert padre == {"type": "data_source_id", "data_source_id": "ds1"}
    assert props["st2"] == {"status": {"name": "Idea"}}
    padre, props, bloques = falso.creadas[1]
    assert padre == {"type": "page_id", "page_id": "cliente"}
    assert "Informe Instagram" in props["title"]["title"][0]["text"]["content"]
    assert any(b["type"] == "table" for b in bloques)
    assert list((tmp_path / "datos" / "lujis").glob("informe-*/informe.md"))
