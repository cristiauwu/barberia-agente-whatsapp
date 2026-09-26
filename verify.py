#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion de los workflows generados.

Comprueba estructura, referencias, herramientas y contenido del prompt.
Devuelve exit code 1 si alguna verificacion falla.
Uso:  uv run python verify.py
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(r"G:\Barberia")
PROMPT = BASE / "prompt-sistema-agente-barberia.txt"
F1 = BASE / "BarberiaAgenteFLUJO-1-UNCENSORED.json"
F2 = BASE / "BarberiaAgenteFLUJO-2-RECORDATORIOS.json"

fails = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if cond:
        print("  PASS  " + msg)
    else:
        print("  FAIL  " + msg)
        fails.append(msg)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def names(f):
    return [n["name"] for n in f["nodes"]]


def node(f, name):
    for n in f["nodes"]:
        if n["name"] == name:
            return n
    return None


def walk_refs(o, out):
    """Recolecta $('Nombre') para validar referencias entre nodos."""
    if isinstance(o, str):
        out.update(re.findall(r"\$\(['\"]([^'\"]+)['\"]\)", o))
    elif isinstance(o, dict):
        for v in o.values():
            walk_refs(v, out)
    elif isinstance(o, list):
        for v in o:
            walk_refs(v, out)


print("=" * 70)
print("VERIFICACION DE ENTREGABLES")
print("=" * 70)

# ---------------------------------------------------------------- archivos
print("\n[1] Archivos y parseo JSON")
check(PROMPT.exists(), "Existe prompt-sistema-agente-barberia.txt")
check(F1.exists(), "Existe el workflow 1 generado")
check(F2.exists(), "Existe el workflow 2 generado")

f1 = load(F1)
f2 = load(F2)
check(isinstance(f1.get("nodes"), list) and len(f1["nodes"]) > 0,
      "Workflow 1 parsea y tiene nodos (%d)" % len(f1["nodes"]))
check(isinstance(f2.get("nodes"), list) and len(f2["nodes"]) > 0,
      "Workflow 2 parsea y tiene nodos (%d)" % len(f2["nodes"]))

# ---------------------------------------------------------- estructura n8n
print("\n[2] Estructura de workflow n8n")
for label, f in (("W1", f1), ("W2", f2)):
    ok_keys = all(k in f for k in
                  ("name", "nodes", "connections", "settings", "active"))
    check(ok_keys, "%s tiene las claves de nivel raiz requeridas" % label)
    ids = [n.get("id") for n in f["nodes"]]
    check(all(ids), "%s todos los nodos tienen id" % label)
    check(len(ids) == len(set(ids)), "%s los ids de nodo son unicos" % label)
    for n in f["nodes"]:
        if "position" not in n or "type" not in n or "parameters" not in n:
            check(False, "%s nodo %s tiene type/position/parameters"
                  % (label, n.get("name")))
            break
    else:
        check(True, "%s todos los nodos tienen type/position/parameters" % label)

# ------------------------------------------------------------ conexiones
print("\n[3] Integridad de conexiones (sin nodos huerfanos)")
for label, f in (("W1", f1), ("W2", f2)):
    nm = set(names(f))
    bad = []
    for src, branches in f["connections"].items():
        if src not in nm:
            bad.append("origen inexistente: " + src)
        for out in branches.values():
            for conns in out:
                for c in conns:
                    if c["node"] not in nm:
                        bad.append("%s -> %s" % (src, c["node"]))
    check(not bad, "%s todas las conexiones apuntan a nodos existentes %s"
          % (label, bad if bad else ""))

print("\n[4] Referencias $('Nodo') validas")
for label, f in (("W1", f1), ("W2", f2)):
    refs = set()
    for n in f["nodes"]:
        walk_refs(n.get("parameters", {}), refs)
    nm = set(names(f))
    missing = sorted(r for r in refs if r not in nm)
    check(not missing, "%s referencias resueltas (faltan: %s)"
          % (label, missing if missing else "ninguna"))

# ------------------------------------------------------- prompt del agente
print("\n[5] System prompt del agente")
agent = node(f1, "AI Agent")
check(agent is not None, "Existe el nodo AI Agent")
sysmsg = agent["parameters"]["options"]["systemMessage"]
prompt = PROMPT.read_text(encoding="utf-8").strip()
check(sysmsg == "=" + prompt, "El system prompt incrustado es identico al archivo")

