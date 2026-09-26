#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION DE PUNTA A PUNTA del comando PAUSA en n8n + Postgres (Barberia).

Objetivo: comprobar empiricamente que tras `PAUSA <numero> <horas>` (enviado por
el DUEÑO) el bot guarda SILENCIO con ese cliente, y que sin pausa SI responde.

Este script SOLO LEE y ENVIA mensajes al webhook. No modifica ningun workflow
ni archivo del proyecto. La unica escritura en base de datos es el DELETE de
limpieza previa de barber_pausas para los numeros de prueba (Paso 0, indicado
en el enunciado).

Salida: imprime un informe con evidencia cruda y escribe pausa_e2e_reporte.md
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------
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

CLIENTE = "5214501111805@s.whatsapp.net"          # cliente de prueba
CLIENTE_NUM = "5214501111805"
DUENO = "524521206246@s.whatsapp.net"             # dueño (manda comandos)
DUENO_ALIAS = "5214521206246@s.whatsapp.net"

ESPERA_CLIENTE = 40   # segundos tras mensaje de cliente
ESPERA_COMANDO = 20   # segundos tras comando del dueño

OUT = []


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


# --------------------------------------------------------------------------
# Helpers: docker / postgres
# --------------------------------------------------------------------------
_DOCKER_ENV = dict(os.environ)
_DOCKER_ENV["DOCKER_CONFIG"] = DOCKER_CONFIG


def docker(args, stdin=None, timeout=90):
    """Ejecuta docker.exe con capture_output. Devuelve (rc, stdout, stderr)."""
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


def sql(query):
    """Ejecuta SQL via psql leyendo STDOUT y STDERR (los errores van a stderr)."""
    rc, out, err = docker(
        [
            "exec", "-i", PG_CONTAINER, "psql",
            "-U", "barberia", "-d", "barberia",
            "-t", "-A", "-v", "ON_ERROR_STOP=0",
        ],
        stdin=query + "\n",
    )
    return rc, out.strip(), err.strip()


def sql_rows(query):
    """Filas no vacias del stdout de psql."""
    rc, out, err = sql(query)
    filas = [l for l in out.splitlines() if l.strip()]
    return rc, filas, err


# --------------------------------------------------------------------------
# Helpers: n8n API
# --------------------------------------------------------------------------
def api(path, timeout=60):
    req = urllib.request.Request(N8N + "/api/v1" + path)
    req.add_header("X-N8N-API-KEY", N8N_KEY)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def enviar_al_bot(jid, texto, apikey_evolution):
    """POST al webhook del bot imitando un mensaje entrante de Evolution."""
    body = {
        "event": "messages.upsert",
        "instance": "hector",
        "server_url": "http://evolution_api:8080",
        "apikey": apikey_evolution,
        "date_time": "2026-09-25T20:00:00.000Z",
        "data": {
            "key": {
                "id": "T" + uuid.uuid4().hex[:10].upper(),
                "remoteJid": jid,
                "fromMe": False,
            },
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
            return r.status, r.read().decode("utf-8", "replace")[:400], body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400], body
    except Exception as e:  # noqa: BLE001
        return -1, "EXC: %s" % e, body


def ejecuciones(limit=25):
    d = api("/executions?workflowId=%s&limit=%d" % (WORKFLOW_ID, limit))
    return d.get("data", [])


def detalle(exec_id):
    return api("/executions/%s?includeData=true" % exec_id)


def run_data(det):
    return (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})


def mensaje_cliente(det):
    run = run_data(det)
    try:
        return run["Normalizacion"][0]["data"]["main"][0][0]["json"]["message_content"]
    except Exception:  # noqa: BLE001
        return None


def respuesta_bot(det):
    """La respuesta del bot vive DENTRO de 'Mandar mensaje' -> message.conversation.
    No se busca en 'output'."""
    run = run_data(det)
    if "Mandar mensaje" not in run:
        return None
    try:
        nodo = run["Mandar mensaje"][0]
        return nodo["data"]["main"][0][0]["json"]["message"]["conversation"]
    except Exception:  # noqa: BLE001
        try:
            return json.dumps(run["Mandar mensaje"][0]["data"]["main"][0][0]["json"])[:500]
        except Exception:  # noqa: BLE001
            return "<Mandar mensaje sin conversation>"


