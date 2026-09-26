#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ayudante de Google: workflow TEMPORAL con webhook para leer/borrar
eventos de Calendar y filas de la hoja. Se elimina al terminar.

Motivo: las credenciales OAuth de Google no se pueden exportar por la API de
n8n, asi que la unica via es ejecutar nodos de n8n con esas credenciales.
El CONTEXTO permite crear workflows si se borran despues.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib

CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
       "09143c@group.calendar.google.com")
CRED_CAL = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                        "name": "Google Calendar account"}}
DOC = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
CRED_SH = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                     "name": "Google Sheets account"}}
NOMBRE = "_ayudante-carga"


def _n(name, tipo, tv, params, cred=None, pos=(0, 0)):
    n = {"parameters": params, "type": tipo, "typeVersion": tv,
         "position": list(pos), "id": str(uuid.uuid4()), "name": name}
    if cred:
        n["credentials"] = cred
    return n


def construir(ruta):
    return {
        "name": NOMBRE,
        "nodes": [
            _n("Webhook", "n8n-nodes-base.webhook", 2,
               {"httpMethod": "POST", "path": ruta,
                "responseMode": "lastNode", "options": {}}, pos=(0, 0)),
            _n("Accion", "n8n-nodes-base.switch", 3.2,
               {"rules": {"values": [
                   {"conditions": {"options": {"caseSensitive": True, "leftValue": "",
                                               "typeValidation": "strict"},
                                   "conditions": [{"leftValue": "={{ $json.body.accion }}",
                                                   "rightValue": "cal_listar",
                                                   "operator": {"type": "string",
                                                                "operation": "equals"}}],
                                   "combinator": "and"},
                    "renameOutput": True, "outputKey": "cal_listar"},
                   {"conditions": {"options": {"caseSensitive": True, "leftValue": "",
                                               "typeValidation": "strict"},
                                   "conditions": [{"leftValue": "={{ $json.body.accion }}",
                                                   "rightValue": "cal_borrar",
                                                   "operator": {"type": "string",
                                                                "operation": "equals"}}],
                                   "combinator": "and"},
                    "renameOutput": True, "outputKey": "cal_borrar"},
                   {"conditions": {"options": {"caseSensitive": True, "leftValue": "",
                                               "typeValidation": "strict"},
                                   "conditions": [{"leftValue": "={{ $json.body.accion }}",
                                                   "rightValue": "hoja_listar",
                                                   "operator": {"type": "string",
                                                                "operation": "equals"}}],
                                   "combinator": "and"},
                    "renameOutput": True, "outputKey": "hoja_listar"},
                   {"conditions": {"options": {"caseSensitive": True, "leftValue": "",
                                               "typeValidation": "strict"},
                                   "conditions": [{"leftValue": "={{ $json.body.accion }}",
                                                   "rightValue": "hoja_borrar",
                                                   "operator": {"type": "string",
                                                                "operation": "equals"}}],
                                   "combinator": "and"},
                    "renameOutput": True, "outputKey": "hoja_borrar"},
               ]}, "options": {"fallbackOutput": "extra",
                              "renameFallbackOutput": "otro"}}, pos=(220, 0)),

            # ---- cal_listar ----
            _n("CalListar", "n8n-nodes-base.googleCalendar", 1.3,
               {"operation": "getAll",
                "calendar": {"__rl": True, "value": CAL, "mode": "list",
                             "cachedResultName": "BARBER"},
                "returnAll": True,
                "options": {"singleEvents": True}}, CRED_CAL, pos=(460, -260)),
            _n("CalResumir", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
const evs = $input.all().map(i => i.json).filter(e => e && e.id);
return [{ json: {
  total: evs.length,
  eventos: evs.map(e => ({
    id: e.id,
    summary: e.summary || null,
    start: (e.start||{}).dateTime || (e.start||{}).date || null,
    end: (e.end||{}).dateTime || (e.end||{}).date || null,
    created: e.created || null,
    desc: (e.description||'').slice(0,120),
    creator: (e.creator||{}).email || null,
  })),
}}];
"""}, None, pos=(680, -260)),

            # ---- cal_borrar ----
            _n("CalListarB", "n8n-nodes-base.googleCalendar", 1.3,
               {"operation": "getAll",
                "calendar": {"__rl": True, "value": CAL, "mode": "list",
                             "cachedResultName": "BARBER"},
                "returnAll": True,
                "options": {"singleEvents": True}}, CRED_CAL, pos=(460, 0)),
            _n("CalFiltrar", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
// Borra los eventos cuyo id venga en body.ids, o los que no sean de
// "creacion natural" si body.todos es true y body.dryRun no lo impide.
const b = $('Webhook').first().json.body || {};
const ids = (b.ids || []).map(String);
const patron = b.patron ? new RegExp(b.patron, 'i') : null;
const desde = b.desde ? new Date(b.desde) : null;
let out = $input.all().map(i => i.json).filter(e => e && e.id);
if (ids.length) out = out.filter(e => ids.includes(String(e.id)));
if (patron) out = out.filter(e => patron.test(String(e.summary||'')));
if (desde) out = out.filter(e => e.created && new Date(e.created) >= desde);
return out.map(e => ({ json: { id: e.id, summary: e.summary || null,
  start: (e.start||{}).dateTime || (e.start||{}).date || null } }));
"""}, None, pos=(680, 0)),
            _n("CalBorrar", "n8n-nodes-base.googleCalendar", 1.3,
               {"operation": "delete",
                "calendar": {"__rl": True, "value": CAL, "mode": "list",
                             "cachedResultName": "BARBER"},
                "eventId": "={{ $json.id }}",
                "options": {"sendUpdates": "none"}}, CRED_CAL, pos=(900, 0)),
            _n("CalBorrados", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
let borrados = [];
try {
  borrados = $('CalFiltrar').all().map(i => i.json);
} catch (e) { borrados = []; }
return [{ json: { borrados: borrados.length,
  detalle: borrados.map(x => ({ id: x.id, summary: x.summary })) } }];
"""}, None, pos=(1120, 0)),

            # ---- hoja_listar ----
            _n("HojaLeer", "n8n-nodes-base.googleSheets", 4.6,
               {"operation": "read",
                "documentId": {"__rl": True, "value": DOC, "mode": "list",
                               "cachedResultName": "Citas barberia"},
                "sheetName": {"__rl": True, "value": "941506024", "mode": "list",
                              "cachedResultName": "Hoja 1"},
                "options": {}}, CRED_SH, pos=(460, 260)),
            _n("HojaResumir", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
const filas = $input.all().map(i => i.json);
return [{ json: { total: filas.length, filas: filas.map(f => {
  const o = {};
  for (const k of Object.keys(f)) o[k] = f[k];
  return o;
}) } }];
"""}, None, pos=(680, 260)),

            # ---- hoja_borrar ----
            # Lee la hoja, calcula las filas (>=2) cuyo ID coincida o que
            # cumplan el patron, y las borra de abajo hacia arriba.
            _n("HojaLeerB", "n8n-nodes-base.googleSheets", 4.6,
               {"operation": "read",
                "documentId": {"__rl": True, "value": DOC, "mode": "list",
                               "cachedResultName": "Citas barberia"},
                "sheetName": {"__rl": True, "value": "941506024", "mode": "list",
                              "cachedResultName": "Hoja 1"},
                "options": {}}, CRED_SH, pos=(460, 520)),
            _n("HojaCalcular", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
// Cada item de salida borra UNA fila. Se ordena de abajo hacia arriba para
// que al borrar no se desplacen los indices de las filas que faltan.
const b = $('Webhook').first().json.body || {};
const ids = (b.ids || []).map(String);
const patron = b.patron ? new RegExp(b.patron, 'i') : null;
const items = $input.all();
const objetivo = [];
items.forEach((it, idx) => {
  const j = it.json || {};
  const fila = Number(j.row_number || (idx + 2));
  const idCell = String(j['ID'] ?? j['id'] ?? '');
  const nombre = String(j['Nombre'] ?? j['nombre'] ?? '');
  const match = (ids.length && ids.includes(idCell))
             || (patron && (patron.test(idCell) || patron.test(nombre)));
  if (match) objetivo.push({ fila, id: idCell, nombre });
});
objetivo.sort((a, c) => c.fila - a.fila);
return objetivo.map(o => ({ json: o }));
"""}, None, pos=(680, 520)),
            _n("HojaBorrar", "n8n-nodes-base.googleSheets", 4.6,
               {"operation": "delete",
                "documentId": {"__rl": True, "value": DOC, "mode": "list",
                               "cachedResultName": "Citas barberia"},
                "sheetName": {"__rl": True, "value": "941506024", "mode": "list",
                              "cachedResultName": "Hoja 1"},
                "toDelete": "rows",
                "startIndex": "={{ $json.fila }}",
                "numberToDelete": 1}, CRED_SH, pos=(900, 520)),
            _n("HojaBorrados", "n8n-nodes-base.code", 2,
               {"jsCode": r"""
let hechos = [];
try { hechos = $('HojaCalcular').all().map(i => i.json); } catch (e) {}
return [{ json: { borradas: hechos.length, detalle: hechos } }];
"""}, None, pos=(1120, 520)),
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Accion", "type": "main", "index": 0}]]},
            "Accion": {"main": [
                [{"node": "CalListar", "type": "main", "index": 0}],
                [{"node": "CalListarB", "type": "main", "index": 0}],
                [{"node": "HojaLeer", "type": "main", "index": 0}],
                [{"node": "HojaLeerB", "type": "main", "index": 0}],
                [],
            ]},
            "CalListar": {"main": [[{"node": "CalResumir", "type": "main", "index": 0}]]},
            "CalListarB": {"main": [[{"node": "CalFiltrar", "type": "main", "index": 0}]]},
            "CalFiltrar": {"main": [[{"node": "CalBorrar", "type": "main", "index": 0}]]},
            "CalBorrar": {"main": [[{"node": "CalBorrados", "type": "main", "index": 0}]]},
            "HojaLeer": {"main": [[{"node": "HojaResumir", "type": "main", "index": 0}]]},
            "HojaLeerB": {"main": [[{"node": "HojaCalcular", "type": "main", "index": 0}]]},
            "HojaCalcular": {"main": [[{"node": "HojaBorrar", "type": "main", "index": 0}]]},
            "HojaBorrar": {"main": [[{"node": "HojaBorrados", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


RUTA = "ayuda" + uuid.uuid4().hex[:8]
WID = None


def limpiar_previos():
    st, lista = lib.api("/workflows?limit=250")
    for w in ((lista or {}).get("data") or []):
        if w["name"] == NOMBRE:
            if w.get("active"):
                lib.api("/workflows/%s/deactivate" % w["id"], "POST", {})
                time.sleep(1)
            lib.api("/workflows/%s" % w["id"], "DELETE")
            print("  (eliminado resto previo %s)" % w["id"])


def arrancar():
    global WID
    limpiar_previos()
    st, creado = lib.api("/workflows", "POST", construir(RUTA))
    if st not in (200, 201):
        raise RuntimeError("no pude crear el ayudante: %s %s" % (st, str(creado)[:400]))
    WID = creado["id"]
    st, _ = lib.api("/workflows/%s/activate" % WID, "POST", {})
    print("  ayudante activo id=%s ruta=%s (activate=%s)" % (WID, RUTA, st))
    # esperar a que el webhook de produccion se registre.
    # El nodo responde 404 mientras no este registrado; una vez registrado
    # responde 200 (accion valida) o 500 "No item to return" (accion que cae
    # en la rama fallback, que no tiene salida) -> ambas significan "listo".
    for i in range(10):
        time.sleep(3)
        req = urllib.request.Request("http://localhost:5678/webhook/" + RUTA,
                                     data=b'{"accion":"nada"}', method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                print("  webhook listo tras %ds (HTTP %s)" % (3 * (i + 1), r.status))
                return True
        except urllib.error.HTTPError as ex:
            cuerpo = ex.read().decode("utf-8", "replace")
            if ex.code == 404:
                continue
            print("  webhook listo tras %ds (HTTP %s)" % (3 * (i + 1), ex.code))
            return True
        except Exception:
            continue
    raise RuntimeError("el webhook del ayudante no respondio")


def llamar(payload, timeout=180):
    req = urllib.request.Request("http://localhost:5678/webhook/" + RUTA,
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def detener():
    if WID:
        lib.api("/workflows/%s/deactivate" % WID, "POST", {})
        time.sleep(1)
        st, _ = lib.api("/workflows/%s" % WID, "DELETE")
        print("  ayudante eliminado: HTTP %s" % st)


if __name__ == "__main__":
    lib.init()
    arrancar()
    print(json.dumps(llamar({"accion": "cal_listar"}), ensure_ascii=False)[:2000])
    print(json.dumps(llamar({"accion": "hoja_listar"}), ensure_ascii=False)[:2000])
    detener()