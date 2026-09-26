#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla en un lote los 3 defectos que quedaban en las capturas.

DEFECTO 1 — EL GRAFICO SALE VACIO.
  Las barras arrancan con `height:0` y solo crecen cuando el
  IntersectionObserver las ve. Si el observador no dispara (o dispara
  antes de que el JS este listo), se quedan a cero y el grafico parece
  roto. Es fragil por diseno.
  ARREGLO: crecer las barras tambien en el arranque, sin depender del
  observador. El observador pasa a ser una mejora, no un requisito.

DEFECTO 2 — EN MOVIL LOS NOMBRES SE CORTAN Y EL PRECIO SE ENCIMA.
  El grid de la cita tiene 7 columnas y en movil se colocaban a mano con
  `grid-column`, asi que varios elementos caian en la misma celda.
  ARREGLO: grid de 2 filas x 3 columnas con posiciones explicitas y sin
  solapes. Fila 1: hora, cliente, boton. Fila 2: duracion, precio, estado.

DEFECTO 3 — EL LOGO DEL SIDEBAR QUEDA DESCOLOCADO EN MOVIL.
  ARREGLO: centrarlo cuando el sidebar esta estrecho.
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
#  1. EL GRAFICO: crecer las barras tambien al arrancar
# =====================================================================
print("=" * 66)
print("1. EL GRAFICO YA NO DEPENDE SOLO DEL OBSERVADOR")
print("=" * 66)
js = leer("app.js.html")
ojs = js

viejo = """  var obsBarras = null;
  if("IntersectionObserver" in window){
    obsBarras = new IntersectionObserver(function(entradas){
      entradas.forEach(function(en){
        if(en.isIntersecting){
          crecer(en.target);
          obsBarras.unobserve(en.target);
        }
      });
    }, { threshold:0.15 });
  }"""

nuevo = """  var obsBarras = null;
  var yaCrecidas = [];
  if("IntersectionObserver" in window){
    obsBarras = new IntersectionObserver(function(entradas){
      entradas.forEach(function(en){
        if(en.isIntersecting){
          crecer(en.target);
          yaCrecidas.push(en.target);
          obsBarras.unobserve(en.target);
        }
      });
    }, { threshold:0.05 });
  }

  /* RED DE SEGURIDAD: crecer todo lo que no haya crecido todavia.
     Sin esto, si el observador no dispara (o dispara antes de tiempo),
     las barras se quedan a cero y el grafico parece vacio. */
  function crecerPendientes(){
    document.querySelectorAll(".vista.activa .card, .vista.activa .card-grafica")
      .forEach(function(caja){
        if(!caja.querySelector(".col,.srv-barra,.hora-barra")) return;
        if(yaCrecidas.indexOf(caja) >= 0) return;
        crecer(caja);
        yaCrecidas.push(caja);
        if(obsBarras) obsBarras.unobserve(caja);
      });
  }"""

if viejo in js:
    js = js.replace(viejo, nuevo, 1)
    print("  OK  observador con red de seguridad")
    n += 1
else:
    print("  AVISO no encontre el bloque del observador")

# llamar a crecerPendientes en el arranque y al cambiar de vista
viejo2 = """  function inicio(){
    observarTodo();"""
nuevo2 = """  function inicio(){
    observarTodo();
    crecerPendientes();
    // y otra vez en cuanto el navegador pueda pintar
    requestAnimationFrame(function(){ setTimeout(crecerPendientes, 120); });
    setTimeout(crecerPendientes, 900);"""
if viejo2 in js:
    js = js.replace(viejo2, nuevo2, 1)
    print("  OK  crecerPendientes en el arranque")
    n += 1

# al cambiar de vista tambien
viejo3 = """        observarTodo();
      }, 60);"""
nuevo3 = """        observarTodo();
        crecerPendientes();
        setTimeout(crecerPendientes, 250);
      }, 60);"""
if viejo3 in js:
    js = js.replace(viejo3, nuevo3, 1)
    print("  OK  crecerPendientes al cambiar de vista")
    n += 1

