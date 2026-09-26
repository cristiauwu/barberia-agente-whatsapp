#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el DESTINO de las notificaciones al barbero.

PROBLEMA ENCONTRADO:
  Los nodos que avisan al encargado mandan el WhatsApp al número
  5215520894522 (el del VENDEDOR). Ni el dueño ni el barbero reciben
  nada: los avisos de "nueva cita" y las escalaciones se van a un
  tercero.

CORRECCIÓN:
  Se apunta al número del dueño (524521206246), que es la fuente de
  verdad que dio el usuario.

NOTA IMPORTANTE: el número del DESTINO debe ser el que WhatsApp espera
para entregar el mensaje. Evolution/A baileys normalmente quiere el JID
con el formato tal como está registrado; se usa el mismo formato que
usaba el flujo original (52+10 dígitos, sin el "1").
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
VIEJO = "5215520894522@s.whatsapp.net"
NUEVO = "524521206246@s.whatsapp.net"
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


def reemplazar(o):
    """Sustituye el número viejo por el nuevo en cualquier profundidad."""
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and VIEJO in v:
                o[k] = v.replace(VIEJO, NUEVO)
                n += 1
            else:
                n += reemplazar(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and VIEJO in v:
                o[i] = v.replace(VIEJO, NUEVO)
                n += 1
            else:
                n += reemplazar(v)
    return n


def main():
    print(f"destino viejo (vendedor): {VIEJO}")
    print(f"destino nuevo (dueño)   : {NUEVO}")
    print()
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print(f"  {wid}: no se pudo leer")
            continue
        activo = wf.get("active")
        json.dump(wf, open(rf"G:\Barberia\archivos\ANTES-destino-{wid}.json",
                           "w", encoding="utf-8"), ensure_ascii=False, indent=2)

        cambios = 0
        for n in wf["nodes"]:
            c = reemplazar(n["parameters"])
            if c:
                print(f"  {wid} :: {n['name']}: {c} valor(es)")
                cambios += c

        if not cambios:
            print(f"  {wid}: sin cambios")
            continue

        if activo:
            api("POST", f"/workflows/{wid}/deactivate", {})
        st2, res = api("PUT", f"/workflows/{wid}", {
            "name": wf["name"], "nodes": wf["nodes"],
            "connections": wf["connections"],
            "settings": wf.get("settings", {}),
        })
        print(f"  {wid} PUT -> HTTP {st2}")
        if st2 not in (200, 201):
            print("  detalle:", str(res)[:300])
            continue
        if activo:
            api("POST", f"/workflows/{wid}/activate", {})
            print(f"  {wid} reactivado")

    print()
    print("=== VERIFICACION ===")
    ok_total = True
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            continue
        txt = json.dumps(wf, ensure_ascii=False)
        viejo = txt.count(VIEJO)
        nuevo = txt.count(NUEVO)
        ok = viejo == 0
        ok_total = ok_total and ok
        print(f"  {'OK  ' if ok else 'MAL '}{wid}: "
              f"vendedor={viejo}  dueño={nuevo}")
    return 0 if ok_total else 1


if __name__ == "__main__":
    sys.exit(main())