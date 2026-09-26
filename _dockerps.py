import subprocess, os
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
p = subprocess.run([DOCKER, "ps", "-a", "--format", "{{.Names}} | {{.Status}} | {{.Image}}"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
print("PS STDOUT:\n" + p.stdout)
print("PS STDERR:\n" + p.stderr, p.returncode)