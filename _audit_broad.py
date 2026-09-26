import json, os, re, subprocess

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

buf = []
def w(*a): buf.append(" ".join(str(x) for x in a))

# 1) Broad scan of project text files
PATS = ["barber_clientes", "INSERT INTO barber_citas", "scheduleTrigger", "APT-", "TXN-",
        "interactive", "button", "revenue", "ingreso", "Metricas", "metricas",
        "Transacciones", "Paco", "Esteban", "Juan", "Carlos", "Miguel"]
root = r"G:\Barberia"
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in (".docker", "_audit", "node_modules", ".git")]
    for fn in files:
        if not fn.lower().endswith((".md", ".txt", ".json", ".py", ".js", ".csv", ".yml", ".env")):
            continue
        p = os.path.join(dirpath, fn)
        if fn.startswith("_audit") or fn.startswith("_"): 
            continue
        try:
            raw = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        hits = {pat: len(re.findall(re.escape(pat), raw, re.I)) for pat in PATS}
        hits = {k: v for k, v in hits.items() if v}
        if hits:
            w(f"FILE {p}: {hits}")

# 2) sql: full column list of every barber_ table
for t in ["barber_auditoria","barber_bloqueos","barber_citas","barber_clientes",
          "barber_consentimiento","barber_escalaciones","barber_lista_espera",
          "barber_operadores","barber_pausas","barber_servicios"]:
    sql = f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position;"
    p = subprocess.run([DOCKER,"exec","barber-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    w(f"\n{t}: {p.stdout.strip().replace(chr(10), ', ')}")

# 3) count executions per workflow
sql = "SELECT w.name||' -> '||count(e.id)||' exec' FROM workflow_entity w LEFT JOIN execution_entity e ON e.\"workflowId\"=w.id GROUP BY w.name ORDER BY 1;"
p = subprocess.run([DOCKER,"exec","barber-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
w("\nEXECUTIONS:\n" + p.stdout + p.stderr)

# 4) node types used across all workflows (search settings/nodejs)
sql = "SELECT name, active, \"updatedAt\" FROM workflow_entity ORDER BY name;"
p = subprocess.run([DOCKER,"exec","barber-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
w("\nWORKFLOWS:\n" + p.stdout + p.stderr)

open(r"G:\Barberia\_audit\_broad.txt","w",encoding="utf-8").write("\n".join(buf))
print("ok")