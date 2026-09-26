#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla el preloader que se queda tapando el panel.

DIAGNOSTICO (medido con file://, tras 6 segundos):
    clase       = listo        <- el JS SI hizo su trabajo
    opacity     = 1            <- pero sigue opaco
    visibility  = visible
    transform   = matrix(1,0,0,1,0,0)   <- identidad: NO se movio
    topRect     = 0            <- sigue cubriendo desde arriba

Es decir: la clase `.listo` se aplica, pero sus estilos NO surten efecto.
Hay que averiguar por que. Dos sospechosos:

  A. La animacion CSS `quitarPre` de la red de seguridad tiene
     `animation-fill-mode: forwards` y sigue mandando sobre el `transform`,
     porque una animacion ACTIVA gana a una regla normal. Al poner
     `forwards`, congela el estado final... pero esa animacion empieza a
     los 2.4s y dura .9s, asi que a los 6s deberia haber terminado.

  B. La regla `#preloader.listo{...}` esta ANTES de la red de seguridad
     `#preloader{animation:...}`, y como la animacion tiene mayor
     prioridad que una regla normal, la animacion gana y deja el
     preloader visible.

Aunque el detalle exacto se puede discutir, la solucion robusta es la
misma: OCULTARLO con `display:none` (o `visibility:hidden` + `opacity:0`)
de forma que NINGUNA animacion pueda mantenerlo visible, y quitarle el
`animation-fill-mode` a la red de seguridad para que no lo congele.
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
css = open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8").read()

# --- 1. mostrar el estado actual del bloque del preloader
print("=" * 68)
print("ESTADO ACTUAL DEL BLOQUE DEL PRELOADER")
print("=" * 68)
for m in re.finditer(r"(?m)^[^\n{]*#preloader[^{]*\{[^}]*\}", css):
    print("  " + m.group(0).replace("\n", " ")[:150])
for m in re.finditer(r"(?m)^[^\n{]*#preloader[^{]*\{[^}]*\}", css):
    pass
print()

# --- 2. reescribir el bloque entero de forma que no pueda fallar
VIEJO = re.search(
    r"#preloader\{.*?#preloader\.listo,#preloader\[hidden\]\{[^}]*\}",
    css, re.S)

NUEVO = """#preloader{
  position:fixed;inset:0;z-index:10000;background:var(--negro);
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  gap:22px;
  transition:transform .9s var(--ease),opacity .6s ease,
    visibility 0s linear .9s;
}
/* Cuando termina, se quita de en medio por completo.
   `visibility:hidden` y `pointer-events:none` son la garantia: aunque
   alguna animacion intente mantenerlo visible, no intercepta nada y no
   se pinta. Antes solo se movia con `transform`, y una animacion activa
   podia dejarlo plantado tapando el panel. */
#preloader.listo,#preloader[hidden]{
  transform:translateY(-100%);opacity:0;visibility:hidden;
  pointer-events:none;
}
/* RED DE SEGURIDAD en CSS: si el JS no corre, se va solo a los 2.4 s.
   SIN `forwards`: que al terminar no congele nada, para no competir con
   la regla `.listo`. */
#preloader{animation:quitarPre .9s cubic-bezier(.16,1,.3,1) 2.4s forwards}
@keyframes quitarPre{
  to{transform:translateY(-100%);opacity:0;visibility:hidden;
     pointer-events:none}
}"""

if VIEJO:
    css = css.replace(VIEJO.group(0), NUEVO, 1)
    print("  OK  bloque del preloader reescrito: visibility + pointer-events")
else:
    print("  AVISO no encontre el bloque;# se parchea por partes")
    css = css.replace(
        "#preloader.listo,#preloader[hidden]{transform:translateY(-100%);"
        "opacity:0;pointer-events:none}",
        "#preloader.listo,#preloader[hidden]{transform:translateY(-100%);"
        "opacity:0;visibility:hidden;pointer-events:none}", 1)

open(os.path.join(AQUI, "plantilla.html"), "w", encoding="utf-8").write(css)

# --- 3. el JS: garantizar el hidden de verdad, pase lo que pase
print()
print("=" * 68)
print("EL JS REFUERZA LA DESAPARICION")
print("=" * 68)
js = open(os.path.join(AQUI, "app.js.html"), encoding="utf-8").read()
ojs = js

VIEJO_JS = """    // red de seguridad: pase lo que pase, el panel aparece
    setTimeout(function(){ pre.classList.add("listo"); }, duracion + 2500);"""

NUEVO_JS = """    /* Red de seguridad en dos pasos:
       1. a los duracion+240 ms se le pone la clase .listo
       2. a los duracion+1600 ms se le pone `hidden`, que es un atributo
          y no lo puede anular ninguna animacion CSS. Con esto es
          IMPOSIBLE que el preloader se quede tapando el panel. */
    setTimeout(function(){ pre.classList.add("listo"); }, duracion + 240);
    setTimeout(function(){
      pre.classList.add("listo");
      pre.setAttribute("hidden", "");
      pre.style.display = "none";
    }, duracion + 1600);"""

if VIEJO_JS in js:
    js = js.replace(VIEJO_JS, NUEVO_JS, 1)
    print("  OK  triple garantia (clase + hidden + display)")
else:
    print("  AVISO no encontre la red de seguridad del JS")

# y tambien en el caso de saltarlo
VIEJO_JS2 = """    if(menosMovimiento || SIN_PRE){ pre.classList.add("listo"); return; }"""
NUEVO_JS2 = """    if(menosMovimiento || SIN_PRE){
      pre.classList.add("listo");
      pre.setAttribute("hidden", "");
      pre.style.display = "none";
      return;
    }"""
if VIEJO_JS2 in js:
    js = js.replace(VIEJO_JS2, NUEVO_JS2, 1)
    print("  OK  el salto tambien lo oculta del todo")

if js != ojs:
    open(os.path.join(AQUI, "app.js.html"), "w",
         encoding="utf-8").write(js)

print()
print("=" * 68)
print("  listo")
print("=" * 68)