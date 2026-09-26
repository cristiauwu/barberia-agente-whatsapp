import json,sys,io,subprocess,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def sh(*a):
    r=subprocess.run([DOCKER,*a],capture_output=True,text=True)
    return (r.stdout+r.stderr).strip()
print("=== n8n TZ ===")
print(sh("exec","barberia-n8n","printenv","TZ"))
print(sh("exec","barberia-n8n","printenv","GENERIC_TIMEZONE"))
print("=== host date ===")
print(datetime.datetime.now().isoformat())
import time
print("utcnow",datetime.datetime.utcnow().isoformat())
print("=== docker-compose n8n env ===")
print(open(r"G:\Barberia\docker-compose.yml",encoding="utf-8",errors="replace").read()[:3000])