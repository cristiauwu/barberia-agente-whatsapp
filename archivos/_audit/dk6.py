import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
base="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@n8n+n8n-nodes-langchain@file++++home+runner+_work+n8n+n8n+packages+@n8n+nodes-langchain/node_modules/@n8n/n8n-nodes-langchain/dist"
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:3500])
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"wc -l {base}/nodes/memory/MemoryPostgresChat/MemoryPostgresChat.node.js; grep -n 'contextWindowLength\\|supplyData\\|k=' {base}/nodes/memory/MemoryPostgresChat/MemoryPostgresChat.node.js"])
W("=== memory contextWindowLength usage ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"grep -n 'responsesApiEnabled\\|useResponsesApi' {base}/nodes/llms/LMChatOpenAi/common.js"])
W("=== responsesApiEnabled in common.js ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"grep -n -B3 -A12 'responsesApiEnabled' {base}/nodes/llms/LMChatOpenAi/common.js"])
W("=== detail ==="); W(o)
open(r"G:\Barberia\archivos\_audit\memnode4.txt","w",encoding="utf-8").write("\n".join(out))
