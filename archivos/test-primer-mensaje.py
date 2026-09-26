#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba en vivo del PRIMER MENSAJE del agente "Chino" (Barber Chinos).

Manda los 6 mensajes de sondeo por el webhook real de n8n, recupera la
respuesta que el bot mando por WhatsApp y la mide: caracteres, lineas,
emojis, y si usa `**` / marcos ASCII / separadores largos.

Para que el caso sea de verdad "primer mensaje", antes de cada envio se
limpia la memoria de la sesion (tabla `n8n_chat_histories`, clave =
remoteJid). La memoria original se respalda con COPY y se restaura al final.

Uso:
    uv run python archivos/test-primer-mensaje.py --fase antes
    uv run python archivos/test-primer-mensaje.py --fase despues
    uv run python archivos/test-primer-mensaje.py --solo-comparar
    uv run python archivos/test-primer-mensaje.py --solo-medir

--solo-medir NO reenvia nada: relee las respuestas crudas ya guardadas en
archivos/respuestas-primer-mensaje-<fase>.json y recalcula las metricas.
"""
import argparse
import json
import os
import re
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

N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
WEBHOOK = "http://localhost:5678/webhook/hector"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
BASE = r"G:\Barberia\archivos"
KEY = open(os.path.join(BASE, ".n8n-key.txt")).read().strip()
JID = "5214501111805@s.whatsapp.net"
BACKUP_MEM = os.path.join(BASE, "_memoria-chat-backup.tsv")

os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

# Los 6 mensajes que pidio el usuario.
CASOS = [
    ("hola", "hola"),
    ("buenas_tardes", "buenas tardes"),
    ("servicios", "que servicios tienen?"),
    ("cita", "quiero una cita"),
    ("precio_corte", "cuanto cuesta el corte?"),
    ("informes", "Buenos d\u00edas, quisiera informes"),
]

# Mensajes extra de no-regresion (no entran en la comparativa antes/despues).
NO_REGRESION = [
    ("agendar_jueves", "quiero un corte el jueves a las 4"),
    ("precio_ceja", "cuanto cuesta la ceja?"),
    ("gracias", "gracias"),
]

# --- Detectores de formato (reglas de WhatsApp del contexto) ---------------
BOX = re.compile(r"[\u2500-\u257F\u2580-\u259F]")
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF"
    "\u2190-\u21FF\u2B50\uFE0F\u200D]")
SEPARADOR = re.compile(r"^(?:\s*[=\-_~*#\u2500\u2501\u2550\u2504\u2505]{4,}\s*)$")

# Limites duros (los del contexto + el tope de 12 lineas del pedido).
MAX_LINEAS = 12
MAX_CHARS = 600
MAX_EMOJIS = 2


def limpiar_emojis(t):
    return len([c for c in EMOJI.findall(t) if c not in ("\uFE0F", "\u200D")])


def medir(texto):
    lineas = texto.split("\n")
    return {
        "caracteres": len(texto),
        "lineas": len(lineas),
        "lineas_no_vacias": len([l for l in lineas if l.strip()]),
        "emojis": limpiar_emojis(texto),
        "asteriscos_dobles": len(re.findall(r"\*\*", texto)),
        "negritas_validas": len(re.findall(r"(?<!\*)\*(?!\*)[^*\n]+\*(?!\*)", texto)),
        "caracteres_marco_ascii": len(BOX.findall(texto)),
        "separadores_largos": sum(1 for l in lineas if SEPARADOR.match(l)),
        "espacios_finales_dobles": sum(1 for l in lineas if l.endswith("  ")),
        "lineas_mayores_60": len([l for l in lineas if len(l) > 60]),
        "preguntas": texto.count("?"),
        "max_largo_linea": max((len(l) for l in lineas), default=0),
    }


def problemas(m, texto):
    out = []
    if m["asteriscos_dobles"]:
        out.append("USA ** (%d): WhatsApp no lo renderiza" % m["asteriscos_dobles"])
    if m["caracteres_marco_ascii"]:
        out.append("marcos/lineas ASCII: %d caracteres" % m["caracteres_marco_ascii"])
    if m["separadores_largos"]:
        out.append("separadores largos: %d" % m["separadores_largos"])
    if m["espacios_finales_dobles"]:
        out.append("dos espacios al final del renglon: %d" % m["espacios_finales_dobles"])
    if m["lineas"] > MAX_LINEAS:
        out.append("demasiadas lineas: %d (>%d)" % (m["lineas"], MAX_LINEAS))
    if m["emojis"] > MAX_EMOJIS:
        out.append("demasiados emojis: %d (>%d)" % (m["emojis"], MAX_EMOJIS))
    if m["caracteres"] > MAX_CHARS:
        out.append("demasiado largo: %d caracteres (>%d)" % (m["caracteres"], MAX_CHARS))
    if m["preguntas"] > 2:
        out.append("muchas preguntas: %d" % m["preguntas"])
    return out or ["sin problemas de formato"]


def muestra_menu(t):
    """Heuristica: la respuesta es un menu si lista >=4 servicios con precio."""
    return len(re.findall(r"-\s", t)) >= 4


# --- n8n / Evolution ------------------------------------------------------
def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())


def apikey_evolution():
    return subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                           "AUTHENTICATION_API_KEY"],
                          capture_output=True, text=True).stdout.strip()


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def respaldar_memoria():
    """Guarda toda n8n_chat_histories a un TSV (COPY escapa saltos de linea)."""
    if os.path.exists(BACKUP_MEM):
        return
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-A", "-t", "-c",
                        "COPY n8n_chat_histories TO STDOUT;"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    with open(BACKUP_MEM, "w", encoding="utf-8", newline="\n") as f:
        f.write(p.stdout or "")
    print("memoria respaldada en %s (%d lineas)"
          % (BACKUP_MEM, len((p.stdout or "").splitlines())))


def restaurar_memoria():
    if not os.path.exists(BACKUP_MEM):
        print("no hay respaldo de memoria; nada que restaurar")
        return
    psql("TRUNCATE n8n_chat_histories;")
    subprocess.run([DOCKER, "cp", BACKUP_MEM,
                    "barberia-postgres:/tmp/_mem.tsv"], capture_output=True)
    o, e = psql("\\copy n8n_chat_histories FROM '/tmp/_mem.tsv'")
    n, _ = psql("SELECT count(*) FROM n8n_chat_histories;")
    print("memoria restaurada: %s filas (err: %s)" % (n, e[:120] or "ninguno"))


def limpiar_sesion():
    psql("DELETE FROM n8n_chat_histories WHERE session_id = '%s';" % JID)


def enviar(texto, apikey, mid):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": apikey,
        "date_time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "data": {
            "key": {"id": mid, "remoteJid": JID, "fromMe": False},
            "pushName": "Prueba Primer Mensaje",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)


def texto_del_bot(run):
    """La respuesta vive en el nodo 'Mandar mensaje' -> message.conversation."""
    nodo = run.get("Mandar mensaje")
    if not nodo:
        return None
    for salida in reversed(nodo):
        try:
            item = salida["data"]["main"][0][0]["json"]
        except Exception:
            continue
        msg = item.get("message") or {}
        txt = (msg.get("conversation")
               or (msg.get("extendedTextMessage") or {}).get("text"))
        if txt:
            return txt
    return None


def error_de(run):
    for nombre, nodo in run.items():
        for salida in (nodo or []):
            if salida.get("error"):
                return "%s: %s" % (nombre, str(salida["error"])[:200])
    return None


def id_entrante(run):
    nodo = run.get("Webhook")
    try:
        return nodo[0]["data"]["main"][0][0]["json"]["body"]["data"]["key"]["id"]
    except Exception:
        return None


def esperar_respuesta(mid, base_id, timeout=55):
    """Sondea las ejecuciones nuevas hasta encontrar la de nuestro mid."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(5)
        try:
            ex = api("/executions?workflowId=%s&limit=25" % WID)
        except Exception:
            continue
        for e in ex.get("data", []):
            if e["id"] <= base_id:
                continue
            try:
                det = api("/executions/%s?includeData=true" % e["id"])
            except Exception:
                continue
            run = (((det.get("data") or {}).get("resultData") or {})
                   .get("runData") or {})
            if id_entrante(run) != mid:
                continue
            return {"estado": det.get("status"), "texto": texto_del_bot(run),
                    "error": error_de(run), "ejecucion": e["id"]}
    return {"estado": "sin_respuesta", "texto": None, "error": None,
            "ejecucion": None}


