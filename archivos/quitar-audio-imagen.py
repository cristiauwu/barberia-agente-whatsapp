#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quita TODO el procesamiento de audio e imagenes del workflow
`barberiaAgenteUncensored`.

Peticion textual del usuario: "no procesar imagenes ni audio".

QUE HACE
--------
1. Respalda el workflow en `ANTES-quitar-multimedia.json`.
2. Borra los 8 nodos de audio/imagen:
     Get Audio, Convertir Audio, Transcribe a recording, Audio Content,
     Audio Content1, Get Image, Convertir Imagen, Describe imagen
3. Deja el `Switch` con UNA sola regla (`Texto`) y manda la salida de
   respaldo ("Otro", renombrada "Solo texto") a un nodo Set nuevo que
   responde un mensaje breve pidiendo que escriban.
4. Limpia los dos unicos restos de audio/imagen que quedaban vivos:
     - `Normalizacion.message_content_type` ya no detecta audio ni imagen.
     - `Normalizacion.message_content` ya no lee el caption de una imagen.
5. Sube el workflow a n8n (desactivar -> PUT -> reactivar) y guarda la copia
   aplicada en `_work/despues.json`.

DISENO (y por que)
------------------
Las salidas de audio e imagen NO se redirigen al camino de texto. Si se
redirigieran, `message_content` (que para un audio viene vacio) entraria al
LLM como mensaje vacio y el bot gastaria tokens para responder cualquier
cosa — o nada. En vez de eso:

    texto  -> Edit Fields2 -> Edit Fields -> AI Agent -> Mandar mensaje
    resto  -> Aviso solo texto (Set con el campo `output`) -> Mandar mensaje

`Mandar mensaje` envia `{{ $json.output }}`, por eso el Set escribe
justamente el campo `output`: asi el aviso se manda por el MISMO nodo de
envio, sin depender del modelo. Ventajas:
  - un audio o una foto reciben respuesta siempre (no silencio, no error);
  - 0 tokens: el LLM ni se ejecuta para multimedia;
  - el camino de texto queda intacto (mismos nodos, mismas conexiones);
  - la salida de respaldo cubre ademas video, documento, sticker, etc., que
    antes se quedaban en silencio.

IDEMPOTENTE: si ya esta aplicado, no vuelve a tocar nada (no duplica el
nodo de aviso ni reescribe el respaldo).

Uso:  uv run python G:\\Barberia\\archivos\\quitar-audio-imagen.py
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
RESPALDO = r"G:\Barberia\archivos\ANTES-quitar-multimedia.json"
DESPUES = r"G:\Barberia\archivos\SALIDA-despues-quitar-multimedia.json"
REPORTE = r"G:\Barberia\archivos\SALIDA-quitar-audio-imagen.txt"

# Los 8 nodos a eliminar, con el tipo real para poder comprobar el borrado.
NODOS_MULTIMEDIA = {
    "Get Audio": "n8n-nodes-base.httpRequest",
    "Convertir Audio": "n8n-nodes-base.convertToFile",
    "Transcribe a recording": "@n8n/n8n-nodes-langchain.openAi",
    "Audio Content": "n8n-nodes-base.set",
    "Audio Content1": "n8n-nodes-base.set",
    "Get Image": "n8n-nodes-base.httpRequest",
    "Convertir Imagen": "n8n-nodes-base.convertToFile",
    "Describe imagen": "@n8n/n8n-nodes-langchain.openAi",
}

CRED_ROTA = "GtV72MoANECFbNoX"

NODO_AVISO = "Aviso solo texto"
MENSAJE_AVISO = ("Por ahora solo puedo atender mensajes escritos. "
                 "¿Me escribes lo que necesitas? 🙏")

# Expresiones limpias (se conservan el resto de campos de Normalizacion).
EXPR_TIPO = ("={{ $json.body.data.message.extendedTextMessage ? 'text': '' }}"
             "{{ $json.body.data.message.conversation ? 'text': '' }}")
