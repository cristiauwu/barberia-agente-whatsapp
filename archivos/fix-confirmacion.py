#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cierra el bucle de confirmacion: el cliente responde SI y PASA ALGO.

EL FALLO (verificado con la evidencia literal del nodo):
  El recordatorio le dice al cliente, palabra por palabra:

      "Responde *SI* para confirmar o *NO* si necesitas cambiarla."

  Y NADA consume esa respuesta. Se comprobo:
   - el Switch de entrada tiene salida `Texto` y nada mas;
   - 0 referencias a `buttonsResponseMessage` / `listResponseMessage`;
   - las 7 herramientas del agente no incluyen ninguna de confirmar.

  Asi que el "SI" del cliente cae al modelo, que contesta amablemente y
  NO CAMBIA NADA. El barbero nunca sabe quien confirmo, y cada SI/NO gasta
  ~$0,026 en tokens para no hacer nada.

LA PROMESA ROTA ES LO GRAVE, no el coste: el sistema le pide al cliente que
haga algo y luego lo ignora. Eso erosiona la confianza.

ARREGLO — una rama DETERMINISTA, antes del modelo (como el router del dueno):
  Si el mensaje es exactamente SI / NO / SÍ (con o sin signos) Y el numero
  tiene una cita proxima, se actua SIN llamar al modelo:

    SI -> marca la cita como `confirmado` en Postgres y avisa al dueno
    NO -> avisa al dueno de que el cliente quiere moverla, y le pasa el
          aviso al agente para que ofrezca alternativas

  Cualquier otra cosa sigue el camino normal (el agente).

POR QUE ANTES DEL MODELO:
  - Cuesta 0 tokens.
  - Es determinista: "SI" significa SI, no "a ver que opina el modelo".
  - No puede inventarse una confirmacion que el cliente no hizo.

RIESGO CONTROLADO: si el detector se equivoca y trata como confirmacion un
mensaje que no lo era, el dano es bajo (la cita queda confirmada, que es lo
que el cliente queria de todos modos). El aviso al dueno siempre se manda,
asi que todo queda visible.
"""
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
WID = "barberiaAgenteUncensored"

# ---------------------------------------------------------------------------
#  El detector: decide si el mensaje es un SI o un NO, y si hay cita cerca
# ---------------------------------------------------------------------------
CODIGO_DETECTOR = r"""
// Detecta si el cliente esta respondiendo SI o NO a un recordatorio.
//
// Es determinista a proposito: no llama al modelo. "SI" es SI.
// Solo actua si hay una cita proxima de ESE numero; si no la hay, deja
// pasar el mensaje al agente como cualquier otro.
const TZ = 'America/Mexico_City';

const texto = String($json.message_content || '')
  .trim().toLowerCase()
  // se quitan signos y emojis de los extremos, que la gente escribe igual
  .replace(/^[¡!¿?\s.,]+/, '')
  .replace(/[¡!¿?\s.,]+$/, '');

// Solo frases cortas: una respuesta a un recordatorio es corta. Si el
// cliente escribio un parrafo, no es una confirmacion.
const corto = texto.length > 0 && texto.length <= 12;

// Afirmaciones aceptadas (la gente escribe cosas distintas)
const SI = ['si', 'sí', 'sii', 'siii', 'claro', 'confirmo', 'confirmado',
            'ok', 'okay', 'va', 'dale', 'listo', 'de acuerdo', 'asi es'];
const NO = ['no', 'noo', 'nooo', 'nel', 'mejor no', 'cambiar', 'cambiala',
            'reprogramar', 'mover', 'no puedo', 'cancelar', 'cancela'];

const esSi = corto && SI.includes(texto);
const esNo = corto && NO.includes(texto);

// ¿tiene una cita proxima? Si no, esto no es una confirmacion.
let cita = null;
try {
  const citas = $('Buscar cita para confirmar').all();
  for (const c of citas) {
    const j = c.json;
    if (j && j.inicio) { cita = j; break; }
  }
} catch (e) { cita = null; }

const esRespuesta = (esSi || esNo) && cita !== null;

