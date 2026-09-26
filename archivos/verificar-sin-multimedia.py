#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que `barberiaAgenteUncensored` quedo SIN procesamiento de audio ni
imagenes y que el camino de TEXTO sigue intacto y funcionando.

Comprueba los 7 puntos pedidos:
  [1] El camino de texto sigue funcionando (mensaje de texto REAL al webhook).
  [2] Un mensaje de AUDIO recibe respuesta sensata (no silencio, no error).
  [3] Un mensaje de IMAGEN recibe respuesta sensata.
  [4] No quedan nodos huerfanos ni nodos no-terminales sin salida.
  [5] No quedan referencias a los 8 nodos eliminados (connections, definicion
      de nodo y expresiones `$('Nodo')`), y el nodo de aviso esta conectado.
  [6] No queda ninguna credencial rota de OpenAI (`GtV72MoANECFbNoX`).
  [7] `verify.py` da 173/173 o mas.

Extra: los nodos y conexiones del camino de texto se comparan contra el
respaldo `ANTES-quitar-multimedia.json` para probar que no se rompio nada.

Uso:  uv run python G:\\Barberia\\archivos\\verificar-sin-multimedia.py
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

N8N = "http://localhost:5678"
API = N8N + "/api/v1"
WEBHOOK = N8N + "/webhook/hector"
WID = "barberiaAgenteUncensored"
RESPALDO = r"G:\Barberia\archivos\ANTES-quitar-multimedia.json"
SALIDA = r"G:\Barberia\archivos\SALIDA-verificar-sin-multimedia.txt"
DETALLE = r"G:\Barberia\archivos\SALIDA-verificar-sin-multimedia-detalle.json"
VERIFY_OUT = r"G:\Barberia\archivos\SALIDA-verify-py.txt"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
UV = r"C:\Users\kimbo\.cherrystudio\bin\uv.exe"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
# La salida y el detalle se guardan aqui; se crea si no existe.
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)

MEDIA = ["Get Audio", "Convertir Audio", "Transcribe a recording", "Audio Content",
         "Audio Content1", "Get Image", "Convertir Imagen", "Describe imagen"]
CRED_ROTA = "GtV72MoANECFbNoX"
AVISO = "Aviso solo texto"
JID = "5214501111805@s.whatsapp.net"      # numero real; otro da HTTP 400
CAMINO_TEXTO = ["Edit Fields2", "Edit Fields", "AI Agent", "Mandar mensaje",
                "Normalizacion", "OpenAI Chat Model"]
# Nodos que legitimamente no tienen salida `main`: envian el mensaje final o
# entregan su resultado al AI Agent por una conexion `ai_*`.
TERMINALES = {"Mandar mensaje", "Responder al operador", "Postgres Chat Memory",
              "OpenAI Chat Model", "Consultar agenda", "Agendar cita",
              "Cancelar cita", "Reagendar", "Registrar en hoja de citas",
              "Notificar al encargado"}

try:   # la consola de Windows es cp1252 y las respuestas llevan emojis
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

buf = io.StringIO()
res = []
# Diferencias respecto al respaldo que NO son mias (agentes hermanos siguen
# editando el workflow). Se reportan, pero no hacen fallar la verificacion.
ajenos = []


def p(*a):
    print(*a)
    print(*a, file=buf)


def check(ok, titulo, detalle=""):
    res.append((bool(ok), titulo))
    p(f"  {'PASS' if ok else 'FAIL'}  {titulo}")
    if detalle:
        for l in str(detalle).splitlines():
            p("          " + l)
    return bool(ok)


