#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion de punta a punta de CANCELAR y REPROGRAMAR una cita.

Proyecto: G:\\Barberia  (n8n + Evolution API + Google Calendar + Google Sheets)

El script hace, en vivo y sin modificar ningun workflow del proyecto:

  PARTE 1 - CANCELAR
    1. Pide al bot una cita en un horario libre futuro y captura el ID del
       evento que devuelve la herramienta "Agendar cita".
    2. Espera a que el flujo 2 (barberiaRecordatorios) procese la fila nueva
       y confirma que arranco y llego a "ESPERAR A 24 H" (status waiting).
    3. Pide al bot que cancele esa cita.
    4. Verifica en el calendario que el evento ya no existe.
    5. Verifica en la hoja que hay una fila nueva con Estatus = cancelado.
    6. Verifica que el flujo 2 proceso la cancelacion: rama "Cancelado" del
       Switch -> "OBTENER INFO DE CITA ELIMINADA" -> "QUITAR RECORDATORIO",
       y que la ejecucion que estaba en espera ya no espera (o fue borrada).

  PARTE 2 - REPROGRAMAR
    1. Crea otra cita con otro numero.
    2. Pide al bot que la mueva a otro horario libre.
    3. Verifica que el evento del calendario cambio de start/end.
    4. Verifica en la hoja que se registro el cambio (actualizado/reprogramado).
    5. Verifica que el Switch del flujo 2 enruta Actualizado/reprogramado a
       "OBTENER INFO DE CITA ELIMINADA".

  PARTE 3 - Resumen de hallazgos (nodos con error, credenciales, desajustes).

NOTA SOBRE EL CALENDARIO
  La API publica de n8n no permite listar el calendario. Para poder COMPROBAR
  la desaparicion/movimiento del evento, el script crea un workflow TEMPORAL
  PROPIO de solo lectura (no toca los del proyecto) y lo destruye al final.
  Sus unicas acciones son OAuth2 de Calendar (getAll) y un Code de resumen.

Uso:  uv run python archivos/test-cancelar-reprogramar.py
"""

import csv
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Configuracion del entorno
# ---------------------------------------------------------------------------
N8N = "http://localhost:5678/api/v1"
WEBHOOK = "http://localhost:5678/webhook/hector"
KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjYmQ1ZGQ2Yi05NzJlLTRlZmYtYWVl"
       "NC03MTAzOWJmM2E5MDIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmZkZmNi"
       "NDQtZmRiMi00MDUwLTg3MWMtMGJkMDI5NGRiOTYwIiwiaWF0IjoxNzkwMjk4ODczfQ"
       ".s04weO8S72yEn6ip2rCGE4wCt-wPw22xVWJij-lF4wc")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

WF_AGENTE = "barberiaAgenteUncensored"
WF_RECORD = "barberiaRecordatorios"

HOJA_ID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
HOJA_GID = "941506024"
HOJA_CSV = ("https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=%s"
            % (HOJA_ID, HOJA_GID))

CAL_ID = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
          "09143c@group.calendar.google.com")
CRED_CAL = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                        "name": "Google Calendar account"}}
WF_TEMP = "_verif-e2e-lectura-calendario"

# Numeros de WhatsApp que EXISTEN.
JID_A = "5214501111805@s.whatsapp.net"   # Parte 1 - cancelar
JID_B = "5214521206246@s.whatsapp.net"   # Parte 2 - reprogramar

# Horarios libres elegidos (los eventos existentes estan el 27, 28 y 29 de
# septiembre de 2026). Los jueves de octubre de 2026 son 1, 8, 15, 22 y 29.
# OJO: el agente resuelve bien "jueves 1 de octubre" pero a veces lo confunde
# con una fecha ya pasada; por eso se envia SIEMPRE la fecha en formato
# AAAA-MM-DD, que resuelve de forma determinista.
CITA_A_FECHA, CITA_A_HORA = "2026-10-01", "11:00"   # jueves (cancelar)
CITA_B_FECHA, CITA_B_HORA = "2026-10-08", "13:00"   # jueves (reprogramar)
CITA_B_NUEVA_HORA = "17:00"
CITA_B_NUEVA_FECHA = CITA_B_FECHA

ESPERA_MENSAJE = 45      # tras cada mensaje al bot
ESPERA_CITA = 90         # tras crear una cita, para el trigger del flujo 2
ESPERA_TRIGGER = 180     # sondeo maximo del trigger del flujo 2
ESPERA_AGENTE = 180      # sondeo maximo de la ejecucion del agente

# ---------------------------------------------------------------------------
# Registro de resultados
# ---------------------------------------------------------------------------
resultados = []     # (seccion, ok, descripcion, detalle)
hallazgos = []      # fallos concretos


def check(seccion, ok, descripcion, detalle=""):
    resultados.append((seccion, bool(ok), descripcion, detalle))
    print("  [%s] %s" % ("OK   " if ok else "FALLO", descripcion))
    if detalle and not ok:
        for linea in str(detalle).splitlines():
            print("         " + linea)
    if not ok:
        hallazgos.append("%s :: %s%s" % (seccion, descripcion,
                                         (" -> " + detalle) if detalle else ""))
    return bool(ok)


def titulo(txt):
    print("\n" + "=" * 74)
    print(txt)
    print("=" * 74)


# ---------------------------------------------------------------------------
# Utilidades HTTP / n8n / docker / hoja
# ---------------------------------------------------------------------------
def api(method, path, body=None, timeout=90):
    """Llamada a la API publica de n8n. Devuelve (status, payload)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def detalle_ejecucion(eid):
    """runData de una ejecucion, o (None, ...) si no existe (fue borrada)."""
    st, det = api("GET", "/executions/%s?includeData=true" % eid)
    if st != 200 or not isinstance(det, dict):
        return None, st, det
    run = (((det.get("data") or {}).get("resultData") or {})
           .get("runData") or {})
    return {"status": det.get("status"), "finished": det.get("finished"),
            "run": run, "raw": det}, st, det


