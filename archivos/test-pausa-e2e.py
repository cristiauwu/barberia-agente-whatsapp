#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test-pausa-e2e.py  —  Verificacion de punta a punta del comando PAUSA (Barberia)

Implementa los 7 pasos del enunciado:
  0. Limpieza previa de barber_pausas
  1. Linea base: cliente sin pausa -> el bot DEBE responder
  2. Comando PAUSA del dueno -> la fila DEBE quedar en barber_pausas
  3. Prueba clave: con pausa -> el bot DEBE callar (sin AI Agent ni Mandar mensaje)
  4. Otro cliente (no pausado) -> el bot DEBE responder (pausa selectiva)
  5. Pausa vencida -> el bot DEBE volver a responder
  6. Limpieza final de barber_pausas
  7. Estructura de los nodos del workflow (alwaysOutputData, cadena, ramas)

Reglas respetadas:
  - NO modifica workflows ni archivos existentes. Solo lee la API de n8n, envia
    POSTs al webhook y ejecuta SQL de prueba (DELETE/UPDATE) sobre barber_pausas,
    tal como piden los pasos 0, 5 y 6.
  - Al final SIEMPRE limpia barber_pausas para los jids de prueba.

Ejecutar:
  C:\\Users\\kimbo\\.cherrystudio\\bin\\uv.exe run --no-project python G:\\Barberia\\archivos\\test-pausa-e2e.py
