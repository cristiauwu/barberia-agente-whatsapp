import json, urllib.request, subprocess, sys

KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY",KEY)
    return json.loads(urllib.request.urlopen(r,timeout=60).read().decode())

out={}
try:
    wfs=api("/workflows?limit=100")
    out["workflows"]=[(w["id"],w["name"],w.get("active")) for w in wfs["data"]]
except Exception as e:
    out["workflows_err"]=repr(e)

DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
try:
    ps=subprocess.run([DOCKER,"ps","--format","{{.Names}}\t{{.Status}}"],capture_output=True,text=True)
    out["docker"]=ps.stdout.strip()
except Exception as e:
    out["docker_err"]=repr(e)

print(json.dumps(out,ensure_ascii=False,indent=1))