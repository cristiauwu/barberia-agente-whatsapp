#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escaneo del historial: ultimas 60 ejecuciones del agente.

Para cada una:
  - texto entrante y respuesta enviada
  - si se ejecuto la herramienta 'Que dia es' y que devolvio
  - cada dia de la semana nombrado, comprobado contra la fecha real
  - tope de 10 lineas
  - sangria inicial de 3 espacios / lineas en blanco de mas
  - estado error y su causa
"""
import datetime
import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
DIR = r"G:\Barberia\archivos\_verif-fechas"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
        "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MAPA_MES = {}
for i, m in enumerate(MESES, 1):
    MAPA_MES[m] = i
MAPA_MES.update({"setiembre": 9, "sep": 9, "sept": 9})
NORM = {"miércoles": "miercoles", "sábado": "sabado", "mi�rcoles": "miercoles"}


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=180) as x:
        return json.loads(x.read().decode())


def normaliza(t):
    t = t.lower()
    for k, v in NORM.items():
        t = t.replace(k, v)
    return t


def buscar_textos(o, prof=0, acc=None):
    """Saca todas las cadenas 'conversation' de un runData[ nodo ][0].data."""
    if acc is None:
        acc = []
    if prof > 16 or len(acc) > 40:
        return acc
    if isinstance(o, dict):
        if o.get("messageType") == "conversation":
            m = o.get("message")
            if isinstance(m, dict) and isinstance(m.get("conversation"), str):
                acc.append(m["conversation"])
        for v in o.values():
            buscar_textos(v, prof + 1, acc)
    elif isinstance(o, list):
        for v in o[:30]:
            buscar_textos(v, prof + 1, acc)
    return acc


# ---------------------------------------------------------------- recoger
ex = api(f"/executions?workflowId={WID}&limit=60")
ids = [e["id"] for e in ex["data"]]
print("ejecuciones descargadas:", len(ids), "->", ids[:3], "...", ids[-1])
meta = {e["id"]: e for e in ex["data"]}

lote = []
for eid in ids:
    try:
        det = api(f"/executions/{eid}?includeData=true")
    except Exception as ex2:
        lote.append({"id": eid, "error_descarga": str(ex2)})
        continue
    d = det["data"]
    rd = ((d.get("resultData") or {}).get("runData") or {})
    norm = rd.get("Normalizacion") or []
    entrante = ""
    remitente = ""
    if norm:
        try:
            j = norm[0]["data"]["main"][0][0]["json"]
            entrante = j.get("message_content") or ""
            remitente = j.get("user_number") or ""
        except Exception:
            pass
    saliente = ""
    if "Mandar mensaje" in rd:
        txts = buscar_textos(rd["Mandar mensaje"])
        if txts:
            saliente = txts[0]
    tool = None
    if "Que dia es" in rd:
        try:
            tool = rd["Que dia es"][0]["data"]["ai_tool"][0][0]["json"]
        except Exception:
            tool = "PRESENTE_SIN_JSON"
    # herramientas usadas en general
    tools = [k for k in rd if k in ("Consultar agenda", "Agendar cita",
                                    "Reajendar", "Reagendar", "Cancelar cita",
                                    "Registrar en hoja de citas",
                                    "Notificar al encargado", "Que dia es")]
    lote.append({"id": eid, "status": meta[eid]["status"],
                 "startedAt": meta[eid].get("startedAt"),
                 "mode": meta[eid].get("mode"),
                 "entrante": entrante, "saliente": saliente,
                 "remitente": remitente, "tool_que_dia": tool,
                 "herramientas": tools,
                 "nodos": list(rd.keys())})

json.dump(lote, open(DIR + r"\historial_crudo.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("guardado historial_crudo.json")

# ---------------------------------------------------------------- analizar
print()
print("=" * 78)
print("ANALISIS")
print("=" * 78)

filas = []
for it in lote:
    if "error_descarga" in it:
        continue
    sal = it["saliente"]
    ent = it["entrante"]
    st = it["status"]
    if not sal:
        filas.append({**it, "nota": "sin respuesta de texto"})
        continue
    # anio de referencia
    anio = int(str(it["startedAt"])[:4]) if it["startedAt"] else 2026
    t = normaliza(sal)
    #   "<dia> <num> de <mes>"  o  "Hoy, <num> de <mes>"
    hallazgos = []
    for m in re.finditer(
            r"(lunes|martes|miercoles|jueves|viernes|sabado|domingo)"
            r"\s+(\d{1,2})\s+de\s+([a-záéíóú]+)", t):
        dia, num, mes = m.group(1), int(m.group(2)), m.group(3)
        mm = MAPA_MES.get(mes)
        if not mm:
            continue
        try:
            real = datetime.date(anio, mm, num)
        except ValueError:
            hallazgos.append((m.group(0), None, "FECHA IMPOSIBLE"))
            continue
        esperado = DIAS[real.weekday()]
        hallazgos.append((m.group(0), esperado, "OK" if dia == esperado
                          else "MAL"))
    # "Hoy, <num> de <mes>"
    hoy_ok = None
    mh = re.search(r"hoy,?\s*(\d{1,2})\s+de\s+([a-záéíóú]+)", t)
    if mh:
        mm = MAPA_MES.get(mh.group(2))
        if mm:
            try:
                real = datetime.date(anio, mm, int(mh.group(1)))
                # el dia de la ejecucion en Mexico
                fecha_ex = datetime.datetime.fromisoformat(
                    it["startedAt"].replace("Z", "+00:00")
                ).astimezone(datetime.timezone(datetime.timedelta(hours=-6))).date()
                hoy_ok = ("OK" if real == fecha_ex else "MAL")
            except Exception:
                hoy_ok = "?"
    filas.append({**it, "hallazgos": hallazgos, "hoy": hoy_ok})

# ---- resumen de acuerdo/desacuerdo ----
tot_frases = 0
ok_frases = 0
mal_frases = 0
for f in filas:
    for (frag, esp, ver) in f.get("hallazgos", []):
        tot_frases += 1
        if ver == "OK":
            ok_frases += 1
        elif ver == "MAL":
            mal_frases += 1

print(f"\nfrases 'dia N de mes' encontradas: {tot_frases}")
print(f"  correctas: {ok_frases}   INCORRECTAS: {mal_frases}")
print(f"  imposibles: {tot_frases - ok_frases - mal_frases}")

print("\n--- FRASES INCORRECTAS (el fallo del dia, en el historial) ---")
for f in filas:
    for (frag, esp, ver) in f.get("hallazgos", []):
        if ver != "OK":
            print(f"  exec {f['id']} [{f['startedAt']}] "
                  f"dijo '{frag}' | debia ser '{esp}' | {ver}")
            print(f"     entrada: {f['entrante'][:90]!r}")

print("\n--- uso de la herramienta 'Que dia es' ---")
con_tool = [f for f in filas if f.get("tool_que_dia")]
print(f"  ejecuciones que ejecutaron la herramienta: {len(con_tool)}")
for f in con_tool:
    print(f"    exec {f['id']} [{f['startedAt']}] tool -> "
          f"{json.dumps(f['tool_que_dia'], ensure_ascii=False)[:160]}")

print("\n--- tope de 10 lineas ---")
for f in filas:
    sal = f.get("saliente") or ""
    if not sal:
        continue
    nl = sal.count("\n") + 1
    if nl > 10:
        print(f"  exec {f['id']} [{f['startedAt']}] {nl} lineas, "
              f"{len(sal)} caracteres | entrada {f['entrante'][:50]!r}")

print("\n--- formato: sangria de 3 espacios / lineas en blanco ---")
for f in filas:
    sal = f.get("saliente") or ""
    if not sal:
        continue
    sangria = [l for l in sal.split("\n") if l.startswith("   ") and l.strip()]
    dobles = re.findall(r"\n\n\n+", sal)
    fin_esp = [l for l in sal.split("\n") if l.endswith(" ") and l.strip()]
    doble_ast = "**" in sal
    if sangria or dobles or fin_esp or doble_ast:
        print(f"  exec {f['id']} [{f['startedAt']}] sangria={len(sangria)} "
              f"blancos_extra={len(dobles)} esp_final={len(fin_esp)} "
              f"doble_asterisco={doble_ast}")

print("\n--- ejecuciones con estado error ---")
for f in filas:
    if f["status"] != "success":
        print(f"  exec {f['id']} [{f['startedAt']}] estado={f['status']} "
              f"nodos={f['nodos'][-3:]}")

print("\n--- ejecuciones SIN respuesta de texto ---")
for f in filas:
    if not f.get("saliente") and "nota" in f:
        print(f"  exec {f['id']} [{f['startedAt']}] estado={f['status']} "
              f"entrada={f['entrante'][:60]!r}")

json.dump(filas, open(DIR + r"\historial_analizado.json", "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1,
          default=str)
print("\nguardado historial_analizado.json")