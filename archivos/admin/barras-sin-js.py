#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hace que las barras tengan su altura correcta SIN depender del JS.

DIAGNOSTICO (verificado con dos pruebas independientes):
  - La sonda del navegador dice que las barras miden 75px.
  - Pero el examen de pixeles de la captura encuentra CERO pixeles de cobre
    en toda la zona del grafico: solo #121212 y #111111.
  Conclusion: en el momento de capturar, las barras seguian a cero. El
  crecimiento dependia de dos cosas fragiles a la vez:
     1. que el IntersectionObserver disparara
     2. que el timeout de crecimiento llegara antes que la captura
  Si cualquiera falla, el grafico sale vacio. Un grafico que puede salir
  vacio por un problema de tiempos esta mal construido.

ARREGLO: la altura final se escribe DIRECTAMENTE en el HTML. La animacion
pasa a ser un adorno encima (un `transform: scaleY()` que no afecta al
layout), no un requisito. Asi:
  - Con JS, se ve crecer.
  - Sin JS, se ve el grafico completo.
  - Con `prefers-reduced-motion` o `?sinanim`, se ve quieto y completo.
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
n = 0


def leer(f):
    return open(os.path.join(AQUI, f), encoding="utf-8").read()


def escribir(f, t):
    open(os.path.join(AQUI, f), "w", encoding="utf-8").write(t)


# =====================================================================
#  1. EL GENERADOR: escribir la altura y el ancho finales en el estilo
# =====================================================================
print("=" * 68)
print("1. EL GENERADOR ESCRIBE LA ALTURA FINAL")
print("=" * 68)
g = leer("generar-admin.py")
og = g

# --- barras verticales del grafico ---
viejo = ("f\"<div class='col' data-alto='{alto:.2f}'>\"\n"
         "            f\"<div class='barra-col' style='--alto:{alto:.2f}%'></div>\"\n"
         "            f\"<span class='pista'>{esc(f'Dia {dia}: ${v:,}')}</span></div>\")")
nuevo = ("f\"<div class='col' data-alto='{alto:.2f}'>\"\n"
         "            # La altura va escrita aqui: el grafico se ve completo\n"
         "            # aunque el JS no corra. El retardo escalona la animacion.\n"
         "            f\"<div class='barra-col' style='--alto:{alto:.2f}%;\"\n"
         "            f\"height:{alto:.2f}%;--d:{i * 0.02:.2f}s'></div>\"\n"
         "            f\"<span class='pista'>{esc(f'Dia {dia}: ${v:,}')}</span></div>\")")
if viejo in g:
    g = g.replace(viejo, nuevo, 1)
    print("  OK  barras verticales con altura final escrita")
    n += 1
else:
    # variante: el comentario puede tener otro formato
    m = re.search(
        r"f\"<div class='barra-col' style='--alto:\{alto:\.2f\}%'>"
        r"</div>\"", g)
    if m:
        g = g.replace(
            m.group(0),
            "f\"<div class='barra-col' style='--alto:{alto:.2f}%;"
            "height:{alto:.2f}%;--d:{i * 0.02:.2f}s'></div>\"", 1)
        print("  OK  barras verticales (por patron)")
        n += 1
    else:
        print("  AVISO no encontre la barra vertical")

# --- barras horizontales de servicios ---
viejo2 = ("f\"<div class='srv-barra'><i style='--w:{pct:.1f}%'></i></div>\"")
nuevo2 = ("f\"<div class='srv-barra'><i style='--w:{pct:.1f}%;\"\n"
          "            f\"width:{pct:.1f}%'></i></div>\"")
if viejo2 in g:
    g = g.replace(viejo2, nuevo2, 1)
    print("  OK  barras de servicios con ancho final")
    n += 1
else:
    print("  AVISO no encontre la barra de servicios")

# --- barras de horas ---
viejo3 = ("f\"<div class='hora-barra'><i style='--w:{pct:.1f}%'></i></div>\"")
nuevo3 = ("f\"<div class='hora-barra'><i style='--w:{pct:.1f}%;\"\n"
          "            f\"width:{pct:.1f}%'></i></div>\"")
if viejo3 in g:
    g = g.replace(viejo3, nuevo3, 1)
    print("  OK  barras de horas con ancho final")
    n += 1
else:
    print("  AVISO no encontre la barra de horas")

if g != og:
    escribir("generar-admin.py", g)

# =====================================================================
#  2. EL CSS: la animacion a base de transform, no de height
# =====================================================================
print()
print("=" * 68)
print("2. EL CSS: ANIMACION POR TRANSFORM")
print("=" * 68)
css = leer("plantilla.html")
ocss = css

# la barra del grafico ya no arranca a 0: su altura la manda el HTML
viejo_css = (".barra-col{\n  width:100%;height:0;border-radius:4px 4px 0 0;"
             "background:var(--cobre);\n  transition:height .9s var(--ease),"
             "background-color .3s ease;\n}")
nuevo_css = (".barra-col{\n"
             "  /* La altura viene escrita en el HTML, asi que el grafico se\n"
             "     ve completo aunque el JS no corra. */\n"
             "  width:100%;height:var(--alto,0);\n"
             "  border-radius:4px 4px 0 0;background:var(--cobre);\n"
             "  transform-origin:bottom center;\n"
             "  animation:subirBarra .9s var(--ease) both;\n"
             "  animation-delay:var(--d,0s);\n"
             "  transition:background-color .3s ease;\n"
             "}\n"
             "@keyframes subirBarra{\n"
             "  from{transform:scaleY(0)}\n"
             "  to{transform:scaleY(1)}\n"
             "}")
