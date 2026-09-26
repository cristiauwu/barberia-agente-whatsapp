#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reapunta los nodos de Google Sheets a la hoja nueva del usuario.

Cambia el documentId y el sheetName en TODOS los nodos que tocan la hoja,
en los dos workflows, preservando las credenciales existentes.

Antes: 17iqMoba... (hoja del vendedor, no accesible)
Ahora: 1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk (hoja del usuario)
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")

NUEVO_ID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
NUEVO_GID = "941506024"
NUEVO_NOMBRE = "Citas barbería"
VIEJO_ID = "17iqMobaQBz29tZ5pP5Q9ejzSJUfkov8lkjB245vpoZY"

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


def reapuntar(wf):
    """Cambia el documento/hoja en todos los nodos de Sheets."""
    cambios = []
    for n in wf.get("nodes", []):
        t = n.get("type", "")
        if "googleSheet" not in t:
            continue
        p = n.setdefault("parameters", {})

        doc = p.get("documentId")
        if isinstance(doc, dict):
            antes = doc.get("value")
            doc["value"] = NUEVO_ID
            doc["mode"] = "list"
            doc["cachedResultName"] = NUEVO_NOMBRE
            doc.pop("cachedResultUrl", None)
            cambios.append(f"    {n['name']}: doc {antes} -> {NUEVO_ID}")

        hoja = p.get("sheetName")
        if isinstance(hoja, dict):
            antes = hoja.get("value")
            hoja["value"] = f"gid={NUEVO_GID}"
            hoja["mode"] = "list"
            hoja["cachedResultName"] = "Hoja 1"
            hoja.pop("cachedResultUrl", None)
            cambios.append(f"    {n['name']}: hoja {antes} -> gid={NUEVO_GID}")
    return cambios


def main():
    for wid in WIDS:
        print("=" * 74)
        print("WORKFLOW:", wid)
        print("=" * 74)

        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print("  no se pudo leer:", st, wf)
            continue
        estaba_activo = wf.get("active")

        # Respaldo
        bk = rf"G:\Barberia\archivos\ANTES-reapuntar-{wid}.json"
        json.dump(wf, open(bk, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"  respaldo: {os.path.basename(bk)}")

        cambios = reapuntar(wf)
        if not cambios:
            print("  (sin nodos de Sheets que cambiar)")
            continue
        for c in cambios:
            print(c)

        # Desactivar si hacia falta, para poder actualizar
        if estaba_activo:
            api("POST", f"/workflows/{wid}/deactivate", {})

        st2, res = api("PUT", f"/workflows/{wid}", {
            "name": wf["name"],
            "nodes": wf["nodes"],
            "connections": wf["connections"],
            "settings": wf.get("settings", {}),
        })
        print(f"  PUT -> HTTP {st2}")
        if st2 not in (200, 201):
            print("  detalle:", str(res)[:300])
            continue

        if estaba_activo:
            st3, r3 = api("POST", f"/workflows/{wid}/activate", {})
            print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")
        print()

    # Verificacion final
    print("=" * 74)
    print("VERIFICACION: a que documento apunta cada nodo ahora")
    print("=" * 74)
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            continue
        for n in wf.get("nodes", []):
            if "googleSheet" not in n.get("type", ""):
                continue
            doc = (n.get("parameters", {}).get("documentId") or {})
            hoja = (n.get("parameters", {}).get("sheetName") or {})
            ok = doc.get("value") == NUEVO_ID
            print(f"  {'OK  ' if ok else 'MAL '} {n['name']:<36} "
                  f"{doc.get('cachedResultName')} | {hoja.get('value')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())