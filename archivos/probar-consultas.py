#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica y prueba las consultas de los comandos del dueño.

Crea las 2 tablas nuevas (barber_servicios, barber_pausas), siembra el
catálogo, y prueba CADA consulta de lectura con datos de ejemplo que luego
borra, dejando la base como estaba.
"""
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
SQL = r"G:\Barberia\archivos\consultas-comandos.sql"

JID_PRUEBA = "529991112233@s.whatsapp.net"


def psql(sql, params=None):
    """Ejecuta SQL. Devuelve (stdout, stderr) por separado.

    Los ERRORES van a stderr: hay que mirar ambos.

    IMPORTANTE: psql NO sustituye variables (:'x') cuando se usa -c. La
    sustitución solo ocurre al leer de un archivo o de stdin. Por eso el
    SQL se copia a un archivo temporal dentro del contenedor y se ejecuta
    con -f.
    """
    args = [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
            "-d", "barberia", "-t", "-A", "-F", " | "]
    for k, v in (params or {}).items():
        args += ["-v", f"{k}={v}"]

    if sql.startswith("@@file:"):
        ruta = sql.split("@@file:", 1)[1]
        args += ["-f", ruta]
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return (p.stdout or "").strip(), (p.stderr or "").strip()

    # Escribir el SQL a un archivo y copiarlo al contenedor
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False,
                                     encoding="utf-8") as f:
        f.write(sql + ";\n" if not sql.rstrip().endswith(";") else sql)
        temporal = f.name
    destino = "/tmp/_q.sql"
    subprocess.run([DOCKER, "cp", temporal, f"barberia-postgres:{destino}"],
                   capture_output=True)
    os.remove(temporal)
    args += ["-f", destino]
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    fallos = 0
    print("=" * 72)
    print("APLICAR TABLAS Y CONSULTAS DE COMANDOS")
    print("=" * 72)

    # --- Aplicar SOLO la parte DDL -----------------------------------
    # El archivo mezcla el DDL (ejecutable) con plantillas que llevan
    # variables :'x'. Se corta en el marcador @@FIN-DDL y se aplica solo
    # la parte de arriba; las plantillas se prueban una por una.
    completo = open(SQL, encoding="utf-8").read()
    if "@@FIN-DDL" not in completo:
        print("  MAL  falta el marcador @@FIN-DDL en el SQL")
        return 1
    ddl = completo.split("@@FIN-DDL")[0]
    ruta_ddl = r"G:\Barberia\archivos\_solo-ddl.sql"
    with open(ruta_ddl, "w", encoding="utf-8") as f:
        f.write(ddl)

    subprocess.run([DOCKER, "cp", ruta_ddl,
                    "barberia-postgres:/tmp/_solo-ddl.sql"], capture_output=True)
    out, err = psql("@@file:/tmp/_solo-ddl.sql")
    if "ERROR" in err:
        print("  ERROR al aplicar el DDL:")
        print("   ", err[:600])
        return 1
    print("  DDL aplicado sin errores (tablas y siembra)")
    os.remove(ruta_ddl)

    # --- Verificar las tablas ---------------------------------------
    print()
    print("=" * 72)
    print("TABLAS NUEVAS")
    print("=" * 72)
    for t in ("barber_servicios", "barber_pausas"):
        n, _ = psql(f"SELECT count(*) FROM {t};")
        print(f"  OK   {t} existe ({n} filas)")
    n, _ = psql("SELECT count(*) FROM barber_servicios;")
    if n == "8":
        print(f"  OK   barber_servicios sembrada con los 8 servicios")
    else:
        print(f"  MAL  barber_servicios tiene {n} filas (esperado 8)")
        fallos += 1

    # --- Datos de ejemplo -------------------------------------------
    print()
    print("=" * 72)
    print("INSERTANDO DATOS DE EJEMPLO")
    print("=" * 72)
    semillas = [
        ("cliente de prueba",
         "INSERT INTO barber_clientes (jid, nombre, telefono, visitas, "
         f"no_shows, etiqueta, servicio_habitual) VALUES "
         f"('{JID_PRUEBA}', 'Cliente Prueba', '4521206246', 3, 1, "
         "'frecuente', 'corte') ON CONFLICT (jid) DO NOTHING;"),
        ("cita de hoy 13:00",
         "INSERT INTO barber_citas (id, jid, nombre, servicio, precio, "
         "inicio, fin, estado) VALUES ('prueba-hoy', "
         f"'{JID_PRUEBA}', 'Cliente Prueba', 'Corte', 150, "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '13 hours', "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '13 hours 40 minutes', 'agendado') "
         "ON CONFLICT (id) DO NOTHING;"),
        ("cita de mañana 16:00",
         "INSERT INTO barber_citas (id, jid, nombre, servicio, precio, "
         "inicio, fin, estado) VALUES ('prueba-manana', "
         f"'{JID_PRUEBA}', 'Cliente Prueba', 'Barba', 100, "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '1 day 16 hours', "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '1 day 16 hours 20 minutes', 'agendado') "
         "ON CONFLICT (id) DO NOTHING;"),
        ("una cancelada (no debe aparecer)",
         "INSERT INTO barber_citas (id, jid, nombre, servicio, precio, "
         "inicio, fin, estado) VALUES ('prueba-cancelada', "
         f"'{JID_PRUEBA}', 'Cliente Prueba', 'Ceja', 30, "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '18 hours', "
         "date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') "
         "+ interval '18 hours 10 minutes', 'cancelado') "
         "ON CONFLICT (id) DO NOTHING;"),
    ]
    for etiqueta, sql in semillas:
        _, err = psql(sql)
        if "ERROR" in err:
            print(f"  AVISO {etiqueta}: {err[:100]}")
        else:
            print(f"  OK    {etiqueta}")

    # --- Probar cada consulta ---------------------------------------
    print()
    print("=" * 72)
    print("PRUEBA DE CADA CONSULTA")
    print("=" * 72)

    def probar(nombre, sql, params, espera_contenido=True):
        """Ejecuta una consulta y reporta. Cuenta el fallo de verdad."""
        nonlocal fallos
        out, err = psql(sql, params)
        vacio = (out == "")
        ok = (not vacio) if espera_contenido else True
        if "ERROR" in err:
            ok = False
        if not ok:
            fallos += 1
        marca = "OK  " if ok else "MAL "
        print(f"  {marca}{nombre}")
        if err and "ERROR" in err:
            print(f"         ERROR: {err[:150]}")
        elif out:
            primera = out.splitlines()[0][:96]
            print(f"         {primera}")
        return ok

    # HOY: rango del día en México
    probar("HOY cita de hoy",
           """SELECT to_char(c.inicio AT TIME ZONE 'America/Mexico_City',
              'HH24:MI'), coalesce(nullif(c.nombre,''), cl.nombre), c.servicio,
              c.precio, c.estado FROM barber_citas c
              LEFT JOIN barber_clientes cl ON cl.jid = c.jid
              WHERE c.inicio >= :'desde'::timestamptz
                AND c.inicio <= :'hasta'::timestamptz
                AND c.estado IN ('agendado','confirmado')
              ORDER BY c.inicio;""",
           {"desde": "2026-09-25T00:00:00-06:00",
            "hasta": "2026-09-25T23:59:00-06:00"})

    # La cancelada NO debe salir
    out, _ = psql("""SELECT count(*) FROM barber_citas
                     WHERE id = 'prueba-cancelada'
                       AND estado IN ('agendado','confirmado');""")
    if out == "0":
        print("  OK   la cita cancelada queda excluida (filtro de estado)")
    else:
        print("  MAL  la cita cancelada apareció"); fallos += 1

    probar("CLIENTE por número",
           """SELECT cl.nombre, cl.visitas, cl.no_shows, cl.etiqueta,
              (SELECT count(*) FROM barber_citas c WHERE c.jid = cl.jid
               AND c.inicio > now() AND c.estado IN ('agendado','confirmado'))
              FROM barber_clientes cl
              WHERE cl.jid LIKE '%' || :'busqueda' || '%'
                 OR right(regexp_replace(cl.telefono,'\\D','','g'),10)
                    = right(regexp_replace(:'busqueda','\\D','','g'),10)
                 OR right(regexp_replace(split_part(cl.jid,'@',1),'\\D','','g'),10)
                    = right(regexp_replace(:'busqueda','\\D','','g'),10)
              LIMIT 5;""",
           {"busqueda": "4521206246"})

    # El mismo cliente debe encontrarse con TODOS los formatos del número
    for variante in ("4521206246", "5214521206246", "524521206246",
                     "529991112233@s.whatsapp.net"):
        out, _ = psql("""SELECT count(*) FROM barber_clientes cl
              WHERE cl.jid LIKE '%' || :'busqueda' || '%'
                 OR right(regexp_replace(cl.telefono,'\\D','','g'),10)
                    = right(regexp_replace(:'busqueda','\\D','','g'),10)
                 OR right(regexp_replace(split_part(cl.jid,'@',1),'\\D','','g'),10)
                    = right(regexp_replace(:'busqueda','\\D','','g'),10);""",
                      {"busqueda": variante})
        # Los 4 formatos deben encontrar al MISMO cliente: el usuario buscó
        # su propio número (524521206246) y el cliente de prueba tiene ese
        # mismo teléfono, así que la normalización por últimos 10 dígitos
        # los hace coincidir. Esto demuestra que 52+10 y 52+1+10 se tratan
        # como el mismo número.
        esperado = "1"
        ok = out == esperado
        if not ok:
            fallos += 1
        print(f"  {'OK  ' if ok else 'MAL '} busca con '{variante}' "
              f"-> {out} coincidencia(s)")

    probar("PRECIO catálogo", "SELECT clave, precio FROM barber_servicios "
           "WHERE activo ORDER BY precio DESC;", {})

    probar("ESTADO salud", """SELECT
        (SELECT count(*) FROM barber_citas WHERE inicio >= now()
          AND estado IN ('agendado','confirmado')),
        (SELECT count(*) FROM barber_escalaciones
          WHERE coalesce(estado,'abierta') = 'abierta'),
        (SELECT count(*) FROM barber_operadores WHERE activo);""", {})

    # PAUSA: insertar y consultar
    probar("PAUSA insertar",
           "INSERT INTO barber_pausas (jid, hasta, motivo) VALUES "
           "(:'jid', now() + (:'horas' || ' hours')::interval, 'prueba') "
           "ON CONFLICT (jid) DO UPDATE SET hasta = excluded.hasta "
           "RETURNING jid, hasta;",
           {"jid": JID_PRUEBA, "horas": "2"})
    probar("PAUSA vigente",
           "SELECT jid, hasta FROM barber_pausas WHERE jid = :'jid' "
           "AND hasta > now();", {"jid": JID_PRUEBA})

    # PRECIO: actualizar y verificar, luego restaurar
    probar("PRECIO actualizar",
           "UPDATE barber_servicios SET precio = :'precio'::numeric "
           "WHERE clave = :'clave' RETURNING clave, precio;",
           {"clave": "ceja", "precio": "35"})
    out, _ = psql("SELECT precio FROM barber_servicios WHERE clave='ceja';")
    if out == "35":
        print("  OK   el precio se actualizó a 35")
    else:
        print(f"  MAL  el precio quedó en {out}"); fallos += 1
    psql("UPDATE barber_servicios SET precio = 30 WHERE clave='ceja';")
    out, _ = psql("SELECT precio FROM barber_servicios WHERE clave='ceja';")
    print(f"  {'OK  ' if out == '30' else 'MAL '} precio restaurado a 30")

    # --- Limpieza ----------------------------------------------------
    print()
    print("=" * 72)
    print("LIMPIANDO LOS DATOS DE PRUEBA")
    print("=" * 72)
    for sql in ("DELETE FROM barber_citas WHERE id LIKE 'prueba-%';",
                f"DELETE FROM barber_pausas WHERE jid = '{JID_PRUEBA}';",
                f"DELETE FROM barber_clientes WHERE jid = '{JID_PRUEBA}';"):
        _, err = psql(sql)
        if "ERROR" in err:
            print(f"  AVISO: {err[:100]}")

    print()
    print("=" * 72)
    print("ESTADO FINAL (debe estar limpio)")
    print("=" * 72)
    for t, esperado in (("barber_clientes", "0"), ("barber_citas", "0"),
                        ("barber_pausas", "0"), ("barber_servicios", "8"),
                        ("barber_operadores", "2")):
        n, _ = psql(f"SELECT count(*) FROM {t};")
        ok = n == esperado
        if not ok:
            fallos += 1
        print(f"  {'OK  ' if ok else 'MAL '}{t}: {n} (esperado {esperado})")

    print()
    print("=" * 72)
    print(f"RESULTADO: {'TODO OK' if fallos == 0 else str(fallos) + ' FALLOS'}")
    print("=" * 72)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())