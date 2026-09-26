import subprocess, os, time, sys
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def run(args, label, timeout=25):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        buf.append(f"### {label}\nOUT:\n{p.stdout}\nERR: {p.stderr}\nRC:{p.returncode}\n")
    except subprocess.TimeoutExpired:
        buf.append(f"### {label}\n!! TIMEOUT {timeout}s\n")

run([DOCKER,"ps","-a","--format","{{.Names}}"], "PS")
run([DOCKER,"exec","barber-postgres","echo","ping"], "PING client")
q = lambda sql, lbl: run([DOCKER,"exec","barber-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c",sql], lbl)

q("SELECT 'citas='||count(*) FROM barber_citas;", "COUNT citas")
q("SELECT 'clientes='||count(*) FROM barber_clientes;", "COUNT clientes")
q("SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='barber_auditoria';", "COLS auditoria")
q("SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='barber_bloqueos';", "COLS bloqueos")
q("SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='barber_pausas';", "COLS pausas")
q("SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='barber_operadores';", "COLS operadores")

open(r"G:\Barberia\_audit\_db3.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")