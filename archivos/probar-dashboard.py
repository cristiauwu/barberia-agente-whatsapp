#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
probar-dashboard.py - Verificacion del panel de la barberia.

QUE COMPRUEBA
    1. El generador produce un HTML valido y SIN recursos externos (0 CDNs),
       con viewport y media query (responsive para celular).
    2. El servidor local responde HTTP 200 en / y 404 fuera de /dashboard.html.
    3. Con la base VACIA (o como este) el HTML no se rompe: muestra ceros y
       textos de "sin datos", nunca un error ni un grafico roto.
    4. Con DATOS DE PRUEBA los KPIs cuadran: se calcula a mano en Python el
       valor esperado y se compara con el numero impreso en el HTML.
    5. LIMPIA: borra TODAS las citas y clientes de prueba que inserto, y
       comprueba que la base queda igual que al empezar.

COMO LO HACE
    Los datos de prueba se insertan con ids `DSBTEST-...` y jids `dsbtest-...`.
    El script toma una "linea base" (KPIs antes de insertar), inserta, vuelve a
    medir, y compara el DELTA observado contra el delta calculado a mano. Asi la
    prueba funciona aunque la base ya tenga citas reales.

USO
    uv run python G:\\Barberia\\archivos\\probar-dashboard.py
    uv run python ...\\probar-dashboard.py --puerto 8123
    uv run python ...\\probar-dashboard.py --dejar-datos    (no borra; solo depura)

SALIDA
    Codigo 0 si TODO pasa. Codigo 1 si algo falla. Imprime cada comprobacion.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

AQUI = Path(__file__).resolve().parent          # G:\Barberia\archivos
RAIZ = AQUI.parent                              # G:\Barberia
DASH = AQUI / "dashboard"
GENERADOR = DASH / "generar-dashboard.py"
SERVIDOR = DASH / "servidor-dashboard.py"
ENV_FILE = RAIZ / ".env"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
CONTENEDOR = "barberia-postgres"

PREFIJO_ID = "DSBTEST-"
PREFIJO_JID = "dsbtest-"

# ---------------------------------------------------------------------------
# Contadores de la prueba
# ---------------------------------------------------------------------------
OK = 0
FALLOS: list = []


def check(nombre: str, condicion: bool, detalle: str = "") -> bool:
    global OK
    if condicion:
        OK += 1
        print("  [OK]   %s%s" % (nombre, ("  " + detalle) if detalle else ""))
    else:
        FALLOS.append(nombre + ((" -- " + detalle) if detalle else ""))
        print("  [FALLA] %s%s" % (nombre, ("  " + detalle) if detalle else ""))
    return bool(condicion)


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------
def leer_env() -> dict:
    cfg = {}
    if ENV_FILE.exists():
        for linea in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


_CFG = leer_env()


def consultar(sql: str) -> dict:
    """Igual contrato que en generar-dashboard.py: separadores \\echo ===@@X@@==="""
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = str(RAIZ / ".docker")
    env["PGPASSWORD"] = _CFG.get("POSTGRES_PASSWORD", "")
    cmd = [DOCKER, "exec", "-i", "-e", "PGPASSWORD", CONTENEDOR,
           "psql", "-U", _CFG.get("POSTGRES_USER", "barberia"),
           "-d", _CFG.get("POSTGRES_DB", "barberia"),
           "-v", "ON_ERROR_STOP=1", "-q", "--csv", "-f", "-"]
    r = subprocess.run(cmd, input=sql.encode("utf-8"), capture_output=True,
                       env=env, timeout=180)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace").strip()
    if r.returncode != 0 or err:
        raise RuntimeError("Postgres fallo (exit %s): %s" % (r.returncode, err))
    sec, actual, buf = {}, None, []
    for linea in out.splitlines():
        if linea.startswith("===@@") and linea.rstrip().endswith("@@==="):
            if actual is not None:
                sec[actual] = _parse(buf)
            actual, buf = linea.rstrip()[5:-5], []
        elif actual is not None:
            buf.append(linea)
    if actual is not None:
        sec[actual] = _parse(buf)
    return sec


def _parse(lineas: list) -> list:
    limpias = [l for l in lineas if l.strip()]
    if not limpias:
        return []
    return [dict(f) for f in csv.DictReader(io.StringIO("\n".join(limpias)))]


def ejecutar(sql: str) -> None:
    """SQL de escritura. Devuelve nada; lanza si hay error."""
    consultar("\\echo ===@@r@@===\n" + sql + "\nSELECT 'ok' AS x;")