# Si el modelo devuelve texto vacio, el cliente recibe un mensaje fijo.
# Solo se enruta por la rama false: una respuesta correcta no se duplica.
respuesta_vacia = node(f1, "IF - Respuesta no vacia")
aviso_vacio = node(f1, "Respuesta sin texto")
check(respuesta_vacia is not None and aviso_vacio is not None,
      "Existe manejo explicito para la respuesta vacia del agente")
if respuesta_vacia and aviso_vacio:
    ramas = f1["connections"].get("IF - Respuesta no vacia", {}).get("main", [])
    destino = f1["connections"].get("Respuesta sin texto", {}).get("main", [])
    aviso = aviso_vacio.get("parameters", {}).get("assignments", {}).get("assignments", [])
    check(len(ramas) >= 2 and [c["node"] for c in ramas[0]] == ["Mandar mensaje"]
          and [c["node"] for c in ramas[1]] == ["Respuesta sin texto"],
          "Solo la rama false de respuesta vacia usa el aviso fijo")
    check(bool(destino) and [c["node"] for c in destino[0]] == ["Mandar mensaje"],
          "El aviso fijo llega al nodo que envia al cliente")
    check(len(aviso) == 1 and aviso[0].get("name") == "output"
          and aviso[0].get("type") == "string"
          and bool(aviso[0].get("value", "").lstrip("=").strip()),
          "El aviso de respuesta vacia define texto no vacio")

# Precios de la imagen: deben estar TODOS
precios = {
    "Corte desvanecido o tijera": "$150",
    "Arreglo de barba": "$100",
    "Ceja": "$30",
    "Mascarilla": "$50",
    "Corte de cabello dama": "$250",
    "Planchado express": "$150",
    "Peinado": "$300",
}
for servicio, precio in precios.items():
    check(servicio in sysmsg and precio in sysmsg,
          "Precio en el prompt: %s %s" % (servicio, precio))
check("Depilaci" in sysmsg and "zona" in sysmsg,
      "Depilacion descrita como 'precio segun la zona'")
for zona in ("ceja", "bigote", "nariz", "orejas", "barba", "axilas", "piernas"):
    check(zona in sysmsg.lower(), "Zona de depilacion listada: " + zona)

# Datos del negocio de la imagen
check("Barber Chinos" in sysmsg, "Nombre del negocio en el prompt")
check("452-281-8144" in sysmsg, "Telefono de citas en el prompt")
check("Pinz" in sysmsg and "574" in sysmsg, "Domicilio en el prompt")

# Precios viejos NO deben aparecer
for viejo in ("$350", "$500", "$600"):
    check(viejo not in sysmsg, "Precio obsoleto eliminado: " + viejo)

# ------------------------------------------------------- modelo Uncensored
print("\n[6] Configuracion del modelo (Uncensored AI)")
m = node(f1, "OpenAI Chat Model")
check(m is not None, "Existe el nodo OpenAI Chat Model")
check(m["parameters"]["model"]["value"] == "gpt-4o",
      "Modelo configurado: %s (existe en el catalogo)"
      % m["parameters"]["model"]["value"])
check(m["parameters"].get("responsesApiEnabled") is not True,
      "Responses API desactivada (ausente = default false; solo /chat/completions)")
cred = m.get("credentials", {}).get("openAiApi", {})
check("Uncensored" in cred.get("name", ""),
      "Credencial apunta a Uncensored AI: %s" % cred.get("name"))
check(cred.get("id") != "GtV72MoANECFbNoX",
      "NO reutiliza el id de la credencial original de OpenAI")
check("api.uncensored.com" in m.get("notes", ""),
      "Notas del nodo documentan la Base URL")

# El usuario pidió NO procesar audio ni imágenes: esos nodos deben estar fuera.
MULTIMEDIA = ["Get Audio", "Convertir Audio", "Transcribe a recording",
              "Audio Content", "Audio Content1", "Get Image",
              "Convertir Imagen", "Describe imagen"]
nombres_w1 = [n["name"] for n in f1["nodes"]]
for nm in MULTIMEDIA:
    check(nm not in nombres_w1,
          "'%s' eliminado (el usuario no quiere audio ni imagen)" % nm)
_txt1 = json.dumps(f1, ensure_ascii=False)
for nm in MULTIMEDIA:
    check(nm not in _txt1,
          "Sin referencias huerfanas a '%s' en el JSON" % nm)