if viejo_css in css:
    css = css.replace(viejo_css, nuevo_css, 1)
    print("  OK  .barra-col con altura propia y animacion por transform")
    n += 1
else:
    m = re.search(r"\.barra-col\{[^}]*\}", css)
    if m:
        css = css.replace(m.group(0), nuevo_css, 1)
        print("  OK  .barra-col reemplazada (por patron)")
        n += 1
    else:
        print("  AVISO no encontre .barra-col")

# las barras horizontales: ancho propio + animacion por transform
viejo_h = (".srv-barra i{display:block;height:100%;width:0;"
           "background:var(--cobre);\n  border-radius:3px;"
           "transition:width .9s var(--ease)}")
nuevo_h = (".srv-barra i{display:block;height:100%;width:var(--w,0);\n"
           "  background:var(--cobre);border-radius:3px;\n"
           "  transform-origin:left center;\n"
           "  animation:crecerAncho .9s var(--ease) both;\n"
           "  animation-delay:var(--d,0s)}")
if viejo_h in css:
    css = css.replace(viejo_h, nuevo_h, 1)
    print("  OK  barras de servicios")
    n += 1
else:
    m = re.search(r"\.srv-barra i\{[^}]*\}", css)
    if m:
        css = css.replace(m.group(0), nuevo_h, 1)
        print("  OK  barras de servicios (por patron)")
        n += 1

viejo_ho = (".hora-barra i{display:block;height:100%;width:0;"
            "border-radius:5px;\n  background:linear-gradient(90deg,"
            "var(--cobre),var(--cobre-claro));\n  transition:width .9s "
            "var(--ease)}")
nuevo_ho = (".hora-barra i{display:block;height:100%;width:var(--w,0);\n"
            "  border-radius:5px;\n"
            "  background:linear-gradient(90deg,var(--cobre),"
            "var(--cobre-claro));\n"
            "  transform-origin:left center;\n"
            "  animation:crecerAncho .9s var(--ease) both;\n"
            "  animation-delay:var(--d,0s)}\n"
            "@keyframes crecerAncho{\n"
            "  from{transform:scaleX(0)}\n"
            "  to{transform:scaleX(1)}\n"
            "}")
if viejo_ho in css:
    css = css.replace(viejo_ho, nuevo_ho, 1)
    print("  OK  barras de horas")
    n += 1
else:
    m = re.search(r"\.hora-barra i\{[^}]*\}", css)
    if m:
        css = css.replace(m.group(0), nuevo_ho, 1)
        print("  OK  barras de horas (por patron)")
        n += 1

# sin animacion cuando se pide
ancla = "@media (prefers-reduced-motion:reduce){"
if ancla in css:
    css = css.replace(
        ancla,
        "/* Sin animacion: el estado final ya esta escrito en el HTML, asi\n"
        "   que se ve completo e inmediato. */\n"
        "html[data-sinanim] .barra-col,\n"
        "html[data-sinanim] .srv-barra i,\n"
        "html[data-sinanim] .hora-barra i{animation:none!important}\n"
        + ancla, 1)
    print("  OK  ?sinanim tambien desactiva las barras")
    n += 1

if css != ocss:
    escribir("plantilla.html", css)

# =====================================================================
#  3. EL JS: que no pelee con el CSS
# =====================================================================
print()
print("=" * 68)
print("3. EL JS YA NO ES NECESARIO PARA EL GRAFICO")
print("=" * 68)
js = leer("app.js.html")
ojs = js

# El JS escribia height/width; ahora ya vienen puestos. Se deja por si el
# HTML viniera sin ellos, pero comprobando que falten.
viejo_js = """      var alto = c.dataset.alto || "0";
      setTimeout(function(){
        b.style.height = alto + "%";
      }, menosMovimiento ? 0 : i * 20);"""
nuevo_js = """      // La altura ya viene escrita en el HTML. Solo se rellena si por
      // alguna razon faltara, para no pisar el valor bueno.
      var alto = c.dataset.alto || "0";
      if(!b.style.height) b.style.height = alto + "%";"""
if viejo_js in js:
    js = js.replace(viejo_js, nuevo_js, 1)
    print("  OK  el JS no pisa la altura ya escrita")
    n += 1
else:
    print("  AVISO no encontre el bloque de altura del JS")

viejo_js2 = """    raiz.querySelectorAll(".srv-barra i, .hora-barra i").forEach(function(i, k){
      var w = i.style.getPropertyValue("--w") || "0%";
      setTimeout(function(){
        i.style.width = w;
      }, menosMovimiento ? 0 : k * 45);
    });"""
nuevo_js2 = """    raiz.querySelectorAll(".srv-barra i, .hora-barra i").forEach(function(i){
      // El ancho ya viene escrito en el HTML; solo se rellena si faltara.
      var w = i.style.getPropertyValue("--w") || "0%";
      if(!i.style.width) i.style.width = w;
    });"""
if viejo_js2 in js:
    js = js.replace(viejo_js2, nuevo_js2, 1)
    print("  OK  el JS no pisa el ancho ya escrito")
    n += 1
else:
    print("  AVISO no encontre el bloque de ancho del JS")

if js != ojs:
    escribir("app.js.html", js)

print()
print("=" * 68)
print(f"  {n} cambios aplicados")
print("=" * 68)