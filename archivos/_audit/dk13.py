import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rln 'googleSheetsTool' /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/ 2>/dev/null | head -5"])
W("files:",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","find /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist -name '*.node.js' | xargs grep -ln 'Google Sheets Tool' 2>/dev/null | head -5"])
W("by displayName:",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'descriptionType' /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/v2/GoogleSheetsTool.node.js 2>/dev/null | head; ls /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/v2/ | head -30"])
W("sheet v2 dir:",o)
open(r"G:\Barberia\archivos\_audit\sheet.txt","w",encoding="utf-8").write("\n".join(out))
