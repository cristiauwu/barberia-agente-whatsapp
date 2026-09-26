import json,sys,io,subprocess,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def psql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",s],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()

BASE=r"G:\Barberia\archivos\_verif"
# backup memoria del cliente de pruebas
rows=psql("SELECT json_agg(row_to_json(t)) FROM (SELECT * FROM n8n_chat_histories WHERE session_id='5214501111805@s.whatsapp.net' ORDER BY id) t;")
open(BASE+r"\bk_memoria_1805.json","w",encoding="utf-8").write(rows)
print("memoria 1805 filas backup bytes:",len(rows))
rows2=psql("SELECT json_agg(row_to_json(t)) FROM (SELECT * FROM n8n_chat_histories WHERE session_id='5214521206246@s.whatsapp.net' ORDER BY id) t;")
open(BASE+r"\bk_memoria_6246.json","w",encoding="utf-8").write(rows2)
print("memoria 6246 backup bytes:",len(rows2))
# citas pg
print("=== barber_citas ===")
print(psql("SELECT * FROM barber_citas LIMIT 5;")[:1500])
print("=== count citas ===",psql("SELECT count(*) FROM barber_citas;"))
print("=== bloqueos ===")
print(psql("SELECT * FROM barber_bloqueos;"))
print("=== pausas ===")
print(psql("SELECT * FROM barber_pausas;"))
print("=== clientes ===")
print(psql("SELECT count(*) FROM barber_clientes;"))
print("=== escalaciones ===")
print(psql("SELECT * FROM barber_escalaciones ORDER BY 1 DESC LIMIT 5;")[:800])