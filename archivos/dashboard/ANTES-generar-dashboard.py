#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generar-dashboard.py - Dashboard de KPIs de "Barber Chinos" (Barberia).

QUE HACE
    Lee la base Postgres local `barberia` (contenedor `barberia-postgres`) y
    escribe un unico archivo `dashboard.html` autocontenido.

POR QUE ASI
    - 100% gratis: sin servicio externo, sin cuenta, sin tarjeta, sin CAPTCHA.
    - 100% local: NO expone la base de datos a internet.
    - 0 dependencias: solo libreria estandar de Python. En el HTML no hay ni un
      CDN, ni una fuente externa, ni una imagen: funciona sin internet.
    - Se ve bien con 0 citas (el caso real hoy): muestra ceros y avisos,
      nunca errores ni graficos rotos.

USO
    uv run python G:\\Barberia\\archivos\\dashboard\\generar-dashboard.py
    uv run python ...\\generar-dashboard.py --salida C:\\ruta\\otro.html
    uv run python ...\\generar-dashboard.py --stdout     (no escribe archivo)

Fechas calculadas en la zona del negocio: America/Mexico_City.
Verificado el 2026-09-25 sobre Postgres 17 / contenedor barberia-postgres.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# --------------------------------------------------------------------------
# Entorno (ningun secreto escrito aqui: se leen de G:\Barberia\.env)
# --------------------------------------------------------------------------
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent          # G:\Barberia
ENV_FILE = RAIZ / ".env"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
CONTENEDOR = "barberia-postgres"
SALIDA_DEFECTO = AQUI / "dashboard.html"

NEGOCIO = "Barber Chinos"
SUBTITULO = "Peluqueria y Barberia &middot; Calle Pinzon #574 &middot; 452-281-8144"
BARBERO = "Esteban Aguilera"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def leer_env(ruta: Path = ENV_FILE) -> dict:
    cfg = {}
    if not ruta.exists():
        return cfg
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def consultar(sql: str) -> dict:
    """Ejecuta un script SQL en el Postgres local.

    El script separa cada resultado con una linea `\\echo ===@@NOMBRE@@===`
    Devuelve {NOMBRE: [dict, ...]} y ademas '_' apuntando al primer resultado.
    """
    cfg = leer_env()
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = str(RAIZ / ".docker")
    env["PGPASSWORD"] = cfg.get("POSTGRES_PASSWORD", "")
    usuario = cfg.get("POSTGRES_USER", "barberia")
    basedatos = cfg.get("POSTGRES_DB", "barberia")

    cmd = [DOCKER, "exec", "-i", "-e", "PGPASSWORD", CONTENEDOR,
           "psql", "-U", usuario, "-d", basedatos,
           "-v", "ON_ERROR_STOP=1", "-q", "--csv", "-f", "-"]
    res = subprocess.run(cmd, input=sql.encode("utf-8"),
                         capture_output=True, env=env, timeout=180)
    texto = res.stdout.decode("utf-8", "replace")
    error = res.stderr.decode("utf-8", "replace").strip()
    if res.returncode != 0 or error:
        raise RuntimeError("Fallo la consulta a Postgres (exit %s).\nstderr: %s"
                           % (res.returncode, error or "(vacio)"))

    secciones: dict = {}
    actual = None
    buffer: list = []
    for linea in texto.splitlines():
        if linea.startswith("===@@") and linea.rstrip().endswith("@@==="):
            if actual is not None:
                secciones[actual] = _parsear(buffer)
            actual = linea.rstrip()[5:-5]
            buffer = []
        elif actual is not None:
            buffer.append(linea)
    if actual is not None:
        secciones[actual] = _parsear(buffer)

    nombres = list(secciones.keys())
    if nombres:
        secciones["_"] = secciones[nombres[0]]
    return secciones


def _parsear(lineas: list) -> list:
    limpias = [l for l in lineas if l.strip() != ""]
    if not limpias:
        return []
    return [dict(f) for f in csv.DictReader(io.StringIO("\n".join(limpias)))]


