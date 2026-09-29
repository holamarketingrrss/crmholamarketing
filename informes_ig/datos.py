"""Trae los datos de Instagram de una cuenta y calcula las métricas, sin Notion ni Claude API.

Pensado para las rutinas de Claude: la rutina corre esto, lee el JSON y escribe
el informe y las ideas en Notion con el conector.

    python -m informes_ig.datos --ig-id 17841449615689473 --dias 90
    python -m informes_ig.datos --ig-id 17841449615689473 --desde 2026-06-01 --hasta 2026-09-30

Lee el token de META_ACCESS_TOKEN.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone

from . import instagram, metricas


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="informes_ig.datos", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ig-id", required=True, help="ID de la cuenta de Instagram")
    ap.add_argument("--dias", type=int, default=90, help="Días hacia atrás (default 90)")
    ap.add_argument("--desde", type=date.fromisoformat, help="AAAA-MM-DD (pisa --dias)")
    ap.add_argument("--hasta", type=date.fromisoformat, help="AAAA-MM-DD (default hoy)")
    ap.add_argument("--zona-horaria", default="America/Argentina/Buenos_Aires")
    ap.add_argument("--version", default=os.environ.get("META_API_VERSION", "v23.0"))
    args = ap.parse_args(argv)

    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        sys.exit("Falta la variable META_ACCESS_TOKEN")

    hasta = args.hasta or date.today()
    desde = args.desde or hasta - timedelta(days=args.dias)
    inicio = datetime.combine(desde, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(hasta, time.max, tzinfo=timezone.utc)

    api = instagram.InstagramAPI(token, args.version)
    perfil = api.perfil(args.ig_id)
    publicaciones = api.publicaciones(args.ig_id, inicio, fin)
    resultado = {
        "perfil": perfil,
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "metricas": metricas.analizar(publicaciones, [], args.zona_horaria),
    }
    json.dump(resultado, sys.stdout, ensure_ascii=False, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
