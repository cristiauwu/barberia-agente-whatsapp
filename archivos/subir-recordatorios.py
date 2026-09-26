#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sube el workflow de recordatorios corregido a n8n por la API.

Preserva las credenciales existentes y reactiva el workflow si estaba activo.
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
ARCHIVO = r"G:\Barberia\BarberiaAgenteFLUJO-2-RECORDATORIOS.json"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return None, str(e)


def main():
    # 1. Estado actual
    st, actual = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("No pude leer el workflow:", st, actual)
        return 1
    estaba_activo = actual.get("active")
    print(f"  estado actual: active={estaba_activo}")

    # Respaldo
    json.dump(actual, open(r"G:\Barberia\archivos\ANTES-w2.json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)

    # 2. Leer el archivo corregido
    d = json.load(open(ARCHIVO, encoding="utf-8"))
    nuevo = d[0] if isinstance(d, list) else d
    print(f"  archivo: {len(nuevo['nodes'])} nodos, "
          f"{len(nuevo['connections'])} conexiones")

    # 3. Desactivar para poder actualizar
    if estaba_activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
        print("  desactivado temporalmente")

    # 4. Subir (PUT reemplaza nodos y conexiones)
    st, res = api("PUT", f"/workflows/{WID}", {
        "name": nuevo["name"],
        "nodes": nuevo["nodes"],
        "connections": nuevo["connections"],
        "settings": actual.get("settings", {}),
    })
    print(f"  PUT -> HTTP {st}")
    if st not in (200, 201):
        print("  detalle:", str(res)[:400])
        return 1

    # 5. Reactivar
    if estaba_activo:
        st2, res2 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st2} active={res2.get('active')}")

    # 6. Confirmar
    st3, fin = api("GET", f"/workflows/{WID}")
    print(f"\n  RESULTADO: {len(fin['nodes'])} nodos, "
          f"{len(fin['connections'])} conexiones, active={fin.get('active')}")

    destinos = set()
    for ramas in fin["connections"].values():
        for salidas in ramas.values():
            for g in salidas:
                for c in g:
                    destinos.add(c["node"])
    huerfanos = [n["name"] for n in fin["nodes"]
                 if n["name"] not in destinos and "Trigger" not in n["type"]]
    print("  nodos sin entrada:", huerfanos or "(ninguno)")
    return 0


if __name__ == "__main__":
    sys.exit(main())