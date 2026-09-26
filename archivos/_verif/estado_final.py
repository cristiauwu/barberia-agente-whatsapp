import sys,io,json,subprocess
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import psql
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
print("=== barber_citas ===")
print(psql("SELECT id_evento,jid,nombre,servicio,inicio::text,estado FROM barber_citas ORDER BY inicio;"))
print("=== escalaciones ===")
print(psql("SELECT * FROM barber_escalaciones;"))
print("=== pausas ===")
print(psql("SELECT * FROM barber_pausas;"))
print("=== bloqueos ===")
print(psql("SELECT * FROM barber_bloqueos;"))
print("=== clientes ===")
print(psql("SELECT * FROM barber_clientes;"))
print("=== max id memoria 1805 ===")
print(psql("SELECT max(id), count(*) FROM n8n_chat_histories WHERE session_id='5214501111805@s.whatsapp.net';"))
bk=json.load(open(r"G:\Barberia\archivos\_verif\bk_memoria_1805.json",encoding="utf-8"))
print("backup filas:",len(bk),"max id backup:",max(r["id"] for r in bk))