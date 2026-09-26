#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CRITICO: reapunta los nodos de recordatorio al Evolution LOCAL.

PROBLEMA ENCONTRADO:
  Los 3 nodos de envio del flujo 2 (Notificar cita nueva al encargado,
  RECORDATORIO 24 H, RECORDATORIO 1 H) apuntan a:
      https://makewhatsapp-evolution-api.1takfl.easypanel.host/...
  y llevan la API key del VENDEDOR en texto plano (CLAVE_DEL_PROVEEDOR-...).

  Consecuencias:
    - Los recordatorios salen por el servidor de un tercero.
    - Ese tercero ve nombre, telefono y cita de cada cliente.
    - Depende de que su servidor siga vivo (si lo apaga, tus avisos mueren).
    - La clave es suya y puede revocarla cuando quiera.

SOLUCION:
  Apuntar al Evolution LOCAL por el nombre interno de Docker
  (http://evolution_api:8080) y usar la credencial httpHeaderAuth con la
  clave propia, ya creada.

Nota: el flujo 2 se dispara desde Google Sheets (no desde Evolution), asi
que no tiene el nodo Normalizacion con instance_server_url. Por eso se usa
la URL interna fija, que es la correcta para este entorno Docker.
"""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaRecordatorios"
EVO_LOCAL = "http://evolution_api:8080"
INSTANCIA = "hector"
NODO_AVISO = "Notificar cita nueva al encargado"


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


def cred_evolution():
    """Busca el id de la credencial 'Evolution API'."""
    st, creds = api("GET", "/credentials")
    if st != 200:
        return None
    for c in creds.get("data", []):
        if c.get("name") == "Evolution API":
            return c["id"]
    return None


def main():
    cred_id = cred_evolution()
    if not cred_id:
        print("no encontre la credencial 'Evolution API'")
        return 1
    print(f"credencial Evolution API: {cred_id}")

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-evo-local.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    cambios = 0
    for n in wf["nodes"]:
        if "httpRequest" not in n["type"]:
            continue
        p = n["parameters"]
        url = p.get("url", "")
        if "easypanel.host" not in url:
            continue

        # Reconstruir la URL con el Evolution local
        sufijo = url.split("easypanel.host", 1)[1]  # /message/sendText/hector
        p["url"] = EVO_LOCAL + sufijo
        p["method"] = "POST"
        p["sendHeaders"] = True
        # Quitar el header literal con la clave del vendedor
        p["headerParameters"] = {"parameters": []}
        p["authentication"] = "genericCredentialType"
        p["genericAuthType"] = "httpHeaderAuth"
        n.setdefault("credentials", {})["httpHeaderAuth"] = {
            "id": cred_id, "name": "Evolution API"}
        # Quitar credenciales que ya no aplican
        for c in list(n.get("credentials", {}).keys()):
            if c != "httpHeaderAuth":
                n["credentials"].pop(c, None)
        n.pop("notes", None)
        cambios += 1
        print(f"  {n['name']}:")
        print(f"     url -> {p['url']}")
        print(f"     usa credencial, sin clave en claro")

    if not cambios:
        print("  (sin cambios)")
        return 0

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificacion final
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    txt = json.dumps(fin, ensure_ascii=False)
    print(f"  {'OK  ' if 'easypanel.host' not in txt else 'MAL '} "
          f"sin referencias al servidor del vendedor")
    print(f"  {'OK  ' if 'CLAVE_DEL_PROVEEDOR' not in txt else 'MAL '} "
          f"sin la clave del vendedor")
    for n in fin["nodes"]:
        if "httpRequest" in n["type"] and "message/sendText" in str(
                n["parameters"].get("url", "")):
            print(f"  {n['name']} -> {n['parameters']['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())