import sys, json, subprocess
sys.stdout.reconfigure(encoding="utf-8")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"

SQL = r"""
\pset pager off
\echo === barber_citas: filas de MIS pruebas ===
select id, jid, nombre, servicio, precio, inicio, fin, estado
from barber_citas
where id in ('verif-rec-wait-24h','verif-cancelado','verif-eliminado',
             'verif-actualizado','verif-reprogramado','verif-rec-t1','verif-rec-t2')
order by id;
\echo === barber_citas: TODA fila cuyo id empieza por verif-rec ===
select count(*) as n from barber_citas where id like 'verif-rec%';
\echo === barber_clientes: el JID de pruebas ===
select jid, nombre, telefono, visitas, etiqueta, primera_visita, ultima_visita
from barber_clientes where jid like '5214501111805%';
\echo === conteo total ===
select (select count(*) from barber_citas) as citas,
       (select count(*) from barber_clientes) as clientes;
"""

p = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                    "-U", "barberia", "-d", "barberia", "-f", "-"],
                   input=SQL.encode("utf-8"), capture_output=True)
print("--- STDOUT ---")
print(p.stdout.decode("utf-8", "replace"))
print("--- STDERR ---")
print(p.stderr.decode("utf-8", "replace"))