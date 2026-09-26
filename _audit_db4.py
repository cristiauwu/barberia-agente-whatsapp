import subprocess, os
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf=[]
def run(args, label, timeout=30):
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=timeout)
        buf.append(f"### {label}\nCMD: {' '.join(args)}\nOUT:\n{p.stdout}\nERR: {p.stderr}\nRC:{p.returncode}\n")
    except subprocess.TimeoutExpired:
        buf.append(f"### {label}\n!! TIMEOUT\n")

run([DOCKER,"ps","-a","--no-trunc","--format","{{.ID}}|{{.Names}}|{{.State}}"], "PS FULL")
run([DOCKER,"context","ls"], "CONTEXT LS")
run([DOCKER,"context","show"], "CONTEXT SHOW")
run([DOCKER,"version","--format","{{.Server.Version}}"], "VERSION")

open(r"G:\Barberia\_audit\_db4.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")