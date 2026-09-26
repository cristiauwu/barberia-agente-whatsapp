#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla el corte de nombres en movil, con los numeros medidos.

MEDICION REAL (iframe de 390px):
    .cita ancho = 234px, columnas del grid = 48.4 | 38.1 | 87.5
    .cita-nombre ancho = 38px, pero su texto necesita 64px

CAUSA: el grid es `auto 1fr auto`. La columna 3 toma el ancho de su hijo
mas ancho, que es la pILDORA "CONFIRMADA" (87px), no el boton (36px). Eso
deja a la columna del medio (1fr) con 38px y el nombre se corta.

ARREGLO: en movil la pildora deja de vivir en la columna 3 y pasa a
abarcar de la 2 a la 3 alineada a la derecha. Asi la columna 3 solo la
manda el boton (36px) y el nombre recupera ~140px. Ademas se aprieta un
poco el espaciado para ganar aire.

Resultado esperado en 390px:
    48 (hora) + 140 (nombre) + 36 (boton) + 24 (gaps) = 248  <  248 justos
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

VIEJO = """  /* --- LA CITA EN MOVIL ---
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
  .cita-servicio{font-size:.75rem}"""

NUEVO = """  /* --- LA CITA EN MOVIL ---
     Grid de 2 filas x 3 columnas. La columna 3 la manda SOLO el boton
     (36px): la pildora abarca de la 2 a la 3, asi no fuerza esa columna
     a 87px y el nombre recupera el ancho que necesita. */
  .cita{
    grid-template-columns:auto 1fr auto;
    grid-template-rows:auto auto;
    gap:5px 12px;padding:14px 16px;
  }
  .cita-hora{grid-column:1;grid-row:1;font-size:1.05rem}
  .cita-info{grid-column:2;grid-row:1}
  .cita .mas{grid-column:3;grid-row:1;align-self:start}
  .cita-sep{display:none}
  .cita-dur{grid-column:1;grid-row:2;font-size:.68rem;
    align-self:center;white-space:nowrap}
  .cita-precio{grid-column:2;grid-row:2;justify-self:start;
    font-size:.9rem}
  /* la pildora ocupa de la columna 2 a la 3, pegada a la derecha */
  .cita .pill{grid-column:2 / 4;grid-row:2;justify-self:end;
    align-self:center}
  .cita-nombre{font-size:.95rem;white-space:normal;line-height:1.25}
  .cita-servicio{font-size:.75rem}
  /* mas aire: la tarjeta pierde relleno en movil */
  .card-lista{border-radius:12px}
  main .card-lista{padding:0}"""

if VIEJO in css:
    css = css.replace(VIEJO, NUEVO, 1)
    print("  OK  el grid de la cita en movil ya no la comprime la pildora")
else:
    # por patron: reemplazar desde el comentario hasta el final del bloque
    m = re.search(r"  /\* --- LA CITA EN MOVIL ---.*?\.cita-servicio\{font-size:\.75rem\}",
                  css, re.S)
    if m:
        css = css.replace(m.group(0), NUEVO, 1)
        print("  OK  reemplazado por patron")
    else:
        print("  MAL no encontre el bloque de la cita en movil")
        sys.exit(1)

# ---- DE PASO: soporte de ?vista= para poder abrir una seccion concreta
# Sirve para enlazar directo a una seccion y para las capturas.
js = open(os.path.join(AQUI, "app.js.html"), encoding="utf-8").read()
if "VISTA_INICIAL" not in js:
    viejo_js = """  (function navegacion(){
    var botones = Array.prototype.slice.call(
      document.querySelectorAll(".nav-item"));"""
    nuevo_js = """  (function navegacion(){
    var botones = Array.prototype.slice.call(
      document.querySelectorAll(".nav-item"));
    /* ?vista=clientes abre esa seccion directamente. Util para enlazar
       y para las pruebas automaticas. */
    var pedida = (location.search.match(/[?&]vista=([a-z]+)/) || [])[1];"""
    if viejo_js in js:
        js = js.replace(viejo_js, nuevo_js, 1)

    viejo_js2 = """    botones.forEach(function(b){
      b.addEventListener("click", function(){ mostrar(b.dataset.vista); });
    });
  })();"""
    nuevo_js2 = """    botones.forEach(function(b){
      b.addEventListener("click", function(){ mostrar(b.dataset.vista); });
    });

    if(pedida && document.querySelector(
        ".nav-item[data-vista='" + pedida + "']")){
      mostrar(pedida);
    }
  })();"""
    if viejo_js2 in js:
        js = js.replace(viejo_js2, nuevo_js2, 1)
        print("  OK  soporte de ?vista= para abrir una seccion")
    open(os.path.join(AQUI, "app.js.html"), "w", encoding="utf-8").write(js)
else:
    print("  el soporte de ?vista= ya estaba")

open(os.path.join(AQUI, "plantilla.html"), "w", encoding="utf-8").write(css)
print("  plantilla actualizada")