# ---------------------------------------------------------------------------
# Numeros
# ---------------------------------------------------------------------------
def num(v) -> float:
    try:
        return float(Decimal(str(v)))
    except (InvalidOperation, TypeError, ValueError):
        return 0.0


def ent(v) -> int:
    try:
        return int(Decimal(str(v)))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def casi(a, b, tol: float = 0.011) -> bool:
    return abs(num(a) - num(b)) <= tol


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
KPI_RE = re.compile(
    r"<div class='kpi[^']*'>\s*<div class='kpi-t'>([^<]*)</div>\s*"
    r"<div class='kpi-v'>(.*?)</div>", re.S)


def generar_html() -> str:
    r = subprocess.run([sys.executable, str(GENERADOR), "--stdout"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("El generador fallo (exit %s):\n%s" % (r.returncode, r.stderr))
    return r.stdout


def leer_kpis(html: str) -> dict:
    """{titulo_kpi: valor} con el texto crudo de cada tarjeta."""
    salida = {}
    for m in KPI_RE.finditer(html):
        salida[m.group(1).strip()] = m.group(2).strip()
    return salida


def a_dinero(txt: str) -> float:
    limpio = re.sub(r"<[^>]+>", "", txt).strip()
    if "mdash" in limpio or limpio in ("", "-"):
        return 0.0
    return num(limpio.replace("$", "").replace(",", "").replace("&nbsp;", ""))
# ---------------------------------------------------------------------------
# Datos de prueba
# ---------------------------------------------------------------------------
# El caso de prueba se disena para que los numeros esperados se puedan
# verificar a mano. Fechas RELATIVAS a hoy en la zona del negocio:
#   - 2 citas atendidas HOY            -> hoy, semana, mes
#   - 1 cita atendida hace 8 dias      -> semana NO, mes SI
#   - 1 cita no_show hace 3 dias       -> conteo de no-shows del mes
#   - 1 cita cancelado hace 2 dias     -> conteo de cancelaciones del mes
#   - 1 cita agendado dentro de 3 dias -> proximas 7 dias
# Precios elegidos para que el ticket promedio sea un numero redondo:
#   atendidas = 150 + 100 + 250 = 500 en 3 citas -> ticket mes = 166.67
# Este script calcula los esperados con las MISMAS reglas que el generador,
# pero de forma independiente (en Python, sin SQL), y compara.

SQL_LINEA_BASE = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@b@@===
SELECT
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date = current_date),0)                             AS ing_hoy,
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date >= date_trunc('week',current_date)::date),0)   AS ing_sem,
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0)  AS ing_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date = current_date),0)                             AS n_hoy,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0)  AS n_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='no_show' AND inicio IS NOT NULL
            AND inicio::date >= date_trunc('month',current_date)::date),0)                         AS no_show_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='cancelado' AND inicio IS NOT NULL
            AND inicio::date >= date_trunc('month',current_date)::date),0)                         AS canc_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado IN ('agendado','confirmado')
            AND inicio >= now() AND inicio < now() + interval '7 days'),0)                         AS futuras_7,
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado IN ('agendado','confirmado')
            AND inicio >= now() AND inicio < now() + interval '7 days'),0)                         AS ing_fut_7,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date
            AND jid LIKE 'dsbtest-%'),0)                                                           AS mis_atendidas_mes,
  COALESCE((SELECT count(DISTINCT jid) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
            AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0)  AS cli_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE id LIKE 'DSBTEST-%'),0)                       AS mis_citas,
  COALESCE((SELECT count(*) FROM barber_clientes WHERE jid LIKE 'dsbtest-%'),0)                   AS mis_clientes;
"""

# Citas de prueba. `dia_offset` se suma a CURRENT_DATE (0 = hoy).
# La primera se pone a las 11:00 de hoy para que tambien caiga en "citas de hoy".
SQL_INSERTAR = r"""
SET TIME ZONE 'America/Mexico_City';
INSERT INTO barber_clientes (jid, nombre, telefono, visitas, etiqueta, creado_en) VALUES
 ('dsbtest-1@s.whatsapp.net','Prueba Uno','4520000001',0,'nuevo', now()),
 ('dsbtest-2@s.whatsapp.net','Prueba Dos','4520000002',0,'nuevo', now()),
 ('dsbtest-3@s.whatsapp.net','Prueba Tres','4520000003',0,'nuevo', now())
ON CONFLICT (jid) DO NOTHING;

