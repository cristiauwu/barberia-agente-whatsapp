import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
def psql(sql):
    return run(["exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",sql])
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=psql("SELECT id, status, started_at, stopped_at, left(retryOf,0) FROM execution_entity WHERE \"workflowId\"='barberiaAgenteUncensored' ORDER BY id DESC LIMIT 20")
W("=== recent executions (agent) ==="); W(o); W(e[:200])
rc,o,e=psql("SELECT status, count(*) FROM execution_entity WHERE \"workflowId\"='barberiaAgenteUncensored' GROUP BY 1")
W("=== status counts agent ==="); W(o)
rc,o,e=psql("SELECT status, count(*) FROM execution_entity WHERE \"workflowId\"='barberiaRecordatorios' GROUP BY 1")
W("=== status counts recordatorios ==="); W(o)
rc,o,e=psql("SELECT w.name, w.\"errorWorkflow\" FROM workflow_entity w")
W("=== errorWorkflow configured per workflow ==="); W(o)
# Check stored node parameters for memory
rc,o,e=psql("SELECT nodes->(SELECT ordinality-1 FROM jsonb_array_elements(nodes) WITH ORDINALITY t(x,ordinality) WHERE x->>'name'='Postgres Chat Memory')->'parameters' FROM workflow_entity WHERE id='barberiaAgenteUncensored'")
W("=== stored memory node params (from DB) ==="); W(o)
open(r"G:\Barberia\archivos\_audit\exec.txt","w",encoding="utf-8").write("\n".join(out))