def lote(nombre_fase, casos, apikey, etiqueta):
    ex = api("/executions?workflowId=%s&limit=1" % WID)
    base_id = ex["data"][0]["id"] if ex.get("data") else 0
    print("=" * 78)
    print("PRIMER MENSAJE (memoria limpia) — %s [%s]" % (nombre_fase.upper(), etiqueta))
    print("=" * 78)

    registro = {}
    for clave, texto in casos:
        mid = "M" + uuid.uuid4().hex[:12].upper()
        limpiar_sesion()
        enviar(texto, apikey, mid)  # el primer mensaje
        r = esperar_respuesta(mid, base_id)
        base_id = max(base_id, r.get("ejecucion") or 0)

        if r["texto"] is None:
            print("\n[%s] CLIENTE: %s" % (clave, texto))
            print("       SIN RESPUESTA (%s) err=%s" % (r["estado"], r["error"]))
            registro[clave] = {"pregunta": texto, "respuesta": None,
                               "metricas": None, "ejecucion": r["ejecucion"],
                               "problemas": ["sin respuesta: %s" % r["estado"]],
                               "es_menu": False}
            continue

        m = medir(r["texto"])
        registro[clave] = {
            "pregunta": texto, "respuesta": r["texto"], "metricas": m,
            "ejecucion": r["ejecucion"], "problemas": problemas(m, r["texto"]),
            "es_menu": muestra_menu(r["texto"]),
        }
        print("\n[%s] CLIENTE: %s" % (clave, texto))
        print("-" * 78)
        print(r["texto"])
        print("-" * 78)
        print("       chars=%d lineas=%d emojis=%d **=%d menu=%s"
              % (m["caracteres"], m["lineas"], m["emojis"],
                 m["asteriscos_dobles"], registro[clave]["es_menu"]))
        print("       problemas: %s" % " | ".join(registro[clave]["problemas"]))
        time.sleep(6)
    return registro