# --------------------------------------------------------------------------
# SQL. Todos los KPIs salen de aqui.
# --------------------------------------------------------------------------
SQL_KPIS = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off

\echo ===@@resumen@@===
WITH at AS (
  SELECT * FROM barber_citas
   WHERE estado = 'atendido' AND precio IS NOT NULL AND inicio IS NOT NULL
)
SELECT
  (SELECT count(*) FROM barber_citas)                                                          AS citas_totales,
  (SELECT count(*) FROM barber_citas WHERE inicio IS NULL)                                     AS citas_sin_fecha,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date = current_date),0)                    AS ing_hoy,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date >= date_trunc('week', current_date)::date),0)  AS ing_sem,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date >= date_trunc('month', current_date)::date),0) AS ing_mes,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date = current_date),0)                       AS n_hoy,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date >= date_trunc('week', current_date)::date),0)     AS n_sem,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date >= date_trunc('month', current_date)::date),0)    AS n_mes,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date = current_date),0)           AS tk_hoy,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date >= date_trunc('week', current_date)::date),0)  AS tk_sem,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date >= date_trunc('month', current_date)::date),0) AS tk_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='no_show' AND inicio IS NOT NULL
            AND inicio::date >= date_trunc('month', current_date)::date),0)                    AS no_show_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='cancelado' AND inicio IS NOT NULL
            AND inicio::date >= date_trunc('month', current_date)::date),0)                    AS canc_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE inicio IS NOT NULL
            AND inicio::date >= date_trunc('month', current_date)::date),0)                    AS prog_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado IN ('agendado','confirmado')
            AND inicio >= now()),0)                                                            AS futuras,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado IN ('agendado','confirmado')
            AND inicio >= now() AND inicio < now() + interval '7 days'),0)                     AS futuras_7,
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado IN ('agendado','confirmado')
            AND inicio >= now() AND inicio < now() + interval '7 days'),0)                     AS ing_fut_7,
  COALESCE((SELECT count(*) FROM barber_clientes),0)                                           AS clientes_crm,
  COALESCE((SELECT count(DISTINCT jid) FROM at WHERE jid IS NOT NULL
            AND inicio::date >= date_trunc('month', current_date)::date),0)                    AS cli_mes,
  COALESCE((SELECT count(*) FROM (
      SELECT jid FROM at WHERE jid IS NOT NULL
      GROUP BY jid
      HAVING min(inicio::date) >= date_trunc('month', current_date)::date
  ) x),0)                                                                                      AS cli_nuevos_mes,
  COALESCE((SELECT count(*) FROM at WHERE jid IS NOT NULL
            AND inicio::date >= date_trunc('month', current_date)::date
            AND jid NOT IN (
              SELECT jid FROM at WHERE jid IS NOT NULL
              GROUP BY jid
              HAVING min(inicio::date) >= date_trunc('month', current_date)::date)),0)         AS citas_recurrentes_mes,
  (SELECT to_char(current_date,'YYYY-MM-DD'))                                                  AS fecha_hoy,
  (SELECT to_char(now(),'HH24:MI'))                                                            AS hora_generado;

\echo ===@@estados@@===
SELECT COALESCE(estado,'(sin estado)') AS estado, count(*) AS n
  FROM barber_citas
 WHERE inicio IS NULL
    OR inicio::date >= date_trunc('month', current_date)::date
 GROUP BY 1 ORDER BY 2 DESC;

\echo ===@@servicios@@===
SELECT COALESCE(servicio,'(sin servicio)') AS servicio,
       count(*) AS n,
       COALESCE(sum(precio),0) AS ingresos
  FROM barber_citas
 WHERE estado='atendido' AND precio IS NOT NULL AND inicio IS NOT NULL
   AND inicio::date >= date_trunc('month', current_date)::date
 GROUP BY 1 ORDER BY 3 DESC, 2 DESC;

\echo ===@@horas@@===
SELECT extract(hour FROM inicio)::int AS hora, count(*) AS n
  FROM barber_citas
 WHERE estado='atendido' AND inicio IS NOT NULL
 GROUP BY 1 ORDER BY 2 DESC, 1;