(con PYTHONIOENCODING=utf-8; tambien fuerza UTF-8 internamente)
"""

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid

# ==========================================================================
# CONFIGURACION
# ==========================================================================
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
DOCKER_CONFIG = r"G:\Barberia\.docker"
PG_CONTAINER = "barberia-postgres"

N8N = "http://localhost:5678"
N8N_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjYmQ1ZGQ2Yi05NzJlLTRlZmYtYWVlNC03MTAzOWJmM2E5MDIi"
    "LCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmZkZmNiNDQtZmRiMi00MDUwLTg3MWMtMGJkMDI5"
    "NGRiOTYwIiwiaWF0IjoxNzkwMjk4ODczfQ.s04weO8S72yEn6ip2rCGE4wCt-wPw22xVWJij-lF4wc"
)
WORKFLOW_ID = "barberiaAgenteUncensored"
WEBHOOK = N8N + "/webhook/hector"

CLIENTE = "5214501111805@s.whatsapp.net"      # cliente que se va a pausar
CLIENTE_NUM = "5214501111805"
OTRO = "5214521206246@s.whatsapp.net"          # otro cliente NO pausado
DUENO = "524521206246@s.whatsapp.net"          # dueno (manda comandos)

ESPERA = 40          # segundos tras cada mensaje al bot (peticion del enunciado)
ESPERA_COMANDO = 20  # segundos tras el comando PAUSA

OUT = []             # lineas del informe


# ==========================================================================
# Utilidades de salida
# ==========================================================================
def log(linea=""):
    linea = str(linea)
    try:
        print(linea, flush=True)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(linea.encode(enc, "replace").decode(enc, "replace"), flush=True)
    OUT.append(linea)


def seccion(t):
    log()
    log("=" * 78)
    log(t)
    log("=" * 78)


def resumen_check(nombre, ok, detalle=""):
    estado = "OK   " if ok else "FALLO"
    linea = "  [%s] %s" % (estado, nombre)
    if detalle:
        linea += "  ->  " + detalle
    log(linea)
    return bool(ok)


# ==========================================================================
# Docker / Postgres
# ==========================================================================
_DOCKER_ENV = dict(os.environ)
_DOCKER_ENV["DOCKER_CONFIG"] = DOCKER_CONFIG


def docker(args, stdin=None, timeout=120):
    """docker.exe con captura de stdout/stderr. Devuelve (rc, out, err)."""
    try:
        p = subprocess.run(
            [DOCKER] + args,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=_DOCKER_ENV,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT tras %ss" % timeout


def sql(query, timeout=120):
    """psql -t -A. IMPORTANTE: psql manda los ERRORES a stderr, no a stdout."""
    return docker(
        ["exec", "-i", PG_CONTAINER, "psql", "-U", "barberia", "-d", "barberia",
         "-t", "-A"],
        stdin=query + "\n",
        timeout=timeout,
    )


def sql_filas(query):
    """Devuelve (filas_no_vacias, stdout_crudo, stderr_crudo)."""
    rc, out, err = sql(query)
    filas = [l.strip() for l in out.splitlines() if l.strip()]
    return filas, out.strip(), err.strip()


# ==========================================================================
# n8n API
# ==========================================================================
def api(path, timeout=60):
    req = urllib.request.Request(N8N + "/api/v1" + path)
    req.add_header("X-N8N-API-KEY", N8N_KEY)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def enviar_al_bot(jid, texto, apikey):
    """POST al webhook imitando un mensaje entrante de Evolution. Devuelve
    (status_http, cuerpo, message_id)."""
    msg_id = "T" + uuid.uuid4().hex[:10].upper()
    body = {
        "event": "messages.upsert",
        "instance": "hector",
        "server_url": "http://evolution_api:8080",
        "apikey": apikey,
        "date_time": "2026-09-25T20:00:00.000Z",
        "data": {
            "key": {"id": msg_id, "remoteJid": jid, "fromMe": False},
            "pushName": "Prueba Pausa",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(WEBHOOK, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")[:300], msg_id
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300], msg_id
    except Exception as e:  # noqa: BLE001
        return -1, "EXC: %s" % e, msg_id


def ejecuciones(limit=30):
    return api("/executions?workflowId=%s&limit=%d" % (WORKFLOW_ID, limit)).get("data", [])


def detalle(exec_id):
    return api("/executions/%s?includeData=true" % exec_id)


def run_data(det):
    return (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})


def nodos(det):
    return list(run_data(det).keys())


def json_normalizacion(det):
    try:
        return run_data(det)["Normalizacion"][0]["data"]["main"][0][0]["json"]
    except Exception:  # noqa: BLE001
        return {}


def mensaje_cliente(det):
    return json_normalizacion(det).get("message_content")


def rama_if(det, nombre):
    """Rama tomada por un nodo IF: 0=true, 1=false. En runData, 'main' tiene una
    entrada por output y la unica no vacia es la rama recorrida."""
    ents = run_data(det).get(nombre)
    if not ents:
        return None
    main = (ents[-1].get("data") or {}).get("main") or []
    tomadas = [i for i, o in enumerate(main) if o]
    if tomadas:
        return tomadas[0]
    try:
        return ents[-1]["data"]["main"][0][0]["branchIndex"]
    except Exception:  # noqa: BLE001
        return "?"


def respuesta_bot(det):
    """La respuesta del bot vive DENTRO de 'Mandar mensaje' -> message.conversation
    (NO en 'output')."""
    run = run_data(det)
    if "Mandar mensaje" not in run:
        return None
    try:
        return run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]["message"]["conversation"]
    except Exception:  # noqa: BLE001
        try:
            return "<Mandar mensaje sin conversation>: " + json.dumps(
                run["Mandar mensaje"][0]["data"]["main"][0][0]["json"],
                ensure_ascii=False)[:400]
        except Exception:  # noqa: BLE001
            return "<Mandar mensaje ilegible>"


def salida_leer_pausa(det):
    """Primer json de salida del nodo 'Leer pausa'."""
    ents = run_data(det).get("Leer pausa")
    if not ents:
        return None
    try:
        return ents[-1]["data"]["main"][0][0]["json"]
    except Exception:  # noqa: BLE001
        return None


def esperar_ejecucion(msg_id, ids_conocidos, timeout=120):
    """Espera la ejecucion cuyo Normalizacion.message_id == msg_id."""
    limite = time.time() + timeout
    candidatas = []
    while time.time() < limite:
        try:
            for e in ejecuciones(30):
                if e["id"] not in ids_conocidos:
                    candidatas.append(e["id"])
        except Exception:  # noqa: BLE001
            pass
        for cid in list(dict.fromkeys(candidatas)):
            try:
                det = detalle(cid)
            except Exception:  # noqa: BLE001
                continue
            if json_normalizacion(det).get("message_id") == msg_id:
                return det
        time.sleep(4)
    # Respaldo: la ejecucion nueva mas reciente
    for cid in list(dict.fromkeys(candidatas)):
        try:
            return detalle(cid)
        except Exception:  # noqa: BLE001
            continue
    return None


def ids_actuales():
    try:
        return {e["id"] for e in ejecuciones(30)}
    except Exception:  # noqa: BLE001
        return set()


def enviar_y_esperar(jid, texto, apikey, etiqueta, espera=ESPERA):
    """Envia, espera 'espera' segundos y devuelve (detalle, msg_id, http_status)."""
    ids = ids_actuales()
    log("  Enviando desde %s: %r" % (jid, texto))
    st, cuerpo, msg_id = enviar_al_bot(jid, texto, apikey)
    log("  HTTP %s | webhook: %s" % (st, cuerpo))
    log("  message_id: %s" % msg_id)
    log("  Esperando %ds..." % espera)
    time.sleep(espera)
    det = esperar_ejecucion(msg_id, ids, timeout=90)
    if det is None:
        log("  !! No se encontro la ejecucion para %s (%s)" % (msg_id, etiqueta))
    return det, msg_id, st


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    resultados = {}
    log("TEST E2E DEL COMANDO PAUSA")
    log("Fecha local: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    log("Workflow: %s" % WORKFLOW_ID)
    log("Cliente a pausar: %s" % CLIENTE)
    log("Otro cliente (no pausado): %s" % OTRO)
    log("Dueno (comandos): %s" % DUENO)

    # ---------------- Entorno ----------------
    seccion("ENTORNO")
    rc, out, err = docker(["ps", "--format", "{{.Names}}|{{.Status}}"])
    log("docker ps rc=%s" % rc)
    log(out.strip() or "(sin stdout)")
    if err.strip():
        log("STDERR: " + err.strip())

    rc, out, err = docker(["exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"])
    apikey = out.strip()
    log("APIKEY Evolution: %s" % (("SI (%d chars)" % len(apikey)) if apikey else "NO"))

    ctx_clientes, _, _ = sql_filas("SELECT count(*) FROM barber_clientes;")
    log("barber_clientes count = %r" % (ctx_clientes,))

    # ---------------- PASO 0 ----------------
    seccion("PASO 0 - LIMPIEZA PREVIA")
    q0 = ("DELETE FROM barber_pausas WHERE jid IN "
          "('%s','%s');" % (CLIENTE, OTRO))
    log("SQL: " + q0)
    rc, out, err = sql(q0)
    log("rc=%s stdout=%r stderr=%r" % (rc, out.strip(), err.strip()))
    if err.strip():
        log("!! ERROR SQL en limpieza previa: " + err.strip())
    filas, out, err = sql_filas("SELECT count(*) FROM barber_pausas;")
    log("barber_pausas total = %r" % (filas,))

    # ---------------- PASO 1 ----------------
    seccion("PASO 1 - LINEA BASE (SIN PAUSA): EL BOT DEBE RESPONDER")
    det1, id1, _ = enviar_y_esperar(CLIENTE, "hola, cuanto cuesta el corte?", apikey, "baseline")
    if det1:
        nd = nodos(det1)
        log("  Ejecucion id=%s status=%s" % (det1.get("id"), det1.get("status")))
        log("  Nodos: %s" % json.dumps(nd, ensure_ascii=False))
        log("  message_content: %r" % mensaje_cliente(det1))
        log("  Rama 'IF - Cliente pausado' (0=true,1=false): %r" % rama_if(det1, "IF - Cliente pausado"))
        log("  Leer pausa: %r" % (salida_leer_pausa(det1),))
        log("  Respuesta del bot: %r" % respuesta_bot(det1))
    else:
        nd = []
        log("  !! Sin ejecucion para el mensaje de linea base")

    r1_ejecutado = ("IF - Cliente pausado" in nodos(det1)) if det1 else False
    r1_rama_false = (rama_if(det1, "IF - Cliente pausado") == 1) if det1 else False
    r1_responde = bool(det1) and ("Mandar mensaje" in nodos(det1)) and bool(
        (respuesta_bot(det1) or "").strip())
    seccion("PASO 1 - RESULTADOS")
    resultados["1a_nodo_pausado_ejecutado"] = resumen_check(
        "El nodo 'IF - Cliente pausado' se ejecuto en la linea base", r1_ejecutado)
    resultados["1b_rama_false"] = resumen_check(
        "Tomo la rama false (no pausado)", r1_rama_false,
        "rama=%r (0=true,1=false)" % (rama_if(det1, "IF - Cliente pausado") if det1 else None))
    resultados["1c_bot_responde"] = resumen_check(
        "El bot RESPONDIO sin pausa", r1_responde,
        "texto=%r" % (respuesta_bot(det1),))
    log("  Ejecucion linea base: id=%s" % (det1.get("id") if det1 else None))

    # ---------------- PASO 2 ----------------
    seccion("PASO 2 - APLICAR LA PAUSA (comando del DUENO)")
    ids = ids_actuales()
    cmd = "PAUSA %s 2h" % CLIENTE_NUM
    log("  Enviando comando desde el dueno %s: %r" % (DUENO, cmd))
    st, cuerpo, msg_id = enviar_al_bot(DUENO, cmd, apikey)
    log("  HTTP %s | webhook: %s" % (st, cuerpo))
    log("  Esperando %ds..." % ESPERA_COMANDO)
    time.sleep(ESPERA_COMANDO)
    det2 = esperar_ejecucion(msg_id, ids, timeout=90)
    if det2:
        nd2 = nodos(det2)
        log("  Ejecucion comando id=%s status=%s" % (det2.get("id"), det2.get("status")))
        log("  Nodos: %s" % json.dumps(nd2, ensure_ascii=False))
        if "Parsear pausa" in nd2:
            try:
                j = run_data(det2)["Parsear pausa"][0]["data"]["main"][0][0]["json"]
                log("  Parsear pausa: pausaOk=%r numero=%r horas=%r"
                    % (j.get("pausaOk"), j.get("numero"), j.get("horas")))
            except Exception as ex:  # noqa: BLE001
                log("  Parsear pausa ilegible: %s" % ex)
        if "Aplicar pausa" in nd2:
            try:
                rd = run_data(det2)["Aplicar pausa"][0]
                log("  Aplicar pausa main: %s"
                    % json.dumps((rd.get("data") or {}).get("main"), ensure_ascii=False)[:600])
            except Exception as ex:  # noqa: BLE001
                log("  Aplicar pausa ilegible: %s" % ex)
        if "Responder al operador" in nd2:
            try:
                r = run_data(det2)["Responder al operador"][0]["data"]["main"][0][0]["json"]
                log("  Respuesta al dueno: %r" % (r.get("message", {}).get("conversation"),))
            except Exception as ex:  # noqa: BLE001
                log("  Respuesta al dueno ilegible: %s" % ex)
    else:
        log("  !! Sin ejecucion para el comando PAUSA")

    q = "SELECT jid, hasta, motivo FROM barber_pausas WHERE jid='%s';" % CLIENTE
    log("  SQL: " + q)
    rc, out, err = sql(q)
    log("  STDOUT: %r" % out.strip())
    log("  STDERR: %r" % err.strip())
    if err.strip():
        log("  !! ERROR SQL al verificar la pausa: " + err.strip())
    fila_pausa = out.strip()
    pausa_guardada = bool(fila_pausa)

    seccion("PASO 2 - RESULTADOS")
    resultados["2_pausa_guardada"] = resumen_check(
        "La pausa quedo guardada en Postgres (barber_pausas)", pausa_guardada,
        "fila=%r" % (fila_pausa or "<vacia>"))

    # ---------------- PASO 3 ----------------
    seccion("PASO 3 - PRUEBA CLAVE: CON PAUSA EL BOT DEBE CALLAR")
    det3, id3, _ = enviar_y_esperar(CLIENTE, "sigo esperando respuesta, cuanto cuesta el corte?",
                                    apikey, "pausado")
    if det3:
        nd3 = nodos(det3)
        log("  Ejecucion id=%s status=%s" % (det3.get("id"), det3.get("status")))
        log("  Nodos: %s" % json.dumps(nd3, ensure_ascii=False))
        log("  message_content: %r" % mensaje_cliente(det3))
        log("  Rama 'IF - Cliente pausado': %r" % rama_if(det3, "IF - Cliente pausado"))
        lp = salida_leer_pausa(det3)
        log("  Leer pausa: %r" % (lp,))
        log("  Respuesta del bot: %r" % respuesta_bot(det3))
    else:
        nd3 = []
        lp = None

    r3_ejecutado = ("IF - Cliente pausado" in nodos(det3)) if det3 else False
    r3_rama_true = (rama_if(det3, "IF - Cliente pausado") == 0) if det3 else False
    r3_sin_ai = ("AI Agent" not in nodos(det3)) if det3 else False
    r3_sin_mandar = ("Mandar mensaje" not in nodos(det3)) if det3 else False
    r3_pausado1 = bool(lp) and str(lp.get("pausado")) == "1"
    texto_fallo = respuesta_bot(det3) if det3 else None

    seccion("PASO 3 - RESULTADOS")
    resultados["3a_nodo_pausado_ejecutado"] = resumen_check(
        "El nodo 'IF - Cliente pausado' se ejecuto", r3_ejecutado)
    resultados["3b_rama_true"] = resumen_check(
        "Tomo la rama true (pausado)", r3_rama_true,
        "rama=%r" % (rama_if(det3, "IF - Cliente pausado") if det3 else None))
    resultados["3c_sin_ai_agent"] = resumen_check(
        "NO existe el nodo 'AI Agent'", r3_sin_ai)
    resultados["3d_sin_mandar_mensaje"] = resumen_check(
        "NO existe el nodo 'Mandar mensaje'", r3_sin_mandar)
    resultados["3e_leer_pausa_1"] = resumen_check(
        "'Leer pausa' devolvio pausado = 1", r3_pausado1, "leer_pausa=%r" % (lp,))
    if r3_sin_mandar and r3_sin_ai:
        log("  => EL BOT GUARDO SILENCIO CON EL CLIENTE PAUSADO.")
    else:
        log("  => !! FALLO GRAVE: EL BOT RESPONDIO AUN CON LA PAUSA ACTIVA.")
        log("     Texto enviado por el bot: %r" % (texto_fallo,))

    # ---------------- PASO 4 ----------------
    seccion("PASO 4 - OTRO CLIENTE (NO PAUSADO) DEBE RECIBIR RESPUESTA")
    det4, id4, _ = enviar_y_esperar(OTRO, "hola, buenas tardes, tienen cita disponible?",
                                    apikey, "otro-cliente")
    if det4:
        nd4 = nodos(det4)
        log("  Ejecucion id=%s status=%s" % (det4.get("id"), det4.get("status")))
        log("  Nodos: %s" % json.dumps(nd4, ensure_ascii=False))
        log("  Rama 'IF - Cliente pausado': %r" % rama_if(det4, "IF - Cliente pausado"))
        log("  Respuesta del bot: %r" % respuesta_bot(det4))
    r4_responde = bool(det4) and ("Mandar mensaje" in nodos(det4)) and bool(
        (respuesta_bot(det4) or "").strip())
    seccion("PASO 4 - RESULTADOS")
    resultados["4_otro_cliente_responde"] = resumen_check(
        "Otro cliente NO pausado SI recibe respuesta (pausa selectiva)", r4_responde,
        "texto=%r" % (respuesta_bot(det4) if det4 else None))

    # ---------------- PASO 5 ----------------
    seccion("PASO 5 - EXPIRACION DE LA PAUSA: EL BOT DEBE VOLVER A RESPONDER")
    q5 = ("UPDATE barber_pausas SET hasta = now() - interval '1 minute' "
          "WHERE jid='%s';" % CLIENTE)
    log("  SQL: " + q5)
    rc, out, err = sql(q5)
    log("  rc=%s stdout=%r stderr=%r" % (rc, out.strip(), err.strip()))
    if err.strip():
        log("  !! ERROR SQL al vencer la pausa: " + err.strip())
    filas, out, err = sql_filas(
        "SELECT jid, hasta FROM barber_pausas WHERE jid='%s';" % CLIENTE)
    log("  Fila ahora: %r" % (filas,))

    det5, id5, _ = enviar_y_esperar(CLIENTE, "hola de nuevo, cuanto cuesta el corte?",
                                    apikey, "expirada")
    if det5:
        nd5 = nodos(det5)
        log("  Ejecucion id=%s status=%s" % (det5.get("id"), det5.get("status")))
        log("  Nodos: %s" % json.dumps(nd5, ensure_ascii=False))
        log("  Rama 'IF - Cliente pausado': %r" % rama_if(det5, "IF - Cliente pausado"))
        log("  Leer pausa: %r" % (salida_leer_pausa(det5),))
        log("  Respuesta del bot: %r" % respuesta_bot(det5))
    r5_responde = bool(det5) and ("Mandar mensaje" in nodos(det5)) and bool(
        (respuesta_bot(det5) or "").strip())
    seccion("PASO 5 - RESULTADOS")
    resultados["5_expirada_responde"] = resumen_check(
        "Al expirar la pausa el bot vuelve a responder", r5_responde,
        "texto=%r" % (respuesta_bot(det5) if det5 else None))

    # ---------------- PASO 6 ----------------
    seccion("PASO 6 - LIMPIEZA FINAL")
    q6 = ("DELETE FROM barber_pausas WHERE jid IN "
          "('%s','%s');" % (CLIENTE, OTRO))
    log("  SQL: " + q6)
    rc, out, err = sql(q6)
    log("  rc=%s stdout=%r stderr=%r" % (rc, out.strip(), err.strip()))
    if err.strip():
        log("  !! ERROR SQL en limpieza final: " + err.strip())

    filas, out, err = sql_filas(
        "SELECT count(*) FROM barber_pausas WHERE jid IN ('%s','%s');" % (CLIENTE, OTRO))
    log("  Pausas restantes para los jids de prueba: %r" % (filas,))
    tabla_limpia = bool(filas) and filas[0] == "0"
    filas_tot, out_tot, _ = sql_filas("SELECT count(*) FROM barber_pausas;")
    log("  barber_pausas total (toda la tabla): %r" % (filas_tot,))

    seccion("PASO 6 - RESULTADOS")
    resultados["6_tabla_limpia"] = resumen_check(
        "Tabla barber_pausas limpia para los jids de prueba", tabla_limpia,
        "restantes=%r | total tabla=%r" % (filas, filas_tot))

    # ---------------- PASO 7 ----------------
    seccion("PASO 7 - ESTRUCTURA DE LOS NODOS DEL WORKFLOW")
    det7_error = None
    try:
        wf = api("/workflows/" + WORKFLOW_ID)
    except Exception as ex:  # noqa: BLE001
        wf = None
        det7_error = "No se pudo consultar el workflow: %s" % ex
        log("  !! " + det7_error)

    if wf:
        por_nombre = {n["name"]: n for n in wf.get("nodes", [])}
        conns = wf.get("connections", {})

        n_leer = por_nombre.get("Leer pausa")
        n_calc = por_nombre.get("Calcular pausa")
        n_if = por_nombre.get("IF - Cliente pausado")
        n_prev = por_nombre.get("IF - No es del bot")
        n_switch = por_nombre.get("Switch")

        log("  Nodo 'Leer pausa':          %s" % ("presente" if n_leer else "AUSENTE"))
        log("    alwaysOutputData = %r" % (n_leer.get("alwaysOutputData") if n_leer else None))
        log("    query contiene barber_pausas = %s"
            % ("barber_pausas" in str((n_leer or {}).get("parameters", {}).get("query", ""))))
        log("  Nodo 'Calcular pausa':      %s" % ("presente" if n_calc else "AUSENTE"))
        log("  Nodo 'IF - Cliente pausado':%s" % ("presente" if n_if else "AUSENTE"))
        log("  Nodo 'IF - No es del bot':  %s" % ("presente" if n_prev else "AUSENTE"))

        def destino(nodo_origen, salida):
            try:
                salidas = conns[nodo_origen]["main"]
                destino_lista = salidas[salida] or []
                return [d["node"] for d in destino_lista]
            except Exception:  # noqa: BLE001
                return []

        cadena = (destino("IF - No es del bot", 0) == ["Leer pausa"]
                  and destino("Leer pausa", 0) == ["Calcular pausa"]
                  and destino("Calcular pausa", 0) == ["IF - Cliente pausado"])
        log("  Cadena IF-No es del bot -> Leer pausa -> Calcular pausa -> IF-Cliente pausado: %s"
            % cadena)
        log("    IF-No es del bot[0] -> %r" % (destino("IF - No es del bot", 0),))
        log("    Leer pausa[0]       -> %r" % (destino("Leer pausa", 0),))
        log("    Calcular pausa[0]   -> %r" % (destino("Calcular pausa", 0),))

        rama_true_dest = destino("IF - Cliente pausado", 0)
        rama_false_dest = destino("IF - Cliente pausado", 1)
        log("    IF-Cliente pausado[0]=true  -> %r" % (rama_true_dest,))
        log("    IF-Cliente pausado[1]=false -> %r" % (rama_false_dest,))
        rama_true_vacia = (rama_true_dest == [])
        rama_false_switch = (rama_false_dest == ["Switch"])

        seccion("PASO 7 - RESULTADOS")
        resultados["7a_leer_pausa_always_output"] = resumen_check(
            "'Leer pausa' existe con alwaysOutputData: true",
            bool(n_leer) and n_leer.get("alwaysOutputData") is True,
            "alwaysOutputData=%r" % (n_leer.get("alwaysOutputData") if n_leer else None))
        resultados["7b_nodos_existen"] = resumen_check(
            "Existen 'Calcular pausa' e 'IF - Cliente pausado'",
            bool(n_calc) and bool(n_if))
        resultados["7c_cadena"] = resumen_check(
            "Cadena IF-No es del bot -> Leer pausa -> Calcular pausa -> IF-Cliente pausado",
            cadena)
        resultados["7d_rama_true_vacia"] = resumen_check(
            "La rama true de 'IF - Cliente pausado' esta VACIA (sin salida)",
            rama_true_vacia, "destinos=%r" % (rama_true_dest,))
        resultados["7e_rama_false_switch"] = resumen_check(
            "La rama false va a 'Switch'", rama_false_switch,
            "destinos=%r" % (rama_false_dest,))
    else:
        seccion("PASO 7 - RESULTADOS")
        resultados["7a_leer_pausa_always_output"] = resumen_check(
            "'Leer pausa' existe con alwaysOutputData: true", False, str(det7_error))
        resultados["7b_nodos_existen"] = resumen_check(
            "Existen 'Calcular pausa' e 'IF - Cliente pausado'", False, str(det7_error))
        resultados["7c_cadena"] = resumen_check(
            "Cadena IF-No es del bot -> Leer pausa -> Calcular pausa -> IF-Cliente pausado",
            False, str(det7_error))
        resultados["7d_rama_true_vacia"] = resumen_check(
            "La rama true de 'IF - Cliente pausado' esta VACIA (sin salida)", False,
            str(det7_error))
        resultados["7e_rama_false_switch"] = resumen_check(
            "La rama false va a 'Switch'", False, str(det7_error))

    # ---------------- Informe final ----------------
    seccion("INFORME FINAL (OK / FALLO POR COMPROBACION)")

    orden = [
        ("1a_nodo_pausado_ejecutado",
         "Linea base: 'IF - Cliente pausado' se ejecuto"),
        ("1b_rama_false", "Linea base: tomo la rama false"),
        ("1c_bot_responde", "Linea base: el bot responde SIN pausa"),
        ("2_pausa_guardada", "La pausa se guardo en Postgres"),
        ("3a_nodo_pausado_ejecutado", "Con pausa: 'IF - Cliente pausado' se ejecuto"),
        ("3b_rama_true", "Con pausa: tomo la rama true"),
        ("3c_sin_ai_agent", "Con pausa: NO existe 'AI Agent'"),
        ("3d_sin_mandar_mensaje", "Con pausa: NO existe 'Mandar mensaje'"),
        ("3e_leer_pausa_1", "Con pausa: 'Leer pausa' devolvio pausado = 1"),
        ("4_otro_cliente_responde", "Otro cliente NO pausado SI recibe respuesta"),
        ("5_expirada_responde", "Al expirar la pausa el bot vuelve a responder"),
        ("6_tabla_limpia", "Tabla barber_pausas limpia al terminar"),
        ("7a_leer_pausa_always_output", "Paso 7: 'Leer pausa' con alwaysOutputData: true"),
        ("7b_nodos_existen", "Paso 7: existen 'Calcular pausa' e 'IF - Cliente pausado'"),
        ("7c_cadena", "Paso 7: cadena IF-No es del bot -> Leer pausa -> Calcular pausa -> IF-Cliente pausado"),
        ("7d_rama_true_vacia", "Paso 7: rama true de 'IF - Cliente pausado' VACIA"),
        ("7e_rama_false_switch", "Paso 7: rama false va a 'Switch'"),
    ]
    for clave, nombre in orden:
        ok = resultados.get(clave)
        log("  [%s] %s" % ("OK   " if ok else "FALLO", nombre))

    total = len(orden)
    oks = sum(1 for c, _ in orden if resultados.get(c))
    log()
    log("  Comprobaciones OK: %d/%d" % (oks, total))

    criticas = ["3d_sin_mandar_mensaje", "3c_sin_ai_agent", "2_pausa_guardada",
                "4_otro_cliente_responde", "5_expirada_responde", "6_tabla_limpia",
                "7a_leer_pausa_always_output", "7c_cadena"]
    fallos_criticos = [n for c, n in orden if c in criticas and not resultados.get(c)]

    seccion("VEREDICTO")
    bot_callo = bool(resultados.get("3d_sin_mandar_mensaje")
                     and resultados.get("3c_sin_ai_agent"))
    log("  El bot GUARDO SILENCIO con el cliente pausado: %s" % ("SI" if bot_callo else "NO"))
    if fallos_criticos:
        log("  FALLOS:")
        for n in fallos_criticos:
            log("    - " + n)
    else:
        log("  Sin fallos criticos.")
    log()
    log("  VEREDICTO GLOBAL: %s"
        % ("PAUSA FUNCIONA PUNTA A PUNTA" if oks == total
           else "PAUSA **NO** FUNCIONA PUNTA A PUNTA (%d/%d)" % (oks, total)))

    resumen = dict(resultados)
    resumen["_bot_callo"] = bot_callo
    resumen["_oks"] = oks
    resumen["_total"] = total
    resumen["_fallos_criticos"] = fallos_criticos
    resumen["_exec_ids"] = {
        "paso1_linea_base": det1.get("id") if det1 else None,
        "paso2_comando": det2.get("id") if det2 else None,
        "paso3_pausado": det3.get("id") if det3 else None,
        "paso4_otro_cliente": det4.get("id") if det4 else None,
        "paso5_expirada": det5.get("id") if det5 else None,
    }
    log()
    log("RESUMEN JSON: " + json.dumps(resumen, ensure_ascii=False, indent=2))

    return 0 if oks == total else 2


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        codigo = 1
    finally:
        # Limpieza garantizada de barber_pausas, incluso si el script aborta.
        try:
            logger = log
            logger("")
            logger("LIMPIEZA DE SEGURIDAD (finally): borrando pausas de prueba...")
            docker(["exec", "-i", PG_CONTAINER, "psql", "-U", "barberia", "-d", "barberia",
                    "-t", "-A", "-c",
                    "DELETE FROM barber_pausas WHERE jid IN ('%s','%s');" % (CLIENTE, OTRO)])
            rc, out, err = docker(["exec", "-i", PG_CONTAINER, "psql", "-U", "barberia",
                                   "-d", "barberia", "-t", "-A", "-c",
                                   "SELECT count(*) FROM barber_pausas WHERE jid IN ('%s','%s');"
                                   % (CLIENTE, OTRO)])
            logger("  Verificacion: filas restantes = %r | stderr = %r" % (out.strip(), err.strip()))
        except Exception:  # noqa: BLE001
            traceback.print_exc()

        try:
            with open(r"G:\Barberia\archivos\test-pausa-e2e-salida.txt", "w",
                      encoding="utf-8") as fh:
                fh.write("\n".join(OUT))
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    sys.exit(codigo)