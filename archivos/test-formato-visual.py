#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba en vivo del formato de las respuestas del agente "Chino".

Envia los 4 mensajes de sondeo por el webhook real de n8n, recupera la
respuesta que el bot mando por WhatsApp y la mide: lineas, caracteres,
emojis, asteriscos dobles, marcos ASCII y separadores largos.

Uso:
    uv run python archivos/test-formato-visual.py --fase antes
    uv run python archivos/test-formato-visual.py --fase despues
    uv run python archivos/test-formato-visual.py --solo-comparar

Guarda las mediciones en archivos/mediciones-<fase>.json y, cuando existen
ambas fases, imprime la tabla comparativa antes/despues.
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
JID = "5214501111805@s.whatsapp.net"
# El payload exige date_time; usar la hora real del negocio (America/Mexico_City)
# para que el agente vea "hoy" coherente con lo que el cliente escribe.
TIMEZONE_OFFSET = "-06:00"

KEY = os.environ.get("N8N_KEY", "")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

# --- Mensajes de sondeo (provocan respuestas largas de distinto tipo) -------
CASOS = [
    ("lista", "dame la lista completa de servicios"),
    ("confirmacion", "quiero agendar un corte el jueves a las 4"),
    ("precio", "cuanto cuesta el corte?"),
    ("consulta", "ya tengo una cita?"),
]

# Caso extra (no entra en la comparativa): busca un hueco libre de verdad para
# poder ver el bloque de confirmacion completo. Fecha explicita y lejana.
CASO_EXTRA = ("confirmacion_libre",
              "quiero un corte desvanecido el martes 3 de noviembre a las 5 de la tarde")

# --- Detectores de formato ------------------------------------------------
BOX = re.compile(r"[\u2500-\u257F\u2580-\u259F]")
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF"
    "\u2190-\u21FF\u2B50\uFE0F\u200D]")
# Separadores dibujados con muchos caracteres repetidos (━━━, ───)
SEPARADOR = re.compile(r"^(?:\s*[=\-_~*#\u2500\u2501\u2550\u2504\u2505]{4,}\s*)$")


def limpiar_emojis(t):
    """Cuenta emojis sin contar dos veces el selector de variacion."""
    return len([c for c in EMOJI.findall(t) if c != "\uFE0F" and c != "\u200D"])


def medir(texto):
    """Devuelve las metricas de formato de un mensaje del bot."""
    lineas = [l for l in texto.split("\n")]
    no_vacias = [l for l in lineas if l.strip()]
    emojis = limpiar_emojis(texto)
    dobles = len(re.findall(r"\*\*", texto))
    # negrita real de WhatsApp: *texto* que no sea parte de **
    simples = len(re.findall(r"(?<!\*)\*(?!\*)[^*\n]+\*(?!\*)", texto))
    caja = len(BOX.findall(texto))
    sep = sum(1 for l in lineas if SEPARADOR.match(l))
    largos = [l for l in lineas if len(l) > 60]
    # cuenta frases interrogativas: un '?' por pregunta
    preguntas = texto.count("?")
    # Markdown de dos espacios al final del renglon: WhatsApp NO lo interpreta
    # como salto, deja huecos raros y puede romper la negrita.
    esp_finales = sum(1 for l in lineas if l.endswith("  "))
    # lineas que contienen un dato duro localizable
    dato = any(re.search(r"\$\d+|\d{1,2}:\d{2}", l) for l in lineas)
    return {
        "caracteres": len(texto),
        "lineas": len(lineas),
        "lineas_no_vacias": len(no_vacias),
        "emojis": emojis,
        "asteriscos_dobles": dobles,
        "negritas_validas": simples,
        "caracteres_marco_ascii": caja,
        "separadores_largos": sep,
        "espacios_finales_dobles": esp_finales,
        "lineas_mayores_60": len(largos),
        "preguntas": preguntas,
        "tiene_dato_clave": dato,
        "max_largo_linea": max((len(l) for l in lineas), default=0),
    }


def problemas(m, texto):
    """Lista de fallos de formato detectados, en texto legible."""
    out = []
    if m["asteriscos_dobles"]:
        out.append("USA ** (WhatsApp no lo renderiza): %d" % m["asteriscos_dobles"])
    if m["caracteres_marco_ascii"]:
        out.append("marcos/seps ASCII (╔ ┏ ━): %d caracteres"
                   % m["caracteres_marco_ascii"])
    if m["separadores_largos"]:
        out.append("separadores largos: %d" % m["separadores_largos"])
    if m["espacios_finales_dobles"]:
        out.append("dos espacios al final del renglon (no es salto en WhatsApp): %d"
                   % m["espacios_finales_dobles"])
    if m["lineas"] > 12:
        out.append("demasiadas lineas: %d (>12)" % m["lineas"])
    if m["emojis"] > 2:
        out.append("demasiados emojis: %d (>2)" % m["emojis"])
    if m["caracteres"] > 600:
        out.append("demasiado largo: %d caracteres (>600)" % m["caracteres"])
    if not out:
        out.append("sin problemas de formato")
    return out


# --- Acceso a n8n ---------------------------------------------------------
def api(path):
    r = urllib.request.Request(N8N + path)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())


def apikey_evolution():
    if KEY:
        pass
    out = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                          "AUTHENTICATION_API_KEY"],
                         capture_output=True, text=True).stdout.strip()
    return out


