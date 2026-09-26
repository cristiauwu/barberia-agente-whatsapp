#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el detector de confirmacion: leia el JSON equivocado.

EL BUG (encontrado probando, no leyendo):
  La cadena es  Normalizacion -> Buscar cita (Postgres) -> Es confirmacion?
  El nodo de Postgres DEVUELVE SUS PROPIAS FILAS, asi que cuando el detector
  se ejecuta, `$json` ya NO es el mensaje del cliente: son las columnas de
  la cita. Por eso `$json.message_content` llegaba vacio y el detector
  respondia `decision=ninguna` incluso con un "si" delante.

  Evidencia de la prueba: con un "si" y una cita existente, el flujo se fue
  al modelo (gasto tokens) y la cita NO se confirmo. El detector dijo
  `decision=ninguna`.

ARREGLO: el detector y los nodos que arman el aviso tienen que leer los
datos del cliente de donde SI estan: `$('Normalizacion').item.json`.
Es el mismo patron que ya usa el resto del workflow (por ejemplo
`$('Webhook').item.json`), asi que es coherente con el proyecto.

Leccion: un nodo que consulta una base de datos REEMPLAZA el contexto.
Hay que referenciar el nodo anterior por nombre, no confiar en `$json`.
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

DETECTOR = r"""
// Detecta si el cliente esta respondiendo SI o NO a un recordatorio.
// Determinista a proposito: NO llama al modelo. "SI" es SI.
//
// OJO: este nodo corre DESPUES de un nodo de Postgres, asi que `$json` son
// las columnas de la cita, no el mensaje del cliente. Los datos del
// mensaje se leen de `Normalizacion` por nombre. (Sin esto el detector
// leia un texto vacio y nunca reconocia un "si".)
const nav = $('Normalizacion').item.json;

const texto = String(nav.message_content || '')
  .trim().toLowerCase()
  .replace(/^[¡!¿?\s.,]+/, '')
  .replace(/[¡!¿?\s.,]+$/, '');

// Solo frases cortas: una respuesta a un recordatorio es corta. Si el
// cliente escribio un parrafo, no es una confirmacion.
const corto = texto.length > 0 && texto.length <= 12;

const SI = ['si', 'sí', 'sii', 'siii', 'claro', 'confirmo', 'confirmado',
            'ok', 'okay', 'va', 'dale', 'listo', 'de acuerdo', 'asi es'];
const NO = ['no', 'noo', 'nooo', 'nel', 'mejor no', 'cambiar', 'cambiala',
            'reprogramar', 'mover', 'no puedo', 'cancelar', 'cancela'];

const esSi = corto && SI.includes(texto);
const esNo = corto && NO.includes(texto);

// ¿tiene una cita proxima? Sin cita, esto NO es una confirmacion.
// (El nodo anterior ya filtro por jid y por fecha; si devolvio una fila
// vacia, no hay cita.)
let cita = null;
try {
  const filas = $input.all();
  for (const f of filas) {
    const j = f.json || {};
    if (j && j.id) { cita = j; break; }
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
    // se conservan los datos del cliente para los nodos siguientes
    texto_recibido: nav.message_content,
    user_number: nav.user_number,
    user_name: nav.user_name,
    message_content: nav.message_content,
    message_content_type: nav.message_content_type,
    instance_server_url: nav.instance_server_url
  }
}];
"""

ARMAR_CONFIRMACION = r"""
// El cliente confirmo. Se arma el aviso al dueno. Determinista: 0 tokens.
const d = $json;
const inicio = d.cita_inicio
  ? String(d.cita_inicio).replace('T', ' ').slice(0, 16) : '';
return [{
  json: {
    ...d,
    aviso_al_dueno:
      'CLIENTE CONFIRMO SU CITA\n\n' +
      (d.cita_nombre || 'Cliente') + '\n' +
      (d.cita_servicio || 'Servicio') + '\n' +
      inicio + '\n\n' +
      String(d.user_number || '').split('@')[0],
    respuesta_al_cliente: 'Gracias por confirmar, te esperamos. 🙏'
  }
}];
"""

ARMAR_CAMBIO = r"""
// El cliente dijo NO: quiere mover o cancelar. Se avisa al dueno y se le
// pasa al agente para que le ofrezca alternativas.
const d = $json;
const inicio = d.cita_inicio
  ? String(d.cita_inicio).replace('T', ' ').slice(0, 16) : '';
return [{
  json: {
    ...d,
    aviso_al_dueno:
      'UN CLIENTE QUIERE CAMBIAR SU CITA\n\n' +
      (d.cita_nombre || 'Cliente') + '\n' +
      (d.cita_servicio || 'Servicio') + '\n' +
      inicio + '\n\n' +
      String(d.user_number || '').split('@')[0] +
      '\n\nHay que ofrecerle otro horario.'
  }
}];
"""


def api(m, p, b=None):
    d = json.dumps(b).encode() if b is not None else None
    r = urllib.request.Request(N8N + p, data=d, method=m)
    r.add_header("X-N8N-API-KEY", KEY)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as x:
            return x.status, json.loads(x.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)


def main():
    print("=" * 68)
    print("CORREGIR EL DETECTOR: LEIA EL JSON EQUIVOCADO")
    print("=" * 68)

    st, wf = api("GET", f"/workflows/{WID}")
    cambios = 0
    for nombre, codigo in (
        ("Es confirmacion?", DETECTOR),
        ("Armar respuesta de confirmacion", ARMAR_CONFIRMACION),
        ("Armar aviso de cambio", ARMAR_CAMBIO),
    ):
        n = next((x for x in wf["nodes"] if x["name"] == nombre), None)
        if not n:
            print(f"  AVISO no existe {nombre}")
            continue
        n["parameters"]["jsCode"] = codigo
        cambios += 1
        print(f"  OK  {nombre}: ahora lee de Normalizacion")

    # el nodo de Postgres debe filtrar por el jid del cliente, que viene de
    # Normalizacion (ahi si esta)
    n = next(x for x in wf["nodes"]
             if x["name"] == "Buscar cita para confirmar")
    n["parameters"]["query"] = (
        "SELECT id, nombre, servicio,\n"
        "       to_char(inicio,'YYYY-MM-DD HH24:MI') AS inicio,\n"
        "       estado, jid\n"
        "  FROM barber_citas\n"
        " WHERE jid = '{{ $('Normalizacion').item.json.user_number }}'\n"
        "   AND estado IN ('agendado','confirmado')\n"
        "   AND inicio BETWEEN now() - interval '2 hours'\n"
        "                  AND now() + interval '48 hours'\n"
        " ORDER BY inicio ASC\n"
        " LIMIT 1;")
    print("  OK  Buscar cita: lee el jid de Normalizacion")
    cambios += 1

    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, r = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {})})
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print(f"  MAL: {str(r)[:250]}")
        return 1
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})
    print(f"  {cambios} nodos corregidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())