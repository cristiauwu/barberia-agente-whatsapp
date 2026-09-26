#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla la causa raíz de los 4 comandos que no respondían.

DIAGNÓSTICO (ejecuciones 635 y 639):
  - HOY / SEMANA / LIBRE: el nodo 'Leer agenda del rango' devolvía 0 items
    (no hay citas), y n8n CORTA la ejecución cuando un nodo no produce
    salida. El flujo nunca llegaba a 'Formatear agenda' ni a responder.
  - CLIENTE: igual, 'Leer ficha del cliente' devolvía 0 filas.

Es el comportamiento por defecto de n8n: si un nodo no emite items, los
nodos siguientes no se ejecutan.

SOLUCIÓN: marcar esos nodos con `alwaysOutputData: true`, que hace que n8n
emita un item vacío en vez de cortar la cadena. Así el nodo formateador
corre siempre y puede decir "no hay citas" en lugar de quedarse callado.
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

# Nodos que pueden devolver 0 filas legítimamente y deben seguir el flujo
NODOS = [
    "Leer agenda del rango",      # sin citas -> 0 eventos
    "Leer ficha del cliente",     # cliente no encontrado -> 0 filas
    "Aplicar pausa",              # cliente inexistente -> 0 filas
    "Actualizar precio",          # clave inválida -> 0 filas
    "Leer estado del sistema",    # siempre devuelve 1 fila, pero por si acaso
    "Leer operadores",            # si no hay operadores, no debe romper
]


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-alwaysoutput.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    cambios = 0
    for n in wf["nodes"]:
        if n["name"] in NODOS:
            n["alwaysOutputData"] = True
            cambios += 1
            print(f"  {n['name']:<30} alwaysOutputData = true")

    if not cambios:
        print("  (sin cambios)")
        return 0

    # Verificar que TODOS los nodos esperados existan
    faltan = [x for x in NODOS
              if not any(n["name"] == x for n in wf["nodes"])]
    if faltan:
        print(f"  AVISO: no existen estos nodos: {faltan}")

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
    for x in NODOS:
        n = next((n for n in fin["nodes"] if n["name"] == x), None)
        if not n:
            continue
        ok = n.get("alwaysOutputData") is True
        print(f"  {'OK  ' if ok else 'MAL '}{x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())