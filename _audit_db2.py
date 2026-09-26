import subprocess, os, time
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def q(sql, label):
    for attempt in range(3):
        p = subprocess.run([DOCKER,"exec","barber-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if "No such container" not in (p.stderr or ""):
            break
        time.sleep(2)
    buf.append(f"### {label}\nSQL: {sql}\nOUT:\n{p.stdout}\nERR: {p.stderr}\nRC:{p.returncode}\n")

tables = ["barber_auditoria","barber_bloqueos","barber_citas","barber_clientes",
          "barber_consentimiento","barber_escalaciones","barber_lista_espera",
          "barber_operadores","barber_pausas","barber_servicios"]
for t in tables:
    q(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position;", f"COLS {t}")

q("SELECT w.name||' -> '||count(e.id)||' exec' FROM workflow_entity w LEFT JOIN execution_entity e ON e.\"workflowId\"=w.id GROUP BY w.name ORDER BY 1;", "EXECUTIONS")
q("SELECT name, active, \"updatedAt\" FROM workflow_entity ORDER BY name;", "WORKFLOWS")
q("SELECT count(*) FROM barber_citas;", "COUNT citas")
q("SELECT count(*) FROM barber_clientes;", "COUNT clientes")
q("SELECT count(*) FROM barber_auditoria;", "COUNT auditoria")
q("SELECT * FROM barber_bloqueos LIMIT 3;", "bloqueos sample")
q("SELECT * FROM barber_pausas LIMIT 3;", "pausas sample")
q("SELECT * FROM barber_escalaciones LIMIT 3;", "escalaciones sample")
q("SELECT * FROM barber_lista_espera LIMIT 3;", "lista_espera sample")
q("SELECT * FROM barber_consentimiento LIMIT 3;", "consentimiento sample")
q("SELECT relname||' = '||n_live_tup FROM pg_stat_user_tables WHERE relname LIKE 'barber%' ORDER BY relname;", "ROWCOUNTS")

open(r"G:\Barberia\_audit\_db2.txt","w",encoding="utf-8").write("\n".join(buf))
print("ok")