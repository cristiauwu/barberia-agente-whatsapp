#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reemplaza el CSS del dashboard por el lenguaje visual de Mr.BLACK.

TOKENS EXTRAIDOS DEL SITIO REAL https://mrblack-case.dolganev.com/:
  colores : #262626 (black), #afab8e (green), #df6341 (orange = ACENTO),
            #de7e64 (salmon), #a59171 (brown), #f3f1e9 (ivory), #f9f7f7 (white)
  fuentes : Inter Tight (base), Courier Prime (mono), Unbounded (accent)
  firma   : TODO en uppercase con letter-spacing -.03em; BORDES DASHED
            (1px dashed color-mix 30%); icono de 6 puntos; transiciones
            cubic-bezier(.22,1,.36,1) a .3s/.6s; caption en mono diminuta
            arriba y cifra enorme debajo; tabular-nums; foco 2px dashed.

Las 3 tipografias se EMBEBEN en base64 para que funcione sin internet.

NO se toca: el SQL, la lectura de datos, ni la firma de los helpers que
usan los bloques (barra, tarjeta, vacio, num, entero, dinero, esc).
"""
import base64
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = Path(r"G:\Barberia\archivos\dashboard")
GEN = AQUI / "generar-dashboard.py"
FUENTES = AQUI / "tipografias"

# ---------------------------------------------------------------------------
# 1. Las tipografias embebidas
# ---------------------------------------------------------------------------
FAMILIAS = [
    ("Inter Tight", "InterTight-Regular.woff2", 400, "normal"),
    ("Courier Prime", "CourierPrime-Regular.woff2", 400, "normal"),
    ("Unbounded", "Unbounded-ExtraBold.woff2", 800, "normal"),
]


def bloque_fuentes() -> str:
    """Genera los @font-face con las fuentes en base64.

    Si falta un archivo, se omite ese @font-face: el CSS tiene pilas de
    respaldo, asi que el dashboard se sigue viendo bien.
    """
    partes = []
    for familia, archivo, peso, estilo in FAMILIAS:
        ruta = FUENTES / archivo
        if not ruta.exists():
            print(f"  aviso: falta {archivo}, se omite (usara respaldo)")
            continue
        b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
        partes.append(
            "@font-face{font-family:'%s';src:url(data:font/woff2;base64,%s) "
            "format('woff2');font-weight:%d;font-style:%s;font-display:swap}"
            % (familia, b64, peso, estilo))
        print(f"  embebida {familia} ({len(b64) // 1024} KB en base64)")
    return "".join(partes)


# ---------------------------------------------------------------------------
# 2. El CSS nuevo
# ---------------------------------------------------------------------------
def construir_css() -> str:
    # OJO: el CSS esta lleno de `%` (porcentajes de ancho). Por eso NO se
    # usa el operador `%` para insertar las fuentes: se usa un marcador y
    # .replace(), que no interpreta los `%`.
    fuentes = bloque_fuentes()
    return (PLANTILLA_CSS.replace("/*@FUENTES@*/", fuentes))


PLANTILLA_CSS = """
/* ==========================================================================
   Panel de Barber Chinos
   Lenguaje visual: Mr.BLACK (mrblack-case.dolganev.com)
   Tokens exactos extraidos de su CSS. Oscuro, monoespaciado en las
   etiquetas, acento unico, bordes discontinuos, cifras tabulares.
   Sin internet: las tipografias van embebidas en base64.
   ========================================================================== */
/*@FUENTES@*/
:root{
  --black:#262626; --green:#afab8e; --orange:#df6341; --salmon:#de7e64;
  --brown:#a59171; --ivory:#f3f1e9; --white:#f9f7f7;
  --font-base:'Inter Tight',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
  --font-mono:'Courier Prime',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --font-accent:'Unbounded',var(--font-base);
  --ease:cubic-bezier(.22,1,.36,1);
  --t:.3s; --t2:.6s;
  /* el tablero es oscuro; el acento es el naranja del sitio */
  --bg:#1c1c1c; --panel:#232323; --linea:rgba(243,241,233,.16);
  --ink:#f3f1e9; --tenue:rgba(243,241,233,.58);
  --radio:2px; --radio-int:1px;
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--ink);
  font-family:var(--font-base); font-size:17px; line-height:120%;
  -webkit-text-size-adjust:100%;
  -webkit-font-smoothing:antialiased;
  font-variant-numeric:tabular-nums;
}
.envoltura{max-width:1180px;margin:0 auto;padding:22px 16px 60px}

