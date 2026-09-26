import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rln 'applyDefaults\\|getNodeParameters' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/ | head -20"])
W("=== files ===",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'applyDefaults' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/NodeHelpers.js | head -20"])
W("=== NodeHelpers applyDefaults ===",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn -A 25 'const applyDefaults' /usr/local/lib/node_modules/n8n/node_modules/n8n-workflow/dist/cjs/NodeHelpers.js | head -50"])
W("=== applyDefaults impl ===",o)
open(r"G:\Barberia\archivos\_audit\def2.txt","w",encoding="utf-8").write("\n".join(out))
