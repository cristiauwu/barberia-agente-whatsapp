import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
base="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@n8n+n8n-nodes-langchain@file++++home+runner+_work+n8n+n8n+packages+@n8n+nodes-langchain/node_modules/@n8n/n8n-nodes-langchain/dist"
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:4500])
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"sed -n '30,120p' {base}/nodes/tools/ToolHttpRequest/descriptions.js"])
W("=== descriptions.js 30-120 ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"sed -n '360,430p' {base}/nodes/tools/ToolHttpRequest/utils.js"])
W("=== utils.js 360-430 ==="); W(o)
open(r"G:\Barberia\archivos\_audit\toolhttp2.txt","w",encoding="utf-8").write("\n".join(out))