\echo ===@@dias30@@===
WITH dias AS (SELECT generate_series(current_date - 29, current_date, interval '1 day')::date AS d)
SELECT to_char(dias.d,'DD/MM') AS etiqueta,
       dias.d::text AS fecha,
       COALESCE(count(c.id),0) AS n,
       COALESCE(sum(c.precio),0) AS ingresos
  FROM dias
  LEFT JOIN barber_citas c
         ON c.inicio::date = dias.d AND c.estado='atendido' AND c.precio IS NOT NULL
 GROUP BY dias.d ORDER BY dias.d;

\echo ===@@hoydia@@===
SELECT COALESCE(to_char(inicio,'HH24:MI'),'--:--') AS hora,
       COALESCE(nombre,'(sin nombre)') AS nombre,
       COALESCE(servicio,'--') AS servicio,
       COALESCE(precio,0) AS precio,
       COALESCE(estado,'--') AS estado
  FROM barber_citas
 WHERE inicio::date = current_date
 ORDER BY inicio;

\echo ===@@proximas@@===
SELECT to_char(inicio,'DD/MM HH24:MI') AS cuando,
       COALESCE(nombre,'(sin nombre)') AS nombre,
       COALESCE(servicio,'--') AS servicio,
       COALESCE(precio,0) AS precio
  FROM barber_citas
 WHERE estado IN ('agendado','confirmado') AND inicio >= now()
 ORDER BY inicio LIMIT 8;
