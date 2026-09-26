#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el bucle de confirmacion completo, de punta a punta.

Se crea una cita de prueba para el JID de pruebas, se manda un "SI" como si
el cliente respondiera al recordatorio, y se comprueba que:
  1. el detector lo reconoce (sin llamar al modelo: 0 tokens)
  2. la cita pasa a `confirmado` en Postgres
  3. se avisa al dueno

Y despues se prueba lo contrario: que un "SI" de alguien SIN cita NO se
intercepta, sino que sigue al agente como cualquier mensaje.

Al terminar borra la cita de prueba.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
JID = "5214501111805@s.whatsapp.net"
CITA = "prueba-confirmacion-1"


def sql(q):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A",
                        "-c", q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return (p.stdout or "").strip()


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def enviar(texto, mid):
    k = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True).stdout.strip()
    body = {"event": "messages.upsert", "instance": "hector",
            "server_url": "http://evolution_api:8080", "apikey": k,
            "date_time": "2026-09-26T23:00:00.000Z",
            "data": {"key": {"id": mid, "remoteJid": JID, "fromMe": False},
                     "pushName": "Prueba Confirmacion",
                     "message": {"conversation": texto},
                     "messageType": "conversation"}}
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=140) as r:
        return r.status


def main():
    print("=" * 68)
    print("PRUEBA DEL BUCLE DE CONFIRMACION")
    print("=" * 68)

    # ---------------------------------------------------------------- 0
    print("\n[0] CREAR UNA CITA DE PRUEBA")
    sql(f"DELETE FROM barber_citas WHERE id = '{CITA}';")
    st = sql(f"""INSERT INTO barber_citas (id,jid,nombre,servicio,precio,
        inicio,fin,estado) VALUES ('{CITA}','{JID}','Prueba Confirmacion',
        'Corte desvanecido o tijera',150,
        now() + interval '20 hours', now() + interval '20 hours 40 min',
        'agendado') RETURNING estado;""")
    print(f"  cita creada con estado: {st}")
    estado0 = sql(f"SELECT estado FROM barber_citas WHERE id='{CITA}';")
    print(f"  estado antes: {estado0}")

    # ---------------------------------------------------------------- 1
    print("\n[1] EL CLIENTE RESPONDE 'SI'")
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca = int(ex["data"][0]["id"]) if ex.get("data") else 0
    mid = "T" + uuid.uuid4().hex[:10].upper()
    print(f"  enviando 'si' (message_id {mid})")
    print(f"  -> HTTP {enviar('si', mid)}")
    time.sleep(30)

    # ---------------------------------------------------------------- 2
    print("\n[2] ¿QUE PASO?")
    estado1 = sql(f"SELECT estado FROM barber_citas WHERE id='{CITA}';")
    print(f"  estado de la cita: {estado1}  "
          f"{'<<< CONFIRMADA' if estado1 == 'confirmado' else ''}")

    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=6")
    toco_modelo = False
    ejecutados = []
    for e in ex.get("data", []):
        if int(e["id"]) <= marca:
            continue
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        ejecutados = list(run.keys())
        if "AI Agent" in run:
            toco_modelo = True
        if "Es confirmacion?" in run:
            try:
                sal = run["Es confirmacion?"][0]["data"]["main"][0][0]["json"]
                print(f"  el detector dijo: decision={sal.get('decision')} "
                      f"es_respuesta={sal.get('es_respuesta_confirmacion')} "
                      f"cita={sal.get('cita_id')}")
            except Exception:
                pass
        if "Armar respuesta de confirmacion" in run:
            print("  OK  paso por 'Armar respuesta de confirmacion'")
        if "Marcar cita confirmada" in run:
            print("  OK  paso por 'Marcar cita confirmada'")
        if "Avisar al dueno de la confirmacion" in run:
            print("  OK  paso por 'Avisar al dueno de la confirmacion'")
        break
    print(f"  ¿se llamo al modelo? {'SI (gasto tokens)' if toco_modelo else 'NO (0 tokens)'}")
    print(f"  nodos ejecutados: {len(ejecutados)}")

    # ---------------------------------------------------------------- 3
    print("\n[3] UN 'SI' DE ALGUIEN SIN CITA: no debe interceptarse")
    print("  (se manda 'si' con un JID al que se le borro la cita)")
    sql(f"DELETE FROM barber_citas WHERE id = '{CITA}';")
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca2 = int(ex["data"][0]["id"]) if ex.get("data") else 0
    mid2 = "T" + uuid.uuid4().hex[:10].upper()
    print(f"  -> HTTP {enviar('si', mid2)}")
    time.sleep(30)

    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=6")
    fue_al_modelo = False
    for e in ex.get("data", []):
        if int(e["id"]) <= marca2:
            continue
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "AI Agent" in run:
            fue_al_modelo = True
            try:
                sal = run["Es confirmacion?"][0]["data"]["main"][0][0]["json"]
                print(f"  el detector dijo: decision={sal.get('decision')} "
                      f"es_respuesta={sal.get('es_respuesta_confirmacion')}")
            except Exception:
                pass
        break
    print(f"  ¿siguio al agente? {'SI (correcto)' if fue_al_modelo else 'NO (se lo trago)'}")

    # ---------------------------------------------------------------- 4
    print("\n[4] LIMPIEZA")
    sql(f"DELETE FROM barber_citas WHERE id = '{CITA}';")
    n = sql(f"SELECT count(*) FROM barber_citas WHERE id='{CITA}';")
    print(f"  cita de prueba borrada: {n} restantes (debe ser 0)")
    print(f"  citas totales: {sql('SELECT count(*) FROM barber_citas;')}")
    print(f"  de las cuales verif-: "
          f"{sql(chr(34)+'SELECT count(*) FROM barber_citas WHERE id LIKE ' + chr(39) + 'verif-%' + chr(39) + chr(34))}")

    print()
    print("=" * 68)
    ok = (estado1 == "confirmado")
    print(f"RESULTADO: el bucle {'CIERRA correctamente' if ok else 'NO cierra'}")
    print("=" * 68)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())