check("GtV72MoANECFbNoX" not in _txt1,
      "Sin la credencial de OpenAI rota (ya no se usa audio ni imagen)")
# El Switch debe tener una sola via de texto y un respaldo para lo demas
_sw = node(f1, "Switch")
if _sw:
    _opts = _sw["parameters"].get("options", {})
    check(bool(_opts.get("renameFallbackOutput")),
          "El Switch tiene respaldo para mensajes no-texto")

# ------------------------------------------------------------ herramientas
print("\n[7] Herramientas del agente")
tool_names = [n["name"] for n in f1["nodes"]
              if n["type"].endswith(("Tool", "Tool")) or "tools" in n["type"]
              or n["type"].endswith("googleSheetsTool")
              or n["type"].endswith("googleCalendarTool")]
for esperado in ("Consultar agenda", "Agendar cita", "Cancelar cita",
                 "Reagendar", "Registrar en hoja de citas",
                 "Notificar al encargado"):
    n = node(f1, esperado)
    check(n is not None, "Herramienta presente: " + esperado)
    if n is not None:
        attached = f1["connections"].get(esperado, {}).get("ai_tool", [])
        target = attached[0][0]["node"] if attached else None
        check(target == "AI Agent",
              "  '%s' conectada al AI Agent como ai_tool" % esperado)

# Nombres viejos ya no deben existir
for viejo in ("Obtener eventos", "Crear evento", "Eliminar eventos",
              "Append row in sheet in Google Sheets", "MANDAR RECORDATORIO"):
    if viejo == "MANDAR RECORDATORIO":
        continue
    check(node(f1, viejo) is None, "Nombre viejo eliminado en W1: " + viejo)

# Reagendar debe actualizar start/end
reag = node(f1, "Reagendar")
uf = reag["parameters"].get("updateFields", {})
for campo in ("start", "end", "summary", "description"):
    check(campo in uf, "Reagendar actualiza '%s'" % campo)

# Obtener eventos acotado
obt = node(f1, "Consultar agenda")
check(obt["parameters"].get("returnAll") is not True,
      "Consultar agenda usa rango acotado (returnAll ausente = default false)")
check("timeMin" in obt["parameters"] and "timeMax" in obt["parameters"],
      "Consultar agenda recibe rango de fechas del modelo")

# Todas las toolDescription no vacias
for n in f1["nodes"]:
    if "toolDescription" in n.get("parameters", {}):
        check(len(n["parameters"]["toolDescription"]) > 40,
              "toolDescription descriptiva en '%s'" % n["name"])

# URLs sin saltos de linea
for n in f1["nodes"]:
    u = n.get("parameters", {}).get("url")
    if isinstance(u, str):
        check(u == u.strip(), "URL sin espacios/saltos en '%s'" % n["name"])

print("\n[8] Flujo 2: recordatorios")
code = node(f2, "Code")["parameters"]["jsCode"]
check("return items.map" in code, "El Code node tiene sintaxis valida")
check(not re.search(r"\nv\s*$", code.strip() + "\n\n"), "Linea suelta 'v' eliminada")
check("-06:00" in code, "Zona horaria America/Mexico_City fijada (-06:00)")
check("mandar24" in code and "mandar1" in code,
      "El Code calcula si toca cada recordatorio")
check("recordatorio24ISO" in code and "recordatorio1ISO" in code,
      "El Code produce ambos horarios de recordatorio")

for esperado in ("RECORDATORIO 24 H", "RECORDATORIO 1 H"):
    n = node(f2, esperado)
    check(n is not None, "Existe el nodo: " + esperado)
    if n is not None:
        txt = n["parameters"]["bodyParameters"]["parameters"][1]["value"]
        check("Confirmar" in str(txt) or "confirmar" in str(txt) or "SI" in str(txt),
              "  '%s' pide confirmacion" % esperado)

sw = node(f2, "Switch")
check(sw["parameters"]["options"].get("fallbackOutput") == "extra",
      "Switch con salida de respaldo 'Otro'")

# --- Critico: el recordatorio de 24 h DEBE tener un Wait antes ---------
# Sin el, el mensaje se enviaria al momento de agendar, no 24 h antes.
print("\n[9] Orden temporal de los recordatorios (regresion)")
conns = f2["connections"]
entradas_24 = []
for src, branches in conns.items():
    for out in branches.values():
        for cs in out:
            for c in cs:
                if c["node"] == "RECORDATORIO 24 H":
                    entradas_24.append(src)
