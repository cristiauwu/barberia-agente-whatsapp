import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
lang="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@n8n+n8n-nodes-langchain@file++++home+runner+_work+n8n+n8n+packages+@n8n+nodes-langchain/node_modules/@n8n/n8n-nodes-langchain"
js=f"const {{BufferWindowMemory}}=require('{lang}/node_modules/@langchain/classic/memory');"
js+="const b=new BufferWindowMemory({memoryKey:'chat_history',returnMessages:true,inputKey:'input',outputKey:'output'});console.log('default k =',b.k);"
js+="const c=new BufferWindowMemory({memoryKey:'chat_history',returnMessages:true,inputKey:'input',outputKey:'output',k:undefined});console.log('k=undefined ->',c.k);"
rc,o,e=run(["exec","barberia-n8n","node","-e",js])
W("=== attempt2 ==="); W(o); W("ERR:",e[:1200])
rc,o,e=run(["exec","barberia-n8n","sh","-c","ls -d /usr/local/lib/node_modules/n8n/node_modules/.pnpm/@langchain+classic* 2>/dev/null | head"])
W("pnpm langchain:",o)
open(r"G:\Barberia\archivos\_audit\lc2.txt","w",encoding="utf-8").write("\n".join(out))