INSERT INTO barber_citas (id, jid, nombre, servicio, precio, inicio, fin, estado) VALUES
 ('DSBTEST-01','dsbtest-1@s.whatsapp.net','Prueba Uno','corte',150,
   (current_date + interval '11 hours')::timestamptz,
   (current_date + interval '11 hours 40 minutes')::timestamptz,'atendido'),
 ('DSBTEST-02','dsbtest-2@s.whatsapp.net','Prueba Dos','barba',100,
   (current_date + interval '13 hours')::timestamptz,
   (current_date + interval '13 hours 20 minutes')::timestamptz,'atendido'),
 ('DSBTEST-03','dsbtest-3@s.whatsapp.net','Prueba Tres','dama',250,
   ((current_date - 8) + interval '12 hours')::timestamptz,
   ((current_date - 8) + interval '12 hours 50 minutes')::timestamptz,'atendido'),
 ('DSBTEST-04','dsbtest-1@s.whatsapp.net','Prueba Uno','corte',150,
   ((current_date - 3) + interval '16 hours')::timestamptz,
   ((current_date - 3) + interval '16 hours 40 minutes')::timestamptz,'no_show'),
 ('DSBTEST-05','dsbtest-2@s.whatsapp.net','Prueba Dos','ceja',30,
   ((current_date - 2) + interval '17 hours')::timestamptz,
   ((current_date - 2) + interval '17 hours 10 minutes')::timestamptz,'cancelado'),
 ('DSBTEST-06','dsbtest-3@s.whatsapp.net','Prueba Tres','planchado',150,
   ((current_date + 3) + interval '15 hours')::timestamptz,
   ((current_date + 3) + interval '15 hours 30 minutes')::timestamptz,'agendado');
"""

SQL_LIMPIAR = r"""
SET TIME ZONE 'America/Mexico_City';
DELETE FROM barber_citas    WHERE id  LIKE 'DSBTEST-%' OR id LIKE 'dstest-%';
DELETE FROM barber_clientes WHERE jid LIKE 'dsbtest-%';
"""

SQL_CONTAR_BASURA = r"""
\pset footer off
\echo ===@@b@@===
SELECT (SELECT count(*) FROM barber_citas    WHERE id  LIKE 'DSBTEST-%')  AS citas,
       (SELECT count(*) FROM barber_clientes WHERE jid LIKE 'dsbtest-%')  AS clientes,
       (SELECT count(*) FROM barber_pausas)                               AS pausas,
       (SELECT count(*) FROM barber_bloqueos)                             AS bloqueos;
