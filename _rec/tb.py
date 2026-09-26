#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caja de herramientas de verificacion para el workflow de Recordatorios.

Crea workflows TEMPORALES en n8n que reutilizan las credenciales OAuth ya
autorizadas, para poder escribir/borrar filas de la hoja y lanzar el flujo.
Cada workflow temporal se borra al terminar.
"""
import json, os, sys, time, urllib.request, urllib.error, uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
HOJA = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
GID = "941506024"
CRED_S = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                    "name": "Google Sheets account"}}
COLUMNAS = ["ID", "Estatus", "Nombre", "Servicio", "Precio del servicio",
            "Día ", "Hora", "Numero celular", "Execution ID"]


def api(method, path, body=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]
    except Exception as e:
        return None, str(e)


def sheet_schema():
    return [{"id": c, "displayName": c, "required": False, "defaultMatch": False,
             "display": True, "type": "string", "canBeUsedToMatch": True,
             "removed": False} for c in COLUMNAS]


def sheets_node(name, operation, extra):
    p = {"operation": operation,
         "documentId": {"__rl": True, "value": HOJA, "mode": "list",
                        "cachedResultName": "Citas barbería"},
         "sheetName": {"__rl": True, "value": GID, "mode": "list",
                       "cachedResultName": "Hoja 1"},
         "options": {}}
    p.update(extra)
    return {"parameters": p, "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4.6, "position": [660, 0], "id": str(uuid.uuid4()),
            "name": name, "credentials": CRED_S}


def run_temp(nombre, nodos, conexiones, payload=None, espera=8, timeout=180):
    """Crea, activa, dispara por webhook, desactiva y BORRA un workflow temporal."""
    # limpiar restos previos
    st, lst = api("GET", "/workflows?limit=100")
    for w in (lst.get("data", []) if st == 200 else []):
        if w["name"] == nombre:
            if w.get("active"):
                api("POST", f"/workflows/{w['id']}/deactivate", {})
                time.sleep(1)
            api("DELETE", f"/workflows/{w['id']}")
    ruta = None
    for n in nodos:
        if n["type"] == "n8n-nodes-base.webhook":
            ruta = n["parameters"].get("path")
            break
    if not ruta:
        ruta = "zz" + uuid.uuid4().hex[:8]
        for n in nodos:
            if n["type"] == "n8n-nodes-base.webhook":
                n["parameters"]["path"] = ruta
    # n8n no admite guiones bajos/espacios en la ruta del webhook
    ruta = ruta.replace("_", "-")
    for n in nodos:
        if n["type"] == "n8n-nodes-base.webhook":
            n["parameters"]["path"] = ruta
    body = {"name": nombre, "nodes": nodos, "connections": conexiones,
            "settings": {"executionOrder": "v1"}}
    st, creado = api("POST", "/workflows", body)
    if st not in (200, 201):
        return {"ok": False, "stage": "create", "http": st, "detail": creado}
    wid = creado["id"]
    st, act = api("POST", f"/workflows/{wid}/activate", {})
    time.sleep(4)
    resp = None
    try:
        req = urllib.request.Request(f"http://localhost:5678/webhook/{ruta}",
                                     data=json.dumps(payload or {}).encode(),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = r.read().decode()[:1500]
    except urllib.error.HTTPError as e:
        resp = f"HTTP {e.code}: {e.read().decode()[:600]}"
    except Exception as e:
        resp = f"FALLO: {e}"
    time.sleep(espera)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")
    return {"ok": True, "workflowId": wid, "webhook": ruta, "respuesta": resp}


def webhook_node(ruta):
    return {"parameters": {"httpMethod": "POST", "path": ruta,
                           "responseMode": "lastNode", "options": {}},
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
            "webhookId": str(uuid.uuid4())}


def code_node(code):
    return {"parameters": {"jsCode": code}, "type": "n8n-nodes-base.code",
            "typeVersion": 2, "position": [220, 0], "id": str(uuid.uuid4()),
            "name": "Armar"}


def append_row(fila, espera=8):
    """Agrega una fila a la hoja usando el nodo nativo (mismos scopes que el flujo)."""
    valores = {c: "={{ $json[%r] }}" % c for c in COLUMNAS}
    nodos = [webhook_node("zz-append-fija"),
             code_node("return [{ json: $json.body }];"),
             sheets_node("Escribir filas", "append",
                         {"columns": {"mappingMode": "defineBelow", "value": valores,
                                      "matchingColumns": ["ID"], "schema": sheet_schema()}})]
    conexiones = {"Webhook": {"main": [[{"node": "Armar", "type": "main", "index": 0}]]},
                  "Armar": {"main": [[{"node": "Escribir filas", "type": "main", "index": 0}]]}}
    r = run_temp("_zz-verif-append", nodos, conexiones, payload=fila, espera=espera)
    r["fila"] = fila
    return r


def delete_row(row_number, espera=6):
    """Borra UNA fila por su numero (1 = encabezado, la primera de datos es 2)."""
    nodos = [webhook_node("zz-delete-fija"),
             code_node(f"return [{{ json: {{ n: {row_number} }} }}];"),
             sheets_node("Borrar fila", "delete",
                         {"toDelete": "rows", "startIndex": row_number,
                          "numberToDelete": 1})]
    conexiones = {"Webhook": {"main": [[{"node": "Armar", "type": "main", "index": 0}]]},
                  "Armar": {"main": [[{"node": "Borrar fila", "type": "main", "index": 0}]]}}
    return run_temp("_zz-verif-delete", nodos, conexiones, payload={}, espera=espera)


def read_sheet():
    url = (f"https://docs.google.com/spreadsheets/d/{HOJA}"
           f"/gviz/tq?tqx=out:csv&gid={GID}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


def parse_csv(txt):
    import csv, io
    rows = list(csv.reader(io.StringIO(txt)))
    return rows


def execs(wid="barberiaRecordatorios", limit=100):
    st, res = api("GET", f"/executions?workflowId={wid}&limit={limit}")
    return res.get("data", []) if st == 200 else []


def exec_meta(eid):
    st, d = api("GET", f"/executions/{eid}?includeData=false")
    x = d.get("data", d)
    return x if isinstance(x, dict) else {}


def exec_full(eid):
    st, d = api("GET", f"/executions/{eid}?includeData=true")
    x = d.get("data", d)
    return x if isinstance(x, dict) else {}


def esperar_nueva(antes_ids, timeout=180, intervalo=10, wid="barberiaRecordatorios"):
    """Espera a que aparezca una ejecucion nueva. Devuelve sus metadatos."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        act = execs(wid)
        nuevas = [e for e in act if e["id"] not in antes_ids]
        if nuevas:
            nuevas.sort(key=lambda e: int(e["id"]))
            return nuevas[0]
        time.sleep(intervalo)
    return None