"""


# --------------------------------------------------------------------------
# Formato
# --------------------------------------------------------------------------
def num(v) -> float:
    try:
        return float(Decimal(str(v)))
    except (InvalidOperation, TypeError, ValueError):
        return 0.0


def entero(v) -> int:
    try:
        return int(Decimal(str(v)))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def dinero(v, decimales: int = 0) -> str:
    n = num(v)
    signo = "-" if n < 0 else ""
    return f"{signo}${abs(n):,.{decimales}f}"


def esc(t) -> str:
    return (str("" if t is None else t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def barra(etiqueta: str, valor_txt: str, proporcion: float, detalle: str = "") -> str:
    """Barra horizontal.

    `valor_txt` y `detalle` se insertan SIN escapar: son plantillas nuestras y
    llevan entidades HTML (&middot;, &ndash;). Nunca meter datos de usuario aqui
    sin escapar antes con esc().
    """
    ancho = max(1.5, min(100.0, proporcion)) if proporcion > 0 else 0.0
    extra = f" <span class='muted'>{detalle}</span>" if detalle else ""
    return ("<div class='fila'>"
            f"<div class='fila-cab'><span class='etiq'>{esc(etiqueta)}</span>"
            f"<span class='val'>{valor_txt}{extra}</span></div>"
            "<div class='pista'>"
            f"<div class='relleno' style='width:{ancho:.2f}%'></div>"
            "</div></div>")


def tarjeta(titulo: str, valor: str, pie: str, acento: bool = False) -> str:
    return (f"<div class='kpi{' kpi-acento' if acento else ''}'>"
            f"<div class='kpi-t'>{esc(titulo)}</div>"
            f"<div class='kpi-v'>{valor}</div>"
            f"<div class='kpi-p'>{pie}</div></div>")


def vacio(mensaje: str) -> str:
    return f"<div class='vacio'>{mensaje}</div>"


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{--bg:#0d0f14;--card:#161a22;--linea:#262d3a;--ink:#eef2f8;--muted:#93a0b5;
--acento:#e5b34a;--acento2:#f4d68b;--ok:#3fb950;--warn:#e3b341;--bad:#f4614f;
--info:#58a6ff;--radio:14px}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-size:15px;line-height:1.45;
-webkit-text-size-adjust:100%;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.envoltura{max-width:980px;margin:0 auto;padding:14px 12px 44px}
header.cab{background:linear-gradient(135deg,#1b2130 0%,#12161f 60%,#1a1408 100%);
border:1px solid var(--linea);border-radius:var(--radio);padding:16px 16px 14px;
margin-bottom:8px;position:relative;overflow:hidden}
header.cab::after{content:"";position:absolute;top:0;bottom:0;left:0;width:5px;
background:linear-gradient(180deg,var(--acento),#8a6520)}
h1{margin:0 0 2px;font-size:clamp(20px,5.6vw,27px);letter-spacing:.3px}
.sub{margin:0;color:var(--muted);font-size:12.5px}
.meta{margin-top:9px;display:flex;flex-wrap:wrap;gap:6px}
.chip{background:#0c0f15;border:1px solid var(--linea);color:var(--muted);
border-radius:999px;padding:3px 10px;font-size:11.5px;white-space:nowrap}
.chip b{color:var(--ink);font-weight:600}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1.4px;color:var(--acento);
margin:22px 4px 9px;font-weight:700}
h2.primero{margin-top:4px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(146px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--linea);border-radius:var(--radio);
padding:13px 14px}
.kpi-acento{background:linear-gradient(160deg,#1e2432,#141922);border-color:#3a3040;
box-shadow:inset 0 0 0 1px rgba(229,179,74,.16)}
.kpi-t{font-size:11.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);
margin-bottom:4px}
.kpi-v{font-size:clamp(21px,6.4vw,29px);font-weight:700;letter-spacing:-.5px;word-break:break-word}
.kpi-acento .kpi-v{color:var(--acento2)}
.kpi-p{font-size:12px;color:var(--muted);margin-top:3px}
.panel{background:var(--card);border:1px solid var(--linea);border-radius:var(--radio);padding:14px}
.fila{margin-bottom:11px}
.fila:last-child{margin-bottom:0}
.fila-cab{display:flex;justify-content:space-between;align-items:baseline;gap:10px;
margin-bottom:4px;font-size:13.5px}
.etiq{font-weight:600}
.val{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.pista{height:9px;background:#0c0f15;border-radius:6px;overflow:hidden}
.relleno{height:100%;border-radius:6px;
background:linear-gradient(90deg,var(--acento),var(--acento2))}
.muted{color:var(--muted)}
.tendencia{display:flex;align-items:flex-end;gap:3px;height:118px;overflow-x:auto;padding-top:6px}
.tendencia .col{flex:1 1 0;min-width:10px;display:flex;flex-direction:column;
justify-content:flex-end;height:100%}
.barra-v{background:linear-gradient(180deg,var(--acento),#926c22);border-radius:3px 3px 0 0;
min-height:3px}
.barra-v.vacia{background:#242b38}
.barra-v.hoy{background:linear-gradient(180deg,#7ee787,#3fb950)}
.eje{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;
margin-top:6px;border-top:1px solid var(--linea);padding-top:5px}
.pila{display:flex;height:16px;border-radius:8px;overflow:hidden;background:#0c0f15}
.pila span{height:100%}
.leyenda{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:10px;font-size:12.5px}
.leyenda i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--linea)}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;
letter-spacing:.7px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:none}
.vacio{background:#12161e;border:1px dashed var(--linea);border-radius:var(--radio);
padding:16px;text-align:center;color:var(--muted);font-size:13.5px}
.vacio b{color:var(--ink);display:block;margin-bottom:3px;font-size:14px}
.aviso{background:#1d1a10;border:1px solid #4a3c14;border-left:4px solid var(--acento);
border-radius:10px;padding:11px 13px;font-size:13px;color:#e9d9a8;margin-bottom:12px}
.aviso b{color:var(--acento2)}
.pill{display:inline-block;border-radius:999px;padding:1px 8px;font-size:11px;
font-weight:600;letter-spacing:.3px}
.pill-atendido{background:rgba(63,185,80,.16);color:#7ee787}
.pill-no_show{background:rgba(244,97,79,.16);color:#ff9d90}
.pill-cancelado{background:rgba(227,179,65,.16);color:#f0d27a}
.pill-agendado,.pill-confirmado{background:rgba(88,166,255,.16);color:#a5d0ff}
.pill-reprogramado,.pill-otro{background:#242b38;color:var(--muted)}
footer.pie{margin-top:26px;padding-top:12px;border-top:1px solid var(--linea);
color:var(--muted);font-size:11.5px;text-align:center;line-height:1.7}
@media (max-width:430px){
  .envoltura{padding:10px 9px 36px}
  .kpis{grid-template-columns:repeat(2,1fr);gap:8px}
  .kpi{padding:11px 11px}
  .kpi-v{font-size:21px}
  .fila-cab{font-size:12.5px}
  th,td{padding:6px 5px;font-size:12.5px}
  .tendencia{height:96px}
}
@media print{body{background:#fff;color:#000}}
"""


