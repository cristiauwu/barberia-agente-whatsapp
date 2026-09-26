#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige los 2 defectos visuales vistos en las capturas.

DEFECTO 1 — La leyenda se rompe con texto largo (móvil).
  En 'bloque_salud' el HTML es:
      <span class='muted'>Base del mes: <b>0</b> cita(s) programadas ...</span>
  y el CSS hacia `.leyenda>span{display:flex}`. En flex, el <b> del medio se
  convierte en un ITEM APARTE, asi que la frase se parte en 3 columnas
  estrechas: el texto se ve troceado y apretado en el movil.
  ARREGLO: la leyenda deja de ser flex. El icono se pone en linea con
  inline-block y margen, que es como se comporta el texto normal.

DEFECTO 2 — El grafico vacio parece un hueco roto.
  Con 0 datos, las 30 barras se dibujan al 1,5% de 190px = ~3px, que queda
  pegado al borde inferior y no se ve. Resultado: un rectangulo grande y
  vacio, que parece un error, no un grafico sin datos.
  ARREGLO: (a) las barras vacias tienen una altura minima visible y algo
  mas de contraste; (b) el area del grafico lleva lineas guia horizontales
  sutiles, asi se lee como "grafico sin datos" y no como un hueco.
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

# --- ARREGLO 1: la leyenda deja de ser flex -------------------------------
VIEJO_LEYENDA = """.leyenda{display:grid;gap:9px;margin-top:14px}
.leyenda>span{
  display:flex;align-items:center;gap:10px;color:var(--tenue);
  font-family:var(--font-mono);font-size:14px;line-height:130%;
}
.leyenda i{width:10px;height:10px;flex:none;border-radius:50%}"""

NUEVO_LEYENDA = """.leyenda{display:grid;gap:9px;margin-top:14px}
/* display:block a proposito: con flex, el <b> de dentro se convierte en
   un item aparte y la frase se trocea en columnas estrechas en el movil. */
.leyenda>span{
  display:block;color:var(--tenue);
  font-family:var(--font-mono);font-size:14px;line-height:140%;
}
.leyenda i{
  display:inline-block;width:10px;height:10px;border-radius:50%;
  margin-right:8px;vertical-align:middle;
}"""

# --- ARREGLO 2: el grafico vacio se lee como grafico ----------------------
VIEJO_GRAF = """.tendencia{
  display:flex;align-items:flex-end;gap:4px;height:190px;
  padding:0 2px;border-bottom:1px dashed var(--linea);
}"""
NUEVO_GRAF = """.tendencia{
  display:flex;align-items:flex-end;gap:4px;height:190px;
  padding:0 2px;border-bottom:1px dashed var(--linea);
  /* Guias horizontales: sin datos, el area se lee como un grafico en cero
     y no como un hueco roto. */
  background-image:repeating-linear-gradient(
    to top, rgba(243,241,233,.07) 0 1px, transparent 1px 38px);
}"""

VIEJO_VACIA = ".barra-v.vacia{background:rgba(243,241,233,.14)}"
NUEVO_VACIA = (".barra-v.vacia{background:rgba(243,241,233,.22);"
               "min-height:3px}")


def main():
    src = GEN.read_text(encoding="utf-8")
    cambios = 0

    for viejo, nuevo, nombre in (
        (VIEJO_LEYENDA, NUEVO_LEYENDA, "leyenda (texto troceado en movil)"),
        (VIEJO_GRAF, NUEVO_GRAF, "guias del grafico"),
        (VIEJO_VACIA, NUEVO_VACIA, "barras vacias visibles"),
    ):
        if viejo in src:
            src = src.replace(viejo, nuevo, 1)
            cambios += 1
            print(f"  OK    {nombre}")
        else:
            print(f"  AVISO no encontre el bloque: {nombre}")

    if cambios:
        GEN.write_text(src, encoding="utf-8")
    print(f"\n  {cambios} de 3 arreglos aplicados")
    return 0 if cambios == 3 else 1


if __name__ == "__main__":
    sys.exit(main())