def errores_en(run):
    """Recorre el runData y devuelve los nodos con objeto 'error'."""
    fuera = []

    def rec(obj, ruta, prof=0):
        if prof > 14:
            return
        if isinstance(obj, dict):
            if isinstance(obj.get("error"), dict):
                e = obj["error"]
                fuera.append({
                    "ruta": ruta,
                    "nodo": ((e.get("node") or {}).get("name")),
                    "message": str(e.get("message")),
                    "description": str(e.get("description")),
                    "httpCode": e.get("httpCode"),
                })
            for k, v in obj.items():
                rec(v, ruta + "/" + str(k), prof + 1)
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:6]):
                rec(v, ruta + "[%d]" % i, prof + 1)

    rec(run, "")
    return fuera


def apikey_evolution():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def enviar_al_bot(texto, jid, apikey, push="Prueba E2E"):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": apikey,
        "date_time": "2026-09-25T20:00:00.000Z",
        "data": {
            "key": {"id": "E" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": jid, "fromMe": False},
            "pushName": push,
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def leer_hoja():
    """Lee la hoja de citas por su export CSV publico."""
    req = urllib.request.Request(HOJA_CSV)
    with urllib.request.urlopen(req, timeout=60) as r:
        crudo = r.read().decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(crudo)))


def ids_agente(limit=8):
    st, ex = api("GET", "/executions?workflowId=%s&limit=%d"
                 % (WF_AGENTE, limit))
    return {e["id"] for e in ex.get("data", [])} if st == 200 else set()


def esperar_agente(msg_enviado, previos=(), espera_max=ESPERA_AGENTE):
    """Espera la ejecucion del agente que corresponde al mensaje enviado.

    Se ignoran las ejecuciones anteriores al envio (previos y cualquier id
    menor o igual a la linea base) para no confundir una respuesta vieja.
    """
    base = 0
    for i in previos:
        try:
            base = max(base, int(i))
        except Exception:
            pass
    t0 = time.time()
    while time.time() - t0 < espera_max:
        time.sleep(10)
        st, ex = api("GET", "/executions?workflowId=%s&limit=8" % WF_AGENTE)
        if st != 200:
            continue
        for e in ex.get("data", []):
            if e["id"] in previos:
                continue
            try:
                if int(e["id"]) <= base:
                    continue
            except Exception:
                pass
            info, st2, _ = detalle_ejecucion(e["id"])
            if not info:
                continue
            run = info["run"]
            contenido = ""
            if "Normalizacion" in run:
                try:
                    contenido = (run["Normalizacion"][0]["data"]["main"][0][0]
                                 ["json"].get("message_content") or "").strip()
                except Exception:
                    contenido = ""
            if contenido != msg_enviado.strip():
                continue
            texto = ""
            if "AI Agent" in run:
                try:
                    texto = (run["AI Agent"][0]["data"]["main"][0][0]["json"]
                             .get("output") or "")
                except Exception:
                    texto = ""
            if texto or info["status"] == "error" or info["finished"]:
                return {"id": e["id"], "status": info["status"], "run": run,
                        "output": texto, "errores": errores_en(run)}
    return None


def ejecuciones_flujo2(limit=30):
    st, ex = api("GET", "/executions?workflowId=%s&limit=%d"
                 % (WF_RECORD, limit))
    return ex.get("data", []) if st == 200 else []


def esperar_trigger_flujo2(antes, espera=ESPERA_TRIGGER):
    """Espera ejecuciones del flujo 2 nuevas respecto de 'antes'."""
    t0 = time.time()
    while time.time() - t0 < espera:
        time.sleep(8)
        actuales = ejecuciones_flujo2()
        nuevas = [e for e in actuales if e["id"] not in antes]
        if nuevas:
            time.sleep(8)
            actuales = ejecuciones_flujo2()
            nuevas = [e for e in actuales if e["id"] not in antes]
            if nuevas:
                return nuevas
    return []


def flujo2_por_evento(event_id, cuantas=30):
    """Ejecucion del flujo 2 cuyo trigger traia ese ID de calendario."""
    for e in ejecuciones_flujo2(cuantas):
        info, st, _ = detalle_ejecucion(e["id"])
        if not info:
            continue
        run = info["run"]
        for nodo in ("Google Sheets Trigger", "Code"):
            if nodo in run:
                try:
                    js = run[nodo][0]["data"]["main"][0][0]["json"]
                except Exception:
                    continue
                if str(js.get("ID")) == str(event_id):
                    return {"id": e["id"], "status": info["status"],
                            "run": run, "nodos": list(run.keys()),
                            "errores": errores_en(run)}
    return None