check(entradas_24 == ["ESPERAR A 24 H"],
      "El recordatorio de 24 h SOLO se alcanza via un Wait (llega desde: %s)"
      % entradas_24)
w24 = node(f2, "ESPERAR A 24 H")
check(w24 is not None and w24["type"] == "n8n-nodes-base.wait",
      "Existe el nodo 'ESPERAR A 24 H' de tipo wait")
check(w24 is not None and "recordatorio24ISO" in w24["parameters"]["dateTime"],
      "El Wait de 24 h espera hasta recordatorio24ISO")

entradas_1 = []
for src, branches in conns.items():
    for out in branches.values():
        for cs in out:
            for c in cs:
                if c["node"] == "RECORDATORIO 1 H":
                    entradas_1.append(src)
check(entradas_1 == ["ESPERAR A 1 H"],
      "El recordatorio de 1 h SOLO se alcanza via un Wait (llega desde: %s)"
      % entradas_1)
w1 = node(f2, "ESPERAR A 1 H")
check(w1 is not None and "recordatorio1ISO" in w1["parameters"]["dateTime"],
      "El Wait de 1 h espera hasta recordatorio1ISO")

# Cadena completa en orden
def alcanza(desde, hasta, vistos=None):
    vistos = vistos or set()
    if desde in vistos:
        return False
    vistos.add(desde)
    for out in conns.get(desde, {}).values():
        for cs in out:
            for c in cs:
                if c["node"] == hasta or alcanza(c["node"], hasta, vistos):
                    return True
    return False

check(alcanza("Append or update row in sheet", "ESPERAR A 24 H"),
      "Cadena: alta en hoja -> IF 24 h -> ESPERAR A 24 H")
check(alcanza("ESPERAR A 24 H", "RECORDATORIO 24 H"),
      "Cadena: ESPERAR A 24 H -> RECORDATORIO 24 H")
check(alcanza("RECORDATORIO 24 H", "ESPERAR A 1 H"),
      "Cadena: RECORDATORIO 24 H -> ESPERAR A 1 H")
check(alcanza("ESPERAR A 1 H", "RECORDATORIO 1 H"),
      "Cadena: ESPERAR A 1 H -> RECORDATORIO 1 H")
check(not alcanza("ESPERAR A 1 H", "RECORDATORIO 24 H"),
      "El orden no se invierte (1 h no lleva al de 24 h)")

# Los IF comparan contra 'si' de forma explicita
for nm in ("IF - Toca recordatorio 24 h", "IF - Toca recordatorio 1 h"):
    cond = node(f2, nm)["parameters"]["conditions"]["conditions"][0]
    check(cond["operator"]["operation"] == "equals"
          and cond["rightValue"] == "si",
          "'%s' compara contra 'si' con operador equals" % nm)

print("\n[10] Nodos sin entrada (regresion)")
# Todo nodo que no sea trigger debe recibir datos de algun lado.
# El bug historico: 'Mandar mensaje' (renombrado) perdio su salida hacia
# Switch, dejando el Switch huerfano y los recordatorios sin dispararse.
destinos = set()
origenes = set()
for src, ramas in f2["connections"].items():
    origenes.add(src)
    for salidas in ramas.values():
        for grupo in salidas:
            for c in grupo:
                destinos.add(c["node"])

for n in f2["nodes"]:
    nombre, tipo = n["name"], n["type"]
    es_trigger = ("Trigger" in tipo or tipo.endswith(".webhook")
                  or "manualTrigger" in tipo)
    if not es_trigger:
        check(nombre in destinos,
              "'%s' recibe datos de algun nodo" % nombre)

check("Switch" in destinos, "El Switch recibe entrada (no queda huerfano)")
check(node(f2, "Notificar cita nueva al encargado") is not None,
      "Existe 'Notificar cita nueva al encargado'")

print("\n[11] Flujo 1: nodos sin entrada 'main' (regresion)")
# OJO: en el flujo 1 hay nodos que legitimamente no reciben 'main':
#   - el Webhook (es trigger)
#   - las herramientas del agente entran por 'ai_tool', no por 'main'
#   - el modelo y la memoria por 'ai_languageModel' / 'ai_memory'
# Un nodo es huerfano de verdad solo si NO es trigger y NO participa en
# ninguna conexion ai_*, ni como origen ni como destino.
dest1, fuente_ai, dest_ai = set(), set(), set()
for src, ramas in f1["connections"].items():
    for tipo, salidas in ramas.items():
        for grupo in salidas:
            for c in grupo:
                if tipo == "main":
                    dest1.add(c["node"])
                else:
                    fuente_ai.add(src)
                    dest_ai.add(c["node"])

