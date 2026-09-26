import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -n -A 30 'getNodeParameter(parameterName' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/execution-engine/node-execution-context/node-execution-context.js | head -45"])
W("=== node-execution-context getNodeParameter ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -n -A 30 'getNodeParameter(parameterName' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/execution-engine/node-execution-context/supply-data-context.js | head -45"])
W("=== supply-data-context ==="); W(o)
open(r"G:\Barberia\archivos\_audit\gnp2.txt","w",encoding="utf-8").write("\n".join(out))
