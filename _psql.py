import subprocess, sys, os

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ)
env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

sql = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else r"G:\Barberia\_audit_sql_out.txt"

p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
                    "-d", "barberia", "-t", "-A", "-c", sql],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
with open(out, "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(p.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(p.stderr)
    f.write(f"\n=== RC {p.returncode} ===\n")
print("written", out)