# --------------------------------------------------------------------------
# Construccion del HTML
# --------------------------------------------------------------------------
COLORES_ESTADO = {
    "atendido": "#3fb950", "no_show": "#f4614f", "cancelado": "#e3b341",
    "agendado": "#58a6ff", "confirmado": "#58a6ff", "reprogramado": "#8b949e",
    "(sin estado)": "#4b5462",
}


def bloque_kpis(res: dict) -> str:
    ing_hoy, ing_sem, ing_mes = num(res["ing_hoy"]), num(res["ing_sem"]), num(res["ing_mes"])
    n_hoy, n_sem, n_mes = entero(res["n_hoy"]), entero(res["n_sem"]), entero(res["n_mes"])
    tk_hoy, tk_sem, tk_mes = num(res["tk_hoy"]), num(res["tk_sem"]), num(res["tk_mes"])

    html = "<div class='kpis'>"
    html += tarjeta("Ingresos hoy", dinero(ing_hoy),
                    f"{n_hoy} cita{'s' if n_hoy != 1 else ''} atendida{'s' if n_hoy != 1 else ''}",
                    acento=True)
    html += tarjeta("Ingresos semana", dinero(ing_sem), f"{n_sem} citas atendidas")
    html += tarjeta("Ingresos mes", dinero(ing_mes), f"{n_mes} citas atendidas")
    html += tarjeta("Ticket promedio hoy",
                    dinero(tk_hoy) if n_hoy else "&mdash;",
                    "sin citas atendidas hoy" if not n_hoy else "por cita atendida")
    html += tarjeta("Ticket promedio mes",
                    dinero(tk_mes) if n_mes else "&mdash;",
                    f"semana: {dinero(tk_sem) if n_sem else '&mdash;'}")
    html += tarjeta("No-shows del mes", str(entero(res["no_show_mes"])),
                    "citas que no llegaron")
    html += tarjeta("Cancelaciones del mes", str(entero(res["canc_mes"])),
                    "citas canceladas")
    html += tarjeta("Proximas 7 dias", str(entero(res["futuras_7"])),
                    f"potencial {dinero(res['ing_fut_7'])}")
    html += "</div>"
    return html


def bloque_avisos(res: dict) -> str:
    prog = entero(res["prog_mes"])
    total = entero(res["citas_totales"])
    sin_fecha = entero(res["citas_sin_fecha"])
    partes = []
    if total == 0:
        partes.append("<b>Sin datos todavia.</b> La base esta vacia: el sistema acaba de "
                      "empezar a registrar citas. Cuando el agente agende y marque citas "
                      "como <i>atendido</i>, los numeros aparecen solos aqui.")
    elif prog == 0:
        partes.append("<b>Sin citas registradas este mes.</b> Los bloques del mes salen en "
                      "cero a proposito (no es un error).")
    if sin_fecha and sin_fecha > 0:
        partes.append(f"Hay <b>{sin_fecha}</b> cita(s) sin fecha de inicio: no entran en "
                      "ningun calculo por periodo.")
    if not partes:
        return ""
    cuerpo = " ".join(partes)
    return f"<div class='aviso'>{cuerpo}</div>"


