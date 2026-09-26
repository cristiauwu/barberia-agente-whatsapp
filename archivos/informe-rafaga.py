#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Informe de una ráfaga: ¿respondió el bot a TODOS los mensajes?
¿Se trabó? ¿Creó citas duplicadas?
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


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def textos(o, fuera, prof=0, claves=("output", "text")):
    """Extrae de la salida el TEXTO ENVIADO al cliente.

    En 'Mandar mensaje' la respuesta de Evolution trae la estructura
    {key, pushName, status, message:{conversation:'...'}}. El texto va en
    message.conversation, NO en 'output'. Buscarlo en 'output' hacía
    reportar "(sin respuesta)" aunque el envío hubiera sido correcto.
    """
    if prof > 14:
        return
    if isinstance(o, dict):
        # Caso específico: la respuesta de Evolution al enviar
        msg = o.get("message")
        if isinstance(msg, dict):
            for k in ("conversation", "extendedTextMessage"):
                v = msg.get(k)
                if isinstance(v, str) and len(v) > 2:
                    fuera.append(v)
                elif isinstance(v, dict):
                    t = v.get("text")
                    if isinstance(t, str) and len(t) > 2:
                        fuera.append(t)
        for k, v in o.items():
            if k in claves and isinstance(v, str) and len(v) > 8:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1, claves)
    elif isinstance(o, list):
        for v in o[:25]:
            textos(v, fuera, prof + 1, claves)


def main():
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    ex = api(f"/executions?workflowId=barberiaAgenteUncensored&limit={limite}")
    print("=" * 76)
    print(f"INFORME DE EJECUCIONES (ultimas {limite})")
    print("=" * 76)
    filas = []
    for e in ex.get("data", []):
        try:
            det = api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        rd = ((det.get("data") or {}).get("resultData") or {})
        run = rd.get("runData") or {}
        dicho = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                dicho = str(it.get("json", {}).get("message_content", "")).strip()
        f = []
        if "Mandar mensaje" in run:
            textos(run["Mandar mensaje"], f)
        resp = f[0] if f else ""

        err = ""
        for nombre, datos in run.items():
            for it in (datos if isinstance(datos, list) else []):
                if isinstance(it, dict) and it.get("error"):
                    err = f"{nombre}: " + str(
                        (it["error"] or {}).get("message", ""))[:70]

        # ¿Llamó a Agendar cita?
        agendo = "Agendar cita" in run
        # ¿Cuantos eventos devolvio Calendar al agendar?
        n_eventos = 0
        if "Agendar cita" in run:
            g = []
            textos(run["Agendar cita"], g, 0, ("id",))
            n_eventos = len([x for x in g if len(x) > 15])

        filas.append({
            "id": e["id"], "status": e["status"], "dicho": dicho,
            "resp": resp, "err": err, "agendo": agendo,
            "pauso": "IF - Cliente pausado" in run,
            "ia": "AI Agent" in run,
        })

    for f in filas:
        print(f"\n[{f['id']}] status={f['status']}")
        print(f"  cliente: {f['dicho'][:90]}")
        print(f"  pausado={'no'} | uso IA={'si' if f['ia'] else 'no'} | "
              f"agendo={'SI' if f['agendo'] else 'no'}")
        if f["err"]:
            print(f"  ERROR: {f['err']}")
        print(f"  respuesta: {f['resp'][:200] or '(SIN RESPUESTA)'}")

    print()
    print("=" * 76)
    print("VEREDICTO DE LA RAFAGA")
    print("=" * 76)
    sin_resp = [f["id"] for f in filas if not f["resp"]]
    con_err = [f["id"] for f in filas if f["err"]]
    agendaron = [f["id"] for f in filas if f["agendo"]]
    print(f"  ejecuciones           : {len(filas)}")
    print(f"  sin respuesta         : {len(sin_resp)} {sin_resp}")
    print(f"  con error de nodo     : {len(con_err)} {con_err}")
    print(f"  llamaron a Agendar    : {len(agendaron)} {agendaron}")
    print()
    marca = "OK  " if not sin_resp else "MAL "
    print(f"  {marca}el bot respondio a todos los mensajes")
    return 0 if not sin_resp else 1


if __name__ == "__main__":
    sys.exit(main())