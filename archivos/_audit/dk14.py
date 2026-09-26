import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'getNodeParameters' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/Workflow.js /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/NodeHelpers.js 2>/dev/null | head -20"])
W("=== getNodeParameters refs ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'applyDefaults\\|getNodeParameters(nodeType' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/NodeHelpers.js | head -20"])
W("=== NodeHelpers applyDefaults ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'getNodeParameter\\b' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/execution-engine/node-execution-context/supply-data-context.js | head"])
W("=== supply-data ==="); W(o)
# Where does the AI agent build the subnode context? check executor
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rln 'SupplyDataContext' /usr/local/lib/node_modules/n8n/node_modules/n8n-core/dist/ | head"])
W("=== SupplyDataContext users ==="); W(o)
open(r"G:\Barberia\archivos\_audit\defs.txt","w",encoding="utf-8").write("\n".join(out))
