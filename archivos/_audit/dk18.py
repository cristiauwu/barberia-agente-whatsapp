import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3500])
p="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@langchain+classic@1.0.27_@aws-sdk+credential-provider-node@3.972.80_@langchain+core@1._14b3f3765668e79e293f0c902e361733/node_modules/@langchain/classic/dist/memory"
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"cat {p}/buffer_window_memory.cjs"])
W("=== buffer_window_memory.cjs ==="); W(o[:4000])
open(r"G:\Barberia\archivos\_audit\lc4.txt","w",encoding="utf-8").write("\n".join(out))