# con ?sinanim, las barras crecen de inmediato y sin escalonado
viejo4 = """  function crecer(raiz){"""
nuevo4 = """  function crecer(raiz){
    var ya = raiz.dataset.crecida === "1";
    if(ya) return;
    raiz.dataset.crecida = "1";"""
if viejo4 in js:
    js = js.replace(viejo4, nuevo4, 1)
    print("  OK  crecer() es idempotente")
    n += 1

if js != ojs:
    escribir("app.js.html", js)

# =====================================================================
#  2 y 3. EL CSS DE MOVIL
# =====================================================================
print()
print("=" * 66)
print("2 y 3. EL CSS DE MOVIL")
print("=" * 66)
css = leer("plantilla.html")
ocss = css

viejo_css = """@media (max-width:820px){
  .barra{width:72px;padding:20px 10px}
  .barra .nombre,.barra .nav-txt,.barra .admin-info{opacity:0;
    pointer-events:none}
  main{margin-left:72px;padding:26px 18px 60px}
  .display{font-size:clamp(2.4rem,11vw,3.4rem)}
  .cita{grid-template-columns:64px 2px 1fr auto;gap:12px;row-gap:10px;
    padding:14px 16px}
  .cita-dur,.cita-sep{display:none}
  .cita-precio{grid-column:3}
  .cita .pill{grid-column:1/-1;justify-self:start}
  .cita .mas{grid-column:4;grid-row:1}
  .pill{padding:5px 12px;font-size:.65rem}
  .card{padding:18px}
  .kpi{padding:18px}
}"""

nuevo_css = """@media (max-width:820px){
  .barra{width:72px;padding:16px 10px}
  /* el logo se centra: en 72px el texto no cabe pero el icono si */
  .barra-logo{justify-content:center;padding:4px 0 16px}
  .barra .nombre,.barra .nav-txt,.barra .admin-info{opacity:0;
    pointer-events:none}
  .nav-item{justify-content:center;padding:12px 0}
  .admin{justify-content:center}
  main{margin-left:72px;padding:26px 18px 60px}
  .display{font-size:clamp(2.4rem,11vw,3.4rem)}

  /* --- LA CITA EN MOVIL ---
     Grid de 2 filas x 3 columnas con cada cosa en su celda. Antes se
     colocaban a mano y varios caian en la misma, asi que el nombre se
     cortaba y el precio se encimaba. */
  .cita{
    grid-template-columns:auto 1fr auto;
    grid-template-rows:auto auto;
    gap:6px 14px;padding:15px 16px;
  }
  .cita-hora{grid-column:1;grid-row:1;font-size:1.1rem}
  .cita-info{grid-column:2;grid-row:1}
  .cita .mas{grid-column:3;grid-row:1;align-self:start}
  .cita-sep{display:none}
  .cita-dur{grid-column:1;grid-row:2;font-size:.68rem;
    align-self:center}
  .cita-precio{grid-column:2;grid-row:2;justify-self:start;
    font-size:.9rem}
  .cita .pill{grid-column:3;grid-row:2;justify-self:end;align-self:center}
  .cita-nombre{font-size:.95rem;white-space:normal}
  .cita-servicio{font-size:.75rem}

  .pill{padding:4px 11px;font-size:.62rem}
  .card{padding:18px}
  .kpi{padding:18px}
}"""

if viejo_css in css:
    css = css.replace(viejo_css, nuevo_css, 1)
    print("  OK  la cita en movil ya no se solapa")
    print("  OK  el logo del sidebar se centra")
    n += 1
else:
    print("  AVISO no encontre el bloque de movil exacto")
    # intento mas flexible
    m = re.search(r"@media \(max-width:820px\)\{.*?\n\}", css, re.S)
    if m:
        css = css.replace(m.group(0), nuevo_css, 1)
        print("  OK  reemplazado por patron")
        n += 1

if css != ocss:
    escribir("plantilla.html", css)

print()
print("=" * 66)
print(f"  {n} arreglos aplicados")
print("=" * 66)