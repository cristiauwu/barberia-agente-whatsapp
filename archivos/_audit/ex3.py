import subprocess, os, io, json
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
def psql(sql):
    return run(["exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",sql])
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:4000])
rc,o,e=psql("SELECT w.id, w.name, coalesce(w.\"errorWorkflow\",'(NULL)') FROM workflow_entity w")
W("=== errorWorkflow ==="); W(o, e[:300])
rc,o,e=psql("SELECT id, status, \"startedAt\", \"stoppedAt\" FROM execution_entity WHERE status='error' ORDER BY id DESC LIMIT 20")
W("=== error exec timestamps ==="); W(o)
rc,o,e=psql("SELECT id, status, \"stoppedAt\" FROM execution_entity WHERE status='running'")
W("=== running ==="); W(o)
# nodes column: is it json or jsonb?
rc,o,e=psql("SELECT pg_typeof(nodes) FROM workflow_entity LIMIT 1")
W("=== nodes type ==="); W(o)
open(r"G:\Barberia\archivos\_audit\exec3.txt","w",encoding="utf-8").write("\n".join(out))
