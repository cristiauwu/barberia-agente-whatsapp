#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RESTAURA el nodo 'ESPERAR A 24 H' a su valor original exacto y verifica."""
import sys, json, copy, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

WID = "barberiaRecordatorios"
ESPERADO_24 = "={{ $('Code').item.json.recordatorio24ISO }}"
ESPERADO_1 = "={{ $('Code').item.json.recordatorio1ISO }}"

st, w = tb.api("GET", f"/workflows/{WID}")
print("GET:", st, "active:", w.get("active"))

# estado actual antes de restaurar
for n in w["nodes"]:
    if n["name"] in ("ESPERAR A 24 H", "ESPERAR A 1 H"):
        print(f"  ANTES  {n['name']}: {json.dumps(n['parameters'], ensure_ascii=False)}")

st_d, _ = tb.api("POST", f"/workflows/{WID}/deactivate", {})
print("deactivate:", st_d)
time.sleep(2)

nodes = copy.deepcopy(w["nodes"])
for n in nodes:
    if n["name"] == "ESPERAR A 24 H":
        n["parameters"] = {"resume": "specificTime", "dateTime": ESPERADO_24}
    if n["name"] == "ESPERAR A 1 H":
        n["parameters"] = {"resume": "specificTime", "dateTime": ESPERADO_1}

body = {"name": w["name"], "nodes": nodes, "connections": w["connections"],
        "settings": w.get("settings", {})}
if w.get("staticData"):
    body["staticData"] = w["staticData"]
st_p, res = tb.api("PUT", f"/workflows/{WID}", body)
print("PUT:", st_p, "" if st_p in (200, 201) else str(res)[:300])
time.sleep(2)
st_a, ra = tb.api("POST", f"/workflows/{WID}/activate", {})
print("activate:", st_a, "active=", ra.get("active") if isinstance(ra, dict) else ra)
time.sleep(2)

st3, w3 = tb.api("GET", f"/workflows/{WID}")
ok = True
for n in w3["nodes"]:
    if n["name"] == "ESPERAR A 24 H":
        v = n["parameters"].get("dateTime")
        print(f"  DESPUES ESPERAR A 24 H: {json.dumps(n['parameters'], ensure_ascii=False)}")
        ok &= (v == ESPERADO_24)
    if n["name"] == "ESPERAR A 1 H":
        v = n["parameters"].get("dateTime")
        print(f"  DESPUES ESPERAR A 1 H : {json.dumps(n['parameters'], ensure_ascii=False)}")
        ok &= (v == ESPERADO_1)

# comparar TODO el workflow contra el respaldo
orig = json.load(open(r"G:\Barberia\_rec\W2_BACKUP_original.json", encoding="utf-8"))
def norm(wf):
    d = {n["name"]: n.get("parameters") for n in wf["nodes"]}
    return json.dumps({"n": d, "c": wf["connections"], "s": wf.get("settings")},
                      sort_keys=True, ensure_ascii=False)
identico = norm(orig) == norm(w3)
print(f"\n  wait24 restaurado: {ok}")
print(f"  workflow IDENTICO al respaldo (nodos+conexiones+settings): {identico}")
print(f"  active: {w3.get('active')}  |  nodos: {len(w3['nodes'])}  |  conexiones: {len(w3['connections'])}")