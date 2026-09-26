#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reapunta los 4 nodos de Google Calendar al calendario BARBER del usuario.

Antes: 391cc272...@group.calendar.google.com  (del vendedor, no accesible)
Ahora: b5e08030...@group.calendar.google.com  (del usuario, crir627@gmail.com)
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
WID = "barberiaAgenteUncensored"

NUEVO_CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
             "09143c@group.calendar.google.com")
VIEJO_CAL = ("391cc272be5989fd77b45438f2f61e9c754501eb5d1b3a4a76d57a9da"
             "3083918@group.calendar.google.com")
NOMBRE = "BARBER"


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
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st, wf)
        return 1
    estaba_activo = wf.get("active")

    # Respaldo
    bk = rf"G:\Barberia\archivos\ANTES-calendario-{WID}.json"
    json.dump(wf, open(bk, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"respaldo: {os.path.basename(bk)}\n")

    cambios = 0
    for n in wf["nodes"]:
        if "googleCalendar" not in n.get("type", ""):
            continue
        cal = n["parameters"].setdefault("calendar", {})
        antes = cal.get("value")
        cal["value"] = NUEVO_CAL
        cal["mode"] = "list"
        cal["cachedResultName"] = NOMBRE
        cal.pop("cachedResultUrl", None)
        print(f"  {n['name']:<20} {antes[:40]}... -> {NUEVO_CAL[:40]}...")
        cambios += 1

    if not cambios:
        print("  (sin nodos de Calendar)")
        return 0

    if estaba_activo:
        api("POST", f"/workflows/{WID}/deactivate", {})

    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1

    if estaba_activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificacion
    st4, fin = api("GET", f"/workflows/{WID}")
    print("\n=== VERIFICACION ===")
    for n in fin["nodes"]:
        if "googleCalendar" in n.get("type", ""):
            v = n["parameters"]["calendar"].get("value")
            print(f"  {'OK  ' if v == NUEVO_CAL else 'MAL '} {n['name']:<20} "
                  f"{n['parameters']['calendar'].get('cachedResultName')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())