# -*- coding: utf-8 -*-
"""Restaura la memoria original del cliente de pruebas desde el respaldo."""
import json, sys, io, subprocess
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
JID="5214501111805@s.whatsapp.net"
def psql(s,entrada=None):
    r=subprocess.run([DOCKER,"exec","-i","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",s],
                     input=entrada,capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()
bk=json.load(open(r"G:\Barberia\archivos\_verif\bk_memoria_1805.json",encoding="utf-8"))
print("filas en respaldo:",len(bk),"ids",bk[0]["id"],"->",bk[-1]["id"])
print("antes:",psql(f"SELECT count(*) FROM n8n_chat_histories WHERE session_id='{JID}';"))
psql("CREATE TEMP TABLE IF NOT EXISTS tmp_mem(id int, session_id text, message jsonb);")
print(psql("DROP TABLE IF EXISTS tmp_mem;"))
print(psql("CREATE TABLE IF NOT EXISTS tmp_mem(id int primary key, session_id text, message jsonb);"))
# construir el INSERT con literal JSON seguro
vals=[]
for r in bk:
    msg=json.dumps(r["message"],ensure_ascii=False).replace("'","''")
    vals.append(f"({r['id']},'{JID}','{msg}'::jsonb)")
LOTE=50
for i in range(0,len(vals),LOTE):
    chunk=",".join(vals[i:i+LOTE])
    psql(f"INSERT INTO tmp_mem(id,session_id,message) VALUES {chunk} ON CONFLICT (id) DO NOTHING;")
print("en tmp_mem:",psql("SELECT count(*) FROM tmp_mem;"))
print(psql(f"""INSERT INTO n8n_chat_histories(id,session_id,message)
  SELECT id,session_id,message FROM tmp_mem ORDER BY id
  ON CONFLICT (id) DO NOTHING;"""))
print("despues:",psql(f"SELECT count(*),min(id),max(id) FROM n8n_chat_histories WHERE session_id='{JID}';"))
print(psql("DROP TABLE IF EXISTS tmp_mem;"))