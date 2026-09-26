import subprocess, os
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def q(sql, label):
    p = subprocess.run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=40)
    buf.append(f"### {label}\n{p.stdout}\nERR:{p.stderr}\n")

q("SELECT now();", "AHORA")
q("SELECT tgname||' | '||tgrelid::regclass::text FROM pg_trigger WHERE NOT tgisinternal;", "TRIGGERS")
q("SELECT string_agg(event_object_table||'.'||trigger_name, ', ') FROM information_schema.triggers;", "TRIGGERS info")
q("SELECT count(*) FROM execution_entity;", "total execuciones")
q("SELECT id||' | '||name||' | '||active FROM workflow_entity;", "workflows")
q("SELECT id||' | '||status||' | '||\"startedAt\"||' | '||\"workflowId\" FROM execution_entity ORDER BY id DESC LIMIT 6;", "ultimas execuciones")
q("SELECT count(*) FROM execution_entity WHERE \"workflowId\"='barberiaRecordatorios';", "exec recordatorios")
q("SELECT count(*) FROM execution_entity WHERE \"workflowId\"='barberiaAgenteUncensored';", "exec agente")
open(r"G:\Barberia\_audit\_db8.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")