/* ---- etiquetas: la firma del sitio. Mono, mayusculas, diminutas ---- */
.etiq,.kpi-t,.chip,.mono,h2,.sub,.pie,.fila-cab .val .muted,
.descriptor{font-family:var(--font-mono)}
.etiq,.kpi-t,.chip,.descriptor{
  text-transform:uppercase;letter-spacing:-.03em;font-size:15px;
}

/* ---- cabecera ---- */
header.cab{
  position:relative;padding:0 0 22px;margin-bottom:26px;
  border-bottom:1px dashed var(--linea);
}
.marca{display:flex;align-items:center;gap:10px;margin-bottom:20px}
.marca svg{width:9px;height:15px;flex:none;color:var(--orange)}
.marca .mono{
  text-transform:uppercase;letter-spacing:-.03em;font-size:15px;color:var(--tenue);
}
h1{
  margin:0;font-family:var(--font-accent);font-weight:800;
  text-transform:uppercase;letter-spacing:-.03em;line-height:100%;
  font-size:clamp(1.875rem,1.15rem + 3.2vw,4rem);color:var(--ivory);
}
.sub{margin:14px 0 0;color:var(--tenue);text-transform:uppercase;
  letter-spacing:-.03em;font-size:15px;line-height:130%}
.meta{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}
.chip{
  display:inline-flex;align-items:center;gap:8px;
  border:1px dashed var(--linea);border-radius:var(--radio);
  padding:8px 12px;color:var(--tenue);background:transparent;
}
.chip b{color:var(--orange);font-weight:400}

/* ---- titulos de seccion ---- */
h2{
  text-transform:uppercase;letter-spacing:-.03em;color:var(--tenue);
  margin:44px 0 16px;font-weight:400;font-size:15px;
  padding-bottom:10px;border-bottom:1px dashed var(--linea);
}
h2.primero{margin-top:8px}
h2::before{content:"/// ";color:var(--orange)}