def bloque_tendencia(filas: list) -> str:
    if not filas:
        return vacio("<b>Sin serie de 30 dias</b>No se pudo calcular la ventana de 30 dias.")
    maxv = max([num(f.get("ingresos")) for f in filas] or [0])
    total = sum(num(f.get("ingresos")) for f in filas)
    cols = []
    for i, f in enumerate(filas):
        v = num(f.get("ingresos"))
        alto = (v / maxv * 100.0) if maxv > 0 else 0.0
        es_hoy = (i == len(filas) - 1)
        clases = "barra-v" + (" vacia" if v <= 0 else "") + (" hoy" if es_hoy else "")
        titulo = f"{f.get('etiqueta','')}: {dinero(v)} ({entero(f.get('n'))} citas)"
        cols.append(f"<div class='col' title='{esc(titulo)}'>"
                    f"<div class='{clases}' style='height:{max(1.5, alto):.1f}%'></div></div>")
    etiquetas = ""
    if len(filas) >= 2:
        etiquetas = (f"<div class='eje'><span>{esc(filas[0].get('etiqueta'))}</span>"
                     f"<span>total 30 dias: {dinero(total)}</span>"
                     f"<span>hoy</span></div>")
    if maxv <= 0:
        nota = ("<div class='vacio' style='margin-top:12px'>"
                "<b>Sin ingresos en los ultimos 30 dias</b>"
                "La escala del grafico esta en cero y ninguna barra se puede dibujar. "
                "No es un error: todavia no hay citas marcadas como <i>atendido</i>."
                "</div>")
    else:
        nota = ""
    return ("<div class='panel'><div class='tendencia'>" + "".join(cols) + "</div>"
            + etiquetas + nota + "</div>")


def bloque_servicios(filas: list) -> str:
    if not filas:
        return vacio("<b>Sin servicios cobrados este mes</b>"
                     "Apareceran cuando haya citas en estado <i>atendido</i> con precio.")
    maxv = max(num(f.get("ingresos")) for f in filas) or 1
    html = "<div class='panel'>"
    for f in filas[:8]:
        ing = num(f.get("ingresos"))
        n = entero(f.get("n"))
        veces = "1 vez" if n == 1 else "%d veces" % n
        html += barra(f.get("servicio") or "(sin servicio)", dinero(ing),
                      ing / maxv * 100.0, f"&middot; {veces}")
    html += "</div>"
    return html


def bloque_horas(filas: list) -> str:
    if not filas:
        return vacio("<b>Sin horas registradas</b>"
                     "El mapa de horas pico se llena con citas atendidas.")
    maxv = max(entero(f.get("n")) for f in filas) or 1
    html = "<div class='panel'>"
    for f in filas[:6]:
        h = entero(f.get("hora"))
        n = entero(f.get("n"))
        html += barra(f"{h:02d}:00 a {h + 1:02d}:00", f"{n} cita{'s' if n != 1 else ''}",
                      n / maxv * 100.0)
    html += "</div>"
    return html


def bloque_estados(filas: list) -> str:
    if not filas:
        return vacio("<b>Sin citas este mes</b>")
    total = sum(entero(f.get("n")) for f in filas) or 1
    pila, leyenda = [], []
    for f in filas:
        est = f.get("estado") or "(sin estado)"
        n = entero(f.get("n"))
        color = COLORES_ESTADO.get(est, "#4b5462")
        ancho = n / total * 100.0
        pila.append(f"<span style='width:{ancho:.2f}%;background:{color}'></span>")
        leyenda.append(f"<span><i style='background:{color}'></i>{esc(est)}: "
                       f"<b>{n}</b> ({ancho:.0f}%)</span>")
    return ("<div class='panel'><div class='pila'>" + "".join(pila) + "</div>"
            "<div class='leyenda'>" + "".join(leyenda) + "</div></div>")


def bloque_hoy(filas: list) -> str:
    if not filas:
        return vacio("<b>Hoy no hay citas registradas</b>")
    t = ["<table><thead><tr><th>Hora</th><th>Cliente</th><th>Servicio</th>"
         "<th class='n'>Precio</th><th>Estado</th></tr></thead><tbody>"]
    for f in filas:
        est = f.get("estado") or "--"
        pill = f"<span class='pill pill-{esc(est)}'>{esc(est)}</span>"
        t.append(f"<tr><td>{esc(f.get('hora'))}</td><td>{esc(f.get('nombre'))}</td>"
                 f"<td>{esc(f.get('servicio'))}</td>"
                 f"<td class='n'>{dinero(f.get('precio'))}</td><td>{pill}</td></tr>")
    t.append("</tbody></table>")
    return "<div class='panel'>" + "".join(t) + "</div>"


