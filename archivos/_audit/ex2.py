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
    s=" ".join(str(x) for x in a); out.append(s); print(s[:4000])
rc,o,e=psql("SELECT column_name FROM information_schema.columns WHERE table_name='execution_entity' ORDER BY ordinal_position")
W("=== execution_entity cols ==="); W(o)
rc,o,e=psql("SELECT id, status, \"workflowId\" FROM execution_entity WHERE status='error' ORDER BY id DESC LIMIT 20")
W("=== error executions ==="); W(o, e[:200])
rc,o,e=psql("SELECT id, status, \"workflowId\" FROM execution_entity WHERE status='running' ORDER BY id DESC LIMIT 20")
W("=== running executions ==="); W(o)
rc,o,e=psql("SELECT w.id, w.name, w.\"errorWorkflow\" IS NULL AS no_error_wf FROM workflow_entity w")
W("=== workflows errorWorkflow NULL check ==="); W(o)
# memory node params via jsonb path
rc,o,e=psql("SELECT jsonb_path_query_first(nodes, '$[*] ? (@.name == \"Postgres Chat Memory\").parameters') FROM workflow_entity WHERE id='barberiaAgenteUncensored'")
W("=== memory node params ==="); W(o, e[:300])
open(r"G:\Barberia\archivos\_audit\exec2.txt","w",encoding="utf-8").write("\n".join(out))