/* ---- rejilla de KPIs: caption diminuto + cifra enorme ---- */
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.kpi{
  position:relative;background:var(--panel);border:1px dashed var(--linea);
  border-radius:var(--radio);padding:18px 18px 20px;
  transition:border-color var(--t) var(--ease),background-color var(--t) var(--ease);
}
.kpi:hover{border-color:rgba(223,99,65,.55);background:#252525}
.kpi-t{
  color:var(--tenue);margin-bottom:14px;display:block;
}
.kpi-v{
  font-family:var(--font-accent);font-weight:800;text-transform:uppercase;
  letter-spacing:-.03em;line-height:100%;
  font-size:clamp(1.5rem,1.05rem + 1.6vw,2.5rem);color:var(--ivory);
  font-variant-numeric:tabular-nums;
}
.kpi-p{color:var(--tenue);margin-top:10px;font-size:14px;line-height:130%}
.kpi-acento .kpi-v{color:var(--orange)}
.kpi-acento{border-color:rgba(223,99,65,.45)}

/* ---- barras horizontales ---- */
.panel{
  background:var(--panel);border:1px dashed var(--linea);
  border-radius:var(--radio);padding:18px;
}
.fila+.fila{margin-top:18px;padding-top:18px;border-top:1px dashed var(--linea)}
.fila-cab{display:flex;justify-content:space-between;align-items:baseline;
  gap:16px;margin-bottom:10px}
.fila-cab .etiq{color:var(--ink);font-size:15px}
.fila-cab .val{
  font-family:var(--font-accent);font-weight:800;text-transform:uppercase;
  letter-spacing:-.03em;font-size:17px;color:var(--orange);text-align:right;
  font-variant-numeric:tabular-nums;
}
.muted{color:var(--tenue);font-family:var(--font-mono);font-size:13px;
  font-weight:400;text-transform:none;letter-spacing:0}
.pista{
  height:6px;background:transparent;border:1px dashed var(--linea);
  border-radius:var(--radio-int);overflow:hidden;
}
.relleno{
  height:100%;background:var(--orange);
  transition:width var(--t2) var(--ease);
}

/* ---- tendencia 30 dias (SVG-free: divs con altura) ---- */
.tendencia{
  display:flex;align-items:flex-end;gap:4px;height:190px;
  padding:0 2px;border-bottom:1px dashed var(--linea);
}
.col{flex:1 1 0;display:flex;align-items:flex-end;height:100%;min-width:0}
.barra-v{
  width:100%;background:var(--green);border-radius:var(--radio-int) var(--radio-int) 0 0;
  transition:height var(--t2) var(--ease),background-color var(--t) var(--ease);
}
.barra-v.hoy{background:var(--orange)}
.barra-v.vacia{background:rgba(243,241,233,.14)}
.col:hover .barra-v{background:var(--orange)}
.eje{
  display:flex;justify-content:space-between;gap:12px;margin-top:12px;
  color:var(--tenue);font-family:var(--font-mono);font-size:13px;
  text-transform:uppercase;letter-spacing:-.03em;
}

/* ---- pila + leyenda (estados, clientes) ---- */
.pila{
  display:flex;height:14px;border:1px dashed var(--linea);
  border-radius:var(--radio-int);overflow:hidden;margin-bottom:18px;
}
.pila span{display:block;height:100%}
.leyenda{display:grid;gap:9px;margin-top:14px}
.leyenda>span{
  display:flex;align-items:center;gap:10px;color:var(--tenue);
  font-family:var(--font-mono);font-size:14px;line-height:130%;
}
.leyenda i{width:10px;height:10px;flex:none;border-radius:50%}
.leyenda b{color:var(--ink);font-weight:400}

/* ---- tablas ---- */
table{width:100%;border-collapse:collapse}
thead th{
  text-align:left;font-family:var(--font-mono);font-weight:400;
  text-transform:uppercase;letter-spacing:-.03em;font-size:13px;
  color:var(--tenue);padding:0 10px 12px 0;
  border-bottom:1px dashed var(--linea);
}
tbody td{padding:13px 10px 13px 0;border-bottom:1px dashed var(--linea);
  font-size:16px}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background-color var(--t) var(--ease)}
tbody tr:hover{background:rgba(243,241,233,.04)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;
  font-family:var(--font-accent);font-weight:800;letter-spacing:-.03em}
.pill{
  display:inline-block;border:1px dashed var(--linea);border-radius:var(--radio);
  padding:3px 9px;font-family:var(--font-mono);font-size:12px;
  text-transform:uppercase;letter-spacing:-.03em;color:var(--tenue);
}
.pill-agendado{border-color:rgba(175,171,142,.6);color:var(--green)}
.pill-atendido{border-color:rgba(223,99,65,.6);color:var(--orange)}
.pill-cancelado,.pill-no_show{border-color:rgba(222,126,100,.55);color:var(--salmon)}
.pill-confirmado{border-color:rgba(243,241,233,.5);color:var(--ivory)}
.pill-reprogramado{border-color:rgba(165,145,113,.6);color:var(--brown)}

/* ---- estado vacio: intencional, nunca roto ---- */
.vacio{
  border:1px dashed var(--linea);border-radius:var(--radio);
  padding:22px 20px;background:transparent;
}
.vacio b{
  display:block;font-family:var(--font-accent);font-weight:800;
  text-transform:uppercase;letter-spacing:-.03em;font-size:17px;
  color:var(--ink);margin-bottom:8px;
}
.vacio{color:var(--tenue);font-size:15px;line-height:140%}
.vacio code,.vacio i{
  font-family:var(--font-mono);font-style:normal;color:var(--green);
}

