import subprocess, os
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def q(sql, label):
    p = subprocess.run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=40)
    buf.append(f"### {label}\nSQL: {sql}\nOUT:\n{p.stdout}\nERR: {p.stderr}\n")

tables = ["barber_auditoria","barber_bloqueos","barber_citas","barber_clientes",
          "barber_consentimiento","barber_escalaciones","barber_lista_espera",
          "barber_operadores","barber_pausas","barber_servicios"]
q("SELECT string_agg(table_name, ', ' ORDER BY table_name) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'barber%';", "TABLAS barber_*")
q("SELECT string_agg(table_name, ', ') FROM information_schema.tables WHERE table_schema='public' AND (table_name ILIKE '%transacc%' OR table_name ILIKE '%metric%' OR table_name ILIKE '%venta%' OR table_name ILIKE '%ingreso%');", "BUSCAR transacciones/metricas (debe vaciar)")
for t in tables:
    q(f"SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='{t}';", f"COLS {t}")
q("SELECT relname||' = '||n_live_tup FROM pg_stat_user_tables WHERE relname LIKE 'barber%' ORDER BY relname;", "ROWCOUNTS")
q("SELECT string_agg(table_name||'='||n_live_tup, ', ') FROM pg_stat_user_tables WHERE relname LIKE 'barber%';", "ROWCOUNTS2")
q("SELECT 'citas='||count(*) FROM barber_citas;", "COUNT citas")
q("SELECT 'clientes='||count(*) FROM barber_clientes;", "COUNT clientes")
q("SELECT 'operadores='||count(*) FROM barber_operadores;", "COUNT operadores")
q("SELECT jid||' | '||nombre||' | '||rol FROM barber_operadores;", "operadores")
q("SELECT string_agg(clave||'='||nombre||' $'||precio||'/'||duracion_min||'min', ', ' ORDER BY clave) FROM barber_servicios;", "servicios")
q("SELECT w.name||' -> '||count(e.id) FROM workflow_entity w LEFT JOIN execution_entity e ON e.\"workflowId\"=w.id GROUP BY w.name ORDER BY 1;", "EXECUTIONS")
open(r"G:\Barberia\_audit\_db6.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")