# ---------------------------------------------------------------------------
# Workflow TEMPORAL de solo lectura del calendario
# ---------------------------------------------------------------------------
def crear_lector_calendario():
    """Crea un workflow propio de SOLO LECTURA para poder ver el calendario."""
    ruta = "vercal" + uuid.uuid4().hex[:8]
    codigo = """return [{ json: { eventos: $input.all().map(i => ({
  id: i.json.id,
  summary: i.json.summary,
  start: (i.json.start || {}).dateTime || (i.json.start || {}).date,
  end: (i.json.end || {}).dateTime || (i.json.end || {}).date
})) } }];"""
    wf = {"name": WF_TEMP, "nodes": [
        {"parameters": {"httpMethod": "POST", "path": ruta,
                        "responseMode": "lastNode", "options": {}},
         "type": "n8n-nodes-base.webhook", "typeVersion": 2,
         "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
         "webhookId": str(uuid.uuid4())},
        {"parameters": {"operation": "getAll",
                        "calendar": {"__rl": True, "value": CAL_ID,
                                     "mode": "list",
                                     "cachedResultName": "BARBER"},
                        "returnAll": True,
                        "options": {"singleEvents": True}},
         "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
         "position": [220, 0], "id": str(uuid.uuid4()), "name": "Listar",
         "credentials": CRED_CAL},
        {"parameters": {"jsCode": codigo}, "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [440, 0], "id": str(uuid.uuid4()),
         "name": "Resumir"}],
        "connections": {
            "Webhook": {"main": [[{"node": "Listar", "type": "main",
                                   "index": 0}]]},
            "Listar": {"main": [[{"node": "Resumir", "type": "main",
                                  "index": 0}]]}},
        "settings": {"executionOrder": "v1"}}

    st, lista = api("GET", "/workflows?limit=100")
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == WF_TEMP:
            if w.get("active"):
                api("POST", "/workflows/%s/deactivate" % w["id"], {})
            api("DELETE", "/workflows/%s" % w["id"])

    st, creado = api("POST", "/workflows", wf)
    if st not in (200, 201):
        print("  no pude crear el lector temporal:", st, creado)
        return None, None
    wid = creado["id"]
    api("POST", "/workflows/%s/activate" % wid, {})
    return ruta, wid


def leer_calendario(ruta, intentos=8):
    if not ruta:
        return None
    for i in range(intentos):
        time.sleep(4)
        try:
            req = urllib.request.Request(
                "http://localhost:5678/webhook/" + ruta, data=b"{}",
                method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode()).get("eventos") or []
        except Exception:
            continue
    return None


def borrar_lector(wid):
    if not wid:
        return
    time.sleep(2)
    api("POST", "/workflows/%s/deactivate" % wid, {})
    time.sleep(1)
    api("DELETE", "/workflows/%s" % wid)


