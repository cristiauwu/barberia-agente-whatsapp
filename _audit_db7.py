import subprocess, os, json, re
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def q(sql, label):
    p = subprocess.run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=40)
    buf.append(f"### {label}\n{p.stdout}\nERR:{p.stderr}\n")

q("SELECT id, name, active FROM workflow_entity ORDER BY name;", "WORKFLOWS EN DB")
q("SELECT id||' | '||left(replace(nodes::text, chr(10), ' '), 1200) FROM workflow_entity WHERE id='OfboyiTEpyl0r60x';", "4th workflow nodes")
q("SELECT id, count(*) FROM execution_entity GROUP BY id LIMIT 1;", "x")
q("SELECT string_agg(DISTINCT \"nodeType\", ', ') FROM execution_data WHERE \"workflowData\"::text ILIKE '%scheduleTrigger%';", "scheduleTrigger en exec data")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%scheduleTrigger%';", "count scheduleTrigger")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%interactive%';", "count interactive")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%revenue%';", "count revenue")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%barber_clientes%';", "count barber_clientes refs")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%INSERT INTO barber_clientes%';", "count INSERT barber_clientes")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%INSERT INTO barber_citas%';", "count INSERT barber_citas")
q("SELECT count(*) FROM execution_data WHERE \"workflowData\"::text ILIKE '%barber_auditoria%';", "count barber_auditoria refs")
open(r"G:\Barberia\_audit\_db7.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")