import subprocess, os, io, json, re
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
base="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@n8n+n8n-nodes-langchain@file++++home+runner+_work+n8n+n8n+packages+@n8n+nodes-langchain/node_modules/@n8n/n8n-nodes-langchain/dist"
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:2500])
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"grep -n -A 20 'contextWindowLengthProperty' {base}/nodes/memory/descriptions.js | head -40"])
W("=== contextWindowLengthProperty ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"grep -rn 'responsesApiEnabled' {base}/nodes/llm/ 2>/dev/null | head -10; echo '---'; find {base}/nodes -iname '*OpenAi*' -maxdepth 3 | head -20"])
W("=== responsesApiEnabled ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"cat {base}/nodes/llm/LmChatOpenAi/LmChatOpenAi.node.js | head -120"])
W("=== LmChatOpenAi ==="); W(o[:6000])
open(r"G:\Barberia\archivos\_audit\memnode2.txt","w",encoding="utf-8").write("\n".join(out))
