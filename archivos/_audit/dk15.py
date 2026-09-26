import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:3000])
js = ("const {BufferWindowMemory}=require('/usr/local/lib/node_modules/n8n/node_modules/@langchain/classic/memory');"
      "const a=new BufferWindowMemory({memoryKey:'chat_history',returnMessages:true,inputKey:'input',outputKey:'output',k:undefined});"
      "console.log('k with undefined =', a.k);"
      "const b=new BufferWindowMemory({memoryKey:'chat_history',returnMessages:true,inputKey:'input',outputKey:'output'});"
      "console.log('k default (omitted) =', b.k);")
rc,o,e=run(["exec","barberia-n8n","node","-e",js])
W("=== LangChain BufferWindowMemory k ==="); W(o); W("ERR:",e[:1500])
open(r"G:\Barberia\archivos\_audit\lc.txt","w",encoding="utf-8").write("\n".join(out))