def enviar(texto, apikey, mid):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": apikey,
        "date_time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z",
                                   time.gmtime()),
        "data": {
            "key": {"id": mid, "remoteJid": JID, "fromMe": False},
            "pushName": "Prueba Formato",
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
    """Extrae el mensaje que el bot mando a WhatsApp (nod 'Mandar mensaje')."""
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


def id_entrante(run):
    """message id del webhook, para emparejar ejecucion y mensaje enviado."""
    nodo = run.get("Webhook")
    if not nodo:
        return None
    try:
        return nodo[0]["data"]["main"][0][0]["json"]["body"]["data"]["key"]["id"]
    except Exception:
        return None


def recolectar(desde_ts, ids):
    """Busca ejecuciones recientes y devuelve {id_mensaje: {texto, metrics}}."""
    res = {}
    ex = api("/executions?workflowId=%s&limit=40" % WID)
    for e in ex.get("data", []):
        if e["id"] < desde_ts:
            continue
        try:
            det = api("/executions/%s?includeData=true" % e["id"])
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        mid = id_entrante(run)
        if mid in ids and mid not in res:
            res[mid] = texto_del_bot(run)
    return res


def correr(fase, extra=False):
    apikey = apikey_evolution()
    # id de ejecucion mas alto antes de empezar
    ex = api("/executions?workflowId=%s&limit=1" % WID)
    base_id = ex["data"][0]["id"] if ex.get("data") else 0

    casos = list(CASOS) + ([CASO_EXTRA] if extra else [])
    preguntas = dict(casos)
    ids = {}
    print("=" * 78)
    print("PRUEBA DE FORMATO EN VIVO — fase: %s" % fase.upper())
    print("=" * 78)
    for nombre, texto in casos:
        mid = "F" + uuid.uuid4().hex[:12].upper()
        ids[mid] = nombre
        print("\n[%s] CLIENTE: %s" % (nombre, texto))
        print("       mid=%s  webhook -> %s" % (mid, enviar(texto, apikey, mid)))
        time.sleep(14)
    print("\nesperando 45 s a que cierren las ejecuciones...")
    time.sleep(45)

    respuestas = recolectar(base_id, set(ids))

    registro = {}
    for mid, nombre in ids.items():
        txt = respuestas.get(mid)
        if txt is None:
            print("\n[%s] SIN RESPUESTA REGISTRADA (revisar ejecucion)" % nombre)
            registro[nombre] = {"pregunta": preguntas.get(nombre),
                                "respuesta": None, "metricas": None,
                                "problemas": ["sin respuesta registrada"]}
            continue
        m = medir(txt)
        registro[nombre] = {
            "pregunta": preguntas.get(nombre),
            "respuesta": txt,
            "metricas": m,
            "problemas": problemas(m, txt),
        }
        print("\n[%s] RESPUESTA DEL BOT:" % nombre)
        print("-" * 78)
        print(txt)
        print("-" * 78)
        print("       metricas: %s" % json.dumps(m, ensure_ascii=False))
        print("       problemas: %s" % " | ".join(problemas(m, txt)))

    ruta = os.path.join(BASE, "mediciones-%s.json" % fase)
    json.dump(registro, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\nmediciones guardadas en %s" % ruta)
    return registro


def comparar():
    rutas = {f: os.path.join(BASE, "mediciones-%s.json" % f)
             for f in ("antes", "despues")}
    for f, r in rutas.items():
        if not os.path.exists(r):
            print("falta %s (corre la fase '%s' primero)" % (r, f))
            return 1
    a = json.load(open(rutas["antes"], encoding="utf-8"))
    d = json.load(open(rutas["despues"], encoding="utf-8"))

    campos = ["caracteres", "lineas", "lineas_no_vacias", "emojis",
              "asteriscos_dobles", "negritas_validas", "caracteres_marco_ascii",
              "separadores_largos", "espacios_finales_dobles",
              "lineas_mayores_60", "max_largo_linea"]

    print("=" * 78)
    print("COMPARATIVA ANTES / DESPUES  (suma de los 4 mensajes o media)")
    print("=" * 78)
    cab = "%-24s %10s %10s %10s" % ("metrica", "ANTES", "DESPUES", "cambio")
    print(cab)
    print("-" * 78)
    for c in campos:
        va = sum((a[k]["metricas"] or {}).get(c, 0) for k in a)
        vd = sum((d[k]["metricas"] or {}).get(c, 0) for k in d)
        dif = vd - va
        signo = "+" if dif > 0 else ""
        print("%-24s %10s %10s %10s" % (c, va, vd, signo + str(dif)))
    print("-" * 78)
    print("%-24s %10s %10s" % ("mensajes con problemas",
                               sum(1 for k in a if a[k]["problemas"] !=
                                   ["sin problemas de formato"]),
                               sum(1 for k in d if d[k]["problemas"] !=
                                   ["sin problemas de formato"])))

    print("\n" + "=" * 78)
    print("DETALLE POR MENSAJE")
    print("=" * 78)
    for nombre in [c[0] for c in CASOS]:
        print("\n### %s — %s" % (nombre, dict(CASOS).get(nombre)))
        for etq, reg in (("ANTES", a), ("DESPUES", d)):
            r = reg.get(nombre) or {}
            m = r.get("metricas") or {}
            print("  %-8s %s" % (etq, json.dumps(m, ensure_ascii=False)))
            print("           %s" % " | ".join(r.get("problemas") or []))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fase", choices=["antes", "despues"], default=None)
    p.add_argument("--solo-comparar", action="store_true")
    p.add_argument("--extra", action="store_true",
                   help="agrega el caso de confirmacion con hueco libre real")
    a = p.parse_args()
    if a.solo_comparar:
        return comparar()
    if not a.fase:
        p.error("indica --fase antes|despues o --solo-comparar")
    correr(a.fase, extra=a.extra)
    return comparar()


if __name__ == "__main__":
    sys.exit(main())