#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integra el router de comandos del dueño en el flujo del agente.

DISENO DEL ENRUTADO (lo mas delicado):

    Normalizacion
      -> ¿Es operador?  (IF)
           true  -> Router de comandos
                      COMANDOS ------> Armar respuesta -> Responder
                      otras salidas --> Comando pendiente -> Responder
                      No es comando --> IF - No es del bot   (sigue normal)
           false -> IF - No es del bot                        (cliente normal)

Puntos clave para NO romper nada:
  1. Un CLIENTE nunca entra al router: va directo al flujo de siempre.
  2. El DUEÑO que escribe algo que no es comando (ej. "hola") cae al
     fallback y sigue al agente normal. No se pierde su mensaje.
  3. Los comandos aun no implementados responden "en construccion" en vez
     de dejar al dueño en silencio.
  4. El nodo de respuesta usa la CREDENCIAL Evolution API, no la clave
     del payload.
"""
import importlib.util
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
GENERADOR = r"G:\Barberia\archivos\generar-nodos-comandos.py"
CRED_EVO = r"G:\Barberia\.env.evolution"

# Comandos que YA tienen implementacion (el resto responde "pendiente")
IMPLEMENTADOS = {"COMANDOS"}


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
    st, creds = api("GET", "/credentials")
    for c in creds.get("data", []):
        if c.get("name") == "Evolution API":
            return c["id"]
    return None


def cargar_generador():
    """Importa el archivo del subagente y devuelve construir_nodos()."""
    spec = importlib.util.spec_from_file_location("gencmd", GENERADOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.construir_nodos()


def main():
    cred_id = cred_evolution()
    if not cred_id:
        print("no encontre la credencial 'Evolution API'")
        return 1

    piezas = cargar_generador()
    nodos_nuevos = piezas["nodes"]
    print(f"nodos del generador: {len(nodos_nuevos)}")

    # --- Ajustes sobre lo generado ------------------------------------
    # 1. El nodo de respuesta usa credencial en vez de la clave del payload
    responder = next(n for n in nodos_nuevos
                     if n["name"] == "Responder al operador")
    responder["parameters"]["headerParameters"] = {"parameters": []}
    responder["parameters"]["authentication"] = "genericCredentialType"
    responder["parameters"]["genericAuthType"] = "httpHeaderAuth"
    responder.setdefault("credentials", {})["httpHeaderAuth"] = {
        "id": cred_id, "name": "Evolution API"}

    # 2. Nodo extra: respuesta para comandos aun no implementados
    nodo_pendiente = {
        "parameters": {
            "assignments": {"assignments": [{
                "id": "pendiente0001",
                "name": "respuesta",
                "value": ("=🚧 El comando *{{ $json.message_content.trim()"
                          ".toUpperCase().split(' ')[0] }}* todavía no está "
                          "activo.\n\nEscribe *COMANDOS* para ver los que sí "
                          "funcionan."),
                "type": "string",
            }]},
            "options": {},
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [-100, 260],
        "id": "setcomandopendiente0000000000001",
        "name": "Comando pendiente",
        "notes": ("Se alcanza cuando el dueño manda un comando válido que\n"
                  "todavía no tiene implementación. Evita el silencio."),
        "notesInFlow": True,
    }
    nodos_nuevos.append(nodo_pendiente)

    # --- Fusionar con el workflow --------------------------------------
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer el workflow:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-comandos.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)
    print("respaldo: ANTES-comandos.json")

    existentes = {n["name"] for n in wf["nodes"]}
    for n in nodos_nuevos:
        if n["name"] in existentes:
            print(f"  ya existia: {n['name']} (se reemplaza)")
            wf["nodes"] = [x for x in wf["nodes"] if x["name"] != n["name"]]
        wf["nodes"].append(n)
    print(f"nodos totales ahora: {len(wf['nodes'])}")

    # --- Enrutado ------------------------------------------------------
    c = wf["connections"]
    nombre_router = "Router de comandos"

    # Orden de salidas del router (el generador las dejo en este orden)
    orden = ["HOY", "MAÑANA", "SEMANA", "LIBRE", "CLIENTE", "BLOQUEAR",
             "CERRAR", "ABRIR", "PRECIO", "PAUSA", "ESTADO", "COMANDOS"]

    salidas = []
    for cmd in orden:
        if cmd in IMPLEMENTADOS:
            salidas.append([{"node": "Armar respuesta COMANDOS",
                             "type": "main", "index": 0}])
        else:
            salidas.append([{"node": "Comando pendiente",
                             "type": "main", "index": 0}])
    # Fallback: el dueño escribio algo que no es comando -> al agente normal
    salidas.append([{"node": "IF - No es del bot", "type": "main", "index": 0}])
    c[nombre_router] = {"main": salidas}

    # El IF de operador: true -> router ; false -> flujo normal del cliente
    c["¿Es operador?"] = {"main": [
        [{"node": nombre_router, "type": "main", "index": 0}],
        [{"node": "IF - No es del bot", "type": "main", "index": 0}],
    ]}

    # Normalizacion ahora entra por el IF de operador
    c["Normalizacion"] = {"main": [[
        {"node": "¿Es operador?", "type": "main", "index": 0}]]}

    # Las dos fuentes de respuesta van al nodo que envia
    c["Armar respuesta COMANDOS"] = {"main": [[
        {"node": "Responder al operador", "type": "main", "index": 0}]]}
    c["Comando pendiente"] = {"main": [[
        {"node": "Responder al operador", "type": "main", "index": 0}]]}

    print("\nenrutado:")
    print("  Normalizacion -> ¿Es operador?")
    print("     true  -> Router de comandos")
    print("                COMANDOS -> Armar respuesta -> Responder")
    print("                resto    -> Comando pendiente -> Responder")
    print("                fallback -> IF - No es del bot (sigue normal)")
    print("     false -> IF - No es del bot (cliente normal)")

    # --- Aplicar -------------------------------------------------------
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": c, "settings": wf.get("settings", {}),
    })
    print(f"\nPUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:400])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # --- Verificacion --------------------------------------------------
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    nombres = {n["name"] for n in fin["nodes"]}
    for requerido in ("¿Es operador?", "Router de comandos",
                      "Responder al operador", "Armar respuesta COMANDOS",
                      "Comando pendiente", "IF - No es del bot"):
        print(f"  {'OK  ' if requerido in nombres else 'MAL '} existe '{requerido}'")

    # Todo nodo no-trigger debe recibir datos
    destinos = set()
    for ramas in fin["connections"].values():
        for salidas_ in ramas.values():
            for g in salidas_:
                for x in g:
                    destinos.add(x["node"])
    huerfanos = [n["name"] for n in fin["nodes"]
                 if n["name"] not in destinos and "Trigger" not in n["type"]]
    print(f"  {'OK  ' if not huerfanos else 'MAL '} nodos sin entrada: "
          f"{huerfanos or 'ninguno'}")
    print(f"  {'OK  ' if 'DC64CCC' not in json.dumps(fin) else 'MAL '} "
          f"sin la clave del vendedor")
    return 0


if __name__ == "__main__":
    sys.exit(main())