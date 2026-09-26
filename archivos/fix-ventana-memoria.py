#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BUG DE COSTE: la memoria de chat no tiene ventana de contexto.

HALLAZGO (verificado):
  El nodo 'Postgres Chat Memory' NO tiene `contextWindowLength`. Eso
  significa que en CADA mensaje el modelo recibe **todo** el historial de
  la conversación, sin límite.

  Evidencia real:
    - La tabla n8n_chat_histories tiene 922 filas y 8 sesiones.
    - Un solo cliente (5214501111805) acumula 618 mensajes.
    - En la ejecución 1035 el nodo de memoria movía 302.223 caracteres
      (~75.000 tokens) para UN mensaje.

  Consecuencia: el coste crece de forma cuadrática. El usuario ya gastó
  24,8 M de tokens de entrada (~7,52 USD) en buena parte por esto. Un
  cliente que escribe 600 veces hace que el mensaje 600 cueste 600 veces
  más que el primero.

SOLUCIÓN:
  Añadir `contextWindowLength: 12` al nodo. n8n conserva solo los últimos
  12 mensajes (6 intercambios) en el contexto que envía al modelo, que es
  de sobra para una conversación de citas: el cliente recuerda su servicio,
  día y hora, y el agente mantiene el hilo.

  La ventana NO borra el historial: la tabla sigue guardando todo. Solo
  limita lo que se envía al modelo, que es lo que se paga.

RIESGO: si el cliente cambia de tema tras 20 mensajes sin relación, el
agente podría perder el contexto viejo. Para una barbería eso no pasa: la
conversación es corta y siempre sobre la misma cita.
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
VENTANA = 12


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-memoria-ventana.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    n = next((x for x in wf["nodes"]
              if "memoryPostgresChat" in x["type"]), None)
    if not n:
        print("no encontré el nodo de memoria")
        return 1

    print("--- ANTES ---")
    print(json.dumps(n["parameters"], ensure_ascii=False, indent=2))
    antes = n["parameters"].get("contextWindowLength")
    n["parameters"]["contextWindowLength"] = VENTANA
    print(f"\n--- DESPUES ---")
    print(f"  contextWindowLength: {antes} -> {VENTANA}")
    n["notes"] = ("Ventana de 12 mensajes. Sin esto, cada mensaje reenvia\n"
                  "TODO el historial al modelo y el coste se dispara\n"
                  "(se detectaron 618 mensajes en una sola conversacion).")
    n["notesInFlow"] = True

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
    n2 = next(x for x in fin["nodes"] if "memoryPostgresChat" in x["type"])
    v = n2["parameters"].get("contextWindowLength")
    ok = v == VENTANA
    print(f"  {'OK  ' if ok else 'MAL '} contextWindowLength = {v}")
    print(f"  {'OK  ' if fin.get('active') else 'MAL '} workflow activo")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())