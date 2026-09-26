#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Libreria comun para las pruebas de carga de Barber Chinos.

Lee las claves SIEMPRE de los archivos del proyecto (nunca hardcodeadas).
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ.setdefault("DOCKER_CONFIG", r"G:\Barberia\.docker")

N8N_BASE = "http://localhost:5678"
N8N_API = N8N_BASE + "/api/v1"
WEBHOOK = N8N_BASE + "/webhook/hector"

PG_CONTAINER = "barberia-postgres"
EVO_CONTAINER = "evolution_api"

WF_AGENTE = "barberiaAgenteUncensored"
WF_RECORDATORIOS = "barberiaRecordatorios"

JID_CLIENTE = "5214501111805@s.whatsapp.net"
JID_DUENO = "524521206246@s.whatsapp.net"          # el del contexto
JID_DUENO_ALT = "5214521206246@s.whatsapp.net"     # presente en barber_operadores

OUTDIR = r"G:\Barberia\archivos\_carga"


# ---------------------------------------------------------------- claves
def n8n_key():
    return open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()


def evolution_key():
    """Lee AUTHENTICATION_API_KEY del env del contenedor (fuente de verdad)."""
    out, err = docker_raw(["exec", EVO_CONTAINER, "printenv", "AUTHENTICATION_API_KEY"])
    k = out.strip()
    if k:
        return k
    # respaldo: del archivo .env.evolution
    for line in open(r"G:\Barberia\.env.evolution", encoding="utf-8"):
        if line.startswith("AUTHENTICATION_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no encontre AUTHENTICATION_API_KEY: %s" % err[:200])


