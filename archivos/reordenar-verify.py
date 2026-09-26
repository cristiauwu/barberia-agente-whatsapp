#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reordena verify.py: mueve la seccion [12] ANTES del veredicto final.

El problema: el bloque [12] se insertó después de `sys.exit(1)`, así que
nunca se ejecutaba. Debe ir antes de la sección de veredicto.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RUTA = r"G:\Barberia\verify.py"

MARCA_VEREDICTO = "# ------------------------------------------------------------- veredicto"
MARCA_12 = 'print("\\n[12] Comandos del dueño (flujo 1)")'

src = open(RUTA, encoding="utf-8").read()

i_v = src.find(MARCA_VEREDICTO)
i_12 = src.find(MARCA_12)
print(f"veredicto en {i_v}, [12] en {i_12}")

if i_v < 0:
    print("no encontré el marcador del veredicto")
    sys.exit(1)
if i_12 < 0:
    print("no encontré la sección [12]")
    sys.exit(1)
if i_12 < i_v:
    print("ya está en el orden correcto; nada que hacer")
    sys.exit(0)

antes = src[:i_v]
veredicto = src[i_v:i_12]
bloque12 = src[i_12:]

nuevo = (antes.rstrip() + "\n\n" + bloque12.strip() + "\n\n"
         + veredicto.strip() + "\n")
open(RUTA, "w", encoding="utf-8").write(nuevo)

# Verificar
c = open(RUTA, encoding="utf-8").read()
a, b = c.find(MARCA_12), c.find(MARCA_VEREDICTO)
print(f"después: [12] en {a}, veredicto en {b}")
print("ORDEN OK" if 0 <= a < b else "ORDEN MAL")
print(f"tamaño: {len(c)} chars")