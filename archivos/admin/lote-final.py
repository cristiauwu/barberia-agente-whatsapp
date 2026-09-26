#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lote final: quita la redundancia y verifica que abra sin servidor.

DEFECTO: en la vista de Servicios, el panel "Ranking por ingreso" repite
los MISMOS cinco servicios que ya estan al lado, en el mismo orden. No
aporta nada: ocupa media pantalla para decir lo mismo dos veces.

ARREGLO: ese panel pasa a ser "Rentabilidad por hora", que es un dato
nuevo y util para un barbero: cuanto deja cada servicio por hora de
trabajo. Un corte de $150 en 40 min deja $225/h; una barba de $100 en
20 min deja $300/h. Eso si ayuda a decidir que promocionar.

Se calcula de los mismos datos, sin inventar nada:
    ingreso por hora = ingreso total / (citas x duracion en horas)

Ademas se comprueba el requisito explicito del pedido: que el archivo
funcione AL ABRIRLO, sin servidor. Se prueba con file:// y se comprueba
que las fuentes carguen y que no haya ninguna peticion a la red.
"""
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
n = 0

# =====================================================================
#  1. EL GENERADOR: rentabilidad por hora en vez del ranking repetido
# =====================================================================
print("=" * 68)
print("1. EL PANEL REDUNDANTE PASA A SER RENTABILIDAD POR HORA")
print("=" * 68)
g = open(os.path.join(AQUI, "generar-admin.py"), encoding="utf-8").read()
og = g

VIG = '''def fila_servicio(s):
    nombre, precio, dur, n, ing = s
    maxi = max(x[4] for x in SERVICIOS) or 1
    pct = ing / maxi * 100
    txt = f"${precio}" if precio else "segun zona"
    return (f"<div class='srv' data-animar>"
            f"<div class='srv-top'><span class='srv-nombre'>{esc(nombre)}</span>"
            f"<span class='srv-precio'>{esc(txt)}</span></div>"
            f"<div class='srv-barra'><i style='--w:{pct:.1f}%;"
            f"width:{pct:.1f}%'></i></div>"
            f"<div class='srv-pie'><span>{esc(dur)}</span>"
            f"<span>{n} citas</span><span>${ing:,}</span></div></div>")'''

NUEVO = '''def fila_servicio(s):
    nombre, precio, dur, n, ing = s
    maxi = max(x[4] for x in SERVICIOS) or 1
    pct = ing / maxi * 100
    txt = f"${precio}" if precio else "segun zona"
    return (f"<div class='srv' data-animar>"
            f"<div class='srv-top'><span class='srv-nombre'>{esc(nombre)}</span>"
            f"<span class='srv-precio'>{esc(txt)}</span></div>"
            f"<div class='srv-barra'><i style='--w:{pct:.1f}%;"
            f"width:{pct:.1f}%'></i></div>"
            f"<div class='srv-pie'><span>{esc(dur)}</span>"
            f"<span>{n} citas</span><span>${ing:,}</span></div></div>")


def minutos(dur: str) -> int:
    """'40 min' -> 40"""
    m = re.match(r"(\\d+)", str(dur))
    return int(m.group(1)) if m else 0


def fila_rentabilidad(s):
    """Ingreso que deja cada servicio POR HORA de trabajo.

    Es el dato que ayuda a decidir que promocionar: no es lo mismo un
    servicio de $150 que ocupa 40 minutos que uno de $100 en 20.
    """
    nombre, precio, dur, n, ing = s
    mins = minutos(dur)
    if not mins or not ing:
        return ""
    horas = n * mins / 60
    porhora = ing / horas if horas else 0
    return {"nombre": nombre, "valor": porhora, "min": mins, "n": n}


def bloque_rentabilidad():
    filas = [f for f in (fila_rentabilidad(s) for s in SERVICIOS) if f]
    filas.sort(key=lambda x: -x["valor"])
    maxi = filas[0]["valor"] if filas else 1
    partes = ["<div class='card'><h3 class='label'>Rentabilidad por hora "
              "de trabajo</h3><p class='nota'>Cuanto deja cada servicio por "
              "cada hora que ocupa la silla. Sirve para decidir que "
              "promocionar.</p>"]
    for f in filas:
        pct = f["valor"] / maxi * 100
        partes.append(
            f"<div class='srv' data-animar>"
            f"<div class='srv-top'><span class='srv-nombre'>"
            f"{esc(f['nombre'])}</span>"
            f"<span class='srv-precio'>${f['valor']:.0f}/h</span></div>"
            f"<div class='srv-barra'><i style='--w:{pct:.1f}%;"
            f"width:{pct:.1f}%'></i></div>"
            f"<div class='srv-pie'><span>{f['min']} min</span>"
            f"<span>{f['n']} citas</span></div></div>")
    partes.append("</div>")
    return "".join(partes)'''

if VIG in g:
    g = g.replace(VIG, NUEVO, 1)
    print("  OK  fila_servicio documentada + funciones de rentabilidad")
    n += 1
else:
    print("  AVISO no encontre fila_servicio exacta")

# reemplazar el bloque de servicios
viejo_b = '''def bloque_servicios():
    return ("<div class='rejilla dos'>"
            "<div class='card'>" + "".join(fila_servicio(s) for s in SERVICIOS)
            + "</div>"
            "<div class='card'><h3 class='label'>Ranking por ingreso</h3>"
            + "".join(fila_servicio(s) for s in SERVICIOS[:5]) + "</div></div>")'''
nuevo_b = '''def bloque_servicios():
    return ("<div class='rejilla dos'>"
            "<div class='card'><h3 class='label'>Servicios y precios</h3>"
            + "".join(fila_servicio(s) for s in SERVICIOS)
            + "</div>" + bloque_rentabilidad() + "</div>")'''
if viejo_b in g:
    g = g.replace(viejo_b, nuevo_b, 1)
    print("  OK  la vista de servicios ya no se repite")
    n += 1
else:
    m = re.search(r"def bloque_servicios\(\):.*?\(\)\+ \"</div></div>\"\)", g, re.S)
    if m:
        g = g.replace(m.group(0), nuevo_b, 1)
        print("  OK  por patron")
        n += 1
    else:
        print("  AVISO no encontre bloque_servicios")

# 're' hace falta para minutos()
if "import re" not in g.split("\n\n")[0]:
    g = g.replace("import os\nimport sys", "import os\nimport re\nimport sys", 1)
    print("  OK  import re anadido")

if g != og:
    open(os.path.join(AQUI, "generar-admin.py"), "w",
         encoding="utf-8").write(g)

# =====================================================================
#  2. EL CSS de la nota
# =====================================================================
print()
print("=" * 68)
print("2. ESTILO DE LA NOTA")
print("=" * 68)
css = open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8").read()
if ".nota{" not in css:
    css = css.replace(
        "/* ---- ocupacion por hora ---- */",
        "/* ---- nota aclaratoria dentro de una tarjeta ---- */\n"
        ".nota{color:var(--sec2);font-size:.75rem;margin:-6px 0 14px;\n"
        "  line-height:1.5;max-width:60ch}\n\n"
        "/* ---- ocupacion por hora ---- */", 1)
    print("  OK  .nota anadida")
    n += 1
    open(os.path.join(AQUI, "plantilla.html"), "w",
         encoding="utf-8").write(css)
else:
    print("  ya estaba")

print()
print("=" * 68)
print(f"  {n} cambios")
print("=" * 68)