# ---------------------------------------------------------------------------
# Helpers de inspeccion del agente
# ---------------------------------------------------------------------------
def buscar_evento(obj, prof=0):
    """Primer dict con pinta de evento de Calendar dentro del runData."""
    if prof > 14:
        return None
    if isinstance(obj, dict):
        if "id" in obj and ("start" in obj or "htmlLink" in obj
                            or "summary" in obj):
            return obj
        for v in obj.values():
            r = buscar_evento(v, prof + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj[:20]:
            r = buscar_evento(v, prof + 1)
            if r:
                return r
    return None


def herramienta_erronea(res, nombre):
    """(bool_error | None, mensaje) de una herramienta del runData."""
    run = res["run"]
    if nombre not in run:
        return None, "la herramienta no se ejecuto"
    txt = json.dumps(run[nombre], ensure_ascii=False)
    malo = ("NodeApiError" in txt or "Forbidden" in txt
            or '"error":{' in txt or '"error": {' in txt)
    if not malo:
        return False, ""
    i = txt.find('"message"')
    return True, (txt[i:i + 220] if i >= 0 else txt[:220])


def respuesta_herramienta(res, nombre):
    """Payload 'response' que devolvio la herramienta (dict o lista).

    OJO: en el flujo el nodo se llama 'Registrar en hoja de citas' tanto en el
    agente (registro para el modelo) como en el flujo 2.
    """
    run = res["run"]
    if nombre not in run:
        return None
    try:
        return run[nombre][0]["data"]["ai_tool"][0][0]["json"].get("response")
    except Exception:
        return None


def entrada_herramienta(res, nombre):
    """Valores que el modelo le paso a la herramienta (inputOverride)."""
    run = res["run"]
    if nombre not in run:
        return None
    try:
        return run[nombre][0]["data"]["ai_tool"][0]["inputOverride"]["ai_tool"][0][0]["json"]
    except Exception:
        try:
            return run[nombre][0]["inputOverride"]["ai_tool"][0][0]["json"]
        except Exception:
            return None


# ===========================================================================
# PARTE 1 - CANCELAR
# ===========================================================================
def parte1(apikey, ruta_cal):
    titulo("PARTE 1 - CANCELAR UNA CITA")

    check("P1", True, "API key de Evolution obtenida (%s...)" % apikey[:8])

    cal_ini = leer_calendario(ruta_cal)
    check("P1.calendario", cal_ini is not None,
          "Lectura inicial del calendario (%s eventos)"
          % (len(cal_ini) if cal_ini is not None else "?"))

    # --- 1. Crear la cita -------------------------------------------------
    print("\n>>> [1] Pidiendo al bot una cita el %s a las %s (%s)"
          % (CITA_A_FECHA, CITA_A_HORA, JID_A))
    msg1 = ("Hola, quiero una cita para un corte desvanecido el %s a las %s. "
            "Mi nombre es Prueba Cancelar."
            % (CITA_A_FECHA, CITA_A_HORA))
    previos = ids_agente()
    enviar_al_bot(msg1, JID_A, apikey, "Prueba Cancelar")
    print("    esperando %d s la respuesta del agente..." % ESPERA_MENSAJE)
    time.sleep(ESPERA_MENSAJE)
    res1 = esperar_agente(msg1, previos)

    if not check("P1.agendar", res1 is not None,
                 "El agente proceso el mensaje de agendado"):
        return None
    print("    ejecucion del agente: %s (status %s)"
          % (res1["id"], res1["status"]))
    print("    respuesta del bot: %s" % (res1["output"] or "")[:300])

    check("P1.agendar", res1["status"] == "success",
          "Estado de la ejecucion del agendado: %s" % res1["status"])
    for e in res1["errores"][:3]:
        check("P1.agendar", False,
              "Nodo con error en el agendado: %s" % e["nodo"],
              "%s | %s" % (e["message"], e["description"][:200]))

    err_her, txt_her = herramienta_erronea(res1, "Agendar cita")
    if err_her is None:
        check("P1.agendar", False,
              "'Agendar cita' NO se ejecuto (el agente no creo la cita)",
              "respuesta del bot: %s" % (res1["output"] or "")[:250])
        check("P1.agendar", False,
              "Herramientas ejecutadas: %s"
              % [k for k in res1["run"]
                 if k in ("Consultar agenda", "Agendar cita", "Cancelar cita",
                          "Reagendar", "Registrar en hoja de citas")])
        return None
    check("P1.agendar", err_her is False,
          "Herramienta 'Agendar cita' sin error", txt_her)

    ev = buscar_evento(res1["run"].get("Agendar cita"))
    if not check("P1.agendar", ev is not None,
                 "Se obtuvo el ID del evento creado por 'Agendar cita'"):
        return None
    event_id = str(ev.get("id")).split("_")[0]
    print("    EVENT ID = %s" % event_id)
    print("    start=%s  end=%s  summary=%s"
          % ((ev.get("start") or {}).get("dateTime"),
             (ev.get("end") or {}).get("dateTime"), ev.get("summary")))

    # OJO: el agente suele pasar el SUMMARY como "ID" a la herramienta
    # "Registrar en hoja de citas" en vez del ID del evento. Hay que anotarlo
    # porque rompe la coincidencia hoja <-> calendario del flujo 2.
    ent_reg = entrada_herramienta(res1, "Registrar en hoja de citas")
    id_que_registro = str((ent_reg or {}).get("ID", "")).strip()
    print("    ID que el agente registro en la hoja: %r (evento real: %s)"
          % (id_que_registro, event_id))
    if id_que_registro and id_que_registro != event_id:
        check("P1.hoja", False,
              "BUG de tool-calling: 'Registrar en hoja de citas' recibio %r "
              "en vez del ID del evento (%s)"
              % (id_que_registro, event_id),
              "El flujo 2 busca la fila por 'ID', asi que con este valor no "
              "puede volver a encontrarla.")

    # --- 2. Esperar el trigger del flujo 2 --------------------------------
    print("\n>>> [2] Esperando %d s al trigger del flujo 2..." % ESPERA_CITA)
    antes = {e["id"] for e in ejecuciones_flujo2()}
    time.sleep(ESPERA_CITA)
    nuevas = esperar_trigger_flujo2(antes)
    check("P1.trigger", bool(nuevas),
          "El flujo 2 arranco por la fila nueva (%d ejecucion/es: %s)"
          % (len(nuevas), [e["id"] for e in nuevas]))

    f2_1 = None
    for e in nuevas:
        info, st, _ = detalle_ejecucion(e["id"])
        if not info:
            continue
        if "Switch" in info["run"]:
            f2_1 = {"id": e["id"], "status": info["status"], "run": info["run"],
                    "errores": errores_en(info["run"])}
    if f2_1 is None:
        f2_1 = flujo2_por_evento(event_id)

    if not check("P1.trigger", f2_1 is not None,
                 "Encontre la ejecucion del flujo 2 de esta cita"):
        return None

    if f2_1["errores"]:
        for x in f2_1["errores"][:3]:
            check("P1.trigger", False,
                  "Nodo con error en el flujo 2 (alta): %s"
                  % (x["nodo"] or x["ruta"]),
                  "%s | %s" % (x["message"], x["description"][:200]))
    else:
        check("P1.trigger", True, "La ejecucion de alta del flujo 2 no tiene errores")

    check("P1.trigger", "ESPERAR A 24 H" in f2_1["run"],
          "La ejecucion llego al nodo 'ESPERAR A 24 H'",
          "nodos: %s" % list(f2_1["run"].keys()))
    check("P1.trigger", f2_1["status"] == "waiting",
          "La ejecucion del flujo 2 quedo en status 'waiting' (era %s)"
          % f2_1["status"])
    ejec_id = None
    try:
        ejec_id = str(f2_1["run"]["Code1"][0]["data"]["main"][0][0]
                      ["json"].get("executionId"))
    except Exception:
        ejec_id = None
    check("P1.trigger", bool(ejec_id) and ejec_id != "None",
          "El nodo 'Code1' guardo el Execution ID (%s)" % ejec_id)

    # --- 3. Cancelar ------------------------------------------------------
    print("\n>>> [3] Pidiendo al bot que CANCELE la cita del %s a las %s"
          % (CITA_A_FECHA, CITA_A_HORA))
    msg2 = ("Hola, necesito cancelar mi cita del %s a las %s. Ya no puedo ir, "
            "por favor cancelala." % (CITA_A_FECHA, CITA_A_HORA))
    antes2 = {e["id"] for e in ejecuciones_flujo2()}
    previos2 = ids_agente()
    enviar_al_bot(msg2, JID_A, apikey, "Prueba Cancelar")
    print("    esperando %d s la respuesta del agente..." % ESPERA_MENSAJE)
    time.sleep(ESPERA_MENSAJE)
    res2 = esperar_agente(msg2, previos2)

    if not check("P1.cancelar", res2 is not None,
                 "El agente proceso el mensaje de cancelacion"):
        return {"event_id": event_id, "ejec_id": ejec_id, "f2": f2_1}
    print("    ejecucion del agente: %s (status %s)"
          % (res2["id"], res2["status"]))
    print("    respuesta del bot: %s" % (res2["output"] or "")[:300])
    check("P1.cancelar", res2["status"] == "success",
          "Estado de la ejecucion del cancelado: %s" % res2["status"])
    for e in res2["errores"][:3]:
        check("P1.cancelar", False,
              "Nodo con error en el cancelado: %s" % e["nodo"],
              "%s | %s" % (e["message"], e["description"][:200]))

    err_c, txt_c = herramienta_erronea(res2, "Cancelar cita")
    check("P1.cancelar", err_c is not None,
          "La herramienta 'Cancelar cita' se ejecuto", txt_c)
    check("P1.cancelar", err_c is not True,
          "La herramienta 'Cancelar cita' no dio error", txt_c)
    ent_c = entrada_herramienta(res2, "Cancelar cita")
    print("    'Cancelar cita' recibio: %s" % json.dumps(ent_c, ensure_ascii=False))
    check("P1.cancelar", str((ent_c or {}).get("Event_ID", "")).strip() == event_id,
          "La herramienta 'Cancelar cita' recibio el ID correcto del evento",
          "esperado %s, recibido %r (si el ID no coincide, la hoja y el "
          "calendario quedan desincronizados)"
          % (event_id, (ent_c or {}).get("Event_ID")))

    # --- 4. Calendario: el evento ya no existe ----------------------------
    print("\n>>> [4] Verificando el calendario...")
    cal_fin = leer_calendario(ruta_cal)
    check("P1.calendario", cal_fin is not None,
          "Segunda lectura del calendario (%s eventos)"
          % (len(cal_fin) if cal_fin is not None else "?"))
    if cal_fin is not None:
        vivos = [e for e in cal_fin if str(e.get("id")).split("_")[0] == event_id]
        check("P1.calendario", not vivos,
              "El evento %s YA NO EXISTE en el calendario" % event_id,
              "todavia presente: %s" % vivos)

    # --- 5. Hoja: fila nueva con Estatus = cancelado ----------------------
    print("\n>>> [5] Verificando la hoja de citas...")
    try:
        hoja = leer_hoja()
    except Exception as e:
        hoja = None
        check("P1.hoja", False, "No pude leer la hoja", str(e)[:200])
    if hoja is not None:
        print("    filas de la hoja: %d" % len(hoja))
        for f in hoja:
            print("      ID=%-45s Estatus=%-12s %s %s %s"
                  % (str(f.get("ID"))[:45], f.get("Estatus"),
                     f.get("Día "), f.get("Hora"), f.get("Execution ID")))
        filas_ev = [f for f in hoja
                    if str(f.get("ID", "")).strip() == event_id]
        filas_txt = [f for f in hoja
                     if "prueba cancelar" in str(f.get("Nombre", "")).lower()
                     or str(f.get("ID", "")).strip() == id_que_registro]
        print("    filas que apuntan al evento real: %d" % len(filas_ev))
        print("    filas de 'Prueba Cancelar' / con el ID que el agente "
              "registro: %d" % len(filas_txt))
        estados = [str(f.get("Estatus", "")).strip().lower() for f in filas_txt]
        check("P1.hoja",
              any("cancelad" in s or "eliminad" in s for s in estados),
              "Hay una fila con Estatus = cancelado para la cita",
              "estatus encontrados en las filas de la cita: %s" % estados)
        check("P1.hoja", bool(filas_ev),
              "Existe una fila cuyo ID es el ID real del evento (%s)"
              % event_id,
              "NINGUNA fila usa el ID del evento: la hoja y el calendario no "
              "se pueden cruzar por ID")

    # --- 6. El flujo 2 proceso la cancelacion -----------------------------
    print("\n>>> [6] Verificando que el flujo 2 proceso la cancelacion...")
    nuevas2 = esperar_trigger_flujo2(antes2, espera=ESPERA_TRIGGER)
    check("P1.flujo2", bool(nuevas2),
          "El flujo 2 arranco por la fila 'cancelado' (%d ejecucion/es: %s)"
          % (len(nuevas2), [e["id"] for e in nuevas2]))

    f2_cancel = None
    for e in nuevas2:
        info, st, _ = detalle_ejecucion(e["id"])
        if not info:
            continue
        if "Switch" in info["run"]:
            f2_cancel = {"id": e["id"], "status": info["status"],
                         "run": info["run"], "errores": errores_en(info["run"])}
    if f2_cancel is None:
        for e in nuevas2:
            info, st, _ = detalle_ejecucion(e["id"])
            if info:
                f2_cancel = {"id": e["id"], "status": info["status"],
                             "run": info["run"],
                             "errores": errores_en(info["run"])}

    if check("P1.flujo2", f2_cancel is not None,
             "Encontre la ejecucion del flujo 2 del cancelado"):
        nodos = list(f2_cancel["run"].keys())
        print("    nodos: %s" % nodos)
        check("P1.flujo2", "OBTENER INFO DE CITA ELIMINADA" in f2_cancel["run"],
              "La rama 'Cancelado' del Switch llego a 'OBTENER INFO DE CITA "
              "ELIMINADA'")
        check("P1.flujo2", "QUITAR RECORDATORIO" in f2_cancel["run"],
              "Despues se ejecuto 'QUITAR RECORDATORIO'")
        er_c = [x for x in f2_cancel["errores"]]
        if er_c:
            for x in er_c[:3]:
                check("P1.flujo2", False,
                      "Nodo con error en el flujo 2 (cancelado): %s"
                      % (x["nodo"] or x["ruta"]),
                      "%s | %s | http=%s"
                      % (x["message"], x["description"][:200], x["httpCode"]))
        else:
            check("P1.flujo2", True,
                  "'QUITAR RECORDATORIO' termino SIN error (credencial n8nApi)"
                  )

    # La ejecucion en espera debe haber dejado de esperar o haber sido borrada
    if ejec_id:
        info_w, st_w, raw_w = detalle_ejecucion(ejec_id)
        if info_w is None:
            check("P1.espera", True,
                  "La ejecucion en espera %s YA NO EXISTE (la borro "
                  "'QUITAR RECORDATORIO')" % ejec_id)
        else:
            check("P1.espera", info_w["status"] != "waiting",
                  "La ejecucion %s ya no esta esperando (status=%s)"
                  % (ejec_id, info_w["status"]),
                  "sigue en status 'waiting': el recordatorio NO se quito")

    return {"event_id": event_id, "ejec_id": ejec_id, "f2_alta": f2_1,
            "f2_cancel": f2_cancel}


# ===========================================================================
# PARTE 2 - REPROGRAMAR
# ===========================================================================
def parte2(apikey, ruta_cal):
    titulo("PARTE 2 - REPROGRAMAR UNA CITA")

    # --- 1. Crear la segunda cita -----------------------------------------
    print("\n>>> [1] Pidiendo al bot una cita el %s a las %s (%s)"
          % (CITA_B_FECHA, CITA_B_HORA, JID_B))
    msg1 = ("Hola, quiero apartar una mascarilla para el %s a las %s. "
            "Soy Prueba Reprogramar." % (CITA_B_FECHA, CITA_B_HORA))
    antes = {e["id"] for e in ejecuciones_flujo2()}
    previos = ids_agente()
    enviar_al_bot(msg1, JID_B, apikey, "Prueba Reprogramar")
    print("    esperando %d s la respuesta del agente..." % ESPERA_MENSAJE)
    time.sleep(ESPERA_MENSAJE)
    res1 = esperar_agente(msg1, previos)

    if not check("P2.agendar", res1 is not None,
                 "El agente proceso el mensaje de agendado"):
        return None
    print("    ejecucion: %s (status %s)" % (res1["id"], res1["status"]))
    print("    respuesta del bot: %s" % (res1["output"] or "")[:300])
    check("P2.agendar", res1["status"] == "success",
          "Estado de la ejecucion del agendado: %s" % res1["status"])
    for e in res1["errores"][:3]:
        check("P2.agendar", False,
              "Nodo con error en el agendado: %s" % e["nodo"],
              "%s | %s" % (e["message"], e["description"][:200]))

    err_a, txt_a = herramienta_erronea(res1, "Agendar cita")
    if err_a is None:
        check("P2.agendar", False,
              "'Agendar cita' NO se ejecuto (el agente no creo la cita)",
              "respuesta: %s" % (res1["output"] or "")[:250])
        return None
    check("P2.agendar", err_a is False,
          "Herramienta 'Agendar cita' sin error", txt_a)

    ev = buscar_evento(res1["run"].get("Agendar cita"))
    if not check("P2.agendar", ev is not None,
                 "Se obtuvo el ID del evento creado"):
        return None
    event_id = str(ev.get("id")).split("_")[0]
    ini_original = (ev.get("start") or {}).get("dateTime")
    fin_original = (ev.get("end") or {}).get("dateTime")
    print("    EVENT ID = %s" % event_id)
    print("    start=%s  end=%s" % (ini_original, fin_original))
    ent_reg = entrada_herramienta(res1, "Registrar en hoja de citas")
    id_que_registro = str((ent_reg or {}).get("ID", "")).strip()
    print("    ID que el agente registro en la hoja: %r" % id_que_registro)
    check("P2.hoja", id_que_registro == event_id,
          "El agente registro en la hoja el ID REAL del evento",
          "registro %r en vez de %s: la hoja y el calendario no se pueden "
          "cruzar por ID" % (id_que_registro, event_id))

    # Trigger del flujo 2
    print("\n    esperando %d s al trigger del flujo 2..." % ESPERA_CITA)
    time.sleep(ESPERA_CITA)
    nuevas = esperar_trigger_flujo2(antes)
    f2_alta = None
    for e in nuevas:
        info, st, _ = detalle_ejecucion(e["id"])
        if info and "Switch" in info["run"]:
            f2_alta = {"id": e["id"], "status": info["status"],
                       "run": info["run"], "errores": errores_en(info["run"])}
    if f2_alta is None:
        f2_alta = flujo2_por_evento(event_id)
    check("P2.trigger", f2_alta is not None,
          "El flujo 2 proceso el alta de la segunda cita",
          "ejecuciones nuevas: %s" % [e["id"] for e in nuevas])
    if f2_alta:
        check("P2.trigger", "ESPERAR A 24 H" in f2_alta["run"],
              "El alta llego a 'ESPERAR A 24 H'")

    # --- 2. Reprogramar ---------------------------------------------------
    print("\n>>> [2] Pidiendo al bot que MUEVA la cita de las %s a las %s"
          % (CITA_B_HORA, CITA_B_NUEVA_HORA))
    msg2 = ("Hola, necesito mover mi mascarilla del %s: pasala de las %s a las "
            "%s del mismo dia." % (CITA_B_FECHA, CITA_B_HORA,
                                   CITA_B_NUEVA_HORA))
    antes2 = {e["id"] for e in ejecuciones_flujo2()}
    previos2 = ids_agente()
    enviar_al_bot(msg2, JID_B, apikey, "Prueba Reprogramar")
    print("    esperando %d s la respuesta del agente..." % ESPERA_MENSAJE)
    time.sleep(ESPERA_MENSAJE)
    res2 = esperar_agente(msg2, previos2)

    if not check("P2.reprogramar", res2 is not None,
                 "El agente proceso el mensaje de reprogramacion"):
        return None
    print("    ejecucion: %s (status %s)" % (res2["id"], res2["status"]))
    print("    respuesta del bot: %s" % (res2["output"] or "")[:300])
    check("P2.reprogramar", res2["status"] == "success",
          "Estado de la ejecucion del reprogramado: %s" % res2["status"])
    for e in res2["errores"][:3]:
        check("P2.reprogramar", False,
              "Nodo con error en el reprogramado: %s" % e["nodo"],
              "%s | %s" % (e["message"], e["description"][:200]))

    err_r, txt_r = herramienta_erronea(res2, "Reagendar")
    check("P2.reprogramar", err_r is not None,
          "La herramienta 'Reagendar' se ejecuto", txt_r)
    check("P2.reprogramar", err_r is not True,
          "La herramienta 'Reagendar' no dio error", txt_r)
    ent_r = entrada_herramienta(res2, "Reagendar")
    print("    'Reagendar' recibio: %s" % json.dumps(ent_r, ensure_ascii=False))
    check("P2.reprogramar",
          str((ent_r or {}).get("Event_ID", "")).strip() == event_id,
          "La herramienta 'Reagendar' recibio el ID correcto del evento",
          "esperado %s, recibido %r"
          % (event_id, (ent_r or {}).get("Event_ID")))

    # --- 3. Calendario: el evento se movio --------------------------------
    print("\n>>> [3] Verificando el calendario...")
    cal = leer_calendario(ruta_cal)
    check("P2.calendario", cal is not None, "Lectura del calendario")
    if cal:
        mio = [e for e in cal if str(e.get("id")).split("_")[0] == event_id]
        check("P2.calendario", len(mio) == 1,
              "El evento %s sigue existiendo (se movio, no se duplico)"
              % event_id, "encontrados: %s" % mio)
        if mio:
            ini_nuevo = mio[0].get("start")
            fin_nuevo = mio[0].get("end")
            print("    antes: %s -> %s" % (ini_original, fin_original))
            print("    ahora: %s -> %s" % (ini_nuevo, fin_nuevo))
            check("P2.calendario", ini_nuevo != ini_original,
                  "El start del evento CAMBIO (%s -> %s)"
                  % (ini_original, ini_nuevo))
            check("P2.calendario", str(ini_nuevo or "").startswith(
                CITA_B_FECHA + "T" + CITA_B_NUEVA_HORA),
                "El nuevo start es el pedido (%sT%s)"
                % (CITA_B_FECHA, CITA_B_NUEVA_HORA), "start=%s" % ini_nuevo)

    # --- 4. Hoja: se registro el cambio -----------------------------------
    print("\n>>> [4] Verificando la hoja de citas...")
    try:
        hoja = leer_hoja()
    except Exception as e:
        hoja = None
        check("P2.hoja", False, "No pude leer la hoja", str(e)[:200])
    if hoja is not None:
        print("    filas de la hoja: %d" % len(hoja))
        for f in hoja:
            print("      ID=%-45s Estatus=%-12s %s %s %s"
                  % (str(f.get("ID"))[:45], f.get("Estatus"),
                     f.get("Día "), f.get("Hora"), f.get("Execution ID")))
        filas_ev = [f for f in hoja
                    if str(f.get("ID", "")).strip() == event_id]
        filas_txt = [f for f in hoja
                     if "prueba reprogramar" in str(f.get("Nombre", "")).lower()
                     or (id_que_registro
                         and str(f.get("ID", "")).strip() == id_que_registro)]
        print("    filas que apuntan al evento real: %d" % len(filas_ev))
        print("    filas de 'Prueba Reprogramar': %d" % len(filas_txt))
        estados = [str(f.get("Estatus", "")).strip().lower() for f in filas_txt]
        check("P2.hoja",
              any(("actualiz" in s or "reprogram" in s or "reagend" in s)
                  for s in estados),
              "Hay una fila con Estatus = actualizado/reprogramado",
              "estatus encontrados en las filas de la cita: %s" % estados)
        check("P2.hoja", bool(filas_ev),
              "Existe una fila para el ID del evento reprogramado (%s)"
              % event_id,
              "el calendario y la hoja no coinciden por ID")

    # --- 5. El Switch del flujo 2 enruta Actualizado ----------------------
    print("\n>>> [5] Verificando que el flujo 2 proceso la reprogramacion...")
    nuevas2 = esperar_trigger_flujo2(antes2, espera=ESPERA_TRIGGER)
    check("P2.flujo2", bool(nuevas2),
          "El flujo 2 arranco por la fila 'actualizado' (%d ejecucion/es)"
          % len(nuevas2), "ids: %s" % [e["id"] for e in nuevas2])

    f2_upd = None
    for e in nuevas2:
        info, st, _ = detalle_ejecucion(e["id"])
        if info and "Switch" in info["run"]:
            f2_upd = {"id": e["id"], "status": info["status"],
                      "run": info["run"], "errores": errores_en(info["run"])}
    if f2_upd is None:
        for e in nuevas2:
            info, st, _ = detalle_ejecucion(e["id"])
            if info:
                f2_upd = {"id": e["id"], "status": info["status"],
                          "run": info["run"],
                          "errores": errores_en(info["run"])}

    if check("P2.flujo2", f2_upd is not None,
             "Encontre la ejecucion del flujo 2 de la reprogramacion"):
        print("    nodos: %s" % list(f2_upd["run"].keys()))
        check("P2.flujo2", "OBTENER INFO DE CITA ELIMINADA" in f2_upd["run"],
              "La rama 'Actualizado' del Switch llego a 'OBTENER INFO DE "
              "CITA ELIMINADA'")
        check("P2.flujo2", "QUITAR RECORDATORIO" in f2_upd["run"],
              "Se ejecuto 'QUITAR RECORDATORIO' (borra el recordatorio viejo)")
        if f2_upd["errores"]:
            for x in f2_upd["errores"][:3]:
                check("P2.flujo2", False,
                      "Nodo con error en el flujo 2 (reprogramacion): %s"
                      % (x["nodo"] or x["ruta"]),
                      "%s | %s | http=%s"
                      % (x["message"], x["description"][:200], x["httpCode"]))
        else:
            check("P2.flujo2", True,
                  "'QUITAR RECORDATORIO' termino SIN error")

    return {"event_id": event_id, "f2_upd": f2_upd}


# ===========================================================================
# PARTE 3 - RESUMEN DE HALLAZGOS
# ===========================================================================
def parte3():
    titulo("PARTE 3 - RESUMEN DE HALLAZGOS")

    print("\n--- Configuracion estatica de los workflows ---")
    st, wf2 = api("GET", "/workflows/%s" % WF_RECORD)
    if st == 200:
        nodos = {n["name"]: n for n in wf2.get("nodes", [])}
        qr = nodos.get("QUITAR RECORDATORIO", {})
        cred = (qr.get("credentials") or {}).get("n8nApi")
        check("P3.credencial", bool(cred),
              "'QUITAR RECORDATORIO' tiene credencial n8nApi asignada",
              "credential = %s" % cred)
        print("      recurso=%s operacion=%s executionId=%s"
              % (qr.get("parameters", {}).get("resource"),
                 qr.get("parameters", {}).get("operation"),
                 qr.get("parameters", {}).get("executionId")))
        sw = nodos.get("Switch", {})
        valores = []
        for regla in (sw.get("parameters", {}).get("rules", {})
                      .get("values", [])):
            for c in regla.get("conditions", {}).get("conditions", []):
                valores.append((regla.get("outputKey"), c.get("rightValue")))
        print("      Switch (salida, valor comparado): %s" % valores)
        check("P3.switch",
              ("Cancelado", "cancelado") in valores
              and ("Actualizado", "actualizado") in valores,
              "El Switch reconoce 'cancelado' y 'actualizado'")

    print("\n--- Errores encontrados en el flujo 2 (barberiaRecordatorios) ---")
    malos = []
    for e in ejecuciones_flujo2(40):
        info, st, _ = detalle_ejecucion(e["id"])
        if not info:
            continue
        for x in errores_en(info["run"]):
            malos.append((e["id"], info["status"], x))
    if malos:
        for eid, st, x in malos[:12]:
            print("   exec %-5s %-8s %-32s %s | %s"
                  % (eid, st, (x["nodo"] or x["ruta"]),
                     x["message"], x["description"][:120]))
        check("P3.errores", False,
              "Hay %d errores en ejecuciones recientes del flujo 2" % len(malos),
              "\n".join("exec %s: %s -> %s"
                        % (eid, (x["nodo"] or x["ruta"]), x["message"])
                        for eid, st, x in malos[:6]))
    else:
        check("P3.errores", True,
              "Sin errores en las ejecuciones recientes del flujo 2")

    titulo("INFORME FINAL")
    ok = sum(1 for r in resultados if r[1])
    mal = len(resultados) - ok
    for seccion in ("P1", "P1.entorno", "P1.agendar", "P1.trigger",
                    "P1.cancelar", "P1.calendario", "P1.hoja", "P1.flujo2",
                    "P1.espera",
                    "P2", "P2.agendar", "P2.trigger", "P2.reprogramar",
                    "P2.calendario", "P2.hoja", "P2.flujo2",
                    "P3.credencial", "P3.switch", "P3.errores"):
        del_seccion = [r for r in resultados if r[0] == seccion]
        if not del_seccion:
            continue
        print("\n%s" % seccion)
        for _, bien, desc, det in del_seccion:
            print("   %s %s" % ("OK   " if bien else "FALLO", desc))
            if not bien and det:
                for linea in str(det).splitlines():
                    print("         " + linea)

    print("\n" + "-" * 74)
    print("TOTAL: %d verificaciones | %d OK | %d FALLOS" % (len(resultados),
                                                            ok, mal))
    if hallazgos:
        print("\nFALLOS CONCRETOS (%d):" % len(hallazgos))
        for h in hallazgos:
            print("  - " + h)
    else:
        print("\nSin fallos: no se detectaron nodos con error ni "
              "credenciales sin asignar.")
    print("-" * 74)
    return 0 if mal == 0 else 1


# ===========================================================================
def main():
    print("=" * 74)
    print("VERIFICACION E2E: CANCELAR Y REPROGRAMAR UNA CITA")
    print("Fecha/hora local: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 74)

    apikey = apikey_evolution()
    if not apikey:
        print("FALLO: no pude obtener la API key de Evolution")
        return 2

    ruta_cal, wid_cal = crear_lector_calendario()
    print("lector temporal de calendario: ruta=%s id=%s" % (ruta_cal, wid_cal))
    if not ruta_cal:
        print("FALLO: no pude crear el lector de calendario "
              "(la API publica de n8n no lista calendarios)")
        return 2

    try:
        parte1(apikey, ruta_cal)
        parte2(apikey, ruta_cal)
    except KeyboardInterrupt:
        print("\ninterrumpido por el usuario")
    except Exception as e:
        import traceback
        print("\nEXCEPCION NO CONTROLADA: %s" % e)
        traceback.print_exc()
    finally:
        borrar_lector(wid_cal)
        print("\nlector temporal de calendario eliminado")

    return parte3()


if __name__ == "__main__":
    sys.exit(main())