#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza: borra SOLO lo que crearon mis pruebas.

Identifica por Execution ID:
  1272  -> c3  "Quiero un corte el viernes a las 4"  (evento 85e7vg5v..., fila 8)
  1282  -> c5  "Agendame un corte el 30 de septiembre a las 3" (evento mfako9a..., fila 10)

Y restaura la memoria del JID de pruebas desde el respaldo previo.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"G:\Barberia\archivos\_verif")
DIR = r"G:\Barberia\archivos\_verif-fechas"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
BASE = "http://localhost:5678/api/v1"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
JID = "5214501111805@s.whatsapp.net"

MIS_EVENTOS = {
    "85e7vg5vkv3pbggu01j9fp2gtk": "c3 (exec 1272)",
    "mfako9a08epskn3irbr3rq4g4o": "c5 (exec 1282)",
}
MIS_FILAS = {8: "c3 (exec 1272)", 10: "c5 (exec 1282)"}


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    q = urllib.request.Request(BASE + path, data=data, method=method)
    q.add_header("X-N8N-API-KEY", KEY)
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=120) as x:
        txt = x.read().decode()
        return json.loads(txt) if txt.strip() else {}


def psql(s, entrada=None):
    r = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A", "-F",
                        "\t", "-c", s], input=entrada, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


# ======================================================= 1. calendario
print("=" * 70)
print("1. CALENDARIO: borrar eventos de mis pruebas")
print("=" * 70)
import cal  # noqa: E402

for eid, quien in MIS_EVENTOS.items():
    try:
        r = cal.borrar(eid)
        print(f"  borrado {eid} ({quien}) -> {json.dumps(r, ensure_ascii=False)[:160]}")
    except Exception as e:
        print(f"  ERROR borrando {eid}: {e}")
    time.sleep(2)

r = cal.listar("2026-09-01T00:00:00-06:00", "2027-03-01T23:59:59-06:00")
ev = (r.get("eventos") if isinstance(r, dict) else
      (r[0] or {}).get("json", {}).get("eventos", [])) or []
cal.limpiar_wf()
print("eventos ahora:", len(ev))
antes = json.load(open(DIR + r"\respaldo_calendario.json", encoding="utf-8"))
ids_antes = {e["id"] for e in antes}
sobran = [e for e in ev if e["id"] not in ids_antes]
print("eventos que siguen sin estar en el respaldo previo:", len(sobran))
for e in sobran:
    print(f"  {e['id']} | {e['start']} | {e['summary']}")

# ======================================================= 2. hoja
print()
print("=" * 70)
print("2. HOJA: borrar las filas de mis pruebas")
print("=" * 70)
wfa = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
creds = next(n for n in wfa["nodes"]
             if n["name"] == "Registrar en hoja de citas")["credentials"]
DOC = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
HOJA = "941506024"

wf = {
 "name": "_verif-fechas-borrar",
 "nodes": [
   {"parameters": {"httpMethod": "POST", "path": "verifborrar",
                   "responseMode": "lastNode", "options": {}},
    "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
    "id": "wh1", "name": "Webhook", "webhookId": "wh-verif-borrar"},
   {"parameters": {"operation": "delete", "documentId": {
       "__rl": True, "value": DOC, "mode": "list",
       "cachedResultName": "Citas barbería"},
     "sheetName": {"__rl": True, "value": HOJA, "mode": "list",
                   "cachedResultName": "Hoja 1"},
     "startIndex": "={{ $json.body.fila }}",
     "options": {}},
    "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
    "position": [220, 0], "id": "gs1", "name": "Borrar",
    "credentials": creds},
 ], "connections": {"Webhook": {"main": [[{"node": "Borrar", "type": "main",
                                           "index": 0}]]}},
 "settings": {"executionOrder": "v1"}}

creado = call("POST", "/workflows", wf)
wid = creado["id"]
try:
    call("POST", f"/workflows/{wid}/activate", {})
    time.sleep(4)
    # borrar de mayor a menor para que no se desplace el indice
    for fila in sorted(MIS_FILAS, reverse=True):
        q = urllib.request.Request("http://localhost:5678/webhook/verifborrar",
                                   data=json.dumps({"fila": fila}).encode(),
                                   method="POST")
        q.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(q, timeout=120) as x:
                print(f"  fila {fila} ({MIS_FILAS[fila]}) -> {x.status} "
                      f"{x.read().decode()[:200]}")
        except Exception as e:
            print(f"  ERROR borrando la fila {fila}: {e}")
        time.sleep(3)
finally:
    time.sleep(2)
    try:
        call("POST", f"/workflows/{wid}/deactivate", {})
    except Exception:
        pass
    time.sleep(1)
    call("DELETE", f"/workflows/{wid}")
    print("workflow temporal de borrado eliminado")

# ======================================================= 3. memoria
print()
print("=" * 70)
print("3. MEMORIA del JID de pruebas: restaurar el respaldo previo")
print("=" * 70)
bk = json.load(open(DIR + r"\respaldo_memoria_1805.json", encoding="utf-8"))
print("filas en el respaldo:", len(bk))
print("antes:", psql(f"SELECT count(*),min(id),max(id) FROM n8n_chat_histories "
                     f"WHERE session_id='{JID}';"))
print(psql(f"DELETE FROM n8n_chat_histories WHERE session_id='{JID}';"))
vals = []
for r in bk:
    msg = json.dumps(r["message"], ensure_ascii=False).replace("'", "''")
    vals.append(f"({r['id']},'{JID}','{msg}'::jsonb)")
for i in range(0, len(vals), 50):
    chunk = ",".join(vals[i:i + 50])
    print(psql(f"INSERT INTO n8n_chat_histories(id,session_id,message) "
               f"VALUES {chunk};"))
print("despues:", psql(f"SELECT count(*),min(id),max(id) FROM n8n_chat_histories "
                       f"WHERE session_id='{JID}';"))
# comprobar que el ultimo mensaje coincide con el respaldo
print("ultimo mensaje:",
      psql(f"SELECT message->>'content' FROM n8n_chat_histories "
           f"WHERE session_id='{JID}' ORDER BY id DESC LIMIT 1;")[:200])
print("ultimo del respaldo:", json.dumps(bk[-1]["message"],
                                          ensure_ascii=False)[:200])
print()
print("secuencia:", psql("SELECT last_value FROM n8n_chat_histories_id_seq;"))