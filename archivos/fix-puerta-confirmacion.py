#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reestructura el bucle de confirmacion: de PARALELO a PUERTA.

LOS DOS BUGS QUE YO MISMO INTRODUJE (los encontro la prueba, no la lectura):

  1. BIFURCACION EN PARALELO.
     Yo conecte `Normalizacion` a DOS sitios a la vez:
         Normalizacion ─► Leer operadores   (el camino del agente)
                       └► Buscar cita       (el de confirmacion)
     Asi que el camino del agente CORRIA IGUAL, en paralelo. Resultado:
     el cliente que responde "SI" recibe la confirmacion Y ADEMAS una
     respuesta del modelo. Dos mensajes. Y se gastan tokens igual.
     Evidencia: la prueba dijo "se llamo al modelo: SI (gasto tokens)".

  2. EL AVISO DE CAMBIO SE DISPARABA SIEMPRE.
     El detector devuelve tres cosas: SI, NO y `ninguna`. Yo use un IF de
     dos salidas, asi que `ninguna` caia en la rama falsa junto con NO. Y
     de esa rama colgaba `Armar aviso de cambio`, que se habria ejecutado
     con CUALQUIER mensaje normal, avisando al dueno de un cambio que
     nadie pidio.

EL ARREGLO — una PUERTA, no una bifurcacion:

    Normalizacion ─► Buscar cita ─► Es confirmacion? ─► Switch
                                                          ├─ SI ──► marcar confirmada ─► avisar al dueno
                                                          ├─ NO ──► avisar cambio ─► avisar al dueno ─► agente
                                                          └─ respaldo (ninguna) ────────────────► agente

  Ahora el camino del agente pasa por UN solo sitio, y solo cuando de
  verdad toca. Un "SI" ya no llama al modelo.

  ADEMAS: el detector reconoce los COMANDOS DEL DUENO (HOY, PRECIO...).
  Si el texto es un comando, nunca se trata como confirmacion, aunque el
  numero tenga una cita. Asi los comandos del dueno no se interceptan.
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
// Detecta si el cliente responde SI o NO a un recordatorio. Determinista.
//
// Este nodo corre DESPUES de un nodo de Postgres, asi que `$json` son las
// columnas de la cita: el mensaje del cliente se lee de `Normalizacion`
// por nombre. (Sin esto el detector leia un texto vacio.)
const nav = $('Normalizacion').item.json;

const texto = String(nav.message_content || '')
  .trim().toLowerCase()
  .replace(/^[¡!¿?\s.,]+/, '')
  .replace(/[¡!¿?\s.,]+$/, '');

// Los COMANDOS DEL DUENO nunca son una confirmacion. Si alguien escribe
// "HOY" o "PRECIO ceja 40", va por su camino de siempre.
const COMANDOS = ['hoy', 'mañana', 'manana', 'semana', 'libre', 'cliente',
                  'bloquear', 'cerrar', 'abrir', 'precio', 'pausa',
                  'estado', 'comandos'];
const pareceComando = COMANDOS.some(function (c) {
  return texto === c || texto.indexOf(c + ' ') === 0;
});

const corto = texto.length > 0 && texto.length <= 12;

const SI = ['si', 'sí', 'sii', 'siii', 'claro', 'confirmo', 'confirmado',
            'ok', 'okay', 'va', 'dale', 'listo', 'de acuerdo', 'asi es'];
const NO = ['no', 'noo', 'nooo', 'nel', 'mejor no', 'cambiar', 'cambiala',
            'reprogramar', 'mover', 'no puedo', 'cancelar', 'cancela'];

const esSi = corto && SI.includes(texto);
const esNo = corto && NO.includes(texto);

// ¿hay una cita proxima de este numero? Sin cita, no es una confirmacion.
let cita = null;
try {
  for (const f of $input.all()) {
    const j = f.json || {};
    if (j && j.id) { cita = j; break; }
  }
} catch (e) { cita = null; }

const decision = pareceComando ? 'comando'
               : (esSi ? 'SI' : (esNo ? 'NO' : 'ninguna'));
const esRespuesta = (decision === 'SI' || decision === 'NO') && cita !== null;