/* ---- avisos ---- */
.avisos{display:grid;gap:10px;margin-bottom:8px}
.aviso{
  border:1px dashed rgba(223,99,65,.5);border-radius:var(--radio);
  padding:14px 16px;font-family:var(--font-mono);font-size:14px;
  text-transform:uppercase;letter-spacing:-.03em;color:var(--orange);
  line-height:140%;
}

/* ---- pie ---- */
.pie{
  margin-top:48px;padding-top:20px;border-top:1px dashed var(--linea);
  color:var(--tenue);font-family:var(--font-mono);font-size:13px;
  text-transform:uppercase;letter-spacing:-.03em;line-height:150%;
}
.pie b{color:var(--ivory);font-weight:400}
.pie code,.pie i{color:var(--green);font-style:normal}

a{color:var(--orange);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px dashed var(--orange);outline-offset:3px}

/* ---- responsive: movil primero el contenido, sin scroll lateral ---- */
@media (max-width:1023px){
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .envoltura{padding:20px 14px 48px}
}
@media (max-width:600px){
  .kpis{grid-template-columns:1fr}
  h1{font-size:clamp(1.5rem,7vw,2rem)}
  .kpi{padding:16px}
  .panel{padding:15px}
  .tendencia{height:150px;gap:2px}
  thead th{font-size:12px}
  tbody td{font-size:15px;padding:11px 8px 11px 0}
}
/* el dueno gira el telefono: este OR es del patron de referencia */
@media (max-width:1100px), (orientation:portrait){
  .kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:.01ms!important;transition-duration:.01ms!important;
  }
}
"""


# ---------------------------------------------------------------------------
# 3. El icono de 6 puntos (marca del sitio)
# ---------------------------------------------------------------------------
ICONO_PUNTOS = (
    "<svg viewBox='0 0 9 15' fill='none' aria-hidden='true'>"
    "<circle cx='1.5' cy='1.5' r='1.5' fill='currentColor'/>"
    "<circle cx='1.5' cy='7.5' r='1.5' fill='currentColor'/>"
    "<circle cx='1.5' cy='13.5' r='1.5' fill='currentColor'/>"
    "<circle cx='4.5' cy='10.5' r='1.5' fill='currentColor'/>"
    "<circle cx='4.5' cy='4.5' r='1.5' fill='currentColor'/>"
    "<circle cx='7.5' cy='7.5' r='1.5' fill='currentColor'/>"
    "</svg>")


def main():
    src = GEN.read_text(encoding="utf-8")
    css_nuevo = construir_css()

    # --- reemplazar el bloque CSS completo (de `CSS = """` a `"""`) ---
    m = re.search(r'CSS = """.*?"""', src, re.S)
    if not m:
        print("ERROR: no encontre el bloque CSS")
        return 1
    print(f"  CSS detectado: {len(m.group(0))} chars")
    src = src[:m.start()] + 'CSS = """' + css_nuevo + '"""' + src[m.end():]
    print(f"  CSS nuevo:     {len(css_nuevo)} chars (+{len(css_nuevo) - len(m.group(0))})")

    # --- inyectar la marca de puntos en la cabecera ---
    viejo = '        "<header class=\'cab\'>",'
    nuevo = ('        "<header class=\'cab\'>",\n'
             f'        "<div class=\'marca\'>{ICONO_PUNTOS}'
             '<span class=\'mono\'>Panel del negocio</span></div>",')
    if viejo in src and "class='marca'" not in src:
        src = src.replace(viejo, nuevo, 1)
        print("  marca de 6 puntos inyectada en la cabecera")
    elif "class='marca'" in src:
        print("  la marca ya estaba")
    else:
        print("  AVISO: no encontre la cabecera exacta; reviso")

    # --- el pie: anadir la nota de que es obra local ---
    GEN.write_text(src, encoding="utf-8")
    print(f"\n  escribir: {GEN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())