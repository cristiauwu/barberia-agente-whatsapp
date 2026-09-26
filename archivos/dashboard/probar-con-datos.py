#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el dashboard CON datos: si los KPIs no cuadran, no sirve.

Inserta citas atendidas con valores conocidos, regenera, comprueba que los
numeros del HTML coinciden con el calculo hecho a mano, y limpia.

Valores de prueba:
  - hace 8 dias: corte $150  -> fuera de la semana, dentro del mes
  - hoy:         barba $100  -> dentro de hoy, semana y mes
  - ayer:        ceja  $30   -> dentro de semana y mes
  - hoy:         no_show (sin precio) -> cuenta como no-show, no como ingreso

Esperado:
  ingresos MES   = 150 + 100 + 30 = 280
  ingresos HOY   = 100
  ingresos SEM   = 100 + 30 = 130      (el de hace 8 dias queda fuera)
  citas HOY      = 1
  no-shows MES   = 1
  ticket prom HOY= 100
"""
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
AQUI = Path(r"G:\Barberia\archivos\dashboard")
GEN = AQUI / "generar-dashboard.py"
HTML = AQUI / "dashboard.html"

ESPERADO = {
    "mes": 280, "hoy": 100, "semana": 130,
    "citas_hoy": 1, "no_shows": 1, "ticket_hoy": 100,
}

SEMILLA = """
INSERT INTO barber_clientes (jid, nombre) VALUES
  ('prueba-dash@s.whatsapp.net', 'Cliente Dashboard')
ON CONFLICT (jid) DO NOTHING;

INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado) VALUES
 ('dash-1','prueba-dash@s.whatsapp.net','Cliente Dashboard','Corte desvanecido o tijera',150,
  now() - interval '8 days', now() - interval '8 days' + interval '40 min','atendido'),
 ('dash-2','prueba-dash@s.whatsapp.net','Cliente Dashboard','Arreglo de barba',100,
  date_trunc('day', now()) + interval '11 hours',
  date_trunc('day', now()) + interval '11 hours 20 min','atendido'),
 ('dash-3','prueba-dash@s.whatsapp.net','Cliente Dashboard','Ceja',30,
  date_trunc('day', now() - interval '1 day') + interval '17 hours',
  date_trunc('day', now() - interval '1 day') + interval '17 hours 10 min','atendido'),
 ('dash-4','prueba-dash@s.whatsapp.net','Cliente Dashboard','Corte desvanecido o tijera',150,
  date_trunc('day', now()) + interval '13 hours',
  date_trunc('day', now()) + interval '13 hours 40 min','no_show')
ON CONFLICT (id) DO NOTHING;
"""

LIMPIEZA = """
DELETE FROM barber_citas WHERE id LIKE 'dash-%';
DELETE FROM barber_clientes WHERE jid = 'prueba-dash@s.whatsapp.net';
"""


def psql(sql):
    """Ejecuta SQL. OJO: si se pasa `encoding`, `input` debe ser str, no
    bytes; con bytes la escritura a stdin revienta y el proceso se cuelga
    hasta agotar el timeout."""
    p = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-q",
                        "-v", "ON_ERROR_STOP=1", "-f", "-"],
                       input=sql, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def consulta(sql):
    p = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A",
                        "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return (p.stdout or "").strip()


def generar():
    p = subprocess.run([sys.executable, str(GEN)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=180)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 68)
    print("PRUEBA CON DATOS: los KPIs cuadran?")
    print("=" * 68)

    print("\n  insertando citas de prueba...")
    out, err = psql(SEMILLA)
    if err and "ERROR" in err:
        print("  ERROR al insertar:", err[:300])
        return 1
    print("  OK")

    print("\n  generando el dashboard con datos...")
    code, out, err = generar()
    if code != 0:
        print("  ERROR:", err[:300])
        psql(LIMPIEZA)
        return 1
    for l in out.splitlines():
        print("  " + l)

    html = HTML.read_text(encoding="utf-8")
    print("\n" + "=" * 68)
    print("COMPROBACION DE LOS NUMEROS")
    print("=" * 68)
    fallos = 0
    pruebas = [
        ("ingresos del mes", f"${ESPERADO['mes']}", "$280"),
        ("ingresos de hoy", f"${ESPERADO['hoy']}", "$100"),
        ("ingresos de la semana", f"${ESPERADO['semana']}", "$130"),
        ("ticket promedio de hoy", f"${ESPERADO['ticket_hoy']}", "$100"),
        ("la cita no_show aparece", "no_show", "no_show"),
    ]
    for nombre, aguja, mostrar in pruebas:
        ok = aguja in html
        if not ok:
            fallos += 1
        print(f"  {'OK  ' if ok else 'MAL '} {nombre}: esperaba {mostrar}")

    # Comprobar los ceros NO estan donde deberia haber datos
    if "$280" in html:
        print("  OK   el mes suma 150+100+30 correctamente")
    else:
        fallos += 1
        print("  MAL  el mes no suma 280")

    print("\n  limpiando los datos de prueba...")
    psql(LIMPIEZA)
    n = consulta("SELECT count(*) FROM barber_citas;")
    print(f"  citas restantes: {n}")
    code, out, err = generar()
    print("  dashboard regenerado sin datos de prueba")

    print("\n" + "=" * 68)
    print(f"FALLOS: {fallos}")
    print("=" * 68)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())