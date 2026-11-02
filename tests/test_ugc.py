from datetime import datetime, timedelta, timezone

from informes_ig import instagram, ugc

AHORA = datetime(2026, 11, 2, tzinfo=timezone.utc)


def post(dias, likes=100, comentarios=10, producto="REELS"):
    ts = (AHORA - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S+0000")
    return {"timestamp": ts, "like_count": likes, "comments_count": comentarios,
            "media_product_type": producto, "permalink": f"https://instagram.com/p/{dias}"}


def test_limpiar_usuario():
    assert ugc.limpiar_usuario("@\\_belenparedes\\_") == "_belenparedes_"
    assert ugc.limpiar_usuario("https://www.instagram.com/lindatucasa?igsh=xx") == "lindatucasa"
    assert ugc.limpiar_usuario("nane Chacón") is None


def test_creadora_activa_con_buena_interaccion_es_recomendada():
    perfil = {"followers_count": 3000, "media": {"data": [post(d) for d in (1, 4, 8, 12, 20)]}}
    m = ugc.evaluar(perfil, AHORA)
    assert m["posteos_ultimos_30_dias"] == 5
    assert m["tasa_interaccion_pct"] == 3.67
    assert m["porcentaje_reels"] == 100
    assert m["sugerencia"] == "🟢 Recomendada"


def test_cuenta_inactiva_es_no():
    perfil = {"followers_count": 3000, "media": {"data": [post(95), post(120)]}}
    assert ugc.evaluar(perfil, AHORA)["sugerencia"] == "🔴 No"


def test_activa_con_poca_interaccion_es_revisar():
    perfil = {"followers_count": 50_000, "media": {"data": [post(d, likes=100) for d in (1, 5, 9, 13)]}}
    assert ugc.evaluar(perfil, AHORA)["sugerencia"] == "🟡 Revisar"


def test_likes_ocultos_no_rompen():
    p = post(2)
    del p["like_count"]
    m = ugc.evaluar({"followers_count": 1000, "media": {"data": [p]}}, AHORA)
    assert m["posteos_con_likes_ocultos"] == 1
    assert m["tasa_interaccion_pct"] is None
    assert m["sugerencia"] == "🟡 Revisar"


class _ApiFalsa(instagram.InstagramAPI):
    def __init__(self, error=None):
        super().__init__("x")
        self.error = error

    def _get(self, url, params=None):
        if self.error:
            raise instagram.ErrorMeta(self.error)
        return {"business_discovery": {"name": "Barbi", "followers_count": 2000,
                                       "media": {"data": [post(3)]}}}


def test_revisar_cuenta_no_visible():
    r = ugc.revisar(_ApiFalsa("110 Invalid user id"), "@cuentapersonal")
    assert r == {"usuario": "cuentapersonal", "visible": False,
                 "motivo": "Cuenta personal, privada o inexistente (Meta no la muestra)"}


def test_revisar_cuenta_visible():
    r = ugc.revisar(_ApiFalsa(), "lindatucasa")
    assert r["visible"] and r["nombre"] == "Barbi"
    assert r["metricas"]["posteos_ultimos_30_dias"] == 1
