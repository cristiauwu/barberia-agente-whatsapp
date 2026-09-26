#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige 2 credenciales rotas y añade resiliencia.

HALLAZGOS REALES de la auditoría:

1. CREDENCIAL ROTA en los nodos 'Transcribe a recording' y
   'Describe imagen': apuntan a la credencial de OpenAI
   GtV72MoANECFbNoX, que NO EXISTE. Consecuencia: si un cliente manda
   un audio o una foto, el flujo falla. Solución inmediata que no
   depende de tener la clave: marcar esos nodos con
   `onError: continueRegularOutput` para que el audio/foto no rompa la
   conversación, y el bot pida que se lo escriban.

2. CREDENCIAL ROTA en 'QUITAR RECORDATORIO': apunta a la credencial
   n8nApi LBEYKKDnChQfHraH, que NO EXISTE. Consecuencia: al cancelar
   una cita, el recordatorio pendiente NO se borra y el cliente sigue
   recibiendo avisos. Solución: crear la credencial con la clave real
   que ya tenemos.

3. Ningún nodo de red tenía reintentos. Si Google o Evolution fallan un
   instante, el mensaje se pierde. Se añaden reintentos a los críticos.
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
N8N_APIKEY = KEY  # la misma clave que usamos para administrar n8n
N8N_URL = "http://localhost:5678"

# Nodos que deben reintentar (llamadas de red que no pueden perderse)
REINTENTAR = {
    "barberiaAgenteUncensored": [
        "Mandar mensaje", "Responder al operador", "Consultar agenda",
        "Agendar cita", "Cancelar cita", "Reagendar",
        "Registrar en hoja de citas", "Notificar al encargado",
        "Leer agenda del rango", "Crear bloqueo en calendario",
        "Leer ficha del cliente", "Actualizar precio", "Aplicar pausa",
        "Leer operadores", "Leer pausa", "Leer estado del sistema",
        "Get Audio", "Get Image",
    ],
    "barberiaRecordatorios": [
        "Notificar cita nueva al encargado", "Append or update row in sheet",
        "OBTENER INFO DE CITA ELIMINADA", "RECORDATORIO 24 H",
        "RECORDATORIO 1 H",
    ],
}

# Nodos que deben seguir aunque fallen (degradación elegante)
SEGUIR_SI_FALLA = ["Transcribe a recording", "Describe imagen",
                   "Get Audio", "Get Image"]


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
    # ---- 1. Crear la credencial n8nApi que falta ---------------------
    print("=" * 72)
    print("1) CREDENCIAL n8nApi (para QUITAR RECORDATORIO)")
    print("=" * 72)
    st, creds = api("GET", "/credentials")
    existentes = {c["id"]: c["name"] for c in creds.get("data", [])}
    n8napi_id = None
    for cid, nombre in existentes.items():
        if nombre in ("n8n API", "n8n API (local)", "n8n-api"):
            st2, det = api("GET", f"/credentials/{cid}")
            if det.get("type") == "n8nApi":
                n8napi_id = cid
                break

    if n8napi_id:
        print(f"  ya existe: {n8napi_id}")
    else:
        st, res = api("POST", "/credentials", {
            "name": "n8n API (local)",
            "type": "n8nApi",
            "data": {"apiKey": N8N_APIKEY, "baseUrl": N8N_URL},
        })
        print(f"  crear -> HTTP {st}")
        if st in (200, 201):
            n8napi_id = res.get("id")
            print(f"  creada: {n8napi_id}")
        else:
            print(f"  detalle: {str(res)[:300]}")

    # ---- 2. Aplicar cambios a los workflows --------------------------
    for wid, nombre_wf in (("barberiaAgenteUncensored", "FLUJO 1"),
                           ("barberiaRecordatorios", "FLUJO 2")):
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print(f"  {nombre_wf}: no se pudo leer")
            continue
        activo = wf.get("active")
        json.dump(wf, open(rf"G:\Barberia\archivos\ANTES-resiliencia-{wid}.json",
                           "w", encoding="utf-8"), ensure_ascii=False, indent=2)

        print()
        print("=" * 72)
        print(f"2) {nombre_wf}")
        print("=" * 72)
        cambios = 0

        # 2a. Reapuntar QUITAR RECORDATORIO si su credencial no existe
        for n in wf["nodes"]:
            creds_n = n.get("credentials") or {}
            for tipo, val in list(creds_n.items()):
                if val.get("id") not in existentes:
                    if tipo == "n8nApi" and n8napi_id:
                        creds_n[tipo] = {"id": n8napi_id,
                                         "name": "n8n API (local)"}
                        print(f"  {n['name']}: n8nApi -> credencial nueva")
                        cambios += 1
                    elif tipo == "openAiApi":
                        # No tenemos la clave de OpenAI; se deja pero se
                        # marca el nodo para que no rompa el flujo.
                        print(f"  {n['name']}: openAiApi sigue rota "
                              f"(falta la clave del usuario) -> se marca "
                              f"para no romper el flujo")
                        cambios += 1

        # 2b. Reintentos en los nodos críticos
        objetivo = set(REINTENTAR.get(wid, []))
        for n in wf["nodes"]:
            if n["name"] in objetivo and not n.get("retryOnFail"):
                n["retryOnFail"] = True
                n["maxTries"] = 3
                n["waitBetweenTries"] = 2000
                cambios += 1
        print(f"  reintentos añadidos a {len(objetivo & {n['name'] for n in wf['nodes']})} nodos")

        # 2c. Degradación elegante en audio/imagen
        for n in wf["nodes"]:
            if n["name"] in SEGUIR_SI_FALLA:
                n["onError"] = "continueRegularOutput"
                n["alwaysOutputData"] = True
                print(f"  {n['name']}: continuar aunque falle")
                cambios += 1

        if not cambios:
            print("  sin cambios")
            continue

        if activo:
            api("POST", f"/workflows/{wid}/deactivate", {})
        st2, res = api("PUT", f"/workflows/{wid}", {
            "name": wf["name"], "nodes": wf["nodes"],
            "connections": wf["connections"],
            "settings": wf.get("settings", {}),
        })
        print(f"  PUT -> HTTP {st2}")
        if st2 not in (200, 201):
            print(f"  detalle: {str(res)[:300]}")
            continue
        if activo:
            st3, r3 = api("POST", f"/workflows/{wid}/activate", {})
            print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # ---- 3. Verificación --------------------------------------------
    print()
    print("=" * 72)
    print("3) VERIFICACION")
    print("=" * 72)
    st, creds = api("GET", "/credentials")
    existentes = {c["id"]: c["name"] for c in creds.get("data", [])}
    for wid, nombre_wf in (("barberiaAgenteUncensored", "FLUJO 1"),
                           ("barberiaRecordatorios", "FLUJO 2")):
        st, wf = api("GET", f"/workflows/{wid}")
        print(f"\n  {nombre_wf}")
        rotras = []
        for n in wf["nodes"]:
            for tipo, val in (n.get("credentials") or {}).items():
                if val.get("id") not in existentes:
                    rotras.append(f"{n['name']} ({tipo})")
        print(f"    credenciales rotas: {rotras or 'ninguna'}")
        con_retry = [n["name"] for n in wf["nodes"] if n.get("retryOnFail")]
        print(f"    nodos con reintentos: {len(con_retry)}")
        con_onerror = [n["name"] for n in wf["nodes"]
                       if n.get("onError")]
        print(f"    nodos con onError: {con_onerror or 'ninguno'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())