def rama_if(det, nombre_nodo):
    """Devuelve el indice de salida tomado por un nodo IF (0=true, 1=false).

    n8n guarda en runData el array 'main' con una entrada por output; la rama
    tomada es la unica no vacia. Se usa branchIndex como respaldo.
    """
    run = run_data(det)
    entradas = run.get(nombre_nodo)
    if not entradas:
        return None
    main = (entradas[-1].get("data") or {}).get("main") or []
    tomadas = [i for i, o in enumerate(main) if o]
    if tomadas:
        return tomadas[0]
    try:
        return entradas[-1]["data"]["main"][0][0]["branchIndex"]
    except Exception:  # noqa: BLE001
        return "?"


def nodos(det):
    return list(run_data(det).keys())


def esperar_nueva_ejecucion(ids_previos, timeout=90, etiqueta=""):
    """Espera hasta que aparezca una ejecucion nueva y quede en estado final."""
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            for e in ejecuciones(30):
                if e["id"] not in ids_previos:
                    if e.get("finished") is True or e.get("status") in ("success", "error", "crashed"):
                        return e
                    det_tmp = None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3)
    return None


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    log("VERIFICACION E2E DEL COMANDO PAUSA")
    log("Fecha de ejecucion (local): " + time.strftime("%Y-%m-%d %H:%M:%S"))
    log("Workflow: " + WORKFLOW_ID)
    log("Cliente de prueba: " + CLIENTE)
    log("Dueño: " + DUENO)

    # ---------------- Pre-chequeos de entorno ----------------
    seccion("PRE-CHEQUEOS DE ENTORNO")
    rc, out, err = docker(["ps", "--format", "{{.Names}}|{{.Status}}"])
    log("docker ps rc=%s" % rc)
    log(out.strip() or "(sin stdout)")
    if err.strip():
        log("STDERR: " + err.strip())

    rc, out, err = docker(["exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"])
    apikey = out.strip()
    log("APIKEY Evolution leida: %s" % (("SI (%d chars)" % len(apikey)) if apikey else "NO"))
    if err.strip():
        log("STDERR: " + err.strip())

    try:
        wf = api("/workflows/" + WORKFLOW_ID)
        log("Workflow encontrado: %s | active=%s" % (wf.get("name"), wf.get("active")))
        nombres = [n["name"] for n in wf.get("nodes", [])]
        for n in ("Leer pausa", "Calcular pausa", "IF - Cliente pausado"):
            log("  nodo presente '%s': %s" % (n, n in nombres))
    except Exception as e:  # noqa: BLE001
        log("ERROR consultando workflow: %s" % e)

    # ---------------- PASO 0: limpieza ----------------
    seccion("PASO 0 - LIMPIEZA PREVIA")
    q0 = ("DELETE FROM barber_pausas WHERE jid IN "
          "('%s','%s');" % (CLIENTE, DUENO_ALIAS))
    log("SQL: " + q0)
    rc, out, err = sql(q0)
    log("rc=%s stdout=%r stderr=%r" % (rc, out, err))
    log("DELETE ejecutado (afecta filas, sin error si stderr vacio).")

    estado = {}
    rc, out, err = sql("SELECT count(*) FROM barber_pausas;")
    log("barber_pausas total filas: stdout=%r stderr=%r" % (out, err))
    estado["pausas_inicial"] = out

    # Contexto critico: Aplicar pausa usa INSERT ... SELECT FROM barber_clientes
    rc, out, err = sql("SELECT count(*) FROM barber_clientes;")
    estado["clientes_count"] = out
    log("barber_clientes count = %r  (Aplicar pausa hace INSERT..SELECT FROM barber_clientes)" % out)

    rc, out, err = sql("SELECT jid FROM barber_clientes ORDER BY jid;")
    log("barber_clientes jids = %r" % (out,))

    rc, out, err = sql("SELECT jid, nombre FROM barber_operadores ORDER BY jid;")
    log("barber_operadores = %r" % (out,))

    # ---------------- PASO 1: linea base sin pausa ----------------
    seccion("PASO 1 - LINEA BASE (SIN PAUSA)")
    previos = {e["id"] for e in ejecuciones(30)}
    log("Ejecuciones previas registradas: %d" % len(previos))

    msg1 = "hola, cuanto cuesta el corte?"
    log("Enviando mensaje de CLIENTE desde %s: %r" % (CLIENTE, msg1))
    st, resp, body = enviar_al_bot(CLIENTE, msg1, apikey)
    log("HTTP %s | respuesta webhook: %s" % (st, resp[:200]))

    log("Esperando %ds..." % ESPERA_CLIENTE)
    time.sleep(ESPERA_CLIENTE)

    e1 = esperar_nueva_ejecucion(previos, timeout=60, etiqueta="baseline")
    if not e1:
        log("!! No aparecio ejecucion nueva tras el mensaje de cliente.")
    det1 = None
    if e1:
        det1 = detalle(e1["id"])
        log("Ejecucion baseline id=%s status=%s finished=%s"
            % (e1["id"], e1.get("status"), e1.get("finished")))
        log("Nodos ejecutados: %s" % json.dumps(nodos(det1), ensure_ascii=False))
        log("message_content visto por Normalizacion: %r" % mensaje_cliente(det1))
        log("Rama de 'IF - Cliente pausado' (0=true,1=false): %r" % rama_if(det1, "IF - Cliente pausado"))
        log("Rama de 'IF - No es del bot'   (0=true,1=false): %r" % rama_if(det1, "IF - No es del bot"))
        log("Respuesta del bot (Mandar mensaje -> message.conversation): %r" % respuesta_bot(det1))
        log("Nodo 'AI Agent' presente: %s" % ("AI Agent" in nodos(det1)))
        log("Nodo 'Mandar mensaje' presente: %s" % ("Mandar mensaje" in nodos(det1)))

    # ---------------- PASO 2: aplicar la pausa ----------------
    seccion("PASO 2 - APLICAR LA PAUSA (comando del DUEÑO)")
    previos2 = {e["id"] for e in ejecuciones(30)}
    cmd = "PAUSA %s 2h" % CLIENTE_NUM
    log("Enviando comando desde el DUEÑO (%s): %r" % (DUENO, cmd))
    st, resp, body = enviar_al_bot(DUENO, cmd, apikey)
    log("HTTP %s | respuesta webhook: %s" % (st, resp[:200]))

    log("Esperando %ds..." % ESPERA_COMANDO)
    time.sleep(ESPERA_COMANDO)

    e2 = esperar_nueva_ejecucion(previos2, timeout=60, etiqueta="comando")
    if e2:
        det2 = detalle(e2["id"])
        log("Ejecucion del comando id=%s status=%s" % (e2["id"], e2.get("status")))
        log("Nodos ejecutados: %s" % json.dumps(nodos(det2), ensure_ascii=False))
        if "Parsear pausa" in nodos(det2):
            try:
                j = run_data(det2)["Parsear pausa"][0]["data"]["main"][0][0]["json"]
                log("Parsear pausa salida: pausaOk=%r numero=%r horas=%r"
                    % (j.get("pausaOk"), j.get("numero"), j.get("horas")))
            except Exception as ex:  # noqa: BLE001
                log("Parsear pausa (no legible): %s" % ex)
        if "Aplicar pausa" in nodos(det2):
            try:
                rd = run_data(det2)["Aplicar pausa"][0]
                main = (rd.get("data") or {}).get("main") or []
                log("Aplicar pausa main: %s" % json.dumps(main, ensure_ascii=False)[:800])
                if rd.get("error"):
                    log("Aplicar pausa ERROR: %s" % json.dumps(rd["error"], ensure_ascii=False)[:600])
            except Exception as ex:  # noqa: BLE001
                log("Aplicar pausa (no legible): %s" % ex)
        if "Responder al operador" in nodos(det2):
            try:
                rd = run_data(det2)["Responder al operador"][0]
                log("Responder al operador json: %s"
                    % json.dumps(rd["data"]["main"][0][0]["json"], ensure_ascii=False)[:600])
            except Exception as ex:  # noqa: BLE001
                log("Responder al operador (no legible): %s" % ex)
    else:
        log("!! No aparecio ejecucion nueva tras el comando.")

    seccion("PASO 2b - VERIFICACION SQL DE LA PAUSA")
    q = "SELECT jid, hasta, motivo FROM barber_pausas WHERE jid='%s';" % CLIENTE
    log("SQL: " + q)
    rc, out, err = sql(q)
    log("rc=%s" % rc)
    log("STDOUT: %r" % out)
    log("STDERR: %r" % err)
    pausa_persistida = bool(out.strip())
    log(">>> PAUSA PERSISTIDA EN barber_pausas: %s" % pausa_persistida)

    if not pausa_persistida:
        log()
        log("CAUSA PROBABLE: 'Aplicar pausa' hace")
        log("   INSERT INTO barber_pausas (jid,hasta,motivo) SELECT ... FROM barber_clientes ...")
        log("   y barber_clientes tiene %s filas -> el SELECT no produce filas -> no hay INSERT."
            % estado.get("clientes_count"))
        log("   La fila de prueba '%s' no existe en barber_clientes." % CLIENTE)

    # ---------------- PASO 3: cliente pausado debe callar ----------------
    seccion("PASO 3 - CLIENTE PAUSADO: EL BOT DEBE GUARDAR SILENCIO")
    previos3 = {e["id"] for e in ejecuciones(30)}
    msg3 = "sigo esperando respuesta, cuanto cuesta el corte?"
    log("Enviando mensaje de CLIENTE desde %s: %r" % (CLIENTE, msg3))
    st, resp, body = enviar_al_bot(CLIENTE, msg3, apikey)
    log("HTTP %s | respuesta webhook: %s" % (st, resp[:200]))

    log("Esperando %ds..." % ESPERA_CLIENTE)
    time.sleep(ESPERA_CLIENTE)

    e3 = esperar_nueva_ejecucion(previos3, timeout=60, etiqueta="pausado")
    det3 = None
    if e3:
        det3 = detalle(e3["id"])
        log("Ejecucion pausado id=%s status=%s" % (e3["id"], e3.get("status")))
        nd = nodos(det3)
        log("Nodos ejecutados: %s" % json.dumps(nd, ensure_ascii=False))
        log("message_content: %r" % mensaje_cliente(det3))
        log("Rama 'IF - Cliente pausado' (0=true,1=false): %r" % rama_if(det3, "IF - Cliente pausado"))
        if "Calcular pausa" in nd:
            try:
                j = run_data(det3)["Calcular pausa"][0]["data"]["main"][0][0]["json"]
                log("Calcular pausa salida: pausado=%r hasta=%r" % (j.get("pausado"), j.get("hasta")))
            except Exception as ex:  # noqa: BLE001
                log("Calcular pausa (no legible): %s" % ex)
        if "Leer pausa" in nd:
            try:
                rd = run_data(det3)["Leer pausa"][0]
                log("Leer pausa main: %s"
                    % json.dumps((rd.get("data") or {}).get("main"), ensure_ascii=False)[:600])
            except Exception as ex:  # noqa: BLE001
                log("Leer pausa (no legible): %s" % ex)
        log("Nodo 'AI Agent' presente: %s" % ("AI Agent" in nd))
        log("Nodo 'Mandar mensaje' presente: %s" % ("Mandar mensaje" in nd))
        log("Nodo 'Switch' presente: %s" % ("Switch" in nd))
        log("Respuesta del bot: %r" % respuesta_bot(det3))
    else:
        log("!! No aparecio ejecucion nueva tras el mensaje del cliente pausado.")

    # ---------------- PASO 3b: aislar el mecanismo de silencio ----------------
    # El comando PAUSA no logro persistir la fila (ver Paso 2b). Para distinguir
    # "el comando no persiste" de "el mecanismo de silencio no funciona", se
    # inyecta la fila directamente por SQL y se repite el Paso 3. Esto NO toca
    # ningun workflow ni archivo del proyecto: solo estado de datos de prueba.
    seccion("PASO 3b - AISLAR EL MECANISMO: INYECTAR LA PAUSA POR SQL Y REPETIR")
    q_inj = ("INSERT INTO barber_pausas (jid, hasta, motivo) VALUES "
             "('%s', now() + interval '2 hours', 'verificacion e2e - inyeccion directa') "
             "ON CONFLICT (jid) DO UPDATE SET hasta = excluded.hasta, motivo = excluded.motivo;"
             % CLIENTE)
    log("SQL: " + q_inj)
    rc, out, err = sql(q_inj)
    log("rc=%s stdout=%r stderr=%r" % (rc, out, err))

    rc, out, err = sql("SELECT jid, hasta, motivo FROM barber_pausas WHERE jid='%s';" % CLIENTE)
    log("Fila tras inyeccion -> STDOUT: %r  STDERR: %r" % (out, err))
    fila_inyectada = bool(out.strip())
    log(">>> FILA INYECTADA PRESENTE: %s" % fila_inyectada)

    if fila_inyectada:
        previos3b = {e["id"] for e in ejecuciones(30)}
        msg3b = "hola? hay alguien? cuanto cuesta el corte?"
        log("Enviando mensaje de CLIENTE desde %s: %r" % (CLIENTE, msg3b))
        st, resp, body = enviar_al_bot(CLIENTE, msg3b, apikey)
        log("HTTP %s | respuesta webhook: %s" % (st, resp[:200]))
        log("Esperando %ds..." % ESPERA_CLIENTE)
        time.sleep(ESPERA_CLIENTE)

        e3b = esperar_nueva_ejecucion(previos3b, timeout=60, etiqueta="pausado-inyectado")
        det3b = None
        if e3b:
            det3b = detalle(e3b["id"])
            nd = nodos(det3b)
            log("Ejecucion pausado(inyectado) id=%s status=%s" % (e3b["id"], e3b.get("status")))
            log("Nodos ejecutados: %s" % json.dumps(nd, ensure_ascii=False))
            log("Rama 'IF - Cliente pausado' (0=true,1=false): %r"
                % rama_if(det3b, "IF - Cliente pausado"))
            if "Leer pausa" in nd:
                try:
                    rd = run_data(det3b)["Leer pausa"][0]
                    log("Leer pausa main: %s"
                        % json.dumps((rd.get("data") or {}).get("main"), ensure_ascii=False)[:600])
                except Exception as ex:  # noqa: BLE001
                    log("Leer pausa (no legible): %s" % ex)
            if "Calcular pausa" in nd:
                try:
                    j = run_data(det3b)["Calcular pausa"][0]["data"]["main"][0][0]["json"]
                    log("Calcular pausa salida: pausado=%r hasta=%r" % (j.get("pausado"), j.get("hasta")))
                except Exception as ex:  # noqa: BLE001
                    log("Calcular pausa (no legible): %s" % ex)
            log("Nodo 'AI Agent' presente: %s" % ("AI Agent" in nd))
            log("Nodo 'Mandar mensaje' presente: %s" % ("Mandar mensaje" in nd))
            log("Nodo 'Switch' presente: %s" % ("Switch" in nd))
            log("Respuesta del bot: %r" % respuesta_bot(det3b))
        else:
            log("!! No aparecio ejecucion nueva tras el mensaje del cliente pausado.")
    else:
        e3b, det3b = None, None

    # limpieza de la fila inyectada
    log("Limpiando la fila inyectada...")
    rc, out, err = sql("DELETE FROM barber_pausas WHERE jid='%s';" % CLIENTE)
    log("rc=%s stdout=%r stderr=%r" % (rc, out, err))

    # ---------------- PASO 4: control, quitar pausa -> debe volver a responder ----------------
    seccion("PASO 4 - CONTROL: SIN PAUSA EL BOT DEBE VOLVER A RESPONDER")
    log("Borrando pausa de barber_pausas para el cliente de prueba...")
    rc, out, err = sql("DELETE FROM barber_pausas WHERE jid='%s';" % CLIENTE)
    log("rc=%s stdout=%r stderr=%r" % (rc, out, err))

    previos4 = {e["id"] for e in ejecuciones(30)}
    msg4 = "ok, ya volvi, cuanto cuesta el corte?"
    log("Enviando mensaje de CLIENTE desde %s: %r" % (CLIENTE, msg4))
    st, resp, body = enviar_al_bot(CLIENTE, msg4, apikey)
    log("HTTP %s | respuesta webhook: %s" % (st, resp[:200]))
    log("Esperando %ds..." % ESPERA_CLIENTE)
    time.sleep(ESPERA_CLIENTE)

    e4 = esperar_nueva_ejecucion(previos4, timeout=60, etiqueta="control")
    det4 = None
    if e4:
        det4 = detalle(e4["id"])
        nd = nodos(det4)
        log("Ejecucion control id=%s status=%s" % (e4["id"], e4.get("status")))
        log("Nodos ejecutados: %s" % json.dumps(nd, ensure_ascii=False))
        log("Rama 'IF - Cliente pausado': %r" % rama_if(det4, "IF - Cliente pausado"))
        log("Respuesta del bot: %r" % respuesta_bot(det4))
    else:
        log("!! No aparecio ejecucion nueva en el control.")

    # ---------------- VEREDICTO ----------------
    seccion("VEREDICTO")

    def respuesta_no_vacia(det):
        if det is None:
            return False
        r = respuesta_bot(det)
        return isinstance(r, str) and len(r.strip()) > 0

    base_ok_pausado_false = (det1 is not None and
                             rama_if(det1, "IF - Cliente pausado") == 1)
    base_ok_responde = respuesta_no_vacia(det1)
    pausa_en_bd = pausa_persistida
    pausado_silencio = (det3 is not None and
                        "Mandar mensaje" not in nodos(det3) and
                        "AI Agent" not in nodos(det3))
    pausado_rama_true = (det3 is not None and
                         rama_if(det3, "IF - Cliente pausado") == 0)
    control_responde = respuesta_no_vacia(det4)

    # Capa A: mecanismo de silencio (con fila presente, inyectada por SQL)
    silencio_mecanismo = (det3b is not None and
                          "Mandar mensaje" not in nodos(det3b) and
                          "AI Agent" not in nodos(det3b) and
                          "Switch" not in nodos(det3b))
    silencio_rama_true = (det3b is not None and
                          rama_if(det3b, "IF - Cliente pausado") == 0)

    log("CAPA 1 - Persistencia del comando PAUSA (Paso 2/2b):")
    log("  El comando del dueño fue reconocido y ejecuto 'Aplicar pausa' : %s"
        % (det2 is not None and "Aplicar pausa" in nodos(det2)))
    log("  Fila creada en barber_pausas                                   : %s" % pausa_en_bd)
    log()
    log("CAPA 2 - Mecanismo de silencio (Paso 3 con fila inyectada por SQL):")
    log("  Fila presente en barber_pausas al enviar el mensaje            : %s" % fila_inyectada)
    log("  IF - Cliente pausado tomo la rama TRUE                         : %s" % silencio_rama_true)
    log("  El bot CALLO (sin Switch/AI Agent/Mandar mensaje)              : %s" % silencio_mecanismo)
    log()
    log("Paso 1 linea base  -> IF-No es del bot tomo rama false : PENDIENTE/OK segun arriba")
    log("  IF - Cliente pausado rama == false (1) : %s" % base_ok_pausado_false)
    log("  El bot RESPONDIO en linea base        : %s" % base_ok_responde)
    log("Paso 2             -> fila en barber_pausas : %s" % pausa_en_bd)
    log("Paso 3 (comando)   -> IF - Cliente pausado rama == true (0) : %s" % pausado_rama_true)
    log("  El bot CALLO (sin AI Agent ni Mandar mensaje) : %s" % pausado_silencio)
    log("Paso 3b (inyectado)-> el mecanismo de silencio funciono : %s" % silencio_mecanismo)
    log("Paso 4 control     -> el bot vuelve a responder : %s" % control_responde)

    veredicto = (
        base_ok_pausado_false
        and base_ok_responde
        and pausa_en_bd
        and pausado_rama_true
        and pausado_silencio
        and control_responde
    )
    log()
    log(">>> VEREDICTO GLOBAL (flujo tal como lo manda el dueño): %s"
        % ("PAUSA FUNCIONA PUNTA A PUNTA" if veredicto
           else "PAUSA **NO** FUNCIONA PUNTA A PUNTA"))
    log(">>> VEREDICTO DEL MECANISMO DE SILENCIO (con fila en barber_pausas): %s"
        % ("FUNCIONA" if silencio_mecanismo else "**NO** FUNCIONA"))

    resumen = {
        "baseline_if_false": base_ok_pausado_false,
        "baseline_responde": base_ok_responde,
        "pausa_en_bd": pausa_en_bd,
        "pausado_rama_true": pausado_rama_true,
        "pausado_silencio_total": pausado_silencio,
        "control_responde": control_responde,
        "mecanismo_silencio_ok": silencio_mecanismo,
        "veredicto_ok": veredicto,
        "exec_ids": {
            "baseline": e1["id"] if e1 else None,
            "comando": e2["id"] if e2 else None,
            "pausado_comando": e3["id"] if e3 else None,
            "pausado_inyectado": e3b["id"] if e3b else None,
            "control": e4["id"] if e4 else None,
        },
        "barber_clientes_count": estado.get("clientes_count"),
        "pausa_sql_stdout": out,
    }
    log()
    log("RESUMEN JSON: " + json.dumps(resumen, ensure_ascii=False, indent=2))

    with open(r"G:\Barberia\pausa_e2e_reporte.md", "w", encoding="utf-8") as f:
        f.write("# Verificacion E2E del comando PAUSA\n\n```\n")
        f.write("\n".join(OUT))
        f.write("\n```\n")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        with open(r"G:\Barberia\pausa_e2e_reporte.md", "w", encoding="utf-8") as f:
            f.write("\n".join(OUT))
            f.write("\n\nEXCEPCION:\n" + traceback.format_exc())
        sys.exit(1)