return [{
  json: {
    decision: decision,
    es_respuesta_confirmacion: esRespuesta,
    cita_id: cita ? cita.id : null,
    cita_inicio: cita ? cita.inicio : null,
    cita_servicio: cita ? cita.servicio : null,
    cita_nombre: cita ? cita.nombre : null,
    texto_recibido: nav.message_content,
    user_number: nav.user_number,
    user_name: nav.user_name,
    message_content: nav.message_content,
    message_content_type: nav.message_content_type,
    instance_server_url: nav.instance_server_url
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
    print("REESTRUCTURAR: UNA PUERTA EN VEZ DE UNA BIFURCACION")
    print("=" * 68)

    st, wf = api("GET", f"/workflows/{WID}")
    nodos = {n["name"]: n for n in wf["nodes"]}

    # ---------------------------------------------------------------- 1
    print("\n[1] El detector ahora reconoce los comandos del dueno")
    nodos["Es confirmacion?"]["parameters"]["jsCode"] = DETECTOR
    print("  OK  si el texto es un comando (HOY, PRECIO...), no se intercepta")

    # ---------------------------------------------------------------- 2
    print("\n[2] Cambiar el IF por un SWITCH de 2 reglas + respaldo")
    # borrar el IF
    wf["nodes"] = [n for n in wf["nodes"]
                   if n["name"] != "IF - Es confirmacion"]
    wf["connections"].pop("IF - Es confirmacion", None)

    existe = any(n["name"] == "Switch confirmacion" for n in wf["nodes"])
    if not existe:
        wf["nodes"].append({
            "id": "switch-confirmacion",
            "name": "Switch confirmacion",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [-780, 300],
            "parameters": {
                "rules": {"values": [
                    {"conditions": {
                        "options": {"caseSensitive": True,
                                    "typeValidation": "loose",
                                    "version": 2},
                        "conditions": [{
                            "id": "r-si",
                            "leftValue": "={{ $json.decision }}",
                            "rightValue": "SI",
                            "operator": {"type": "string",
                                         "operation": "equals"}}],
                        "combinator": "and"},
                     "renameOutput": True, "outputKey": "SI"},
                    {"conditions": {
                        "options": {"caseSensitive": True,
                                    "typeValidation": "loose",
                                    "version": 2},
                        "conditions": [{
                            "id": "r-no",
                            "leftValue": "={{ $json.decision }}",
                            "rightValue": "NO",
                            "operator": {"type": "string",
                                         "operation": "equals"}}],
                        "combinator": "and"},
                     "renameOutput": True, "outputKey": "NO"},
                ]},
                "options": {"fallbackOutput": "extra"},
            },
            "notes": ("Decide que hacer con la respuesta: SI confirma, NO "
                      "avisa un cambio, y todo lo demas sigue al agente. "
                      "Antes era un IF de dos salidas y el caso 'ninguna' "
                      "se mezclaba con NO, disparando avisos falsos."),
        })
        print("  OK  Switch con salidas SI / NO / respaldo")
    else:
        print("  ya existia")

    # ---------------------------------------------------------------- 3
    print("\n[3] Reconectar: UNA sola puerta")
    con = wf["connections"]

    # quitar la bifurcacion paralela
    for origen in ("Normalizacion",):
        if origen in con:
            con[origen]["main"] = [[d for d in rama
                                    if d["node"] != "Leer operadores"]
                                   for rama in con[origen]["main"]]
            # quitar ramas vacias de mas
            con[origen]["main"] = [r for r in con[origen]["main"] if r]
    print("  OK  Normalizacion ya NO va directo al agente (se quito el paralelo)")

    def une(origen, destino, salida=0):
        actual = con.setdefault(origen, {})
        ramas = actual.setdefault("main", [])
        while len(ramas) <= salida:
            ramas.append([])
        if not any(d["node"] == destino for d in ramas[salida]):
            ramas[salida].append({"node": destino, "type": "main",
                                  "index": 0})
            return True
        return False

    # Normalizacion -> Buscar cita -> detector -> Switch
    une("Normalizacion", "Buscar cita para confirmar")
    une("Buscar cita para confirmar", "Es confirmacion?")
    une("Es confirmacion?", "Switch confirmacion")

    # limpiar la salida del switch y rearmarla
    con.pop("Switch confirmacion", None)
    une("Switch confirmacion", "Armar respuesta de confirmacion", 0)   # SI
    une("Switch confirmacion", "Armar aviso de cambio", 1)             # NO
    une("Switch confirmacion", "Leer operadores", 2)                   # resto

    # SI: marcar y avisar
    con.pop("Armar respuesta de confirmacion", None)
    une("Armar respuesta de confirmacion", "Marcar cita confirmada")
    une("Marcar cita confirmada", "Avisar al dueno de la confirmacion")

    # NO: avisar y ADEMAS pasar al agente para ofrecer alternativas
    con.pop("Armar aviso de cambio", None)
    une("Armar aviso de cambio", "Avisar al dueno de la confirmacion")
    une("Armar aviso de cambio", "Leer operadores", 0)
    print("  OK  SI  -> marcar confirmada -> avisar al dueno")
    print("  OK  NO  -> avisar el cambio -> avisar al dueno -> agente")
    print("  OK  resto -> directo al agente")

    # ---------------------------------------------------------------- 4
    print("\n[4] Que 'Avisar al dueno' tolere las dos ramas")
    n = nodos.get("Avisar al dueno de la confirmacion")
    if n:
        n["parameters"]["bodyParameters"]["parameters"][1]["value"] = \
            "={{ $json.aviso_al_dueno }}"
        n["alwaysOutputData"] = True
        print("  OK  el texto sale de aviso_al_dueno (lo arma cada rama)")

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

    # ---------------------------------------------------------------- 5
    print("\n[5] VERIFICACION ESTRUCTURAL")
    st, fin = api("GET", f"/workflows/{WID}")
    c = fin["connections"]
    salidas = c["Switch confirmacion"]["main"]
    pruebas = [
        ("Normalizacion NO va directo al agente",
         not any(d["node"] == "Leer operadores"
                 for r in c["Normalizacion"]["main"] for d in r)),
        ("el Switch tiene 3 salidas", len(salidas) == 3),
        ("salida 0 (SI) -> Armar respuesta",
         [d["node"] for d in salidas[0]] == ["Armar respuesta de confirmacion"]),
        ("salida 1 (NO) -> Armar aviso",
         [d["node"] for d in salidas[1]] == ["Armar aviso de cambio"]),
        ("salida 2 (resto) -> Leer operadores",
         [d["node"] for d in salidas[2]] == ["Leer operadores"]),
        ("el workflow sigue activo", fin.get("active") is True),
    ]
    fallos = 0
    for n2, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {n2}")
        if not ok:
            fallos += 1
    print(f"\n  nodos: {len(fin['nodes'])}   FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())