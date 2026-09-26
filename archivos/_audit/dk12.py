import subprocess, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args,t=180):
    r=subprocess.run([DOCKER]+args,capture_output=True,text=True,timeout=t,env=env,encoding="utf-8",errors="replace"); return r.returncode,r.stdout,r.stderr
base="/usr/local/lib/node_modules/n8n/node_modules/.pnpm/@n8n+n8n-nodes-langchain@file++++home+runner+_work+n8n+n8n+packages+@n8n+nodes-langchain/node_modules/@n8n/n8n-nodes-langchain/dist"
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:4000])
rc,o,e=run(["exec","barberia-n8n","sh","-c",f"sed -n '222,245p' {base}/nodes/llms/LMChatOpenAi/LmChatOpenAi.node.js"])
W("=== responsesApiEnabled definition ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rn 'descriptionType' /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/GoogleSheetsTool.node.js /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet/*.js 2>/dev/null | head -10; echo '--- tool file list'; find /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/nodes/Google/Sheet -name '*Tool*' | head"])
W("=== googleSheetsTool descriptionType ==="); W(o)
rc,o,e=run(["exec","barberia-n8n","sh","-c","grep -rln 'GoogleSheetsTool\\|googleSheetsTool' /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-base/dist/ | head"])
W("=== tool node files ==="); W(o)
open(r"G:\Barberia\archivos\_audit\last.txt","w",encoding="utf-8").write("\n".join(out))