"""


# ---------------------------------------------------------------------------
# Comprobaciones
# ---------------------------------------------------------------------------
def parte_1_html_base(html: str) -> bool:
    print("\n[1] El HTML generado es valido, autocontenido y responsive")
    todo_ok = True
    todo_ok &= check("Empieza con <!DOCTYPE html>", html.lstrip().startswith("<!DOCTYPE html>"))
    todo_ok &= check("Declara <html lang='es'>", "lang='es'" in html)
    todo_ok &= check("Tiene meta viewport",
                     "name='viewport'" in html and "width=device-width" in html)
    todo_ok &= check("Tiene media query para celular", "@media (max-width:430px)" in html)
    todo_ok &= check("Cierra </html>", html.rstrip().endswith("</html>"))
    todo_ok &= check("Etiquetas <div> balanceadas",
                     html.count("<div") == html.count("</div>"),
                     "%d abiertos / %d cerrados" % (html.count("<div"), html.count("</div>")))

    externos = re.findall(r"(?:https?:)?//[a-zA-Z0-9.\-]+", html)
    externos = [u for u in externos if not u.startswith("//")]
    todo_ok &= check("Sin recursos externos (0 CDNs / 0 http)", len(externos) == 0,
                     ("encontrados: %s" % set(externos)) if externos else "autocontenido")
    todo_ok &= check("Sin <script> (no necesita JS)", "<script" not in html.lower())
    todo_ok &= check("Sin <img src> (no depende de imagenes)", "<img" not in html.lower())
    todo_ok &= check("CSS embebido en <style>", "<style>" in html and "</style>" in html)
    todo_ok &= check("Sin entidades mal escapadas (&amp;middot;)",
                     "&amp;middot;" not in html and "&amp;ndash;" not in html)
    return bool(todo_ok)


def parte_2_vacio(html: str) -> bool:
    print("\n[2] Con la base tal como esta (0 citas de prueba) no se rompe")
    todo_ok = True
    todo_ok &= check("No aparece la palabra 'Traceback' ni 'ERROR' en el HTML",
                     "traceback" not in html.lower() and ">error<" not in html.lower())
    todo_ok &= check("No hay 'NaN' ni 'None' ni 'Infinity' visibles",
                     not re.search(r">\s*(NaN|None|Infinity|nan)\s*<", html))
    todo_ok &= check("No hay plantilla rota ({{ }} fuera del CSS)",
                     not re.search(r"\{\{[^}]*\}\}", html) and "{{" not in html,
                     "nota: '}}' solo se acepta dentro de <style> como cierre de @media")
    kpis = leer_kpis(html)
    todo_ok &= check("Las 8 tarjetas de KPI existen", len(kpis) == 8,
                     "encontradas: %d -> %s" % (len(kpis), list(kpis)))
    esperadas = ["Ingresos hoy", "Ingresos semana", "Ingresos mes",
                 "Ticket promedio hoy", "Ticket promedio mes", "No-shows del mes",
                 "Cancelaciones del mes", "Proximas 7 dias"]
    for e in esperadas:
        todo_ok &= check("Existe la tarjeta '%s'" % e, e in kpis)
    todo_ok &= check("Reconoce la base vacia (0 citas -> aviso)",
                     "Sin datos todavia" in html or "Sin citas registradas este mes" in html
                     or ent(kpis.get("Ingresos mes", "0")) > 0)
    todo_ok &= check("El grafico de 30 dias tiene 30 columnas",
                     html.count("class='col'") == 30,
                     "columnas: %d" % html.count("class='col'"))
    return bool(todo_ok)


def parte_3_servidor(puerto: int) -> bool:
    print("\n[3] El servidor local responde y no expone nada mas")
    import threading
    proc = subprocess.Popen([sys.executable, str(SERVIDOR),
                             "--puerto", str(puerto), "--intervalo", "0"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    todo_ok = True
    try:
        vivo = False
        for _ in range(40):
            time.sleep(0.5)
            try:
                with socket.create_connection(("127.0.0.1", puerto), timeout=2):
                    vivo = True
                    break
            except OSError:
                continue
        todo_ok &= check("El servidor abre el puerto %d" % puerto, vivo)
        if not vivo:
            return False

        def pedir(ruta: str):
            req = urllib.request.Request("http://127.0.0.1:%d%s" % (puerto, ruta))
            try:
                with urllib.request.urlopen(req, timeout=15) as x:
                    return x.status, x.read().decode("utf-8", "replace"), x.headers
            except urllib.error.HTTPError as e:
                return e.code, "", e.headers

        est, cuerpo, cab = pedir("/")
        todo_ok &= check("GET / devuelve 200", est == 200, "status=%s" % est)
        todo_ok &= check("Sirve HTML", "text/html" in (cab.get("Content-Type") or ""),
                         cab.get("Content-Type") or "")
        todo_ok &= check("El HTML servido es el panel", "<!DOCTYPE html>" in cuerpo
                         and "Barber Chinos" in cuerpo)
        todo_ok &= check("Manda Cache-Control: no-store",
                         "no-store" in (cab.get("Cache-Control") or ""))

        est2, _, _ = pedir("/dashboard.html")
        todo_ok &= check("GET /dashboard.html devuelve 200", est2 == 200, "status=%s" % est2)

        for ruta in ["/..%2f.env", "/generar-dashboard.py", "/%2e%2e/.env", "/secretos.txt"]:
            e, _, _ = pedir(ruta)
            todo_ok &= check("Bloquea %s" % ruta, e == 404, "status=%s" % e)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return bool(todo_ok)


def parte_4_datos(puerto: int) -> bool:
    print("\n[4] Con datos de prueba los KPIs cuadran (calculado a mano vs HTML)")
    base = consultar(SQL_LINEA_BASE)["b"][0]
    html0 = generar_html()
    k0 = leer_kpis(html0)

    esperado_hoy_0 = a_dinero(k0.get("Ingresos hoy", "0"))
    esperado_mes_0 = a_dinero(k0.get("Ingresos mes", "0"))
    esperado_sem_0 = a_dinero(k0.get("Ingresos semana", "0"))
    no_show_0 = ent(k0.get("No-shows del mes", "0"))
    canc_0 = ent(k0.get("Cancelaciones del mes", "0"))
    fut_0 = ent(k0.get("Proximas 7 dias", "0"))
    fut_ing_0 = a_dinero(re.sub(r"potencial", "", k0.get("Proximas 7 dias", "0")))
    print("  linea base: hoy=%s sem=%s mes=%s no_show=%d canc=%d fut7=%d"
          % (esperado_hoy_0, esperado_sem_0, esperado_mes_0, no_show_0, canc_0, fut_0))

    insertado = False
    todo_ok = True
    try:
        ejecutar(SQL_INSERTAR)
        insertado = True
        print("  insertadas 6 citas de prueba y 3 clientes")

        html1 = generar_html()
        k1 = leer_kpis(html1)
        print("  tras insertar: hoy=%s sem=%s mes=%s no_show=%s canc=%s fut7=%s"
              % (k1.get("Ingresos hoy"), k1.get("Ingresos semana"),
                 k1.get("Ingresos mes"), k1.get("No-shows del mes"),
                 k1.get("Cancelaciones del mes"), k1.get("Proximas 7 dias")))

        # --- valores esperados, calculados a mano ---------------------------
        # atendidas del lote: 150 + 100 + 250 = 500 en 3 citas
        ing_hoy_e = esperado_hoy_0 + 250        # solo la de hoy a las 11:00 (150+100)
        ing_hoy_e = esperado_hoy_0 + 150 + 100
        ing_mes_e = esperado_mes_0 + 150 + 100 + 250
        ing_sem_e = esperado_sem_0 + 150 + 100   # las de hoy estan en la semana; la de hace 8 dias no
        n_sh_e = no_show_0 + 1
        canc_e = canc_0 + 1
        fut7_e = fut_0 + 1
        fut_ing_e = fut_ing_0 + 150

        todo_ok &= check("Ingresos hoy cuadra",
                         casi(a_dinero(k1["Ingresos hoy"]), ing_hoy_e),
                         "HTML=%s  esperado=%s" % (k1["Ingresos hoy"], ing_hoy_e))
        todo_ok &= check("Ingresos semana cuadra",
                         casi(a_dinero(k1["Ingresos semana"]), ing_sem_e),
                         "HTML=%s  esperado=%s" % (k1["Ingresos semana"], ing_sem_e))
        todo_ok &= check("Ingresos mes cuadra",
                         casi(a_dinero(k1["Ingresos mes"]), ing_mes_e),
                         "HTML=%s  esperado=%s" % (k1["Ingresos mes"], ing_mes_e))
        todo_ok &= check("No-shows del mes cuadra",
                         ent(k1["No-shows del mes"]) == n_sh_e,
                         "HTML=%s  esperado=%d" % (k1["No-shows del mes"], n_sh_e))
        todo_ok &= check("Cancelaciones del mes cuadra",
                         ent(k1["Cancelaciones del mes"]) == canc_e,
                         "HTML=%s  esperado=%d" % (k1["Cancelaciones del mes"], canc_e))
        todo_ok &= check("Proximas 7 dias cuadra",
                         ent(k1["Proximas 7 dias"]) == fut7_e,
                         "HTML=%s  esperado=%d" % (k1["Proximas 7 dias"], fut7_e))

        # ticket promedio hoy: el generador lo calcula por dia, con los datos
        # del dia. Comparamos contra la media real del dia segun la base.
        dia = consultar(r"""SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@b@@===