def bloque_proximas(filas: list) -> str:
    if not filas:
        return vacio("<b>Sin citas futuras agendadas</b>")
    t = ["<table><thead><tr><th>Cuando</th><th>Cliente</th><th>Servicio</th>"
         "<th class='n'>Precio</th></tr></thead><tbody>"]
    for f in filas:
        t.append(f"<tr><td>{esc(f.get('cuando'))}</td><td>{esc(f.get('nombre'))}</td>"
                 f"<td>{esc(f.get('servicio'))}</td>"
                 f"<td class='n'>{dinero(f.get('precio'))}</td></tr>")
    t.append("</tbody></table>")
    return "<div class='panel'>" + "".join(t) + "</div>"

def bloque_clientes(res: dict) -> str:
    nuevos = entero(res["cli_nuevos_mes"])
    atendidos = entero(res["cli_mes"])
    recur = max(0, atendidos - nuevos)
    crm = entero(res["clientes_crm"])
    citas_recur = entero(res["citas_recurrentes_mes"])
    total = max(1, atendidos)
    pn = nuevos / total * 100.0
    pr = recur / total * 100.0
    if atendidos == 0:
        return vacio("<b>Sin clientes atendidos este mes</b>"
                     f"El CRM local tiene <b>{crm}</b> ficha(s) de cliente. "
                     "El reparto nuevo/recurrente aparece cuando haya citas atendidas.")
    return (
        "<div class='panel'><div class='pila'>"
        f"<span style='width:{pn:.2f}%;background:#58a6ff'></span>"
        f"<span style='width:{pr:.2f}%;background:#e5b34a'></span></div>"
        "<div class='leyenda'>"
        f"<span><i style='background:#58a6ff'></i>Nuevos: <b>{nuevos}</b> "
        f"({pn:.0f}%)</span>"
        f"<span><i style='background:#e5b34a'></i>Recurrentes: <b>{recur}</b> "
        f"({pr:.0f}%)</span>"
        f"<span class='muted'>Citas de clientes recurrentes: {citas_recur}</span>"
        f"<span class='muted'>Fichas en el CRM: {crm}</span>"
        "</div></div>")


def bloque_salud(res: dict) -> str:
    prog = entero(res["prog_mes"])
    ns, ca = entero(res["no_show_mes"]), entero(res["canc_mes"])
    base = max(1, prog)
    atendidas = entero(res["n_mes"])
    lineas = [
        barra("No-shows", f"{ns}", ns / base * 100.0,
              f"&middot; {ns / base * 100.0:.1f}% de las citas del mes"),
        barra("Cancelaciones", f"{ca}", ca / base * 100.0,
              f"&middot; {ca / base * 100.0:.1f}% de las citas del mes"),
        barra("Atendidas", f"{atendidas}", atendidas / base * 100.0,
              f"&middot; {atendidas / base * 100.0:.1f}% de las citas del mes"),
    ]
    nota = (f"<div class='leyenda'><span class='muted'>Base del mes: "
            f"<b>{prog}</b> cita(s) programadas (todas las que tienen fecha en el mes"
            f" en curso, en cualquier estado).</span></div>")
    return "<div class='panel'>" + "".join(lineas) + nota + "</div>"


def bloque_barberos(res: dict) -> str:
    return (
        "<div class='panel'><div class='leyenda' style='margin-top:0'>"
        f"<span>Barbero unico: <b>{esc(BARBERO)}</b></span>"
        "<span class='muted'>No hay desglose por barbero: el negocio tiene un solo "
        "profesional, asi que cualquier tabla de &laquo;rendimiento por barbero&raquo; "
        "seria una fila repetida sin informacion.</span></div></div>")