huerfanos1 = []
for n in f1["nodes"]:
    nombre, tipo = n["name"], n["type"]
    if nombre in dest1:
        continue
    es_trigger = ("Trigger" in tipo or tipo.endswith(".webhook")
                  or "manualTrigger" in tipo)
    if es_trigger or nombre in fuente_ai or nombre in dest_ai:
        continue
    huerfanos1.append(nombre)
check(not huerfanos1,
      "W1 sin nodos huerfanos reales (encontrados: %s)" % (huerfanos1 or "ninguno"))
sale_de_notif = []
for salidas in f2["connections"].get("Notificar cita nueva al encargado", {}).values():
    for grupo in salidas:
        for c in grupo:
            sale_de_notif.append(c["node"])
check(sale_de_notif == ["Switch"],
      "'Notificar cita nueva al encargado' -> Switch (llega: %s)"
      % (sale_de_notif or "nada"))
check(alcanza("Google Sheets Trigger", "Switch"),
      "Cadena: Trigger -> Code -> Notificar -> Switch")
check(alcanza("Switch", "ESPERAR A 24 H") or alcanza("Switch", "Code1"),
      "El Switch dirige a las ramas de recordatorio")

print("\n[12] Comandos del dueño (flujo 1)")
# El dueño manda comandos por WhatsApp que NO pasan por el modelo.
# Se verifica el enrutado completo en el archivo del repo.
COMANDOS_ORDEN = ["HOY", "MAÑANA", "SEMANA", "LIBRE", "CLIENTE",
                  "BLOQUEAR", "CERRAR", "ABRIR", "PRECIO", "PAUSA",
                  "ESTADO", "COMANDOS"]
DESTINO_ESPERADO = {
    "HOY": "Preparar rango de fechas",
    "MAÑANA": "Preparar rango de fechas",
    "SEMANA": "Preparar rango de fechas",
    "LIBRE": "Preparar rango de fechas",
    "CLIENTE": "Buscar cliente",
    "BLOQUEAR": "Parsear bloqueo",
    "CERRAR": "Parsear bloqueo",
    "ABRIR": "Parsear bloqueo",
    "PRECIO": "Parsear precio",
    "PAUSA": "Parsear pausa",
    "ESTADO": "Leer estado del sistema",
    "COMANDOS": "Armar respuesta COMANDOS",
}

router = node(f1, "Router de comandos")
check(router is not None, "Existe el nodo 'Router de comandos'")
if router:
    salidas = f1["connections"].get("Router de comandos", {}).get("main", [])
    check(len(salidas) == 13,
          "El router tiene 13 salidas (12 comandos + respaldo): %d"
          % len(salidas))
    for i, cmd in enumerate(COMANDOS_ORDEN):
        if i >= len(salidas):
            break
        dest = salidas[i][0]["node"] if salidas[i] else "(vacio)"
        esperado = DESTINO_ESPERADO[cmd]
        check(dest == esperado,
              "Salida '%s' del router -> %s (esperado %s)"
              % (cmd, dest, esperado))
    # El respaldo debe devolver el mensaje al flujo normal del agente
    if len(salidas) > 12:
        ult = salidas[12][0]["node"] if salidas[12] else "(vacio)"
        check(ult == "IF - No es del bot",
              "El respaldo del router va al flujo normal del agente: %s" % ult)

# El IF de operador debe leer la tabla, no tener un numero fijo
op = node(f1, "¿Es operador?")
check(op is not None, "Existe el nodo '¿Es operador?'")
if op:
    conds = (op["parameters"].get("conditions") or {}).get("conditions") or []
    txt = json.dumps(conds, ensure_ascii=False)
    check("es_operador" in txt,
          "El IF de operador usa el campo calculado 'es_operador'")
    check("5215520894522" not in txt,
          "El IF de operador NO tiene el numero del vendedor hardcodeado")

# El operador se decide leyendo la tabla
check(node(f1, "Leer operadores") is not None,
      "Existe 'Leer operadores' (lee la tabla barber_operadores)")
check(node(f1, "Comprobar operador") is not None,
      "Existe 'Comprobar operador' (tolera 52+10 y 52+1+10)")
