"""Carga de configuración: variables de entorno + archivo de clientes (YAML)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _cargar_dotenv(ruta: Path) -> None:
    """Lee un .env simple (CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


@dataclass
class Pack:
    """Pack contratado. Si no se completa, se deduce de la página Estrategia."""

    posteos_mes: int | None = None
    reels_mes: int | None = None
    historias_semana: int | None = None


@dataclass
class Cliente:
    nombre: str
    notion_pagina_cliente: str
    # "facebook": cuenta vinculada a un Business Manager (token de usuario del sistema).
    # "instagram": cuenta solo de Instagram; el cliente autoriza con `conectar`.
    conexion: str = "facebook"
    ig_user_id: str = ""
    token_env: str = "META_ACCESS_TOKEN"
    zona_horaria: str = "America/Argentina/Buenos_Aires"
    # Opcionales: si no están, se descubren navegando la página del cliente.
    notion_estrategia: str | None = None
    notion_plan_base: str | None = None
    notion_informes_padre: str | None = None
    pack: Pack = field(default_factory=Pack)
    notas: str = ""

    @property
    def token_meta(self) -> str:
        token = os.environ.get(self.token_env, "")
        if not token:
            raise SystemExit(
                f"Falta el token de Meta para {self.nombre}: definí la variable {self.token_env}"
            )
        return token

    @property
    def slug(self) -> str:
        return "".join(c.lower() if c.isalnum() else "-" for c in self.nombre).strip("-")


@dataclass
class Config:
    notion_token: str
    anthropic_model: str
    meta_api_version: str
    clientes: list[Cliente]
    dir_datos: Path

    def cliente(self, nombre: str) -> Cliente:
        buscado = nombre.strip().lower()
        for c in self.clientes:
            if c.nombre.lower() == buscado or c.slug == buscado:
                return c
        disponibles = ", ".join(c.nombre for c in self.clientes)
        raise SystemExit(f"No encontré el cliente '{nombre}'. Disponibles: {disponibles}")


def cargar_config(ruta_clientes: str | Path = "clientes.yaml") -> Config:
    raiz = Path.cwd()
    _cargar_dotenv(raiz / ".env")

    ruta = Path(ruta_clientes)
    if not ruta.exists():
        raise SystemExit(
            f"No existe {ruta}. Copiá clientes.example.yaml a clientes.yaml y completalo."
        )
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}

    clientes = []
    for c in datos.get("clientes", []):
        pack = Pack(**(c.pop("pack", None) or {}))
        campos = {
            k: str(v) if v is not None and k.startswith(("ig_", "notion_")) else v
            for k, v in c.items()
        }
        clientes.append(Cliente(pack=pack, **campos))

    return Config(
        notion_token=os.environ.get("NOTION_TOKEN", ""),
        anthropic_model=os.environ.get("CLAUDE_MODEL", "claude-opus-5"),
        meta_api_version=os.environ.get("META_API_VERSION", "v23.0"),
        clientes=clientes,
        dir_datos=Path(os.environ.get("DIR_DATOS", "datos")),
    )
