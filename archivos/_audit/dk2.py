import subprocess, os, io, json
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=120):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:2000])
rc,o,e = run(["exec","barberia-n8n","n8n","--version"]); W("n8n version rc",rc,o.strip(),e.strip()[:300])
rc,o,e = run(["exec","barberia-n8n","sh","-c","ls /usr/local/lib/node_modules/n8n/node_modules/@n8n/n8n-nodes-langchain/dist/nodes/memory/ 2>/dev/null || find / -name 'memoryPostgresChat*' -maxdepth 8 2>/dev/null | head -20"])
W("memory dir rc",rc); W(o[:3000]); W("ERR:",e[:500])
rc,o,e = run(["exec","barberia-n8n","sh","-c","find / -path '*n8n-nodes-langchain*' -name '*PostgresChat*' 2>/dev/null | head"])
W("find PostgresChat:", o[:2000], e[:300])
open(r"G:\Barberia\archivos\_audit\docker2.txt","w",encoding="utf-8").write("\n".join(out))