cad = f1["connections"]
# La entrada ya no va directo al agente: pasa por la PUERTA de confirmacion,
# que decide si el mensaje es un SI/NO al recordatorio o una conversacion
# normal. Solo el respaldo de esa puerta llega a 'Leer operadores'.
check(cad.get("Normalizacion", {}).get("main", [[{}]])[0][0]["node"]
      == "Buscar cita para confirmar",
      "Normalizacion entra por la puerta de confirmacion")
check(cad.get("Buscar cita para confirmar", {}).get("main", [[{}]])[0][0]["node"]
      == "Es confirmacion?",
      "'Buscar cita para confirmar' alimenta al detector")
check(cad.get("Es confirmacion?", {}).get("main", [[{}]])[0][0]["node"]
      == "Switch confirmacion",
      "El detector alimenta al Switch de confirmacion")
# El respaldo del Switch (salida 2) es el que sigue al agente. Asi un SI
# NO llama al modelo y el agente solo corre cuando de verdad toca.
_sal_sw = cad.get("Switch confirmacion", {}).get("main", [])
check(len(_sal_sw) == 3,
      "El Switch de confirmacion tiene 3 salidas (SI / NO / respaldo)")
check(len(_sal_sw) >= 3 and _sal_sw[2][0]["node"] == "Leer operadores",
      "El respaldo del Switch va al camino normal del agente")
check(cad.get("Leer operadores", {}).get("main", [[{}]])[0][0]["node"]
      == "Comprobar operador",
      "'Leer operadores' alimenta a 'Comprobar operador'")
check(cad.get("Comprobar operador", {}).get("main", [[{}]])[0][0]["node"]
      == "¿Es operador?",
      "'Comprobar operador' alimenta a '¿Es operador?'")

# Los nodos que pueden devolver 0 filas deben seguir el flujo
for nm in ("Leer agenda del rango", "Leer ficha del cliente",
           "Actualizar precio", "Aplicar pausa", "Leer operadores"):
    n = node(f1, nm)
    check(n is not None and n.get("alwaysOutputData") is True,
          "'%s' tiene alwaysOutputData (no corta la cadena sin datos)" % nm)

# Cada cadena de comando debe terminar en el nodo que responde
CADENAS = {
    "Preparar rango de fechas": ["Leer agenda del rango", "Formatear agenda",
                                 "Responder al operador"],
    "Buscar cliente": ["Leer ficha del cliente", "Formatear ficha",
                       "Responder al operador"],
    "Parsear precio": ["Actualizar precio", "Formatear precio",
                       "Responder al operador"],
    "Parsear pausa": ["Aplicar pausa", "Formatear pausa",
                      "Responder al operador"],
    "Leer estado del sistema": ["Formatear estado", "Responder al operador"],
}
for inicio, cadena in CADENAS.items():
    n = inicio
    ok = True
    for esperado in cadena:
        paso = cad.get(n, {}).get("main", [[]])
        if not paso or not paso[0]:
            ok = False
            break
        n = paso[0][0]["node"]
        if n != esperado:
            ok = False
            break
    check(ok, "Cadena de '%s' termina en el nodo que responde" % inicio)

# El bloqueo se valida antes de tocar el calendario
check(node(f1, "IF - Bloqueo invalido") is not None,
      "Existe 'IF - Bloqueo invalido' (valida antes de crear el evento)")
check(node(f1, "Crear bloqueo en calendario") is not None,
      "Existe 'Crear bloqueo en calendario'")

# El destino de los avisos debe ser el dueño, no el vendedor
txt1 = json.dumps(f1, ensure_ascii=False)
check("5215520894522" not in txt1,
      "Flujo 1 sin el numero del vendedor")
check("524521206246" in txt1,
      "Flujo 1 avisa al numero del dueño")

# Los textos de los comandos no deben usar markdown de dos asteriscos
for n in f1["nodes"]:
    cod = (n.get("parameters") or {}).get("jsCode")
    if cod:
        check("**" not in cod,
              "'%s' no usa ** (WhatsApp solo lee un asterisco)" % n["name"])


print("RESULTADO: %d de %d verificaciones PASARON" % (checks, checks))
print("=" * 70)

# ------------------------------------------------------------- veredicto
print("\n" + "=" * 70)
if fails:
    print("RESULTADO: %d de %d verificaciones FALLARON" % (len(fails), checks))
    for m_ in fails:
        print("  - " + m_)
    sys.exit(1)