def guardar(nombre, registro):
    ruta = os.path.join(BASE, "respuestas-primer-mensaje-%s.json" % nombre)
    json.dump(registro, open(ruta, "w", encoding="utf-8"), ensure_ascii=False,
              indent=2)
    print("\nguardado: %s" % ruta)
    return ruta


def cargar(nombre):
    ruta = os.path.join(BASE, "respuestas-primer-mensaje-%s.json" % nombre)
    if not os.path.exists(ruta):
        print("falta %s (corre la fase primero)" % ruta)
        return None
    return json.load(open(ruta, encoding="utf-8"))


def recalc(reg):
    """Recalcula metricas desde el texto crudo (modo --solo-medir)."""
    for k, v in (reg or {}).items():
        if v.get("respuesta"):
            v["metricas"] = medir(v["respuesta"])
            v["problemas"] = problemas(v["metricas"], v["respuesta"])
            v["es_menu"] = muestra_menu(v["respuesta"])
    return reg


def tabla(nombre, reg):
    print("\n" + "=" * 78)
    print("MEDICION — %s" % nombre.upper())
    print("=" * 78)
    print("%-14s %8s %6s %7s %5s %6s %6s %6s" %
          ("caso", "chars", "lineas", "emojis", "**", "**total", "menu", "preg"))
    print("-" * 78)
    for clave, _ in CASOS:
        v = (reg or {}).get(clave) or {}
        m = v.get("metricas") or {}
        print("%-14s %8s %6s %7s %5s %6s %6s %6s" %
              (clave, m.get("caracteres", "-"), m.get("lineas", "-"),
               m.get("emojis", "-"), m.get("asteriscos_dobles", "-"),
               m.get("asteriscos_dobles", "-"), v.get("es_menu", "-"),
               m.get("preguntas", "-")))
    print("-" * 78)
    n_menu = sum(1 for k, _ in CASOS if (reg.get(k) or {}).get("es_menu"))
    print("casos con menu de servicios: %d/%d" % (n_menu, len(CASOS)))
    con_prob = sum(1 for k, _ in CASOS
                   if (reg.get(k) or {}).get("problemas") not in
                   (None, ["sin problemas de formato"]))
    print("casos con problemas de formato: %d/%d" % (con_prob, len(CASOS)))


