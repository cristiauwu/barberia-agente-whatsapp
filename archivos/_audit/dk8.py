import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'function getNodeParameter' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/ 2>/dev/null | head"])
W("=== getNodeParameter in n8n-core ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn -A 25 'function getNodeParameter' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/esm/WorkflowDataProxy.js /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/*.js 2>/dev/null | grep -A25 'getNodeParameter(node' | head -40"])
W("=== impl ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rln 'getNodeParameter(parameterName' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/ /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/ 2>/dev/null | head"])
W("=== files ==="); W(o)
open(r"G:\Barberia\archivos\_audit\gnp.txt","w",encoding="utf-8").write("\n".join(out))