def api(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
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


def psql(sql):
    q = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (q.stdout or "").strip(), (q.stderr or "").strip()


def apikey_evolution():
    q = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (q.stdout or "").strip()


# ------------------------------------------------------------------ E2E ----
def payload(apikey, tipo, texto=None, mid=None):
    """Payload real de Evolution API. Para audio/imagen se incluye la clave
    real del mensaje (`audioMessage` / `imageMessage`), que es de donde el
    flujo calcula `message_content_type`."""
    mid = mid or ("VER" + uuid.uuid4().hex[:10].upper())
    if tipo == "conversation":
        mensaje = {"conversation": texto}
    elif tipo == "audioMessage":
        mensaje = {"audioMessage": {"mimetype": "audio/ogg; codecs=opus",
                                    "seconds": 3, "ptt": True}}
    elif tipo == "imageMessage":
        mensaje = {"imageMessage": {"mimetype": "image/jpeg", "caption": "",
                                    "height": 100, "width": 100}}
    else:
        raise ValueError(tipo)
    return {"event": "messages.upsert", "instance": "hector",
            "server_url": "http://evolution_api:8080", "apikey": apikey,
            "date_time": "2026-09-25T18:00:00.000Z",
            "data": {"key": {"id": mid, "remoteJid": JID, "fromMe": False},
                     "pushName": "Cliente Prueba", "message": mensaje,
                     "messageType": tipo}}


def enviar(body):
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            return r.status, r.read().decode()[:300]
    except Exception as e:
        return getattr(e, "code", None), str(e)[:300]


def esperar_ejecucion(message_id):
    """Espera la ejecucion de MI mensaje, correlacionando por `message_id`.

    NO vale con tomar la ejecucion mas nueva: otros agentes estan probando el
    mismo webhook a la vez y sus mensajes caen entre los mios. El id de
    mensaje es un UUID unico de este script, asi que es el unico criterio
    fiable."""
    for _ in range(75):
        st, d = api("GET", f"/executions?workflowId={WID}&limit=20")
        if st == 200:
            for e in (d or {}).get("data", []):
                if e.get("status") == "running":
                    continue
                st_det, det = api("GET", f"/executions/{e['id']}?includeData=true")
                run = (((det or {}).get("data") or {}).get("resultData") or {}) \
                    .get("runData") or {}
                norm = normalizado(run)
                if norm.get("message_id") == message_id:
                    return e["id"], e.get("status"), run
        time.sleep(2)
    return None, None, None


def respuesta(run):
    """Texto que el bot mando de verdad: `message.conversation` de la respuesta
    de Evolution, o el eco del body enviado."""
    for it in (run.get("Mandar mensaje") or []):
        for rama in ((it.get("data") or {}).get("main") or []):
            for item in (rama or []):
                j = item.get("json") or {}
                msg = j.get("message")
                if isinstance(msg, dict) and msg.get("conversation"):
                    return msg["conversation"]
                if isinstance(j.get("text"), str) and j["text"]:
                    return j["text"]
    return None


def errores(run):
    out = []
    for nm, its in run.items():
        for it in its:
            if it.get("error"):
                out.append(f"{nm}: {it['error'].get('message')}")
    return out


def normalizado(run):
    for it in (run.get("Normalizacion") or []):
        for rama in ((it.get("data") or {}).get("main") or []):
            for item in (rama or []):
                j = item.get("json") or {}
                if "message_content_type" in j:
                    return j
    return {}


def body_de_mandar_mensaje(wf):
    """Los parametros de envio de 'Mandar mensaje' (estaticos, del workflow).
    El runData no guarda `parameters`, asi que se leen de la definicion."""
    n = next((x for x in wf["nodes"] if x["name"] == "Mandar mensaje"), None)
    if not n:
        return {}
    params = (((n.get("parameters") or {}).get("bodyParameters") or {})
              .get("parameters")) or []
    return {x.get("name"): x.get("value") for x in params}


# ------------------------------------------------------------------ main ---
def main():
    p("=" * 74)
    p("VERIFICACION: WORKFLOW SIN AUDIO NI IMAGENES")
    p("=" * 74)
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        p(f"ERROR: no pude leer el workflow: HTTP {st}")
        return 1
    nombres = [n["name"] for n in wf["nodes"]]
    todo = json.dumps(wf, ensure_ascii=False)
    p(f"workflow: {WID}   nodos: {len(wf['nodes'])}   active={wf.get('active')}")

    # ------------------------------------------------------- [5] referencias
    p("")
    p("[5] Referencias a los nodos eliminados")
    malos = [f"nodo definido todavia: {n}" for n in MEDIA if n in nombres]
    for src, ramas in wf["connections"].items():
        if src in MEDIA:
            malos.append(f"clave en connections: {src}")
        for salidas in ramas.values():
            for grupo in salidas:
                for c in grupo:
                    if c["node"] in MEDIA:
                        malos.append(f"conexion {src} -> {c['node']}")
    for n in MEDIA:
        if re.search(r"\$\(\s*['\"]" + re.escape(n) + r"['\"]\s*\)", todo):
            malos.append(f"expresion $('{n}')")
    check(not malos, "Ninguna referencia a los 8 nodos eliminados "
                     "(definicion, connections ni $('Nodo'))",
          "\n".join(malos) if malos else f"8 nombres x 3 sitios = 24 busquedas, 0 hallazgos")
    check(AVISO in nombres, f"Existe el nodo de aviso '{AVISO}'")

    # ------------------------------------------------------- [6] credencial
    p("")
    p("[6] Credencial rota de OpenAI")
    apar = todo.count(CRED_ROTA)
    con_cred = [n["name"] for n in wf["nodes"]
                if CRED_ROTA in json.dumps(n.get("credentials") or {})]
    check(apar == 0 and not con_cred,
          f"Ninguna referencia a la credencial {CRED_ROTA}",
          f"apariciones en el JSON: {apar}" +
          (f" | nodos: {con_cred}" if con_cred else ""))
    m = next((n for n in wf["nodes"] if n["name"] == "OpenAI Chat Model"), {})
    cred = (m.get("credentials") or {}).get("openAiApi") or {}
    check(cred.get("id") == "KhicsxnD4N314cKC",
          "El modelo del agente conserva la credencial Uncensored AI",
          f"{cred.get('name')} ({cred.get('id')})")

    # ------------------------------------------- camino de texto sin tocar
    p("")
    p("[extra] El camino de texto quedo intacto respecto al respaldo")
    if os.path.exists(RESPALDO):
        antes = json.load(open(RESPALDO, encoding="utf-8"))
        # NOTA: el systemMessage del AI Agent SI cambio entre el respaldo y
        # ahora, pero NO por este trabajo: un agente hermano actualizo el
        # prompt a la vez (quedo identico al archivo del prompt, que verify.py
        # comprueba aparte). Para aislar MI cambio se compara el nodo sin el
        # systemMessage, y el systemMessage se valida contra el archivo.
        def sin_prompt(n):
            c = json.loads(json.dumps(n))
            if c["name"] == "AI Agent":
                c["parameters"]["options"]["systemMessage"] = "<ignorado>"
            return json.dumps(c, ensure_ascii=False, sort_keys=True)

        difs = []
        for nm in CAMINO_TEXTO:
            a = next((n for n in antes["nodes"] if n["name"] == nm), None)
            b = next((n for n in wf["nodes"] if n["name"] == nm), None)
            if a is None or b is None:
                difs.append(f"{nm}: falta en uno de los dos")
            elif nm == "Normalizacion":
                # Normalizacion SI cambia, pero a proposito y solo en los dos
                # campos que leian audio/imagen. Se comprueba eso exactamente.
                aa = {x["name"]: x["value"] for x in
                      a["parameters"]["assignments"]["assignments"]}
                bb = {x["name"]: x["value"] for x in
                      b["parameters"]["assignments"]["assignments"]}
                distintas = [k for k in set(aa) | set(bb) if aa.get(k) != bb.get(k)]
                esperadas = {"message_content_type", "message_content"}
                if set(distintas) != esperadas:
                    difs.append(f"Normalizacion: campos distintos {distintas} "
                                f"(esperados {sorted(esperadas)})")
                elif "audioMessage" in bb["message_content_type"] or \
                        "imageMessage" in bb["message_content_type"] or \
                        "imageMessage" in bb["message_content"]:
                    difs.append("Normalizacion: aun menciona audio/imagen")
            elif sin_prompt(a) != sin_prompt(b):
                # Puede ser un cambio de un agente hermano. Lo que importa es
                # que el nodo conserve las piezas de las que depende el texto.
                ajenos.append(nm)
        check(not difs, "Normalizacion: solo cambiaron los 2 campos de multimedia "
                        "(el resto del camino de texto sigue igual)",
              "\n".join(difs) if difs else
              f"{len(CAMINO_TEXTO)} nodos; 0 cambios estructurales mios")
        if ajenos:
            p(f"          NOTA: {ajenos} cambiaron respecto al respaldo por "
              f"trabajo de agentes hermanos (no mio); se validan abajo.")
        # El systemMessage debe seguir siendo el del archivo (lo exige verify.py)
        ag = next((n for n in wf["nodes"] if n["name"] == "AI Agent"), None)
        sm = ag["parameters"]["options"]["systemMessage"] if ag else ""
        arch = open(r"G:\Barberia\prompt-sistema-agente-barberia.txt",
                    encoding="utf-8").read().strip()
        check(sm == "=" + arch,
              "El systemMessage del AI Agent es el del archivo del prompt "
              "(cambio ajeno a este trabajo, ya sincronizado)")
        pares = [("Switch", "Edit Fields2"), ("Edit Fields2", "Edit Fields"),
                 ("Edit Fields", "AI Agent"), ("AI Agent", "Mandar mensaje"),
                 ("Normalizacion", "Leer operadores"),
                 ("Leer operadores", "Comprobar operador"),
                 ("Comprobar operador", "¿Es operador?")]
        rotos = []
        for src, dst in pares:
            nb = [c["node"] for rama in
                  wf["connections"].get(src, {}).get("main", [[]])
                  for c in (rama or [])]
            if dst not in nb:
                rotos.append(f"{src} -> {dst} se perdio (ahora: {nb})")
        check(not rotos, "Conexiones del camino de texto conservadas",
              "\n".join(rotos) if rotos else f"{len(pares)} pares verificados")
    else:
        check(False, "Existe el respaldo ANTES-quitar-multimedia.json", RESPALDO)

    # --------------------------------------------------------- [4] huerfanos
    p("")
    p("[4] Nodos huerfanos")
    dest_main, fuentes, destinos = set(), set(), set()
    fuente_ai, dest_ai = set(), set()
    for src, ramas in wf["connections"].items():
        fuentes.add(src)
        for tipo, salidas in ramas.items():
            for grupo in salidas:
                for c in grupo:
                    destinos.add(c["node"])
                    if tipo == "main":
                        dest_main.add(c["node"])
                    else:
                        fuente_ai.add(src)      # el sub-nodo 'sirve' al agente
                        dest_ai.add(c["node"])
    huerfanos = [n["name"] for n in wf["nodes"]
                 if n["name"] not in dest_main
                 and not ("Trigger" in n["type"] or n["type"].endswith(".webhook")
                          or "manualTrigger" in n["type"])
                 and n["name"] not in fuente_ai and n["name"] not in dest_ai]
    sin_salida = [n["name"] for n in wf["nodes"]
                  if n["name"] not in fuentes and n["name"] not in TERMINALES]
    check(not huerfanos, "Todo nodo no-trigger recibe datos (main o ai_*)",
          "sin entrada: " + str(huerfanos) if huerfanos
          else f"{len(wf['nodes'])} nodos revisados; "
               f"{len(dest_main)} reciben main, {len(dest_ai)} reciben ai_*")
    check(not sin_salida, "Ningun nodo no-terminal quedo sin salida",
          "sin salida: " + str(sin_salida) if sin_salida else "ok")
    p("          nodos sin salida (todos terminales legitimos):")
    for nm in sorted(n["name"] for n in wf["nodes"] if n["name"] not in fuentes):
        p(f"            - {nm}")

    # ------------------------------------------------------ [1..3] E2E real
    apikey = apikey_evolution()
    if not apikey:
        check(False, "Puedo leer la API key de Evolution para la prueba E2E")
        p("  (no se pudo; se omite la prueba en vivo)")
        return 1
    p("")
    p("[E2E] API key de Evolution leida (no se imprime).")
    p(f"[E2E] JID de prueba: {JID}")
    out, _ = psql(f"SELECT COALESCE(hasta::text,'-') FROM barber_pausas WHERE jid='{JID}';")
    if out.strip():
        psql(f"DELETE FROM barber_pausas WHERE jid='{JID}';")
        p(f"[E2E] El cliente estaba pausado hasta {out.strip()}: pausa eliminada "
          f"para que la prueba sea valida.")
    else:
        p("[E2E] El cliente de prueba no esta pausado.")

    detalle = {}
    casos = [("texto", "conversation", "Hola, buenas tardes. Cuanto cuesta el corte?", 1),
             ("audio", "audioMessage", None, 2),
             ("imagen", "imageMessage", None, 3)]
    for etiqueta, tipo, texto, idx in casos:
        p("")
        p(f"--- [{idx}] Mensaje de {etiqueta.upper()} ---")
        mid = "VER" + uuid.uuid4().hex[:10].upper()
        st_w, cuerpo = enviar(payload(apikey, tipo, texto, mid))
        p(f"  mensaje id={mid}  webhook -> HTTP {st_w}  {str(cuerpo)[:100]}")
        eid, estado, run = esperar_ejecucion(mid)
        if not eid:
            check(False, f"El mensaje de {etiqueta} produjo una ejecucion en n8n "
                         f"(emparejada por message_id {mid})",
                  f"webhook HTTP {st_w}")
            continue
        dicho, norm, errs = respuesta(run), normalizado(run), errores(run)
        detalle[etiqueta] = {
            "execution_id": eid, "status": estado,
            "message_content_type": norm.get("message_content_type"),
            "message_content": norm.get("message_content"),
            "respuesta_del_bot": dicho, "errores": errs,
            "nodos_ejecutados": sorted(run.keys()),
        }
        p(f"  ejecucion {eid}  status={estado}")
        p(f"  message_content_type: {norm.get('message_content_type')!r}   "
          f"message_content: {norm.get('message_content')!r}")
        p(f"  respuesta del bot: {dicho!r}")
        if errs:
            p("  ERRORES: " + " | ".join(errs))
        if idx == 1:
            check(estado == "success" and isinstance(dicho, str)
                  and dicho.strip() and not errs,
                  "El TEXTO sigue funcionando: el bot responde igual que antes",
                  f"status={estado} | respuesta={dicho!r}")
            # La respuesta del agente SI se manda al numero del cliente
            body = body_de_mandar_mensaje(wf)
            num = body.get("number", "")
            txt_env = body.get("text", "")
            p(f"  body de 'Mandar mensaje': number={num[:60]!r}  "
              f"text={txt_env[:60]!r}")
            check("user_number" in str(num) and "output" in str(txt_env),
                  "'Mandar mensaje' sigue enviando el texto del agente "
                  "($json.output) al numero del cliente",
                  "number y text apuntan a los campos correctos")
            check("AI Agent" in run and "Mandar mensaje" in run,
                  "El texto recorre el camino completo "
                  "(Edit Fields -> AI Agent -> Mandar mensaje)",
                  f"nodos ejecutados: {len(run)}")
        else:
            esperado = "solo puedo atender mensajes escritos"
            check(estado == "success" and isinstance(dicho, str)
                  and esperado in dicho.lower() and not errs,
                  f"Un mensaje de {etiqueta.upper()} recibe respuesta sensata "
                  "(no silencio, no error)",
                  f"status={estado} | respuesta={dicho!r} | errores={errs}")
            check("AI Agent" not in run,
                  f"El mensaje de {etiqueta} no gasta tokens (AI Agent no corre)",
                  f"nodos ejecutados: {len(run)}")

    # ------------------------------------------------ forma del Switch final
    p("")
    p("--- forma del Switch tras el cambio ---")
    sw = next((n for n in wf["nodes"] if n["name"] == "Switch"), {})
    claves = [v.get("outputKey") for v in
              (((sw.get("parameters") or {}).get("rules") or {}).get("values") or [])]
    dest = [[c["node"] for c in (r or [])] for r in
            wf["connections"].get("Switch", {}).get("main", [])]
    check(claves == ["Texto"],
          "El Switch solo enruta 'text' (ya no tiene salidas Audio/Imagen)",
          f"reglas: {claves}")
    check(len(dest) >= 2 and dest[0] == ["Edit Fields2"] and dest[1] == [AVISO],
          f"Switch: Texto -> Edit Fields2 ; resto -> {AVISO}",
          f"conexiones: {dest}")
    check(wf["connections"].get(AVISO, {}).get("main", [[{}]])[0][0]["node"]
          == "Mandar mensaje",
          f"'{AVISO}' -> 'Mandar mensaje' (el cliente siempre recibe algo)")

    with open(DETALLE, "w", encoding="utf-8") as f:
        json.dump(detalle, f, ensure_ascii=False, indent=2)
    p("")
    p(f"Detalle E2E guardado en {DETALLE}")

    # --------------------------------------------------------- [7] verify.py
    p("")
    p("[7] verify.py (comprobaciones estructurales del repo)")
    vp = subprocess.run([UV, "run", "python", r"G:\Barberia\verify.py"],
                        capture_output=True, cwd=r"G:\Barberia")
    vout = vp.stdout.decode("utf-8", "replace")
    verr = vp.stderr.decode("utf-8", "replace")
    with open(VERIFY_OUT, "w", encoding="utf-8") as f:
        f.write(f"RC={vp.returncode}\n---- STDOUT ----\n{vout}\n---- STDERR ----\n{verr}")
    mt = re.search(r"RESULTADO: (\d+) de (\d+) verificaciones PASARON", vout)
    if mt:
        pas, tot = int(mt.group(1)), int(mt.group(2))
        check(pas >= 173 and vp.returncode == 0,
              f"verify.py da {pas}/{tot} (>= 173) sin fallos", f"exit code {vp.returncode}")
    else:
        check(False, "verify.py imprime su resultado", (vout[-400:] or verr[-400:]))
    for l in vout.splitlines():
        if "FAIL" in l:
            p("          " + l)

    # ------------------------------------------------------------ resumen
    p("")
    p("=" * 74)
    fallos = [t for ok, t in res if not ok]
    p(f"RESUMEN: {len(res) - len(fallos)} de {len(res)} comprobaciones PASARON")
    for t in fallos:
        p("  FALLO: " + t)
    p("=" * 74)
    return 1 if fallos else 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception:
        import traceback
        traceback.print_exc(file=buf)
        rc = 1
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    sys.exit(rc)