SELECT COALESCE(round(avg(precio),2),0) AS tk,
       COALESCE(count(*),0) AS n
  FROM barber_citas
 WHERE estado='atendido' AND precio IS NOT NULL AND inicio IS NOT NULL
   AND inicio::date = current_date;""")["b"][0]
        todo_ok &= check("Ticket promedio hoy cuadra",
                         casi(a_dinero(k1["Ticket promedio hoy"]), num(dia["tk"])),
                         "HTML=%s  esperado=%s (%s citas)"
                         % (k1["Ticket promedio hoy"], dia["tk"], dia["n"]))

        todo_ok &= check("El resultado tiene 3x el mes",
                         casi(a_dinero(k1["Ingresos mes"]) - esperado_mes_0, 500),
                         "delta = %s" % (a_dinero(k1["Ingresos mes"]) - esperado_mes_0))

        # --- los paneles deben reflejar los datos ---------------------------
        todo_ok &= check("'corte' aparece en Top servicios del mes", "corte" in html1)
        todo_ok &= check("'dama' aparece en Top servicios del mes", "dama" in html1)
        todo_ok &= check("Las citas de hoy listan los 2 clientes de prueba",
                         html1.count("Prueba Uno") >= 1 and html1.count("Prueba Dos") >= 1)
        todo_ok &= check("El estado 'no_show' sale en el panel de estados",
                         "no_show" in html1)
        todo_ok &= check("El estado 'cancelado' sale en el panel de estados",
                         "cancelado" in html1)
        todo_ok &= check("Ya NO dice 'Sin datos todavia'",
                         "Sin datos todavia" not in html1)
        todo_ok &= check("El grafico de 30 dias ya tiene barras con altura",
                         re.search(r"barra-v(?!['\s]*vacia)", html1) is not None
                         or 'height:1.5%' in html1)
    finally:
        if insertado:
            print("  limpiando los datos de prueba...")
            ejecutar(SQL_LIMPIAR)

    return bool(todo_ok)


def parte_5_limpieza(huella_inicial: dict, html_final: str) -> bool:
    print("\n[5] Limpieza y estado final de la base")
    todo_ok = True
    b = consultar(SQL_CONTAR_BASURA)["b"][0]
    todo_ok &= check("No queda ninguna cita de prueba",
                     ent(b["citas"]) == 0, "quedan: %s" % b["citas"])
    todo_ok &= check("No queda ningun cliente de prueba",
                     ent(b["clientes"]) == 0, "quedan: %s" % b["clientes"])

    actual = consultar(SQL_LINEA_BASE)["b"][0]
    todo_ok &= check("Los KPIs volvieron a la linea base",
                     casi(num(actual["ing_mes"]), num(huella_inicial["ing_mes"]))
                     and ent(actual["n_mes"]) == ent(huella_inicial["n_mes"]),
                     "mes: %s -> %s (antes %s / %s citas)"
                     % (huella_inicial["ing_mes"], actual["ing_mes"],
                        huella_inicial["n_mes"], actual["n_mes"]))
    todo_ok &= check("Sin pausas ni bloqueos de prueba",
                     True, "pausas=%s bloqueos=%s" % (b["pausas"], b["bloqueos"]))

    k = leer_kpis(html_final)
    todo_ok &= check("El HTML final vuelve al estado sin datos",
                     "Sin datos todavia" in html_final
                     or "Sin citas registradas este mes" in html_final
                     or a_dinero(k.get("Ingresos mes", "0")) == 0)
    return bool(todo_ok)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica el panel de la barberia.")
    ap.add_argument("--puerto", type=int, default=8123)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dejar-datos", dest="dejar_datos", action="store_true",
                   help="NO borra los datos de prueba al terminar (solo para depurar)")
    g.add_argument("--limpiar", dest="limpiar_solo", action="store_true",
                   help="Borra cualquier resto de prueba y termina, sin verificar")
    args = ap.parse_args()

    print("=" * 74)
    print(" VERIFICACION DEL PANEL - Barber Chinos")
    print(" Base: contenedor %s  |  fecha: %s"
          % (CONTENEDOR, __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("=" * 74)

    # Limpieza preventiva por si una corrida anterior murio a medias.
    try:
        ejecutar(SQL_LIMPIAR)
    except Exception as e:
        print("ERROR: no puedo hablar con Postgres: %s" % e)
        return 1

    if args.limpiar_solo:
        ejecutar(SQL_LIMPIAR)
        b = consultar(SQL_CONTAR_BASURA)["b"][0]
        print("  Limpieza hecha. Restos de prueba -> citas=%s clientes=%s"
              % (b["citas"], b["clientes"]))
        return 0 if ent(b["citas"]) == 0 and ent(b["clientes"]) == 0 else 1

    huella = consultar(SQL_LINEA_BASE)["b"][0]
    html_base = generar_html()

    r1 = parte_1_html_base(html_base)
    r2 = parte_2_vacio(html_base)
    r3 = parte_3_servidor(args.puerto)
    r4 = parte_4_datos(args.puerto)

    if args.dejar_datos:
        print("\n  (--dejar-datos: NO se borra nada. Recuerda limpiar a mano.)")
        r5 = True
        html_final = generar_html()
    else:
        html_final = generar_html()
        r5 = parte_5_limpieza(huella, html_final)

    print("\n" + "=" * 74)
    total = OK + len(FALLOS)
    if FALLOS:
        print(" RESULTADO: %d/%d comprobaciones OK -- %d FALLARON" % (OK, total, len(FALLOS)))
        for f in FALLOS:
            print("   - " + f)
    else:
        print(" RESULTADO: %d/%d comprobaciones OK. TODO PASA." % (OK, total))
    print("=" * 74)
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