EXPR_CONTENIDO = ("={{ $json.body.data.message.extendedTextMessage?.text || '' }} "
                  "{{ $json.body.data.message.conversation || '' }}")

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
# La copia aplicada se guarda aqui; se crea si no existe.
os.makedirs(os.path.dirname(DESPUES), exist_ok=True)

buf = io.StringIO()


def p(*a):
    print(*a)
    print(*a, file=buf)


def api(method, path, body=None, timeout=90):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return -1, str(e)


def reglas_del_switch(wf):
    sw = next((n for n in wf["nodes"] if n["name"] == "Switch"), None)
    valores = (((sw or {}).get("parameters") or {}).get("rules") or {}).get("values") or []
    return sw, valores


def ya_aplicado(wf):
    """¿El workflow ya quedo sin multimedia y con el nodo de aviso?"""
    nombres = [n["name"] for n in wf["nodes"]]
    sin_nodos = not any(n in nombres for n in NODOS_MULTIMEDIA)
    _, valores = reglas_del_switch(wf)
    claves = [v.get("outputKey") for v in valores]
    sin_reglas = "Audio" not in claves and "Imagen" not in claves
    txt = json.dumps(wf, ensure_ascii=False)
    return (sin_nodos and sin_reglas and CRED_ROTA not in txt
            and NODO_AVISO in nombres)


