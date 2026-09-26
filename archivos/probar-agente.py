#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simula un mensaje entrante de WhatsApp (payload de Evolution API) contra el
webhook de n8n, para comprobar que el agente responde de verdad.

No escribe nada en disco salvo el resultado de la prueba.
"""
import json
import os
import subprocess
import sys
import urllib.request
import uuid

WEBHOOK = "http://localhost:5678/webhook/hector"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def payload(texto, apikey, jid="5214501111805@s.whatsapp.net"):
    """Estructura de un mensaje de Evolution API (messages.upsert).

    OJO: server_url debe ser el nombre interno del contenedor
    (evolution_api), porque quien lo consume es el contenedor de n8n.
    'localhost' alli apunta a n8n mismo -> ECONNREFUSED.
    """
    mid = "TEST" + uuid.uuid4().hex[:12].upper()
    return {
        "event": "messages.upsert",
        "instance": "hector",
        "server_url": "http://evolution_api:8080",
        "apikey": apikey,
        "date_time": "2026-09-25T01:00:00.000Z",
        "data": {
            "key": {"id": mid, "remoteJid": jid, "fromMe": False},
            "pushName": "Cliente Prueba",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }


def enviar(texto, apikey):
    body = json.dumps(payload(texto, apikey)).encode()
    req = urllib.request.Request(WEBHOOK, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read().decode()[:600]
    except Exception as e:
        code = getattr(e, "code", None)
        return code, str(e)[:400]


def apikey_de_evolution():
    """Lee la API key real de Evolution para que la prueba sea fiel."""
    p = subprocess.run(
        [DOCKER, "exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def ejecuciones_recientes(n=5):
    """Ultimas ejecuciones del workflow, para ver si fallaron."""
    p = subprocess.run(
        [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
         "-d", "barberia", "-t", "-A", "-c",
         f"""SELECT COALESCE(string_agg(x, E'\\n'), '(sin ejecuciones)') FROM (
               SELECT e.id || ' | ' || e.status || ' | ' ||
                 COALESCE(e."stoppedAt"::text,'-') AS x
               FROM execution_entity e
               ORDER BY e.id DESC LIMIT {n}) s;"""],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def error_de(exec_id):
    p = subprocess.run(
        [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
         "-d", "barberia", "-t", "-A", "-c",
         f"""SELECT left(regexp_replace(ed."data"::text,
               '.*"error"\\s*:\\s*\\{{[^}}]*"message"\\s*:\\s*"([^"]*)".*',
               '\\1'), 300)
             FROM execution_data ed WHERE ed."executionId" = {exec_id};"""],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def main():
    apikey = apikey_de_evolution()
    if not apikey:
        print("No pude leer la API key de Evolution")
        return 1
    print("Usando la API key real de Evolution (no se imprime).")

    casos = [
        "Hola, quiero un corte manana a las 4 de la tarde, me llamo Juan",
        "cuanto cuesta el corte de dama?",
    ]
    print("=" * 74)
    print("PRUEBA DEL AGENTE (mensajes simulados de WhatsApp)")
    print("=" * 74)
    for i, c in enumerate(casos, 1):
        print(f"\n--- CASO {i} ---")
        print("CLIENTE:", c)
        st, body = enviar(c, apikey)
        print("webhook ->", st)
        print("respuesta:", (body or "")[:300])

    print()
    print("=" * 74)
    print("EJECUCIONES EN N8N")
    print("=" * 74)
    print(ejecuciones_recientes())

    # Si la ultima fallo, mostrar el error
    ejec = ejecuciones_recientes(1)
    if ejec:
        try:
            eid = int(ejec.split("|")[0].strip())
            estado = ejec.split("|")[1].strip()
            if estado != "success":
                print("\n>>> ERROR DE LA ULTIMA EJECUCION:")
                print(error_de(eid))
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())