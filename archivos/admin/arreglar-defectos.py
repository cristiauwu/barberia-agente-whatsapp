#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla los defectos encontrados en la captura.

DEFECTO 1 (el grave): CHOQUE DE CLASES `.barra`
  La clase `.barra` se usa para DOS cosas distintas:
     - el sidebar lateral  -> `.barra { width: var(--sidebar) }`
     - las barras del grafico -> `.barra { width:100%; height:0 }`
  Al ser la misma clase y estar la del grafico despues en el CSS, gana esa
  y el sidebar se estira a los 1270px del contenedor. Eso arrastra todo lo
  demas: los botones del pie del sidebar aparecen a todo el ancho.

  ARREGLO: renombrar las barras del grafico a `.barra-col`. Son otra cosa y
  merecen otra clase. Se cambia en el CSS, en el JS y en el generador.

DEFECTO 2: la barra cobre de la parte superior
  Es el `.pre-linea` del preloader, que se ve como una linea suelta antes
  de que el preloader se vaya. Al ocultar el preloader de raiz desaparece.

DEFECTO 3: los KPI aparecen a medio animar en la captura
  La animacion de entrada arranca al entrar en pantalla; en una captura
  headless el elemento esta a medio recorrer. No es un defecto del panel,
  pero para la captura conviene poder desactivarlo con `?sinanim`.
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
cambios = 0


def leer(nombre):
    return open(os.path.join(AQUI, nombre), encoding="utf-8").read()


def escribir(nombre, texto):
    open(os.path.join(AQUI, nombre), "w", encoding="utf-8").write(texto)


# ---------------------------------------------------------------- CSS
print("=" * 66)
print("1. RENOMBRAR LAS BARRAS DEL GRAFICO A .barra-col")
print("=" * 66)
css = leer("plantilla.html")
orig = css

# 1a. la regla de la barra del grafico
#     hay que ser preciso: la del sidebar tiene position:fixed
viejo = (".barra{\n  width:100%;height:0;border-radius:4px 4px 0 0;"
         "background:var(--cobre);")
nuevo = (".barra-col{\n  width:100%;height:0;border-radius:4px 4px 0 0;"
         "background:var(--cobre);")
if viejo in css:
    css = css.replace(viejo, nuevo, 1)
    print("  OK  .barra -> .barra-col (regla de la barra del grafico)")
    cambios += 1
else:
    # variante con el salto de linea distinto
    m = re.search(r"\.barra\{\s*width:100%;height:0;[^}]*\}", css)
    if m:
        css = css.replace(m.group(0),
                          m.group(0).replace(".barra{", ".barra-col{", 1), 1)
        print("  OK  .barra -> .barra-col (por patron)")
        cambios += 1
    else:
        print("  AVISO no encontre la regla de la barra del grafico")

# 1b. el hover de la barra
if ".col:hover .barra{" in css:
    css = css.replace(".col:hover .barra{", ".col:hover .barra-col{", 1)
    print("  OK  hover de la barra")
    cambios += 1

# 1c. la variante vacia si existiera
css = css.replace(".barra.vacia", ".barra-col.vacia")

# 1d. el preloader: ocultarlo de raiz y quitar la linea suelta
if "#preloader.listo{" in css:
    css = css.replace(
        "#preloader.listo{",
        "#preloader.listo,#preloader[hidden]{", 1)
    print("  OK  el preloader tambien se oculta con [hidden]")
    cambios += 1

# 1e. permitir desactivar animaciones para las capturas
ancla = "[data-animar]{opacity:0;transform:translateY(40px);"
if ancla in css:
    css = css.replace(
        ancla,
        "/* Para capturas y pruebas: ?sinanim deja todo visible ya. */\n"
        "html[data-sinanim] [data-animar]{opacity:1!important;"
        "transform:none!important;transition:none!important}\n"
        + ancla, 1)
    print("  OK  modo sinanim para capturas")
    cambios += 1

if css != orig:
    escribir("plantilla.html", css)

# ---------------------------------------------------------------- JS
print()
print("=" * 66)
print("2. ACTUALIZAR EL JS")
print("=" * 66)
js = leer("app.js.html")
ojs = js

# la barra del grafico se busca por su clase nueva
if 'c.querySelector(".barra")' in js:
    js = js.replace('c.querySelector(".barra")',
                    'c.querySelector(".barra-col")', 1)
    print("  OK  el JS busca .barra-col")
    cambios += 1

# respetar ?sinanim y ?sinpre
if "var salta = " in js:
    js = js.replace(
        "var salta = /(\\?|&)sinpre/.test(location.search);",
        "var salta = /(\\?|&)sinpre/.test(location.search);", 1)
if "menosMovimiento = " in js and "data-sinanim" not in js:
    js = js.replace(
        'var menosMovimiento =\n    window.matchMedia("(prefers-reduced-motion: reduce)").matches;',
        'var menosMovimiento =\n'
        '    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||\n'
        '    /(\\?|&)sinanim/.test(location.search);\n'
        '  if(/(\\?|&)sinanim/.test(location.search)){\n'
        '    document.documentElement.setAttribute("data-sinanim", "");\n'
        '  }', 1)
    print("  OK  el JS respeta ?sinanim")
    cambios += 1

if js != ojs:
    escribir("app.js.html", js)

# ---------------------------------------------------------------- generador
print()
print("=" * 66)
print("3. ACTUALIZAR EL GENERADOR")
print("=" * 66)
gen = leer("generar-admin.py")
ogen = gen
if '"barra"' in gen or "class='barra'" in gen:
    gen = gen.replace('class=\'barra\'', 'class=\'barra-col\'')
    print("  OK  el generador emite .barra-col")
    cambios += 1
# la barra del grafico se emite con su clase
if "f\"<div class='barra' style=" in gen:
    gen = gen.replace("f\"<div class='barra' style=",
                      "f\"<div class='barra-col' style=", 1)
    print("  OK  el generador emite la barra del grafico como .barra-col")
    cambios += 1
if gen != ogen:
    escribir("generar-admin.py", gen)

print()
print("=" * 66)
print(f"  {cambios} cambios aplicados")
print("=" * 66)