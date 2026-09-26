#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBA VIVA del Wait de 24 h.

Parchea TEMPORALMENTE el nodo 'ESPERAR A 24 H' para que se reanude en ~3 min
(expression $now.plus(3,'minutes')), inserta una fila de prueba con una cita a
~10 dias, y observa si la ejecucion se reanuda y si el recordatorio se ENVIA.
"""
import sys, json, time, copy
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

WID = "barberiaRecordatorios"
ORIGINAL = "={{ $('Code').item.json.recordatorio24ISO }}"
PARCHE = "={{ $now.plus(3, 'minutes').toISO() }}"

FASE = sys.argv[1] if len(sys.argv) > 1 else "all"


def get_wf():
    st, w = tb.api("GET", f"/workflows/{WID}")
    return w


def put_wf(w, nodes):
    body = {"name": w["name"], "nodes": nodes,
            "connections": w["connections"], "settings": w.get("settings", {})}
    if w.get("staticData"):
        body["staticData"] = w["staticData"]
    return tb.api("PUT", f"/workflows/{WID}", body)


if FASE in ("all", "patch"):
    print("="*90)
    print("PASO 1: desactivar -> PUT con el Wait parcheado -> reactivar")
    print("="*90)
    st, w = tb.api("GET", f"/workflows/{WID}")
    print("  GET:", st, "active=", w.get("active"))
    st_d, _ = tb.api("POST", f"/workflows/{WID}/deactivate", {})
    print("  deactivate HTTP:", st_d)
    time.sleep(2)

    nodes = copy.deepcopy(w["nodes"])
    tocado = False
    for n in nodes:
        if n["name"] == "ESPERAR A 24 H":
            n["parameters"]["dateTime"] = PARCHE
            tocado = True
    print("  nodo parcheado:", tocado, "->", PARCHE)
    st_p, res = put_wf(w, nodes)
    print("  PUT HTTP:", st_p, "" if st_p in (200, 201) else str(res)[:400])
    time.sleep(2)
    st_a, ra = tb.api("POST", f"/workflows/{WID}/activate", {})
    print("  activate HTTP:", st_a, "active=", ra.get("active") if isinstance(ra, dict) else ra)
    time.sleep(2)

    st2, w2 = tb.api("GET", f"/workflows/{WID}")
    for n in w2["nodes"]:
        if n["name"] == "ESPERAR A 24 H":
            print("  CONFIRMADO en vivo:", json.dumps(n["parameters"], ensure_ascii=False))
    print("  active:", w2.get("active"), "nodos:", len(w2["nodes"]))
    json.dump(w2, open(r"G:\Barberia\_rec\W2_parcheado.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

if FASE in ("all", "insert"):
    print()
    print("="*90)
    print("PASO 2: insertar fila de prueba (cita a ~10 dias -> mandar24 = true)")
    print("="*90)
    antes = {e["id"] for e in tb.execs(limit=100)}
    json.dump(sorted(antes), open(r"G:\Barberia\_rec\antes_ids.json", "w"))
    print("  ejecuciones antes:", len(antes))

    fila = {
        "ID": "verif-rec-wait-24h", "Estatus": "agendado",
        "Nombre": "Verif Wait 24h", "Servicio": "Ceja",
        "Precio del servicio": "30", "Día ": "2026-10-06",
        "Hora": "15:00:00", "Numero celular": "5214501111805@s.whatsapp.net",
        "Execution ID": "",
    }
    r = tb.append_row(fila)
    print("  append:", json.dumps({k: v for k, v in r.items() if k != "fila"}, ensure_ascii=False))
    time.sleep(3)
    rows = tb.parse_csv(tb.read_sheet())
    for i, rr in enumerate(rows, 1):
        if rr and rr[0] == "verif-rec-wait-24h":
            print(f"  fila insertada en la fila {i} de la hoja")