import subprocess, os, io, json
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"]=r"G:\Barberia\.docker"
def run(args, t=180):
    r = subprocess.run([DOCKER]+args, capture_output=True, text=True, timeout=t, env=env, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr
def psql(sql, db="barberia"):
    return run(["exec","barberia-postgres","psql","-U","barberia","-d",db,"-t","-A","-F","|","-c",sql])
out=[]
def W(*a):
    s=" ".join(str(x) for x in a); out.append(s); print(s[:4000])
rc,o,e=psql("SELECT column_name FROM information_schema.columns WHERE table_name='execution_data'")
W("=== execution_data cols ==="); W(o)
rc,o,e=psql("SELECT \"executionId\", left(data::text, 400) FROM execution_data WHERE \"executionId\"=770")
W("=== exec 770 data ==="); W(o,e[:300])
# maybe workflowData column exists in old table
rc,o,e=psql("SELECT count(*) FROM execution_data")
W("=== execution_data rows ==="); W(o)
# Search error strings across execution_data
rc,o,e=psql("SELECT \"executionId\", substring(data::text from position('\"error\"' in data::text) for 500) FROM execution_data WHERE data::text LIKE '%error%' ORDER BY \"executionId\" DESC LIMIT 5")
W("=== error snippets ==="); W(o)
open(r"G:\Barberia\archivos\_audit\err2.txt","w",encoding="utf-8").write("\n".join(out))
