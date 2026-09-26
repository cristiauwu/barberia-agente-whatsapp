#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el comando PAUSA, que fallaba SIEMPRE.

BUG ENCONTRADO (ejecución 801, reportado por el test E2E):
  El nodo 'Aplicar pausa' hacía:
      INSERT INTO barber_pausas (jid, hasta, motivo)
      SELECT jid, now() + interval 'N hours', '...'
      FROM barber_clientes
      WHERE right(...) = right('NUMERO', 10)
      ON CONFLICT (jid) DO UPDATE ...

  El problema: `barber_clientes` está VACÍA (nadie escribe en ella; el
  registro de clientes no está implementado). Un INSERT ... SELECT que no
  encuentra filas **no inserta nada y NO da error**. El nodo devolvía
  {"success": true}, así que parecía funcionar, pero la pausa nunca se
  guardaba y el bot seguía contestando al cliente.

  Comprobado: el dueño mandaba `PAUSA 5214501111805 2h`, recibía
  "Pausado por 2 h", y el cliente seguía recibiendo respuestas.

SOLUCIÓN:
  Construir el JID directamente desde el número que el dueño escribió, sin
  depender de barber_clientes. Se normaliza a los últimos 10 dígitos y se
  toma el formato 521+10, que es el que usa Evolution en este entorno.

  Nota: WhatsApp México usa dos formatos (52+10 y 521+10). El JID que
  guarda Evolution y el que llega en remoteJid es el que importa para que
  el filtro 'Leer pausa' lo encuentre. Se comprobó que las citas reales
  usan 521+10, así que se usa ese formato.
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

# Nueva consulta: sin depender de barber_clientes
CONSULTA = """INSERT INTO barber_pausas (jid, hasta, motivo)
SELECT
  '521' || right(regexp_replace('{{ $json.numero }}', '\\D', '', 'g'), 10)
    || '@s.whatsapp.net',
  now() + (interval '1 hour' * {{ $json.horas }}),
  'comando del dueño'
ON CONFLICT (jid) DO UPDATE
  SET hasta = excluded.hasta, motivo = excluded.motivo
RETURNING jid, hasta, motivo;"""


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-pausa-fix2.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    n = next((x for x in wf["nodes"] if x["name"] == "Aplicar pausa"), None)
    if not n:
        print("no existe el nodo 'Aplicar pausa'")
        return 1

    print("--- ANTES ---")
    print(n["parameters"].get("query", "")[:400])
    n["parameters"]["query"] = CONSULTA
    print("\n--- DESPUES ---")
    print(CONSULTA[:400])

    # El nodo debe seguir emitiendo aunque no haya filas, para que
    # 'Formatear pausa' pueda decir que falló.
    n["alwaysOutputData"] = True

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

    # Verificación
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    n2 = next(x for x in fin["nodes"] if x["name"] == "Aplicar pausa")
    q = n2["parameters"]["query"]
    print(f"  {'OK  ' if 'barber_clientes' not in q else 'MAL '} "
          f"ya no depende de barber_clientes")
    print(f"  {'OK  ' if '521' in q else 'MAL '} construye el JID del número")
    print(f"  {'OK  ' if n2.get('alwaysOutputData') else 'MAL '} "
          f"emite salida aunque no inserte")
    return 0


if __name__ == "__main__":
    sys.exit(main())