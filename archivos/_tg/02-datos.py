import subprocess, io, json

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
out = io.StringIO()

def psql(sql, label):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia", "-d", "barberia", "-t", "-A", "-F", "|", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.write(f"\n--- {label} ---\n")
    out.write((p.stdout or "").strip() + "\n")
    if (p.stderr or "").strip():
        out.write("STDERR: " + p.stderr.strip()[:500] + "\n")

psql("select count(*) from barber_citas", "total citas")
psql("select estado, count(*) from barber_citas group by estado order by 2 desc", "citas por estado")
psql("select date(inicio) d, count(*) from barber_citas group by 1 order by 1", "citas por dia")
psql("select count(*) from barber_escalaciones", "total escalaciones")
psql("select * from barber_escalaciones order by 1 desc limit 10", "ultimas escalaciones")
psql("select jid, nombre, rol, activo from barber_operadores", "operadores")
psql("select count(*) from barber_clientes", "clientes")
psql("select jid, nombre, visitas, no_shows, etiqueta from barber_clientes order by visitas desc limit 10", "top clientes")
psql("select fecha, accion, detalle from barber_auditoria order by 1 desc limit 15", "auditoria reciente")

open(r"G:\Barberia\archivos\_tg\02-datos.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")