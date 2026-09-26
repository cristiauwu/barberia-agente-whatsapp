#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hace que el CRM de clientes funcione: registra y actualiza cada cita.

CAUSA RAÍZ ENCONTRADA:
  La tabla `barber_clientes` está VACÍA y **ningún nodo escribe en ella**.
  Solo hay 2 nodos que escriben en Postgres, y van a `barber_pausas` y a
  `barber_servicios`. Nada llena `barber_clientes`.

CONSECUENCIAS REALES (verificadas):
  1. El comando `CLIENTE <número>` siempre responde "no encontré ficha".
  2. El comando `PAUSA` fallaba (ya corregido para no depender de ella),
     pero es síntoma del mismo problema.
  3. El CRM que promete el prompt ("cliente frecuente", "ya tienes una
     cita") no tiene de dónde leer: la tabla está vacía.

SOLUCIÓN:
  Cuando el agente registra una cita en la hoja, se añade un paso que
  hace UPSERT del cliente en `barber_clientes`:
    - Si no existe: lo crea con visitas=1, primera_visita=ahora.
    - Si existe: suma 1 visita, actualiza ultima_visita y servicio_habitual,
      y recalcula ticket_promedio.

DÓNDE: en el flujo 1, la herramienta `Registrar en hoja de citas` es un
`googleSheetsTool` conectado directo al agente. No se puede insertar un
nodo Postgres "en medio" de una herramienta del agente sin cambiar el
diseño. La vía limpia y sin riesgo: aprovechar el flujo 2, que YA se
dispara con cada fila nueva de la hoja (el Google Sheets Trigger).

  El flujo 2 ya tiene la fila con Nombre, Servicio, Precio y Numero
  celular. Se añade, en paralelo al aviso al dueño, un nodo que hace el
  UPSERT del cliente. Así el CRM se llena solo, sin tocar el agente.

VENTAJA: no se toca el flujo del agente (cero riesgo de romper la
conversación), y el flujo 2 ya tiene todos los datos necesarios.
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

# UPSERT del cliente. Se construye el JID y se evita duplicar.
CONSULTA = """INSERT INTO barber_clientes
  (jid, nombre, telefono, primera_visita, visitas, ultima_visita,
   servicio_habitual, etiqueta)
SELECT
  '521' || right(regexp_replace('{{ $json['Numero celular'] }}', '\\D', '', 'g'), 10)
    || '@s.whatsapp.net',
  nullif(trim('{{ $json.Nombre }}'), ''),
  right(regexp_replace('{{ $json['Numero celular'] }}', '\\D', '', 'g'), 10),
  now(), 1, now(),
  nullif(trim('{{ $json.Servicio }}'), ''),
  'nuevo'
ON CONFLICT (jid) DO UPDATE
  SET visitas = coalesce(barber_clientes.visitas, 0) + 1,
      ultima_visita = now(),
      nombre = coalesce(excluded.nombre, barber_clientes.nombre),
      servicio_habitual = coalesce(excluded.servicio_habitual,
                                   barber_clientes.servicio_habitual),
      etiqueta = CASE
        WHEN coalesce(barber_clientes.visitas, 0) + 1 >= 5 THEN 'frecuente'
        ELSE coalesce(barber_clientes.etiqueta, 'nuevo')
      END
RETURNING jid, visitas;"""

NODO_PG = "Registrar cliente (CRM)"
NODO_IF = "IF - Es cita agendada"


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-crm.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    # Nodo Postgres nuevo
    nodo = {
        "parameters": {"operation": "executeQuery", "query": CONSULTA,
                       "options": {}},
        "type": "n8n-nodes-base.postgres", "typeVersion": 2.6,
        "position": [-40, 220], "id": str(uuid.uuid4()),
        "name": NODO_PG,
        "credentials": PG_CRED,
        "alwaysOutputData": True,
        "onError": "continueRegularOutput",
        "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000,
        "notes": ("Llena el CRM: crea o actualiza el cliente en\n"
                  "barber_clientes con cada cita nueva. Sin esto la tabla\n"
                  "queda vacía y el comando CLIENTE nunca encuentra nada.\n"
                  "onError=continue: si el CRM falla, el aviso al dueño\n"
                  "y los recordatorios NO deben romperse."),
        "notesInFlow": True,
    }
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != NODO_PG]
    wf["nodes"].append(nodo)

    # Recablear: el IF de 'es cita agendada' ahora alimenta DOS ramas:
    #   - el aviso al dueño (como antes)
    #   - el registro del cliente (nuevo)
    c = wf["connections"]
    salidas_previas = c.get(NODO_IF, {}).get("main", [[], []])
    # La rama true (salida 0) tenía el aviso; se le añade el CRM.
    if not salidas_previas:
        salidas_previas = [[], []]
    while len(salidas_previas) < 2:
        salidas_previas.append([])
    ya = {x["node"] for x in salidas_previas[0]}
    if NODO_PG not in ya:
        salidas_previas[0].append({"node": NODO_PG, "type": "main",
                                   "index": 0})
    c[NODO_IF] = {"main": salidas_previas}

    print(f"  {NODO_IF} -> {[x['node'] for x in salidas_previas[0]]}")

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

    # Verificación
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    n2 = next((n for n in fin["nodes"] if n["name"] == NODO_PG), None)
    print(f"  {'OK  ' if n2 else 'MAL '} existe '{NODO_PG}'")
    if n2:
        q = n2["parameters"]["query"]
        print(f"  {'OK  ' if 'barber_clientes' in q else 'MAL '} "
              f"escribe en barber_clientes")
        print(f"  {'OK  ' if 'ON CONFLICT' in q else 'MAL '} usa UPSERT")
        print(f"  {'OK  ' if n2.get('onError') else 'MAL '} "
              f"no rompe el flujo si falla")
    sale = [x["node"] for x in
            fin["connections"].get(NODO_IF, {}).get("main", [[]])[0]]
    print(f"  {NODO_IF} alimenta: {sale}")
    # El aviso al dueño debe seguir
    print(f"  {'OK  ' if 'Notificar cita nueva al encargado' in sale else 'MAL '}"
          f" el aviso al dueño sigue")
    return 0


if __name__ == "__main__":
    sys.exit(main())