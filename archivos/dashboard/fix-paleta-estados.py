#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alinea los colores de estado con la paleta de Mr.BLACK.

HALLAZGO: la pila de estados y la de clientes usaban colores heredados de
GitHub (#58a6ff azul, #3fb950 verde, #f4614f rojo, #e5b34a ambar), que NO
estan en la paleta del sitio de referencia. El resultado se veia
dispar: un verde fosforito y un azul brillante junto al naranja.

PALETA DE MR.BLACK (la unica valida):
    #262626 black · #afab8e green · #df6341 orange · #de7e64 salmon
    #a59171 brown · #f3f1e9 ivory  · #f9f7f7 white

Mapeo nuevo, con jerarquia (lo bueno -> naranja, lo neutro -> green,
lo problematico -> salmon):
    atendido      -> #df6341 (orange)   ingreso real, lo que importa
    confirmado    -> #f3f1e9 (ivory)    confirmado por el cliente
    agendado      -> #afab8e (green)    todavia no ha pasado
    no_show       -> #de7e64 (salmon)   perdida
    cancelado     -> #a59171 (brown)    perdida pero menos grave
    reprogramado  -> #afab8e (green)
    (sin estado)  -> rgba tenue
"""
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GEN = Path(r"G:\Barberia\archivos\dashboard\generar-dashboard.py")

VIEJO = '''COLORES_ESTADO = {
    "atendido": "#3fb950", "no_show": "#f4614f", "cancelado": "#e3b341",
    "agendado": "#58a6ff", "confirmado": "#58a6ff", "reprogramado": "#8b949e",
    "(sin estado)": "#4b5462",
}'''

NUEVO = '''# Paleta de Mr.BLACK. Un solo acento (orange) con dos apoyos.
# Jerarquia: lo que da dinero resalta; lo neutro queda en green/ivory;
# lo problematico usa salmon y brown, que son del mismo mundo cromatico.
COLORES_ESTADO = {
    "atendido": "#df6341",      # orange: ingreso real
    "confirmado": "#f3f1e9",    # ivory: confirmado por el cliente
    "agendado": "#afab8e",      # green: todavia no ha pasado
    "reprogramado": "#afab8e",  # green
    "no_show": "#de7e64",       # salmon: se perdio
    "cancelado": "#a59171",     # brown: se perdio, menos grave
    "(sin estado)": "rgba(243,241,233,.35)",
}'''

# Los dos colores sueltos del bloque de clientes
VIEJO_CLI = '''        f"<span style='width:{pn:.2f}%;background:#58a6ff'></span>"
        f"<span style='width:{pr:.2f}%;background:#e5b34a'></span></div>"
        "<div class='leyenda'>"
        f"<span><i style='background:#58a6ff'></i>Nuevos: <b>{nuevos}</b> "
        f"({pn:.0f}%)</span>"
        f"<span><i style='background:#e5b34a'></i>Recurrentes: <b>{recur}</b> "'''

NUEVO_CLI = '''        f"<span style='width:{pn:.2f}%;background:#df6341'></span>"
        f"<span style='width:{pr:.2f}%;background:#afab8e'></span></div>"
        "<div class='leyenda'>"
        f"<span><i style='background:#df6341'></i>Nuevos: <b>{nuevos}</b> "
        f"({pn:.0f}%)</span>"
        f"<span><i style='background:#afab8e'></i>Recurrentes: <b>{recur}</b> "'''


def main():
    src = GEN.read_text(encoding="utf-8")
    cambios = 0

    if VIEJO in src:
        src = src.replace(VIEJO, NUEVO, 1)
        cambios += 1
        print("  OK    paleta de estados alineada")
    else:
        print("  AVISO no encontre COLORES_ESTADO")

    if VIEJO_CLI in src:
        src = src.replace(VIEJO_CLI, NUEVO_CLI, 1)
        cambios += 1
        print("  OK    colores de clientes alineados")
    else:
        print("  AVISO no encontre el bloque de clientes")

    # Buscar cualquier color de GitHub que haya quedado
    restantes = [c for c in re.findall(r"#[0-9a-fA-F]{6}", src)
                 if c.lower() in ("#58a6ff", "#3fb950", "#f4614f", "#e3b341",
                                  "#8b949e", "#4b5462", "#e5b34a")]
    if restantes:
        print(f"  AVISO quedan colores fuera de paleta: {set(restantes)}")
    else:
        print("  OK    no queda ningun color fuera de la paleta")

    if cambios:
        GEN.write_text(src, encoding="utf-8")
    print(f"\n  {cambios} de 2 cambios aplicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())