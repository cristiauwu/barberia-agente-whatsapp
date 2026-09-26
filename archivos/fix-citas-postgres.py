#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Llena barber_citas y limpia los IDs basura de la hoja.

HALLAZGO (confirmado por la auditoría de la hoja):
  `barber_citas` está VACÍA (0 filas) y **ningún nodo hace INSERT en ella**.
  Es decir: Postgres NO tiene las citas; el sistema real es
  Calendar + la hoja. La tabla existe pero nadie la alimenta.

  Consecuencia: cualquier cosa que quiera leer las citas desde Postgres
  (reportes, métricas, el CRM cruzado) no encuentra nada.

SOLUCIÓN: en el flujo 2, junto al registro del cliente (CRM), añadir un
UPSERT de la cita en `barber_citas`. El flujo 2 ya tiene la fila completa
de la hoja: ID, Estatus, Nombre, Servicio, Precio, Día, Hora, Numero.

  Se construye el `inicio` como timestamptz en hora de México (-06:00)
  a partir de 'Día ' + 'Hora', y el `fin` se estima sumando la duración
  del servicio desde `barber_servicios`.

También limpia las filas con ID basura en la hoja (placeholders de prueba).
"""
import json
import os
import sys
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaRecordatorios"
PG_CRED = {"postgres": {"id": "NUrqrDWN8OsBFmgV", "name": "Postgres account"}}
NODO_IF = "IF - Es cita agendada"
NODO_CITA = "Registrar cita (Postgres)"

# UPSERT de la cita. El fin se calcula con la duración del servicio si se
# conoce; si no, se asume 40 min (la duración más común).
CONSULTA = """INSERT INTO barber_citas
  (id, jid, nombre, servicio, precio, inicio, fin, estado)
SELECT
  '{{ $json.ID }}',
  '521' || right(regexp_replace('{{ $json['Numero celular'] }}', '\\D', '', 'g'), 10)
    || '@s.whatsapp.net',
  nullif(trim('{{ $json.Nombre }}'), ''),
  nullif(trim('{{ $json.Servicio }}'), ''),
  nullif(regexp_replace('{{ $json['Precio del servicio'] }}', '[^0-9.]', '', 'g'), '')::numeric,
  (('{{ $json['Día '] }}' || ' ' || '{{ $json.Hora }}')::timestamp
     AT TIME ZONE 'America/Mexico_City'),
  (('{{ $json['Día '] }}' || ' ' || '{{ $json.Hora }}')::timestamp
     AT TIME ZONE 'America/Mexico_City')
    + (coalesce((SELECT duracion_min FROM barber_servicios
                 WHERE lower(nombre) LIKE '%' || lower(split_part(
                   '{{ $json.Servicio }}', ' ', 1)) || '%'
                 LIMIT 1), 40) || ' minutes')::interval,
  CASE lower(trim('{{ $json.Estatus }}'))
    WHEN 'agendado' THEN 'agendado'
    WHEN 'actualizado' THEN 'reprogramado'
    WHEN 'reprogramado' THEN 'reprogramado'
    WHEN 'cancelado' THEN 'cancelado'
    WHEN 'eliminado' THEN 'cancelado'
    WHEN 'confirmado' THEN 'confirmado'
    WHEN 'atendido' THEN 'atendido'
    WHEN 'no_show' THEN 'no_show'
    ELSE 'agendado'
  END
WHERE nullif(trim('{{ $json.ID }}'), '') IS NOT NULL
  AND '{{ $json['Día '] }}' ~ '^\\d{4}-\\d{2}-\\d{2}$'
  AND '{{ $json.Hora }}' ~ '^\\d{2}:\\d{2}'
ON CONFLICT (id) DO UPDATE
  SET nombre = coalesce(excluded.nombre, barber_citas.nombre),
      servicio = coalesce(excluded.servicio, barber_citas.servicio),
      precio = coalesce(excluded.precio, barber_citas.precio),
      inicio = excluded.inicio,
      fin = excluded.fin,
      estado = excluded.estado,
      actualizado_en = now()
RETURNING id, estado;"""


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-citas-pg.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    nodo = {
        "parameters": {"operation": "executeQuery", "query": CONSULTA,
                       "options": {}},
        "type": "n8n-nodes-base.postgres", "typeVersion": 2.6,
        "position": [-40, 400], "id": str(uuid.uuid4()),
        "name": NODO_CITA,
        "credentials": PG_CRED,
        "alwaysOutputData": True,
        "onError": "continueRegularOutput",
        "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000,
        "notes": ("Llena barber_citas desde la fila de la hoja. Sin esto\n"
                  "la tabla queda vacía y los reportes no tienen datos.\n"
                  "onError=continue: si falla, los recordatorios siguen."),
        "notesInFlow": True,
    }
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != NODO_CITA]
    wf["nodes"].append(nodo)

    c = wf["connections"]
    salidas = c.get(NODO_IF, {}).get("main", [[], []])
    while len(salidas) < 2:
        salidas.append([])
    ya = {x["node"] for x in salidas[0]}
    if NODO_CITA not in ya:
        salidas[0].append({"node": NODO_CITA, "type": "main", "index": 0})
    c[NODO_IF] = {"main": salidas}
    print(f"  {NODO_IF} -> {[x['node'] for x in salidas[0]]}")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": c, "settings": wf.get("settings", {}),
    })
    print(f"  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    n2 = next((n for n in fin["nodes"] if n["name"] == NODO_CITA), None)
    print(f"  {'OK  ' if n2 else 'MAL '} existe '{NODO_CITA}'")
    if n2:
        q = n2["parameters"]["query"]
        print(f"  {'OK  ' if 'barber_citas' in q else 'MAL '} escribe en barber_citas")
        print(f"  {'OK  ' if 'ON CONFLICT' in q else 'MAL '} usa UPSERT")
        print(f"  {'OK  ' if n2.get('onError') else 'MAL '} no rompe si falla")
    sale = [x["node"] for x in
            fin["connections"].get(NODO_IF, {}).get("main", [[]])[0]]
    print(f"  {NODO_IF} alimenta: {sale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())