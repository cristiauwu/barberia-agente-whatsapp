#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el formato del gid en los nodos de Sheets.

BUG DE N8N: la funcion getSheetId() es
    if (value === 'gid=0') return 0;
    return parseInt(value);
Con 'gid=941506024' -> parseInt devuelve NaN -> "Sheet with ID ... not found".
Solo el gid 0 funciona, por el caso especial.

SOLUCION: usar el gid en crudo, sin el prefijo 'gid='.
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
GID_LIMPIO = "941506024"
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


def main():
    for wid in WIDS:
        print("=" * 74)
        print("WORKFLOW:", wid)
        print("=" * 74)
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print("  no se pudo leer:", st)
            continue
        activo = wf.get("active")

        bk = rf"G:\Barberia\archivos\ANTES-gid-{wid}.json"
        json.dump(wf, open(bk, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

        cambios = 0
        for n in wf.get("nodes", []):
            if "googleSheet" not in n.get("type", ""):
                continue
            hoja = n["parameters"].get("sheetName")
            if not isinstance(hoja, dict):
                continue
            antes = hoja.get("value")
            if antes != GID_LIMPIO:
                hoja["value"] = GID_LIMPIO
                hoja["mode"] = "list"
                hoja["cachedResultName"] = "Hoja 1"
                hoja.pop("cachedResultUrl", None)
                print(f"  {n['name']:<36} {antes!r} -> {GID_LIMPIO!r}")
                cambios += 1

        if not cambios:
            print("  (ya estaba correcto)")
            continue

        if activo:
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
        if activo:
            st3, r3 = api("POST", f"/workflows/{wid}/activate", {})
            print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")
        print()

    # Verificacion
    print("=" * 74)
    print("VERIFICACION")
    print("=" * 74)
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            continue
        for n in wf.get("nodes", []):
            if "googleSheet" not in n.get("type", ""):
                continue
            v = (n["parameters"].get("sheetName") or {}).get("value")
            ok = v == GID_LIMPIO
            print(f"  {'OK  ' if ok else 'MAL '} {n['name']:<36} {v!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())