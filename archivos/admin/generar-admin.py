#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el panel administrativo, servido exclusivamente desde el mismo origen de la API.

Las fuentes se incrustan en el HTML; ni los datos ni la sesion se incrustan.
"""
from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
FUENTES = AQUI / "fuentes-inline.css"
SALIDA = AQUI / "barber-chinos-admin.html"


def icono(nombre, tam=18):
    """Un unico juego de iconos SVG para la navegacion."""
    trazos = {
        "dashboard": "<rect x='3' y='3' width='7' height='9' rx='1.5'/><rect x='14' y='3' width='7' height='5' rx='1.5'/><rect x='14' y='12' width='7' height='9' rx='1.5'/><rect x='3' y='16' width='7' height='5' rx='1.5'/>",
        "agenda": "<rect x='3' y='5' width='18' height='16' rx='2'/><path d='M3 10h18M8 3v4M16 3v4'/>",
        "clientes": "<circle cx='9' cy='8' r='3.5'/><path d='M2.5 20a6.5 6.5 0 0 1 13 0'/><path d='M16 5.5a3 3 0 0 1 0 5.8M17.5 20a6.2 6.2 0 0 0-2.2-4.7'/>",
        "servicios": "<circle cx='6.5' cy='17.5' r='2.5'/><circle cx='17.5' cy='17.5' r='2.5'/><path d='M8.4 15.6 19 5M5 5l10.6 10.6M15.5 3.5l5 5'/>",
        "reportes": "<path d='M4 20V10M10 20V4M16 20v-7M22 20H2'/>",
        "config": "<circle cx='12' cy='12' r='3'/><path d='M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1'/>",
    }
    return (f'<svg class="ico" width="{tam}" height="{tam}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{trazos[nombre]}</svg>')


VISTAS = (("dashboard", "Inicio"), ("agenda", "Agenda"),
          ("clientes", "Clientes"), ("servicios", "Servicios"),
          ("reportes", "Reportes"), ("config", "Configuración"))


def main():
    if not FUENTES.is_file():
        print("Falta fuentes-inline.css; ejecuta embeber-fuentes.py", file=sys.stderr)
        return 1
    fuente = FUENTES.read_text(encoding="utf-8")
    plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
    js = (AQUI / "app.js.html").read_text(encoding="utf-8")
    nav = "".join(
        f'<button class="nav-item{" activo" if i == 0 else ""}" data-vista="{clave}" '
        f'type="button" aria-current="{"page" if i == 0 else "false"}">'
        f'{icono(clave)}<span>{titulo}</span></button>'
        for i, (clave, titulo) in enumerate(VISTAS))
    vistas = "".join(
        f'<section class="vista" id="vista-{clave}" data-vista-panel="{clave}" '
        f'aria-labelledby="titulo-{clave}"{"" if i == 0 else " hidden"}>'
        f'<div class="vista-cab"><h1 id="titulo-{clave}">{titulo}</h1>'
        f'<p id="subtitulo-{clave}" class="vista-sub"></p></div>'
        f'<div class="vista-contenido" id="contenido-{clave}" aria-live="polite"></div></section>'
        for i, (clave, titulo) in enumerate(VISTAS))
    html = (plantilla.replace("/*@FUENTES@*/", fuente)
            .replace("<!--@NAV@-->", nav)
            .replace("<!--@VISTAS@-->", vistas)
            .replace("<!--@JS@-->", js))
    if any(x in html for x in ("/*@FUENTES@*/", "<!--@NAV@-->", "<!--@VISTAS@-->", "<!--@JS@-->")):
        raise ValueError("Quedaron marcadores de plantilla sin reemplazar")
    SALIDA.write_text(html, encoding="utf-8")
    print(f"escrito: {SALIDA} ({SALIDA.stat().st_size // 1024} KB; {fuente.count('@font-face')} fuentes; {len(VISTAS)} vistas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
