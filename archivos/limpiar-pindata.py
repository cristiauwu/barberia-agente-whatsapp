#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpia el pinData de los workflows, que aun guarda datos del vendedor.

`pinData` son datos de prueba que n8n guarda en el workflow. Los nuestros
venian del flujo original y contienen la API key del vendedor y otros
datos de su entorno. No se usan para nada en produccion.

Ademas se revisa el historial de versiones (workflow_history) de n8n,
que puede guardar copias antiguas con la clave.
"""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
WIDS = ["barberiaAgenteUncensored", "barberiaRecordatorios"]


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    # --- 1. limpiar pinData ------------------------------------------
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print(f"  {wid}: no se pudo leer")
            continue
        activo = wf.get("active")
        tenia = bool(wf.get("pinData"))

        if activo:
            api("POST", f"/workflows/{wid}/deactivate", {})
        st2, _ = api("PUT", f"/workflows/{wid}", {
            "name": wf["name"],
            "nodes": wf["nodes"],
            "connections": wf["connections"],
            "settings": wf.get("settings", {}),
            "pinData": {},            # <-- esto limpia los datos de prueba
        })
        print(f"  {wid}: pinData {'limpiado' if tenia else 'ya estaba vacio'} "
              f"(PUT {st2})")
        if activo:
            api("POST", f"/workflows/{wid}/activate", {})

    # --- 2. revisar el historial de versiones ------------------------
    print("\n=== HISTORIAL DE VERSIONES (puede guardar la clave) ===")
    for wid in WIDS:
        n = psql(f"""SELECT count(*) FROM workflow_history
                     WHERE "workflowId" = '{wid}';""")
        conc = psql(f"""SELECT count(*) FROM workflow_history
                        WHERE "workflowId" = '{wid}'
                        AND nodes::text LIKE '%DC64CCC%';""")
        print(f"  {wid}: {n} versiones guardadas, "
              f"{conc} contienen la clave del vendedor")

    # --- 3. verificar ------------------------------------------------
    print("\n=== VERIFICACION FINAL ===")
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            continue
        txt = json.dumps(wf, ensure_ascii=False)
        print(f"  {wid}:")
        print(f"    clave del vendedor: "
              f"{'SI <-- problema' if 'DC64CCC' in txt else 'no'}")
        print(f"    servidor del vendedor: "
              f"{'SI <-- problema' if 'easypanel.host' in txt else 'no'}")
        print(f"    active={wf.get('active')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())