# ---------------------------------------------------------------- docker
def docker_raw(args, timeout=180):
    try:
        p = subprocess.run([DOCKER] + list(args), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.stdout or "", p.stderr or ""
    except Exception as e:
        return "", "docker_excepcion: %s" % e


def docker(*args, timeout=180):
    return docker_raw(list(args), timeout=timeout)


def docker3(*args, timeout=180):
    """Devuelve (rc, stdout, stderr)."""
    try:
        p = subprocess.run([DOCKER] + list(args), capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env={**os.environ, "DOCKER_CONFIG": r"G:\Barberia\.docker"},
                           timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return -1, "", "docker_excepcion: %s" % e


# ---------------------------------------------------------------- postgres
def psql(sql, timeout=180):
    """psql -t -A -F'|'. Devuelve (rc, out, err)."""
    rc, out, err = 0, "", ""
    p = subprocess.run(
        [DOCKER, "exec", PG_CONTAINER, "psql", "-U", "barberia", "-d", "barberia",
         "-t", "-A", "-F", "|", "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "DOCKER_CONFIG": r"G:\Barberia\.docker"}, timeout=timeout)
    return p.returncode, p.stdout or "", p.stderr or ""


def q(sql, timeout=180):
    """SELECT -> lista de listas. Lanza si hay error (los ERROR van a stderr)."""
    rc, out, err = psql(sql, timeout=timeout)
    if rc != 0 or (not out.strip() and err.strip()):
        raise RuntimeError("SQL fallo rc=%s\nSTDERR: %s\nSQL: %s" % (rc, err.strip()[:500], sql[:200]))
    return [ln.split("|") for ln in out.splitlines() if ln.strip()]


def q1(sql):
    r = q(sql)
    return r[0] if r else None


def scal(sql):
    r = q1(sql)
    if not r:
        return None
    return r[0] if r[0] != "" else None


def sql_script(text, name="carga_script.sql", timeout=300):
    """Ejecuta un guion SQL completo en UNA sola sesion (necesario para
    bloques DO/BEGIN y para conservar el estado entre sentencias)."""
    local = os.path.join(OUTDIR, name)
    with open(local, "w", encoding="utf-8") as f:
        f.write(text)
    rc, out, err = docker("cp", local, "%s:/tmp/%s" % (PG_CONTAINER, name))
    if rc != 0:
        return rc, out, "docker cp fallo: %s" % err
    rc, out, err = docker("exec", PG_CONTAINER, "psql", "-U", "barberia",
                          "-d", "barberia", "-t", "-A", "-F", "|",
                          "-v", "ON_ERROR_STOP=1", "-f", "/tmp/%s" % name)
    return rc, out, err


# ---------------------------------------------------------------- n8n API
def api(path, method="GET", body=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N_API + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", n8n_key())
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return -1, str(e)


# ---------------------------------------------------------------- envio
def payload(jid, texto, mid=None, from_me=False, push="Prueba Carga"):
    return {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": ENV["EVOKEY"],
        "date_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "data": {
            "key": {"id": mid or ("T" + uuid.uuid4().hex[:10].upper()),
                    "remoteJid": jid, "fromMe": from_me},
            "pushName": push,
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }


def enviar(jid, texto, mid=None, from_me=False, timeout=180, push="Prueba Carga"):
    """POST sincrono al webhook. Devuelve dict con http, ms, msg_id."""
    body = payload(jid, texto, mid, from_me, push)
    mid = body["data"]["key"]["id"]
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode("utf-8"),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    res = {"msg_id": mid, "jid": jid, "texto": texto, "http": None,
           "error": None, "ms": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res["http"] = r.status
    except urllib.error.HTTPError as e:
        res["http"] = e.code
        try:
            res["error"] = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            res["error"] = "HTTP %s" % e.code
    except Exception as e:
        res["error"] = str(e)[:300]
    res["ms"] = int((time.time() - t0) * 1000)
    return res


def enviar_concurrente(envios, timeout=300):
    """envios: lista de (jid, texto[, mid[, from_me]]). Un hilo por mensaje.
    Devuelve lista de resultados en el mismo orden."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    res = [None] * len(envios)

    def work(i, spec):
        jid, texto = spec[0], spec[1]
        mid = spec[2] if len(spec) > 2 else None
        fm = spec[3] if len(spec) > 3 else False
        res[i] = enviar(jid, texto, mid, fm, timeout=timeout)

    with ThreadPoolExecutor(max_workers=max(1, len(envios))) as ex:
        futs = [ex.submit(work, i, s) for i, s in enumerate(envios)]
        for f in futs:
            try:
                f.result(timeout=timeout + 60)
            except Exception:
                pass
    return [r for r in res if r]


# ---------------------------------------------------------------- ejecuciones
def ejecuciones(wf=WF_AGENTE, limite=250):
    todas, cursor = [], None
    for _ in range(40):
        p = "/executions?workflowId=%s&limit=%d" % (wf, limite)
        if cursor:
            p += "&cursor=" + urllib.parse.quote(str(cursor))
        st, d = api(p)
        if st != 200 or not isinstance(d, dict):
            break
        lote = d.get("data") or []
        todas.extend(lote)
        cursor = d.get("nextCursor")
        if not cursor or not lote:
            break
    return todas


def ejecuciones_desde(wf, dt):
    """Ejecuciones con startedAt >= dt (datetime con tz)."""
    out = []
    for e in ejecuciones(wf):
        st = e.get("startedAt")
        if not st:
            continue
        try:
            t = datetime.fromisoformat(st.replace("Z", "+00:00"))
        except Exception:
            continue
        if t >= dt:
            out.append(e)
    return out


def detalle(eid, timeout=180):
    st, d = api("/executions/%s?includeData=true" % eid, timeout=timeout)
    return d if isinstance(d, dict) else {"id": str(eid), "_error": str(d)[:200]}


def nodos_de(ej):
    rd = (ej.get("data") or {}).get("resultData") or {}
    return rd.get("runData") or {}


def texto_salida(ej, nombre_nodo):
    """Extrae el texto de un nodo que manda/recibe mensajes."""
    run = nodos_de(ej).get(nombre_nodo)
    if not run:
        return None
    try:
        j = run[0]["data"]["main"][0][0]["json"]
    except Exception:
        return None
    msg = j.get("message")
    if isinstance(msg, dict):
        return (msg.get("conversation")
                or (msg.get("extendedTextMessage") or {}).get("text"))
    if isinstance(msg, str):
        return msg
    return j.get("text") or j.get("conversation")


def errores_de(ej):
    """Lista de (nodo, mensaje) de los errores de una ejecucion."""
    out = []
    rd = (ej.get("data") or {}).get("resultData") or {}
    if rd.get("error"):
        g = rd["error"]
        nodo = g.get("node")
        nombre = nodo.get("name") if isinstance(nodo, dict) else str(nodo)
        out.append((nombre, str(g.get("messages") or g.get("description"))[:400]))
    for nombre, ejecs in (rd.get("runData") or {}).items():
        for e in (ejecs or []):
            if isinstance(e, dict) and e.get("error"):
                er = e["error"]
                out.append((nombre, str(er.get("messages") or er.get("description"))[:400]))
    return out


def duracion_ms(ej):
    a, b = ej.get("startedAt"), ej.get("stoppedAt")
    if not a or not b:
        return None
    try:
        return int((datetime.fromisoformat(b.replace("Z", "+00:00"))
                    - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds() * 1000)
    except Exception:
        return None


# ---------------------------------------------------------------- varios
def esperar_quieto(max_seg=180, quieto=3, paso=8, wf=WF_AGENTE):
    """Espera hasta que el numero de ejecuciones deje de crecer."""
    prev, estables = -1, 0
    t0 = time.time()
    n = None
    while time.time() - t0 < max_seg:
        time.sleep(paso)
        n = len(ejecuciones(wf))
        if n == prev:
            estables += 1
            if estables >= quieto:
                break
        else:
            estables = 0
        prev = n
    return n


def docker_stats(containers=("barberia-n8n", "barberia-postgres", "evolution_api")):
    """docker stats --no-stream de los contenedores dados."""
    out = {}
    so, se = docker("stats", "--no-stream", "--format",
                    "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}",
                    *containers)
    for ln in so.strip().splitlines():
        if "|" in ln:
            f = ln.split("|")
            out[f[0]] = {"cpu": f[1], "mem": f[2], "mem_perc": f[3],
                         "net": f[4], "block": f[5]}
    if se.strip() and not out:
        out["_error"] = se.strip()[:300]
    return out


def h(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)
    sys.stdout.flush()


import urllib.parse  # noqa: E402  (usado en ejecuciones())

ENV = {}


def init():
    ENV["N8NKEY"] = n8n_key()
    ENV["EVOKEY"] = evolution_key()
    return ENV