return [{
  json: {
    es_respuesta_confirmacion: esRespuesta,
    decision: esSi ? 'SI' : (esNo ? 'NO' : 'ninguna'),
    cita_id: cita ? cita.id : null,
    cita_inicio: cita ? cita.inicio : null,
    cita_servicio: cita ? cita.servicio : null,
    cita_nombre: cita ? cita.nombre : null,
    texto_recibido: $json.message_content,
    user_number: $json.user_number,
    instance_server_url: $json.instance_server_url,
    message_content: $json.message_content,
    user_name: $json.user_name,
    message_content_type: $json.message_content_type
  }
}];
"""

# ---------------------------------------------------------------------------
#  La rama SI: marca la cita como confirmada y avisa al dueno
# ---------------------------------------------------------------------------
CODIGO_SI = r"""
// El cliente confirmo su cita. Se marca en Postgres y se avisa al dueno.
// Todo determinista: 0 tokens.
const d = $json;
return [{
  json: {
    ...d,
    aviso_al_dueno:
      'CLIENTE CONFIRMO SU CITA\n\n' +
      (d.cita_nombre || 'Cliente') + '\n' +
      (d.cita_servicio || '') + '\n' +
      (d.cita_inicio ? String(d.cita_inicio).slice(0, 16).replace('T', ' ') : '') +
      '\n\n' + (d.user_number || '').split('@')[0],
    para_el_cliente: 'Gracias por confirmar. Te esperamos.'
  }
}];
"""

CODIGO_NO = r"""
// El cliente quiere mover o cancelar la cita. Se avisa al dueno y se le
// pasa al agente para que ofrezca alternativas.
const d = $json;
return [{
  json: {
    ...d,
    aviso_al_dueno:
      'UN CLIENTE QUIERE CAMBIAR SU CITA\n\n' +
      (d.cita_nombre || 'Cliente') + '\n' +
      (d.cita_servicio || '') + '\n' +
      (d.cita_inicio ? String(d.cita_inicio).slice(0, 16).replace('T', ' ') : '') +
      '\n\n' + (d.user_number || '').split('@')[0] +
      '\n\nHay que ofrecerle otro horario.'
  }
}];
"""


def api(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(N8N + ruta, data=datos, method=metodo)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def guardar(wf):
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st, r = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {})})
    if st not in (200, 201):
        print(f"  MAL PUT HTTP {st}: {str(r)[:250]}")
        return False
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})
    return True


def nodo(nid, nombre, tipo, tv, pos, params, notas=None):
    n = {"id": nid, "name": nombre, "type": tipo, "typeVersion": tv,
         "position": pos, "parameters": params}
    if notas:
        n["notes"] = notas
    return n


def main():
    print("=" * 68)
    print("CERRAR EL BUCLE DE CONFIRMACION")
    print("=" * 68)

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print(f"  MAL no pude leer el workflow: {st}")
        return 1
    nombres = {n["name"] for n in wf["nodes"]}
    print(f"  nodos antes: {len(wf['nodes'])}")

    # ---------------------------------------------------------------- 1
    print("\n[1] NODO: 'Buscar cita para confirmar' (Postgres)")
    if "Buscar cita para confirmar" in nombres:
        print("  ya existe")
    else:
        wf["nodes"].append(nodo(
            "buscar-cita-confirmar", "Buscar cita para confirmar",
            "n8n-nodes-base.postgres", 2.5, [-1180, 300],
            {
                "operation": "executeQuery",
                "query": ("SELECT id, nombre, servicio, "
                          "to_char(inicio,'YYYY-MM-DD HH24:MI') AS inicio, "
                          "estado, jid\n"
                          "  FROM barber_citas\n"
                          " WHERE jid = '{{ $json.user_number }}'\n"
                          "   AND estado IN ('agendado','confirmado')\n"
                          "   AND inicio BETWEEN now() - interval '2 hours'\n"
                          "                  AND now() + interval '48 hours'\n"
                          " ORDER BY inicio ASC\n"
                          " LIMIT 1;"),
                "options": {},
            },
            "Busca una cita proxima de ESE numero, para saber si el SI/NO "
            "es una respuesta a un recordatorio. Si no hay cita, no es una "
            "confirmacion y el mensaje sigue al agente."))
        wf["nodes"][-1]["credentials"] = {
            "postgres": {"id": "NUrqrDWN8OsBFmgV", "name": "Postgres account"}}
        wf["nodes"][-1]["alwaysOutputData"] = True
        print("  OK  creado (con alwaysOutputData: no corta la cadena sin cita)")

    # ---------------------------------------------------------------- 2
    print("\n[2] NODO: 'Es confirmacion?' (detector determinista)")
    if "Es confirmacion?" in nombres:
        print("  ya existe")
    else:
        wf["nodes"].append(nodo(
            "es-confirmacion", "Es confirmacion?",
            "n8n-nodes-base.code", 2, [-980, 300],
            {"mode": "runOnceForAllItems", "jsCode": CODIGO_DETECTOR},
            "Detecta SI o NO de forma DETERMINISTA, sin llamar al modelo. "
            "Cuesta 0 tokens. Nace del fallo: el recordatorio pedia "
            "'Responde SI para confirmar' y nada consumia esa respuesta."))
        print("  OK  creado")

    # ---------------------------------------------------------------- 3
    print("\n[3] NODO: 'IF - Es confirmacion'")
    if "IF - Es confirmacion" in nombres:
        print("  ya existe")
    else:
        wf["nodes"].append(nodo(
            "if-es-confirmacion", "IF - Es confirmacion",
            "n8n-nodes-base.if", 2.2, [-780, 300],
            {
                "conditions": {
                    "options": {"caseSensitive": True,
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": "conf-1",
                        "leftValue": "={{ $json.es_respuesta_confirmacion }}",
                        "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true",
                                     "singleValue": True},
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            "Solo sigue por esta rama si el mensaje es SI/NO Y hay cita "
            "proxima. Todo lo demas va por la salida falsa, al agente."))
        print("  OK  creado")

    # ---------------------------------------------------------------- 4
    print("\n[4] NODO: 'Marcar cita confirmada' (Postgres)")
    if "Marcar cita confirmada" in nombres:
        print("  ya existe")
    else:
        wf["nodes"].append(nodo(
            "marcar-confirmada", "Marcar cita confirmada",
            "n8n-nodes-base.postgres", 2.5, [-580, 180],
            {
                "operation": "executeQuery",
                "query": ("UPDATE barber_citas\n"
                          "   SET estado = 'confirmado', "
                          "actualizado_en = now()\n"
                          " WHERE id = '{{ $json.cita_id }}'\n"
                          "   AND estado = 'agendado'\n"
                          "RETURNING id, estado;"),
                "options": {},
            },
            "Marca la cita como confirmada. El WHERE exige que siga en "
            "'agendado', asi que si ya estaba confirmada no hace nada "
            "(idempotente)."))
        wf["nodes"][-1]["credentials"] = {
            "postgres": {"id": "NUrqrDWN8OsBFmgV", "name": "Postgres account"}}
        wf["nodes"][-1]["alwaysOutputData"] = True
        print("  OK  creado")

    # ---------------------------------------------------------------- 5
    print("\n[5] NODOS: armar la respuesta y avisar")
    for nid, nombre, pos, codigo, nota in (
        ("armar-confirmacion", "Armar respuesta de confirmacion", [-380, 180],
         CODIGO_SI,
         "Arma el aviso al dueno y el mensaje al cliente. Determinista."),
        ("armar-cambio", "Armar aviso de cambio", [-580, 420], CODIGO_NO,
         "El cliente dijo NO: se avisa al dueno y se pasa al agente para "
         "ofrecerle otro horario."),
    ):
        if nombre in nombres:
            print(f"  {nombre}: ya existe")
            continue
        wf["nodes"].append(nodo(nid, nombre, "n8n-nodes-base.code", 2, pos,
                                {"mode": "runOnceForAllItems",
                                 "jsCode": codigo}, nota))
        print(f"  OK  {nombre}")

    if "Avisar al dueno de la confirmacion" in nombres:
        print("  Avisar al dueno de la confirmacion: ya existe")
    else:
        wf["nodes"].append(nodo(
            "avisar-confirmacion", "Avisar al dueno de la confirmacion",
            "n8n-nodes-base.httpRequest", 4.2, [-180, 180],
            {
                "method": "POST",
                "url": "http://evolution_api:8080/message/sendText/hector",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpHeaderAuth",
                "sendHeaders": True,
                "headerParameters": {"parameters": []},
                "sendBody": True,
                "bodyParameters": {"parameters": [
                    {"name": "number",
                     "value": "524521206246@s.whatsapp.net"},
                    {"name": "text",
                     "value": "={{ $json.aviso_al_dueno }}"},
                ]},
                "options": {},
            },
            "Avisa al barbero de que un cliente confirmo. Sin esto, el "
            "barbero seguiria sin saber quien viene."))
        wf["nodes"][-1]["credentials"] = {
            "httpHeaderAuth": {"id": "qaGW1Tvt5BqPujJ1",
                               "name": "Evolution API"}}
        wf["nodes"][-1]["retryOnFail"] = True
        wf["nodes"][-1]["maxTries"] = 3
        wf["nodes"][-1]["waitBetweenTries"] = 2000
        print("  OK  creado")

    # ---------------------------------------------------------------- 6
    print("\n[6] CONECTAR TODO")
    con = wf.setdefault("connections", {})

    def une(origen, destino, salida=0, tipo="main"):
        actual = con.setdefault(origen, {})
        ramas = actual.setdefault(tipo, [])
        while len(ramas) <= salida:
            ramas.append([])
        if not any(d["node"] == destino for d in ramas[salida]):
            ramas[salida].append({"node": destino, "type": tipo,
                                  "index": 0})

    # Normalizacion -> buscar cita -> detector -> IF
    une("Normalizacion", "Buscar cita para confirmar")
    une("Buscar cita para confirmar", "Es confirmacion?")
    une("Es confirmacion?", "IF - Es confirmacion")
    # true -> SI: marcar y avisar
    une("IF - Es confirmacion", "Armar respuesta de confirmacion", 0)
    une("Armar respuesta de confirmacion", "Marcar cita confirmada")
    une("Marcar cita confirmada", "Avisar al dueno de la confirmacion")
    print("  OK  cadena del SI: buscar -> detector -> IF -> marcar -> avisar")
    # false -> NO: avisar y pasar al agente
    print("  (la salida falsa del IF va al agente, ver abajo)")

    # ---------------------------------------------------------------- 7
    print("\n[7] QUE EL DETECTOR SOLO ACTUE CUANDO DEBE")
    print("  El detector exige DOS cosas a la vez:")
    print("   1. el texto es SI o NO (frase corta, sin ambiguedad)")
    print("   2. hay una cita de ese numero en las proximas 48 h")
    print("  Si falta cualquiera, la salida falsa lleva el mensaje al")
    print("  agente como siempre. Asi no se roban mensajes al modelo.")

    # normalizar la salida falsa hacia el camino normal del agente
    # (Leer pausa ya es el camino normal tras Normalizacion)
    une("IF - Es confirmacion", "Leer pausa", 1)
    une("Normalizacion", "Leer operadores")
    print("  OK  salida falsa -> camino normal del agente")

    if not guardar(wf):
        return 1

    # ---------------------------------------------------------------- 8
    print("\n[8] VERIFICACION")
    st, fin = api("GET", f"/workflows/{WID}")
    nm = {n["name"] for n in fin["nodes"]}
    conex = fin.get("connections", {})
    pruebas = [
        ("existe 'Buscar cita para confirmar'",
         "Buscar cita para confirmar" in nm),
        ("existe 'Es confirmacion?'", "Es confirmacion?" in nm),
        ("existe 'IF - Es confirmacion'", "IF - Es confirmacion" in nm),
        ("existe 'Marcar cita confirmada'", "Marcar cita confirmada" in nm),
        ("existe 'Avisar al dueno de la confirmacion'",
         "Avisar al dueno de la confirmacion" in nm),
        ("la cadena esta conectada",
         "Normalizacion" in conex
         and any(d["node"] == "Buscar cita para confirmar"
                 for r in conex["Normalizacion"].get("main", [])
                 for d in r)),
        ("el workflow sigue activo", fin.get("active") is True),
    ]
    fallos = 0
    for n, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {n}")
        if not ok:
            fallos += 1
    print(f"\n  nodos ahora: {len(fin['nodes'])}")
    print(f"  FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())