def main():
    global KEY
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        p(f"ERROR: no pude leer {WID}: HTTP {st} {str(wf)[:200]}")
        return 1

    p("=" * 74)
    p("QUITAR PROCESAMIENTO DE AUDIO E IMAGENES")
    p("=" * 74)
    p(f"workflow: {WID}  ({wf.get('name')})")
    p(f"nodos antes: {len(wf['nodes'])}   activo: {wf.get('active')}")

    if ya_aplicado(wf):
        p("")
        p("[IDEMPOTENTE] El workflow YA esta sin multimedia y con el nodo")
        p(f"  '{NODO_AVISO}'. No toco nada (no reescribo el respaldo).")
        return 0

    # ---------------------------------------------------------- 1. respaldo
    with open(RESPALDO, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    p("")
    p(f"[1] Respaldo guardado en {RESPALDO}")

    # ---------------------------------------------- 2. borrar nodos media
    antes = [n["name"] for n in wf["nodes"]]
    presentes = [n for n in antes if n in NODOS_MULTIMEDIA]
    faltan = [n for n in NODOS_MULTIMEDIA if n not in antes]
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] not in NODOS_MULTIMEDIA]
    p(f"[2] Nodos eliminados ({len(presentes)}):")
    for n in presentes:
        p(f"      - {n}  ({NODOS_MULTIMEDIA[n]})")
    if faltan:
        p(f"    NOTA: no existian (ya estaban fuera): {faltan}")

    conex = wf["connections"]
    for n in list(NODOS_MULTIMEDIA):
        if n in conex:
            del conex[n]

    # ------------------------------------------------ 3. Switch + aviso
    sw, reglas_viejas = reglas_del_switch(wf)
    if sw is None:
        p("ERROR: no existe el nodo Switch; aborto sin subir nada.")
        return 1

    p("[3] Switch ANTES:")
    for v in reglas_viejas:
        cond = v["conditions"]["conditions"][0]
        p(f"      salida '{v.get('outputKey')}'  cuando message_content_type == "
          f"{cond.get('rightValue')!r}")
    p("    conexiones del Switch ANTES: "
      + json.dumps(conex.get("Switch", {}).get("main", []), ensure_ascii=False))

    sw["parameters"] = {
        "rules": {
            "values": [{
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "",
                                "typeValidation": "strict", "version": 2},
                    "conditions": [{
                        "id": "ebf44caf-794d-434c-be9b-88adfc2d34a0",
                        "leftValue": "={{ $json.message_content_type }}",
                        "rightValue": "text",
                        "operator": {"type": "string", "operation": "equals",
                                     "name": "filter.operator.equals"},
                    }],
                    "combinator": "and",
                },
                "renameOutput": True,
                "outputKey": "Texto",
            }],
        },
        "options": {"fallbackOutput": "extra",
                    "renameFallbackOutput": "Solo texto"},
    }

    id_aviso = "a71001e5-0000-4000-8000-000000000001"
    wf["nodes"].append({
        "id": id_aviso,
        "name": NODO_AVISO,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [672, 576],
        "notesInFlow": True,
        "notes": ("Respuesta fija para audio, imagen y cualquier otro formato que "
                  "no sea texto.\nNo pasa por el modelo: 0 tokens y nunca se "
                  "queda en silencio."),
        "parameters": {
            "assignments": {"assignments": [{
                "id": "a71001e5-0000-4000-8000-000000000002",
                "name": "output",
                "value": "=" + MENSAJE_AVISO,
                "type": "string",
            }]},
            "options": {},
        },
    })
    p(f"[3] Switch DESPUES: 1 regla ('Texto' -> message_content_type == 'text')")
    p(f"    salida de respaldo 'Solo texto' -> '{NODO_AVISO}'")
    p(f"    nodo nuevo '{NODO_AVISO}' (Set) escribe el campo 'output'")

    # ------------------------------------- 4. conexiones del Switch
    conex["Switch"] = {"main": [
        [{"node": "Edit Fields2", "type": "main", "index": 0}],   # 0 = Texto
        [{"node": NODO_AVISO, "type": "main", "index": 0}],       # 1 = respaldo
    ]}
    conex[NODO_AVISO] = {"main": [
        [{"node": "Mandar mensaje", "type": "main", "index": 0}],
    ]}
    p("[4] Conexiones: Switch(Texto) -> Edit Fields2 ; "
      f"Switch(resto) -> {NODO_AVISO} -> Mandar mensaje")

    # -------------------------------- 5. limpiar restos en Normalizacion
    norm = next((n for n in wf["nodes"] if n["name"] == "Normalizacion"), None)
    if norm is None:
        p("ERROR: no existe el nodo Normalizacion; aborto sin subir nada.")
        return 1
    cambios_norm = []
    for a in norm["parameters"]["assignments"]["assignments"]:
        if a["name"] == "message_content_type" and a["value"] != EXPR_TIPO:
            a["value"] = EXPR_TIPO
            cambios_norm.append("message_content_type (ya no detecta audio/imagen)")
        if a["name"] == "message_content" and a["value"] != EXPR_CONTENIDO:
            a["value"] = EXPR_CONTENIDO
            cambios_norm.append("message_content (ya no lee el caption de imagen)")
    p("[5] Normalizacion:")
    for c in cambios_norm:
        p("      - limpiado: " + c)
    if not cambios_norm:
        p("      - (ya estaba limpio)")

    # --------------------------------------------------- 6. subir a n8n
    activo = wf.get("active")
    if activo:
        st_d, _ = api("POST", f"/workflows/{WID}/deactivate", {})
        p("")
        p(f"[6] desactivado -> HTTP {st_d}")
    cuerpo = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {}),
        "staticData": wf.get("staticData"),
    }
    st_put, res = api("PUT", f"/workflows/{WID}", cuerpo)
    p(f"    PUT -> HTTP {st_put}")
    if st_put not in (200, 201):
        p("    ERROR al subir: " + str(res)[:500])
        p("    El respaldo esta en " + RESPALDO)
        return 1
    if activo:
        st_a, r = api("POST", f"/workflows/{WID}/activate", {})
        p(f"    reactivado -> HTTP {st_a} active={(r or {}).get('active')}")

    # --------------------------------------------------- 7. re-leer y guardar
    st2, final = api("GET", f"/workflows/{WID}")
    if st2 == 200:
        with open(DESPUES, "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)
        p("")
        p(f"[7] Estado final releido de n8n: {len(final['nodes'])} nodos, "
          f"active={final.get('active')}  -> {DESPUES}")

    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        import traceback
        traceback.print_exc(file=buf)
        rc = 1
    with open(REPORTE, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    sys.exit(rc)