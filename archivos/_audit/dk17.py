import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:2500])
p="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@langchain+classic@1.0.27_@aws-sdk+credential-provider-node@3.972.80_@langchain+core@1._14b3f3765668e79e293f0c902e361733/node_modules/@langchain/classic"
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"ls {p}/dist/memory/ | head -20"])
W("memory dir:",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"grep -rn 'this.k\\|k =\\|windowSize\\|k:' {p}/dist/memory/buffer_window.cjs 2>/dev/null | head -20"])
W("buffer_window k:",o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"cat {p}/dist/memory/buffer_window.cjs 2>/dev/null | head -80"])
W("file:",o[:3000])
open(r"G:\Barberia\archivos\_audit\lc3.txt","w",encoding="utf-8").write("\n".join(out))
