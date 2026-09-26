#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integra los nodos de comandos en el workflow del agente.

ENRUTADO FINAL del router (12 comandos + fallback):
   0 HOY        -> Preparar rango de fechas
   1 MAÑANA     -> Preparar rango de fechas (mismo nodo)
   2 SEMANA     -> Preparar rango de fechas
   3 LIBRE      -> Preparar rango de fechas
   4 CLIENTE    -> Buscar cliente
   5 BLOQUEAR   -> Parsear bloqueo
   6 CERRAR     -> Parsear bloqueo
   7 ABRIR      -> Parsear bloqueo
   8 PRECIO     -> Parsear precio
   9 PAUSA      -> Parsear pausa
  10 ESTADO     -> Leer estado del sistema
  11 COMANDOS   -> Armar respuesta COMANDOS
  12 fallback   -> IF - No es del bot   (sigue al agente normal)

Todos los caminos que responden terminan en "Responder al operador".
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
GEN = r"G:\Barberia\archivos\generar-nodos-agenda.py"
RESPONDER = "Responder al operador"


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
    import importlib.util
    spec = importlib.util.spec_from_file_location("genag", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    nuevos = mod.construir()["nodes"]
    print(f"nodos a integrar: {len(nuevos)}")

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-comandos-agenda.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    existentes = {n["name"] for n in wf["nodes"]}
    for n in nuevos:
        if n["name"] in existentes:
            wf["nodes"] = [x for x in wf["nodes"] if x["name"] != n["name"]]
        wf["nodes"].append(n)
    print(f"nodos totales: {len(wf['nodes'])}")

    c = wf["connections"]

    def uno(nodo):
        return [{"node": nodo, "type": "main", "index": 0}]

    # --- Router: 12 salidas + fallback --------------------------------
    orden = ["HOY", "MAÑANA", "SEMANA", "LIBRE", "CLIENTE", "BLOQUEAR",
             "CERRAR", "ABRIR", "PRECIO", "PAUSA", "ESTADO", "COMANDOS"]
    destino = {
        "HOY": "Preparar rango de fechas",
        "MAÑANA": "Preparar rango de fechas",
        "SEMANA": "Preparar rango de fechas",
        "LIBRE": "Preparar rango de fechas",
        "CLIENTE": "Buscar cliente",
        "BLOQUEAR": "Parsear bloqueo",
        "CERRAR": "Parsear bloqueo",
        "ABRIR": "Parsear bloqueo",
        "PRECIO": "Parsear precio",
        "PAUSA": "Parsear pausa",
        "ESTADO": "Leer estado del sistema",
        "COMANDOS": "Armar respuesta COMANDOS",
    }
    salidas = [uno(destino[cmd]) for cmd in orden]
    salidas.append(uno("IF - No es del bot"))   # fallback
    c["Router de comandos"] = {"main": salidas}

    # --- Cadenas ------------------------------------------------------
    c["Preparar rango de fechas"] = {"main": [uno("Leer agenda del rango")]}
    c["Leer agenda del rango"] = {"main": [uno("Formatear agenda")]}
    c["Formatear agenda"] = {"main": [uno(RESPONDER)]}

    # BLOQUEAR/CERRAR/ABRIR: el parseo puede fallar -> IF
    c["Parsear bloqueo"] = {"main": [uno("IF - Bloqueo invalido")]}
    c["IF - Bloqueo invalido"] = {"main": [
        uno("Respuesta de bloqueo"),          # true: invalido -> ayuda
        uno("Crear bloqueo en calendario"),   # false: valido  -> Calendar
    ]}
    c["Respuesta de bloqueo"] = {"main": [uno(RESPONDER)]}
    c["Crear bloqueo en calendario"] = {"main": [uno("Confirmar bloqueo")]}
    c["Confirmar bloqueo"] = {"main": [uno(RESPONDER)]}

    c["Buscar cliente"] = {"main": [uno("Leer ficha del cliente")]}
    c["Leer ficha del cliente"] = {"main": [uno("Formatear ficha")]}
    c["Formatear ficha"] = {"main": [uno(RESPONDER)]}

    c["Parsear pausa"] = {"main": [uno("Aplicar pausa")]}
    c["Aplicar pausa"] = {"main": [uno("Formatear pausa")]}
    c["Formatear pausa"] = {"main": [uno(RESPONDER)]}

    c["Parsear precio"] = {"main": [uno("Actualizar precio")]}
    c["Actualizar precio"] = {"main": [uno("Formatear precio")]}
    c["Formatear precio"] = {"main": [uno(RESPONDER)]}

    c["Leer estado del sistema"] = {"main": [uno("Formatear estado")]}
    c["Formatear estado"] = {"main": [uno(RESPONDER)]}

    # --- Nodo extra: confirmación del bloqueo -------------------------
    if not any(n["name"] == "Confirmar bloqueo" for n in wf["nodes"]):
        from uuid import uuid4
        wf["nodes"].append({
            "parameters": {"assignments": {"assignments": [{
                "id": str(uuid4()), "name": "respuesta",
                "value": "={{ $('Parsear bloqueo').first().json.ok_msg }}",
                "type": "string"}]}, "options": {}},
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [-120, 660],
            "id": str(uuid4()),
            "name": "Confirmar bloqueo",
            "notes": "Confirma el bloqueo ya creado en el calendario.",
            "notesInFlow": True,
        })

    print("\nenrutado configurado")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": c, "settings": wf.get("settings", {}),
    })
    print(f"PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:400])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # --- Verificacion -------------------------------------------------
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    nombres = {n["name"] for n in fin["nodes"]}
    for n in nuevos:
        if n["name"] not in nombres:
            print(f"  MAL  falta '{n['name']}'")

    destinos = set()
    for ramas in fin["connections"].values():
        for sal in ramas.values():
            for g in sal:
                for x in g:
                    destinos.add(x["node"])

    fuente_ai = set()
    for src, ramas in fin["connections"].items():
        for tipo in ramas:
            if tipo != "main":
                fuente_ai.add(src)
    ai_dest = set()
    for ramas in fin["connections"].values():
        for tipo, sal in ramas.items():
            if tipo != "main":
                for g in sal:
                    for x in g:
                        ai_dest.add(x["node"])

    huerfanos = []
    for n in fin["nodes"]:
        nm, t = n["name"], n["type"]
        if nm in destinos:
            continue
        if ("Trigger" in t or t.endswith(".webhook") or "manualTrigger" in t
                or nm in fuente_ai or nm in ai_dest):
            continue
        huerfanos.append(nm)
    print(f"  {'OK  ' if not huerfanos else 'MAL '} nodos huerfanos reales: "
          f"{huerfanos or 'ninguno'}")
    print(f"  {'OK  ' if 'DC64CCC' not in json.dumps(fin) else 'MAL '} "
          f"sin la clave del vendedor")

    # Cada rama debe llegar a Responder
    print("\n  rutas hacia el dueño:")
    for cmd in orden:
        i = orden.index(cmd)
        d = salidas[i]
        print(f"    {cmd:<9} -> {d[0]['node']}")
    print(f"    {'(fallback)':<9} -> {salidas[12][0]['node']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())