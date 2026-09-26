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
rc,o,e=psql("SELECT w.id, w.name, w.settings::text FROM workflow_entity w")
W("=== workflow settings ==="); W(o, e[:200])
rc,o,e=psql("SELECT id, \"workflowId\", data::text FROM execution_data WHERE \"executionId\" IN (770,763,759,758,733,722,720,660,603)")
W("=== execution_data for errors (truncated) ==="); W(o[:6000])
open(r"G:\Barberia\archivos\_audit\err.txt","w",encoding="utf-8").write("\n".join(out))
