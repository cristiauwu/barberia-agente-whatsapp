#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBA VIVA de cancelacion / aliases del Switch.

Usa SOLO ejecuciones propias como objetivos, para no borrar recordatorios
reales pendientes.
"""
import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

HOY = "2026-10-06"

def estado(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)[:200]


import urllib.request, urllib.error

def nueva_aparicion(antes, timeout=200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        act = [e for e in tb.execs(limit=80) if e["id"] not in antes]
        if act:
            act.sort(key=lambda e: int(e["id"]))
            return act[0]
        time.sleep(10)
    return None


def fila(id_, estatus, exec_id):
    return {
        "ID": id_, "Estatus": estatus, "Nombre": f"Verif {estatus}",
        "Servicio": "Ceja", "Precio del servicio": "30",
        "Día ": HOY, "Hora": "15:00:00",
        "Numero celular": "5214501111805@s.whatsapp.net",
        "Execution ID": exec_id,
    }


CASOS = [
    ("cancelado",    None,  "no debe llegar a QUITAR (bug A)"),
    ("eliminado",    None,  "no debe llegar a QUITAR (bug A)"),
    ("actualizado",  "1300", "debe BORRAR la ejecucion 1300"),
    ("reprogramado", "1298", "debe BORRAR la ejecucion 1298"),
]

resultados = []
for estatus, objetivo, esperado in CASOS:
    print("="*100)
    print(f"CASO estatus={estatus!r}  objetivo={objetivo}  esperado: {esperado}")
    print("="*100)
    antes = {e["id"] for e in tb.execs(limit=100)}

    # estado del objetivo ANTES
    if objetivo:
        x = tb.exec_meta(objetivo)
        print(f"  objetivo {objetivo} ANTES: status={x.get('status')} waitTill={x.get('waitTill')}")

    r = tb.append_row(fila(f"verif-{estatus}", estatus, objetivo or ""))
    print("  append:", "ok" if r.get("ok") else r)
    time.sleep(4)

    ne = nueva_aparicion(antes, timeout=220)
    if not ne:
        print("  >> NO aparecio ninguna ejecucion nueva")
        resultados.append({"estatus": estatus, "objetivo": objetivo, "ejecucion": None,
                           "esperado": esperado, "observado": "sin ejecucion"})
        continue
    eid = ne["id"]
    print(f"  ejecucion nueva: {eid}")
    time.sleep(12)
    x = tb.exec_full(eid)
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    print(f"  status={x.get('status')} last={rd.get('lastNodeExecuted')}")
    print(f"  nodos: {sorted(run.keys())}")
    sw = run.get("Switch") or []
    if sw:
        mains = (sw[0].get("data") or {}).get("main") or []
        print(f"  Switch salidas con datos: {[i for i,m in enumerate(mains) if m]}")
    quit_ = run.get("QUITAR RECORDATORIO") or []
    if quit_:
        for rr in quit_:
            print(f"  QUITAR RECORDATORIO: status={rr.get('executionStatus')}")
            inp = (rr.get("inputData") or {}).get("main")
            print("     input:", json.dumps(inp, ensure_ascii=False)[:400])
            if rr.get("error"):
                print("     ERROR:", json.dumps(rr["error"], ensure_ascii=False)[:400])
    else:
        print("  QUITAR RECORDATORIO: NO se ejecuto")
    obt = run.get("OBTENER INFO DE CITA ELIMINADA") or []
    if obt:
        out = (obt[0].get("data") or {}).get("main")
        print("  OBTENER INFO out:", json.dumps(out, ensure_ascii=False)[:500])

    # estado del objetivo DESPUES
    if objetivo:
        st, body = estado(f"http://localhost:5678/api/v1/executions/{objetivo}")
        print(f"  objetivo {objetivo} DESPUES: HTTP {st} {body[:200]}")
        resultados.append({"estatus": estatus, "objetivo": objetivo, "ejecucion": eid,
                           "esperado": esperado, "http_objetivo": st,
                           "observado": "BORRADA" if st == 404 else f"HTTP {st}"})
    else:
        resultados.append({"estatus": estatus, "objetivo": None, "ejecucion": eid,
                           "esperado": esperado, "observado": "no ejecuto QUITAR"})
    time.sleep(3)

print("\n" + "="*100)
print("RESUMEN CANCELACION")
print("="*100)
for r in resultados:
    print(json.dumps(r, ensure_ascii=False))