#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera los workflows modificados del agente de barberia (Barber Chinos).

No toca los archivos originales: escribe archivos NUEVOS.
Uso:  uv run python transforms.py
"""
import json
import pathlib
import uuid

BASE = pathlib.Path(r"G:\Barberia")
SRC1 = BASE / "BarberiaAgenteFLUJO 1.json"
SRC2 = BASE / "BarberiaAgenteFLUJO 2.json"
PROMPT = BASE / "prompt-sistema-agente-barberia.txt"
OUT1 = BASE / "BarberiaAgenteFLUJO-1-UNCENSORED.json"
OUT2 = BASE / "BarberiaAgenteFLUJO-2-RECORDATORIOS.json"

SHEET_DOC = "17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY"
SHEET_GID = "gid=0"
OWNER_WA = "5215520894522@s.whatsapp.net"
EVO_SERVER = "https://makewhatsapp-evolution-api.1takfl.easypanel.host"
EVO_KEY = "CLAVE_DEL_PROVEEDOR_ANTIGUA"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def dump(obj, p):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")


def node(flow, name):
    for n in flow["nodes"]:
        if n["name"] == name:
            return n
    raise KeyError(name)


def fromai(name, desc, typ="string"):
    return "={{ $fromAI('%s', '%s', '%s') }}" % (name, desc, typ)


def tdesc(flow, name, text):
    node(flow, name)["parameters"]["toolDescription"] = text


def rename_node(flow, old, new):
    """Renombra un nodo actualizando su clave, los destinos y las referencias."""
    n = node(flow, old)
    n["name"] = new

    # Clave de origen en connections
    if old in flow["connections"]:
        flow["connections"][new] = flow["connections"].pop(old)

    # Destinos en connections
    for branches in flow["connections"].values():
        for out in branches.values():
            for conns in out:
                for c in conns:
                    if c.get("node") == old:
                        c["node"] = new

    # Referencias $('Nodo') dentro de expresiones
    for other in flow["nodes"]:
        s = json.dumps(other.get("parameters", {}), ensure_ascii=False)
        if "$('" + old + "')" in s:
            s = s.replace("$('" + old + "')", "$('" + new + "')")
            other["parameters"] = json.loads(s)


def base_sheet_params(operation):
    """Parametros comunes de la herramienta de Google Sheets."""
    return {
        "operation": operation,
        "documentId": {
            "__rl": True, "value": SHEET_DOC, "mode": "list",
            "cachedResultName": "Citas barberia",
        },
        "sheetName": {
            "__rl": True, "value": SHEET_GID, "mode": "list",
            "cachedResultName": "Hoja 1",
        },
    }


def sheet_logger():
    """Herramienta: registrar una accion en la hoja de citas."""
    columnas = {
        "ID": "ID del evento de Google Calendar que devolvio Crear evento o Consultar agenda",
        "Estatus": "agendado, actualizado o cancelado, segun la accion realizada",
        "Nombre": "Nombre del cliente",
        "Servicio": "Servicio o servicios agendados",
        "Precio del servicio": "Precio total en MXN, solo el numero, por ejemplo 250",
        # OJO: la columna real de la hoja se llama "D\u00eda " (con acento).
        # \u00ed es "i" con acento agudo; se escribe escapado para no perderlo.
        "D\u00eda ": "Fecha de la cita en formato AAAA-MM-DD",
        "Hora": "Hora de la cita en formato HH:MM:SS de 24 horas, por ejemplo 16:00:00",
    }
    cols = {k: fromai(k.strip(), v) for k, v in columnas.items()}
    cols["Numero celular"] = "={{ $('Normalizacion').item.json.user_number }}"
    schema = [
        {"id": "ID", "displayName": "ID", "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Estatus", "displayName": "Estatus", "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Nombre", "displayName": "Nombre", "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Servicio", "displayName": "Servicio", "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Precio del servicio", "displayName": "Precio del servicio",
         "required": False, "defaultMatch": False, "display": True,
         "type": "string", "canBeUsedToMatch": True, "removed": False},
        {"id": "D\u00eda ", "displayName": "D\u00eda ",
         "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Hora", "displayName": "Hora", "required": False,
         "defaultMatch": False, "display": True, "type": "string",
         "canBeUsedToMatch": True, "removed": False},
        {"id": "Numero celular", "displayName": "Numero celular",
         "required": False, "defaultMatch": False, "display": True,
         "type": "string", "canBeUsedToMatch": True, "removed": False},
    ]
    p = base_sheet_params("append")
    p["toolDescription"] = (
        "Registra una fila nueva en la hoja de control de citas del negocio. "
        "Ejecutala despues de CADA accion sobre una cita: agendar, reprogramar o "
        "cancelar. Al reprogramar registra dos filas con el mismo ID: una "
        "'cancelado' con el horario anterior y una 'agendado' con el nuevo."
    )
    p["columns"] = {
        "mappingMode": "defineBelow",
        "value": cols,
        "matchingColumns": ["ID"],
        "schema": schema,
        "attemptToConvertTypes": False,
        "convertFieldsToString": False,
    }
    p["options"] = {}
    return {
        "parameters": p,
        "type": "n8n-nodes-base.googleSheetsTool",
        "typeVersion": 4.6,
        "position": [1320, 940],
        "id": str(uuid.uuid4()),
        "name": "Registrar en hoja de citas",
        "credentials": {
            "googleSheetsOAuth2Api": {
                "id": "EHIP8e88rmbBU8t9",
                "name": "Google Sheets account",
            }
        },
    }


def notifier():
    """Herramienta: escalar al encargado por WhatsApp (Evolution API)."""
    return {
        "parameters": {
            "toolDescription": (
                "Avisa al encargado de la barberia por WhatsApp cuando el cliente "
                "pide hablar con una persona, pide un descuento o un precio que no "
                "esta en la lista, quiere un servicio que no ofrecemos, tiene una "
                "queja, o cuando no pudiste resolver su solicitud. El texto debe "
                "resumir quien es el cliente, que pidio y su numero de WhatsApp."
            ),
            "url": EVO_SERVER + "/message/sendText/hector",
            "authentication": "none",
            "method": "POST",
            "sendBody": True,
            "specifyBody": "keypair",
            "parametersBody": {"values": [
                {"name": "number", "valueProvider": "fieldValue",
                 "value": OWNER_WA},
                {"name": "text", "valueProvider": "modelRequired"},
                {"name": "delay", "valueProvider": "fieldValue", "value": "1000"},
            ]},
            "sendHeaders": True,
            "specifyHeaders": "keypair",
            "parametersHeaders": {"values": [
                {"name": "apikey", "valueProvider": "fieldValue", "value": EVO_KEY},
            ]},
            "options": {},
        },
        "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
        "typeVersion": 1.1,
        "position": [1320, 1120],
        "id": str(uuid.uuid4()),
        "name": "Notificar al encargado",
        "notes": (
            "Escala al encargado por WhatsApp con el mismo servidor Evolution del "
            "flujo. Cambia 'number' si el encargado usa otro numero."
        ),
        "notesInFlow": True,
    }


def transform_flow1(prompt_text):
    f = load(SRC1)

    # --- 1. System prompt profesional -------------------------------------
    agent = node(f, "AI Agent")
    agent["parameters"]["options"]["systemMessage"] = "=" + prompt_text
    agent["parameters"]["text"] = (
        "=Cliente: {{ $('Normalizacion').item.json.user_name || 'sin nombre' }}"
        " (WhatsApp {{ $('Normalizacion').item.json.user_number }})\n"
        "Mensaje: {{ $json.chat_input }}"
    )

    # --- 2. Modelo Uncensored AI ------------------------------------------
    model = node(f, "OpenAI Chat Model")
    model["parameters"]["model"] = {
        "__rl": True, "value": "gpt-4o", "mode": "list",
        "cachedResultName": "gpt-4o",
    }
    model["parameters"]["responsesApiEnabled"] = False
    model["credentials"] = {
        "openAiApi": {
            "id": "uncensored-ai",
            "name": "Uncensored AI (OpenAI-compatible)",
        }
    }
    model["notes"] = (
        "Credencial requerida: 'Uncensored AI (OpenAI-compatible)'.\n"
        "Base URL: https://api.uncensored.com/api/v1\n"
        "API Key: tu llave de uncensored.com (Developer Dashboard).\n"
        "Header extra: x-api-key = tu llave (la API acepta x-api-key y Bearer).\n"
        "Modelo: cualquier ID de https://api.uncensored.com/api/v1/models\n"
        "IMPORTANTE: esta credencial debe ser DISTINTA de la de OpenAI, porque "
        "Whisper y el analisis de imagenes siguen usando OpenAI."
    )
    model["notesInFlow"] = True

    # --- 3. Descripciones de herramientas --------------------------------
    tdesc(f, "Obtener eventos",
          "Consulta las citas ya ocupadas en el calendario de la barberia dentro "
          "de un rango de fechas. Usala SIEMPRE antes de agendar o reprogramar, "
          "para no empalmar dos citas. Devuelve los eventos con su ID, resumen, "
          "descripcion, inicio y fin.")
    tdesc(f, "Crear evento",
          "Agenda una cita nueva en el calendario. Antes de usarla confirma que el "
          "horario esta libre con 'Consultar agenda'. El resumen debe ser "
          "'Servicio - Nombre del cliente' y la descripcion debe incluir nombre, "
          "servicio, precio, numero de WhatsApp y notas.")
    tdesc(f, "Eliminar eventos",
          "Cancela definitivamente una cita del calendario. Requiere el ID del "
          "evento que devuelve 'Consultar agenda' o 'Crear evento'. No la uses sin "
          "haber localizado la cita exacta.")
    tdesc(f, "Reagendar",
          "Mueve una cita existente a un horario nuevo conservando su ID. Requiere "
          "el ID del evento y el nuevo inicio y fin. Verifica la disponibilidad del "
          "nuevo horario antes de reprogramar.")

    # --- 4. Reagendar: updateFields estaba vacio -------------------------
    node(f, "Reagendar")["parameters"]["updateFields"] = {
        "start": fromai("Start",
                        "Nueva fecha y hora de inicio en ISO 8601 con offset "
                        "-06:00, por ejemplo 2026-05-14T16:00:00-06:00"),
        "end": fromai("End",
                      "Nueva fecha y hora de fin en ISO 8601 con offset -06:00, "
                      "calculada como el inicio mas la duracion del servicio"),
        "summary": fromai("Summary",
                          "Servicio y nombre del cliente con el formato "
                          "Servicio - Nombre"),
        "description": fromai("Description",
                              "Nombre del cliente, servicio, precio, numero de "
                              "WhatsApp y notas"),
    }

    # --- 5. Obtener eventos: rango acotado ------------------------------
    obtener = node(f, "Obtener eventos")
    obtener["parameters"]["returnAll"] = False
    obtener["parameters"]["timeMin"] = fromai(
        "After", "Inicio del rango a consultar en ISO 8601 con offset -06:00, por "
        "ejemplo 2026-05-14T00:00:00-06:00")
    obtener["parameters"]["timeMax"] = fromai(
        "Before", "Fin del rango a consultar en ISO 8601 con offset -06:00, por "
        "ejemplo 2026-05-14T23:59:59-06:00. Consulta el dia completo.")

    # --- 6. Reescribir la herramienta de Sheets --------------------------
    sheets = node(f, "Append row in sheet in Google Sheets")
    nuevo = sheet_logger()
    keep_name, keep_id = sheets["name"], sheets["id"]
    sheets.clear()
    sheets.update(nuevo)
    sheets["name"] = keep_name      # rename_node (paso 8) hace el renombrado
    sheets["id"] = keep_id

    # --- 7. Nueva herramienta de escalamiento ---------------------------
    notificar = notifier()
    f["nodes"].append(notificar)
    f["connections"][notificar["name"]] = {
        "ai_tool": [[{"node": "AI Agent", "type": "ai_tool", "index": 0}]]
    }

    # --- 8. Nombres de herramientas legibles para el modelo -------------
    rename_node(f, "Obtener eventos", "Consultar agenda")
    rename_node(f, "Crear evento", "Agendar cita")
    rename_node(f, "Eliminar eventos", "Cancelar cita")
    rename_node(f, "Append row in sheet in Google Sheets",
                "Registrar en hoja de citas")

    # --- 9. Limpieza: URLs con saltos de linea --------------------------
    for n in f["nodes"]:
        p = n.get("parameters", {})
        if isinstance(p.get("url"), str):
            p["url"] = p["url"].strip()

    f["name"] = "Barberia - Agente de citas (Uncensored AI)"
    f["id"] = "barberiaAgenteUncensored"
    f["versionId"] = str(uuid.uuid4())
    return f


# --------------------------------------------------------------------------
# FLUJO 2 - Recordatorios
# --------------------------------------------------------------------------
CODE_REMINDERS = r'''// Calcula las horas de la cita en zona horaria de Mexico y arma los
// recordatorios de 24 h y 1 h. Las horas de la hoja se interpretan como
// America/Mexico_City (UTC-06:00, sin horario de verano).
const TZ_OFFSET = "-06:00";
const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;

return items.map((item) => {
  // La columna de la hoja se llama "D\u00eda " (con acento).
  const rawDate = item.json["D\u00eda "] || item.json["D\u00eda"] ||
    item.json["Dia "] || item.json["Fecha"];
  let rawTime = item.json["Hora"] || "00:00:00";

  if (typeof rawDate !== "string" || typeof rawTime !== "string") {
    throw new Error("Fecha y hora deben ser texto: 'AAAA-MM-DD' y 'HH:MM:SS'");
  }

  const timeParts = rawTime.split(":");
  if (timeParts.length < 2 || timeParts.length > 3) {
    throw new Error(`Hora invalida: ${rawTime}. Usa HH:MM o HH:MM:SS`);
  }
  while (timeParts.length < 3) timeParts.push("00");
  const [hh, mm, ss] = timeParts.map((p) => (p.length === 1 ? "0" + p : p));

  const [year, month, day] = rawDate.trim().split("-");
  if (!year || !month || !day) {
    throw new Error(`Fecha invalida: ${rawDate}. Usa AAAA-MM-DD`);
  }

  // La hora es local de Mexico: se fija el offset explicitamente.
  const cita = new Date(
    `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}` +
    `T${hh}:${mm}:${ss}${TZ_OFFSET}`
  );
  if (isNaN(cita.getTime())) {
    throw new Error(`Fecha invalida: ${rawDate}T${rawTime}`);
  }

  const t = cita.getTime();
  const r24 = new Date(t - DAY_MS);
  const r1 = new Date(t - HOUR_MS);
  const ahora = Date.now();

  item.json.fechaISO = cita.toISOString();
  item.json.fechaLegible = cita.toLocaleString("es-MX", {
    timeZone: "America/Mexico_City",
  });
  item.json.recordatorio24ISO = r24.toISOString();
  item.json.recordatorio1ISO = r1.toISOString();
  item.json.recordatorio24Legible = r24.toLocaleString("es-MX", {
    timeZone: "America/Mexico_City",
  });

  // Si la cita es en menos de 24 h ya no se manda el recordatorio de 24 h.
  item.json.mandar24 = r24.getTime() > ahora;
  item.json.mandar1 = r1.getTime() > ahora;

  // Alias retrocompatible con el flujo original.
  item.json.recordatorioISO = r1.toISOString();
  item.json.recordatorioLegible = r1.toLocaleString("es-MX", {
    timeZone: "America/Mexico_City",
  });

  return item;
});
'''

MSG_24 = (
    "=Hola {{ $('Google Sheets Trigger').item.json.Nombre }}! 💈\n"
    "Te recuerdo tu cita de manana en Barber Chinos:\n"
    "{{ $json.fechaLegible }}\n"
    "Responde *SI* para confirmar o *NO* si necesitas cambiarla."
)

MSG_1 = (
    "=Hola {{ $('Google Sheets Trigger').item.json.Nombre }}! ✂️\n"
    "Tu cita en Barber Chinos es en 1 hora: {{ $json.fechaLegible }}.\n"
    "Te esperamos en Calle Pinzon #574. Si no puedes asistir, responde *NO* para "
    "confirmar tu cancelacion y liberar tu lugar."
)


def flow2_message_nodes():
    """Nodos de envio de recordatorio (Evolution API)."""
    def http(name, text, pos):
        return {
            "parameters": {
                "method": "POST",
                "url": EVO_SERVER + "/message/sendText/hector",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "apikey", "value": EVO_KEY}]},
                "sendBody": True,
                "bodyParameters": {"parameters": [
                    {"name": "number",
                     "value": "={{ $('Google Sheets Trigger').item.json['Numero celular'] }}"},
                    {"name": "text", "value": text},
                    {"name": "delay", "value": "={{ 1000 }}"}]},
                "options": {},
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": pos,
            "id": str(uuid.uuid4()),
            "name": name,
        }
    return (http("RECORDATORIO 24 H", MSG_24, [960, -80]),
            http("RECORDATORIO 1 H", MSG_1, [960, 320]))


def transform_flow2():
    f = load(SRC2)

    # --- 1. Code node: sintaxis rota + bug de zona horaria ---------------
    node(f, "Code")["parameters"]["jsCode"] = CODE_REMINDERS

    # --- 2. Nodos de recordatorio ----------------------------------------
    r24, r1 = flow2_message_nodes()
    f["nodes"].append(r24)
    f["nodes"].append(r1)

    # --- 3. Renombrar el aviso al encargado -------------------------------
    rename_node(f, "Mandar mensaje", "Notificar cita nueva al encargado")

    # --- 5. Filtros: solo esperar y enviar si el momento aun no paso ------
    def if_mandar(name, campo, pos):
        # Se compara contra 'si'/'no' (operador string equals), el mismo
        # formato que ya usa el Switch del flujo original: probado y sin
        # ambiguedad sobre el operador booleano del nodo IF.
        return {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "",
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": str(uuid.uuid4()),
                        "leftValue": "={{ $('Code').item.json." + campo +
                                     " ? 'si' : 'no' }}",
                        "rightValue": "si",
                        "operator": {"type": "string", "operation": "equals"},
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": pos,
            "id": str(uuid.uuid4()),
            "name": name,
        }

    if24 = if_mandar("IF - Toca recordatorio 24 h", "mandar24", [700, 120])
    if1 = if_mandar("IF - Toca recordatorio 1 h", "mandar1", [900, 120])
    f["nodes"].append(if24)
    f["nodes"].append(if1)

    # --- 6. Wait de 24 h ---------------------------------------------------
    # Sin este nodo el recordatorio de 24 h se enviaria AL MOMENTO de agendar.
    # Espera hasta T-24 h; si ese momento ya paso, el IF lo desvia.
    wait24 = {
        "parameters": {
            "resume": "specificTime",
            "dateTime": "={{ $('Code').item.json.recordatorio24ISO }}",
        },
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1.1,
        "position": [1100, 20],
        "id": str(uuid.uuid4()),
        "name": "ESPERAR A 24 H",
        "webhookId": str(uuid.uuid4()),
        "notes": (
            "Espera hasta 24 h antes de la cita. Sin este nodo el mensaje "
            "saldria de inmediato."
        ),
        "notesInFlow": True,
    }
    f["nodes"].append(wait24)

    # --- 7. Cableado ------------------------------------------------------
    c = f["connections"]
    c["Switch"] = {"main": [
        [{"node": "Code1", "type": "main", "index": 0}],
        [{"node": "OBTENER INFO DE CITA ELIMINADA", "type": "main", "index": 0}],
    ]}
    c["Code1"] = {"main": [[
        {"node": "Append or update row in sheet", "type": "main", "index": 0}]]}
    c["Append or update row in sheet"] = {"main": [[
        {"node": "IF - Toca recordatorio 24 h", "type": "main", "index": 0}]]}
    # true -> esperar a T-24h -> mandar 24h -> seguir al wait de 1 h
    # false -> ya no da tiempo, saltar directo al wait de 1 h
    c["IF - Toca recordatorio 24 h"] = {"main": [
        [{"node": "ESPERAR A 24 H", "type": "main", "index": 0}],
        [{"node": "IF - Toca recordatorio 1 h", "type": "main", "index": 0}],
    ]}
    c["ESPERAR A 24 H"] = {"main": [[
        {"node": "RECORDATORIO 24 H", "type": "main", "index": 0}]]}
    c["RECORDATORIO 24 H"] = {"main": [[
        {"node": "IF - Toca recordatorio 1 h", "type": "main", "index": 0}]]}
    c["IF - Toca recordatorio 1 h"] = {"main": [
        [{"node": "Wait", "type": "main", "index": 0}],
        [],
    ]}
    c["Wait"] = {"main": [[
        {"node": "RECORDATORIO 1 H", "type": "main", "index": 0}]]}
    c["RECORDATORIO 1 H"] = {"main": [[]]}
    c["MANDAR RECORDATORIO"] = {"main": [[]]}
    # OJO: 'Notificar cita nueva al encargado' NO es un nodo final. En el
    # original era "Mandar mensaje" y alimentaba al Switch. Si se deja con
    # salida vacia, el Switch queda huerfano y los recordatorios nunca salen.
    c["Notificar cita nueva al encargado"] = {"main": [[
        {"node": "Switch", "type": "main", "index": 0}]]}

    # --- 8. Wait de 1 h ---------------------------------------------------
    wait = node(f, "Wait")
    wait["parameters"] = {
        "resume": "specificTime",
        "dateTime": "={{ $('Code').item.json.recordatorio1ISO }}",
    }
    wait["position"] = [1300, 200]
    wait["name"] = "ESPERAR A 1 H"
    if wait["name"] != "Wait":
        f["connections"]["ESPERAR A 1 H"] = f["connections"].pop("Wait")
        for branches in f["connections"].values():
            for out in branches.values():
                for conns in out:
                    for cc in conns:
                        if cc.get("node") == "Wait":
                            cc["node"] = "ESPERAR A 1 H"

    # --- 9. Switch: salida de respaldo -----------------------------------
    sw = node(f, "Switch")
    sw["parameters"]["options"] = {
        "fallbackOutput": "extra",
        "renameFallbackOutput": "Otro",
    }

    # --- 10. Eliminar el recordatorio viejo -----------------------------
    # 'MANDAR RECORDATORIO' era el nodo original de aviso. Lo sustituyen
    # 'RECORDATORIO 24 H' y 'RECORDATORIO 1 H', asi que dejarlo seria un
    # nodo huerfano (sin entrada ni salida).
    viejos = [n for n in f["nodes"] if n["name"] == "MANDAR RECORDATORIO"]
    if viejos:
        f["nodes"] = [n for n in f["nodes"]
                      if n["name"] != "MANDAR RECORDATORIO"]
        f["connections"].pop("MANDAR RECORDATORIO", None)

    f["name"] = "Barberia - Recordatorios de cita"
    f["id"] = "barberiaRecordatorios"
    f["versionId"] = str(uuid.uuid4())
    return f


# --------------------------------------------------------------------------
def main():
    prompt_text = PROMPT.read_text(encoding="utf-8").strip()
    f1 = transform_flow1(prompt_text)
    dump(f1, OUT1)
    f2 = transform_flow2()
    dump(f2, OUT2)
    print("OK ->", OUT1.name, "|", OUT2.name)
    print("prompt chars:", len(prompt_text))
    for path, flow in ((OUT1, f1), (OUT2, f2)):
        print(path.name, "nodes:", len(flow["nodes"]),
              "connections:", len(flow["connections"]))


if __name__ == "__main__":
    main()