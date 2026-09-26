import subprocess, json, os, io
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=90):
    try:
        r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", repr(e)
out=io.StringIO()
rc,o,e = run(["ps","--format","{{.Names}}\t{{.Image}}\t{{.Status}}"])
print("PS rc=",rc); print(o); print("ERR:",e[:800])
rc,o,e = run(["exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c","SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"])
print("TABLES rc=",rc); print(o); print("ERR:",e[:800])
open(r"G:\Barberia\archivos\_audit\docker.txt","w",encoding="utf-8").write(out.getvalue())