def comparar():
    a = cargar("antes")
    d = cargar("despues")
    if a is None or d is None:
        return 1
    campos = ["caracteres", "lineas", "emojis", "asteriscos_dobles",
              "negritas_validas", "caracteres_marco_ascii",
              "separadores_largos", "espacios_finales_dobles",
              "lineas_mayores_60", "preguntas", "max_largo_linea"]
    print("\n" + "=" * 78)
    print("COMPARATIVA ANTES / DESPUES — suma de los 6 mensajes")
    print("=" * 78)
    print("%-26s %10s %10s %10s" % ("metrica", "ANTES", "DESPUES", "cambio"))
    print("-" * 78)
    for c in campos:
        va = sum(((a.get(k) or {}).get("metricas") or {}).get(c, 0) for k, _ in CASOS)
        vd = sum(((d.get(k) or {}).get("metricas") or {}).get(c, 0) for k, _ in CASOS)
        dif = vd - va
        print("%-26s %10s %10s %10s" % (c, va, vd, ("+" if dif > 0 else "") + str(dif)))
    print("-" * 78)
    ma = sum(1 for k, _ in CASOS if (a.get(k) or {}).get("es_menu"))
    md = sum(1 for k, _ in CASOS if (d.get(k) or {}).get("es_menu"))
    print("%-26s %10s %10s %10s" % ("casos con menu", ma, md, ("+" if md > ma else "") + str(md - ma)))
    pa = sum(1 for k, _ in CASOS if (a.get(k) or {}).get("problemas") not in (None, ["sin problemas de formato"]))
    pd = sum(1 for k, _ in CASOS if (d.get(k) or {}).get("problemas") not in (None, ["sin problemas de formato"]))
    print("%-26s %10s %10s %10s" % ("casos con problemas", pa, pd, ("+" if pd > pa else "") + str(pd - pa)))

    print("\n" + "=" * 78)
    print("DETALLE POR MENSAJE")
    print("=" * 78)
    for clave, texto in CASOS:
        print("\n### %s — \"%s\"" % (clave, texto))
        for etq, reg in (("ANTES", a), ("DESPUES", d)):
            v = reg.get(clave) or {}
            m = v.get("metricas") or {}
            print("  %-8s chars=%s lineas=%s emojis=%s **=%s menu=%s"
                  % (etq, m.get("caracteres"), m.get("lineas"), m.get("emojis"),
                     m.get("asteriscos_dobles"), v.get("es_menu")))
            print("           %s" % " | ".join(v.get("problemas") or []))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fase", choices=["antes", "despues"])
    p.add_argument("--solo-comparar", action="store_true")
    p.add_argument("--solo-medir", action="store_true",
                   help="recalcula metricas desde lo guardado, sin reenviar")
    p.add_argument("--no-regresion", action="store_true",
                   help="corre ademas los 3 casos de no-regresion")
    p.add_argument("--restaurar-memoria", action="store_true",
                   help="solo restaura la memoria respaldada y sale")
    a = p.parse_args()

    if a.restaurar_memoria:
        restaurar_memoria()
        return 0

    if a.solo_medir:
        reg = recalc(cargar(a.fase)) if a.fase else None
        if reg is None:
            for f in ("antes", "despues"):
                r = recalc(cargar(f))
                if r:
                    guardar(f, r)
                    tabla(f, r)
            return 0
        guardar(a.fase, reg)
        tabla(a.fase, reg)
        return 0

    if a.solo_comparar:
        return comparar()

    if not a.fase:
        p.error("indica --fase antes|despues, --solo-comparar, --solo-medir\n"
                "o --restaurar-memoria")

    apikey = apikey_evolution()
    respaldar_memoria()
    reg = lote(a.fase, CASOS, apikey, "6 mensajes del pedido")
    guardar(a.fase, reg)
    tabla(a.fase, reg)

    if a.no_regresion:
        nr = lote(a.fase + "-no-regresion", NO_REGRESION, apikey, "no-regresion")
        guardar(a.fase + "-no-regresion", nr)

    restaurar_memoria()
    if a.fase == "despues":
        comparar()
    return 0


if __name__ == "__main__":
    sys.exit(main())