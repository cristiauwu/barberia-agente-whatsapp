import subprocess, os, json

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ)
env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
OUT = r"G:\Barberia\_audit_pg_report.txt"

def q(sql, label):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
                        "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return (f"\n{'='*70}\n{label}\nSQL: {sql}\n{'='*70}\n"
            f"--STDOUT--\n{p.stdout}\n--STDERR--\n{p.stderr}\n--RC {p.returncode}--\n")

queries = [
 ("A) LISTA DE TABLAS", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"),
 ("B) TABLAS barber_* (confirmacion)", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'barber%' ORDER BY 1;"),
 ("C) BUSCAR TABLAS TRANSACCIONES/METRICAS", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND (table_name ILIKE '%transacc%' OR table_name ILIKE '%metric%' OR table_name ILIKE '%venta%' OR table_name ILIKE '%ingreso%' OR table_name ILIKE '%ventas%');"),
 ("D) COLUMNAS barber_clientes", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_clientes' ORDER BY ordinal_position;"),
 ("E) COLUMNAS barber_citas", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_citas' ORDER BY ordinal_position;"),
 ("F) CONTEO FILAS TODAS LAS TABLAS barber_*", "SELECT relname||' = '||n_live_tup FROM pg_stat_user_tables WHERE relname LIKE 'barber%' ORDER BY relname;"),
 ("G) CONTENIDO barber_clientes (primeras 20)", "SELECT * FROM barber_clientes ORDER BY 1 LIMIT 20;"),
 ("H) CONTEO barber_clientes", "SELECT count(*) FROM barber_clientes;"),
 ("I) CONTEO barber_citas por estado", "SELECT estado||' = '||count(*) FROM barber_citas GROUP BY estado;"),
 ("J) MUESTRA barber_citas", "SELECT id||' | '||jid||' | '||coalesce(nombre,'')||' | '||servicio||' | '||precio||' | '||inicio||' | '||estado FROM barber_citas ORDER BY creado_en DESC LIMIT 10;"),
 ("K) barber_operadores", "SELECT * FROM barber_operadores LIMIT 20;"),
 ("L) barber_servicios", "SELECT * FROM barber_servicios LIMIT 30;"),
 ("M) barber_auditoria muestra", "SELECT * FROM barber_auditoria ORDER BY 1 DESC LIMIT 5;"),
 ("N) COLUMNAS barber_servicios", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_servicios' ORDER BY ordinal_position;"),
 ("O) COLUMNAS barber_escalaciones", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_escalaciones' ORDER BY ordinal_position;"),
 ("P) COLUMNAS barber_lista_espera", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_lista_espera' ORDER BY ordinal_position;"),
 ("Q) COLUMNAS barber_consentimiento", "SELECT column_name||' | '||data_type FROM information_schema.columns WHERE table_name='barber_consentimiento' ORDER BY ordinal_position;"),
 ("R) CONTEO barber_citas total", "SELECT count(*) FROM barber_citas;"),
 ("S) schedule/cron en postgres? n8n workflows", "SELECT id, name, active FROM workflow_entity ORDER BY name;"),
 ("T) n8n nodos tipo schedule", "SELECT DISTINCT \"nodeName\" FROM (SELECT 1) x WHERE false;"),
]

buf = []
for label, sql in queries:
    try:
        buf.append(q(sql, label))
    except Exception as e:
        buf.append(f"\n!! ERROR en {label}: {e}\n")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(buf))
print("OK ->", OUT)