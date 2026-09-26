#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CRITICO: reapunta los nodos de Sheets del flujo 2 a TU hoja.

BUG ENCONTRADO (5 ejecuciones fallidas con 'Forbidden'):
  El nodo 'Append or update row in sheet' del flujo de recordatorios
  apuntaba a la hoja VIEJA del vendedor:
      documentId = 17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY
  En vez de a la del usuario:
      documentId = 1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk
  Por eso Google respondia "The caller does not have permission":
  el usuario no tiene acceso a la hoja del vendedor.

  CONSECUENCIA REAL: los recordatorios NUNCA funcionaron. El flujo moria
  en ese nodo, asi que ni se actualizaba la hoja ni se llegaba a los
  recordatorios de 24 h y 1 h.

Tambien se revisa el nodo 'OBTENER INFO DE CITA ELIMINADA'.
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
HOJA_OK = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
HOJA_OK_NOMBRE = "Citas barbería"
HOJA_MALA = "17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY"
GID = "941506024"


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
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-hoja-f2.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    cambios = 0
    for n in wf["nodes"]:
        if "googleSheets" not in n["type"]:
            continue
        p = n["parameters"]
        doc = p.get("documentId")
        if not isinstance(doc, dict):
            continue
        antes = doc.get("value")
        if antes == HOJA_OK:
            print(f"  {n['name']:<34} ya apunta a tu hoja")
            continue
        doc["value"] = HOJA_OK
        doc["mode"] = "list"
        doc["cachedResultName"] = HOJA_OK_NOMBRE
        doc.pop("cachedResultUrl", None)
        # El nombre de la pestaña debe ser el gid en crudo
        hoja = p.get("sheetName")
        if isinstance(hoja, dict):
            hoja["value"] = GID
            hoja["mode"] = "list"
            hoja["cachedResultName"] = "Hoja 1"
            hoja.pop("cachedResultUrl", None)
        print(f"  {n['name']:<34} {antes[:24] if antes else '(vacio)'}... "
              f"-> tu hoja")
        cambios += 1

    if not cambios:
        print("sin cambios")
        return 0

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\nPUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    txt = json.dumps(fin, ensure_ascii=False)
    print(f"  {'OK  ' if HOJA_MALA not in txt else 'MAL '} "
          f"sin la hoja vieja del vendedor")
    for n in fin["nodes"]:
        if "googleSheets" in n["type"]:
            doc = (n["parameters"].get("documentId") or {}).get("value", "?")
            hoja = (n["parameters"].get("sheetName") or {}).get("value", "?")
            ok = doc == HOJA_OK
            print(f"  {'OK  ' if ok else 'MAL '}{n['name']:<34} "
                  f"doc={doc[:22]}... gid={hoja}")
    return 0


if __name__ == "__main__":
    sys.exit(main())