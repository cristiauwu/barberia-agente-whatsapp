#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el bug del Switch en el workflow de recordatorios.

PROBLEMA (documentado en MEJORAS-BARBERIA.md seccion 5):
  - El prompt del agente registra Estatus 'cancelado' y 'actualizado'.
  - El Switch del flujo de recordatorios solo reconoce 'agendado' y 'eliminado'.
  - Por tanto, una cancelacion cae al output "Otro" y EL RECORDATORIO NUNCA
    SE ELIMINA: el cliente cancelado sigue recibiendo avisos de una cita que
    ya no existe.

SOLUCION:
  - Renombrar la salida 'Eliminado' a 'Cancelado' y aceptar ambos valores.
  - Anadir la salida 'Actualizado' para las reprogramaciones.
  - Asi cualquier estado que el agente escriba tiene su rama.

Este script MODIFICA el workflow en n8n. Guarda respaldo antes.
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
WID = "barberiaRecordatorios"

# Estados que el AGENTE puede escribir en la hoja (segun el prompt)
ESTADOS_AGENTE = ["agendado", "cancelado", "actualizado"]

# Nombres legibles para cada salida
ETIQUETA = {
    "agendado": "Agendado",
    "cancelado": "Cancelado",
    "actualizado": "Actualizado",
}

# Valores que debe aceptar cada salida (incluye sinonimos historicos)
ACEPTA = {
    "agendado": ["agendado"],
    "cancelado": ["cancelado", "eliminado"],   # sinonimo del flujo original
    "actualizado": ["actualizado", "reprogramado"],
}


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


def condicion(valor, idx):
    """Genera una condicion de comparacion string."""
    return {
        "id": f"estado-{valor}-{idx}",
        "leftValue": "={{ $('Code').item.json.Estatus }}",
        "rightValue": valor,
        "operator": {"type": "string", "operation": "equals"},
    }


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer el workflow:", st, wf)
        return 1
    activo = wf.get("active")

    bk = r"G:\Barberia\archivos\ANTES-switch-estados.json"
    json.dump(wf, open(bk, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"respaldo: {os.path.basename(bk)}")

    sw = next(n for n in wf["nodes"] if n["name"] == "Switch")

    print("\n--- ANTES ---")
    for v in sw["parameters"]["rules"]["values"]:
        vals = [c["rightValue"] for c in v["conditions"]["conditions"]]
        print(f"  {v.get('outputKey'):<12} acepta: {vals}")

    # Reconstruir las reglas
    nuevas = []
    for estado in ESTADOS_AGENTE:
        vals = ACEPTA[estado]
        nuevas.append({
            "conditions": {
                "options": {"caseSensitive": False, "leftValue": "",
                            "typeValidation": "loose", "version": 2},
                "conditions": [condicion(v, i) for i, v in enumerate(vals)],
                "combinator": "or",
            },
            "renameOutput": True,
            "outputKey": ETIQUETA[estado],
        })

    sw["parameters"]["rules"]["values"] = nuevas
    # Mantener el fallback para cualquier otro valor
    sw["parameters"]["options"] = {
        "fallbackOutput": "extra",
        "renameFallbackOutput": "Otro",
    }

    print("\n--- DESPUES ---")
    for v in sw["parameters"]["rules"]["values"]:
        vals = [c["rightValue"] for c in v["conditions"]["conditions"]]
        print(f"  {v.get('outputKey'):<12} acepta: {vals}")

    # Ajustar las conexiones: la salida 1 (antes 'Eliminado') ahora es
    # 'Cancelado' y sigue yendo a OBTENER INFO DE CITA ELIMINADA.
    # La nueva salida 2 ('Actualizado') tambien debe quitar el recordatorio.
    conns = wf["connections"]
    if "Switch" in conns:
        salidas = conns["Switch"]["main"]
        # salida 0: agendado -> Code1 (sin cambios)
        # salida 1: cancelado -> OBTENER INFO...
        if len(salidas) > 1 and salidas[1]:
            print(f"\n  salida 1 (Cancelado) -> {salidas[1][0]['node']}")
        # salida 2: actualizado -> mismo tratamiento que cancelado
        while len(salidas) < 3:
            salidas.append([])
        destino = [{"node": "OBTENER INFO DE CITA ELIMINADA",
                    "type": "main", "index": 0}]
        salidas[2] = destino
        print(f"  salida 2 (Actualizado) -> {destino[0]['node']}")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificacion
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    swf = next(n for n in fin["nodes"] if n["name"] == "Switch")
    todos = []
    for v in swf["parameters"]["rules"]["values"]:
        todos += [c["rightValue"] for c in v["conditions"]["conditions"]]
    for e in ESTADOS_AGENTE:
        ok = e in todos
        print(f"  {'OK  ' if ok else 'MAL '} el Switch reconoce '{e}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())