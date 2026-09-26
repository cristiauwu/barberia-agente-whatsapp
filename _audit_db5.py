import subprocess, os
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def run(args, label, timeout=30, e=env):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=e, timeout=timeout)
        buf.append(f"### {label}\nCMD: {' '.join(args)}\nOUT:\n{p.stdout}\nERR: {p.stderr}\nRC:{p.returncode}\n")
    except subprocess.TimeoutExpired:
        buf.append(f"### {label}\n!! TIMEOUT\n")

run([DOCKER,"exec","-i","barberia-postgres","echo","hi"], "EXEC -i echo", e=dict(os.environ, DOCKER_CONFIG=r"G:\Barberia\.docker"))
run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c","SELECT 1;"], "EXEC psql 1")
run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c","SELECT count(*) FROM barber_citas;"], "COUNT citas")
run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-c","SELECT count(*) FROM barber_clientes;"], "COUNT clientes")

open(r"G:\Barberia\_audit\_db5.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")