def render(resumen: dict, estados: list, servicios: list, horas: list,
           dias30: list, hoydia: list, proximas: list, fecha_hoy: str) -> str:
    r = resumen
    try:
        y, m, d = [int(x) for x in fecha_hoy.split("-")]
        fecha_larga = f"{DIAS[datetime(y, m, d).weekday()]} {d} de {MESES[m - 1]} de {y}"
    except Exception:
        fecha_larga = fecha_hoy

    partes = [
        "<!DOCTYPE html>",
        "<html lang='es'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta name='color-scheme' content='dark'>",
        "<meta name='robots' content='noindex,nofollow'>",
        f"<title>{esc(NEGOCIO)} - Panel del dueno</title>",
        f"<style>{CSS}</style></head><body><div class='envoltura'>",
        "<header class='cab'>",
        f"<h1>{esc(NEGOCIO)}</h1>",
        f"<p class='sub'>{SUBTITULO}</p>",
        "<div class='meta'>",
        f"<span class='chip'>Hoy: <b>{esc(fecha_larga)}</b></span>",
        f"<span class='chip'>Generado: <b>{esc(r.get('hora_generado', '--:--'))}</b></span>",
        f"<span class='chip'>Agenda: <b>{entero(r['futuras'])}</b> citas futuras</span>",
        "</div></header>",
        bloque_avisos(r),
        "<h2 class='primero'>Dinero y citas</h2>",
        bloque_kpis(r),
        "<h2>Ingresos por dia (ultimos 30 dias)</h2>",
        bloque_tendencia(dias30),
        "<h2>Servicios mas rentables del mes</h2>",
        bloque_servicios(servicios),
        "<h2>Horas pico (citas atendidas)</h2>",
        bloque_horas(horas),
        "<h2>Estado de las citas del mes</h2>",
        bloque_estados(estados),
        "<h2>No-shows y cancelaciones</h2>",
        bloque_salud(r),
        "<h2>Clientes nuevos vs recurrentes (mes)</h2>",
        bloque_clientes(r),
        "<h2>Citas de hoy</h2>",
        bloque_hoy(hoydia),
        "<h2>Proximas citas</h2>",
        bloque_proximas(proximas),
        "<h2>Equipo</h2>",
        bloque_barberos(r),
        "<footer class='pie'>",
"Panel generado desde la base local <b>barberia</b> (contenedor "
        "<code>barberia-postgres</code>). Ningun dato sale de este equipo.",
        "<br>Este archivo no carga nada de internet: funciona sin conexion.",
        "</footer></div></body></html>",
    ]
    return "\n".join(partes)


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera el dashboard HTML de la barberia.")
    ap.add_argument("--salida", default=str(SALIDA_DEFECTO),
                    help="Ruta del HTML a escribir (por defecto: dashboard.html junto al script)")
    ap.add_argument("--stdout", action="store_true",
                    help="Imprime el HTML en pantalla y no escribe archivo")
    args = ap.parse_args()

    try:
        sec = consultar(SQL_KPIS)
    except Exception as e:
        print("ERROR al leer la base de datos:\n%s" % e, file=sys.stderr)
        return 2

    filas_resumen = sec.get("resumen") or []
    if not filas_resumen:
        print("ERROR: no se pudo leer el resumen de KPIs.", file=sys.stderr)
        return 3
    r = filas_resumen[0]

    html = render(
        resumen=r,
        estados=sec.get("estados") or [],
        servicios=sec.get("servicios") or [],
        horas=sec.get("horas") or [],
        dias30=sec.get("dias30") or [],
        hoydia=sec.get("hoydia") or [],
        proximas=sec.get("proximas") or [],
        fecha_hoy=(r.get("fecha_hoy") or "1970-01-01"),
    )

    if args.stdout:
        sys.stdout.write(html)
        return 0

    destino = Path(args.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print("Dashboard escrito en: %s" % destino)
    print("  bytes: %d" % len(html.encode("utf-8")))
    print("  citas totales en la base: %s" % entero(r["citas_totales"]))
    print("  ingresos mes: %s (%s citas atendidas)"
          % (dinero(r["ing_mes"]), entero(r["n_mes"])))
    print("  fecha del negocio: %s %s" % (r.get("fecha_hoy"), r.get("hora_generado")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
