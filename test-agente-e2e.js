// Prueba end-to-end REAL: replica el bucle del AI Agent de n8n contra
// Uncensored AI, usando las MISMAS herramientas y el MISMO system prompt
// que quedaron en el workflow.
//
// La llave se lee de process.env.UNC_KEY y NUNCA se escribe en disco.
const fs = require("fs");
const BASE = "https://api.uncensored.com/api/v1/chat/completions";

const SYSTEM_PROMPT = fs
  .readFileSync("G:/Barberia/prompt-sistema-agente-barberia.txt", "utf8")
  .trim();

// Herramientas equivalentes a las del workflow (Calendar + Sheets + escalar)
const TOOLS = [
  {
    type: "function",
    function: {
      name: "Consultar_agenda",
      description:
        "Consulta las citas ya ocupadas en el calendario de la barberia dentro de un rango de fechas. Usala SIEMPRE antes de agendar o reprogramar.",
      parameters: {
        type: "object",
        properties: {
          After: { type: "string", description: "Inicio del rango en ISO 8601 con offset -06:00" },
          Before: { type: "string", description: "Fin del rango en ISO 8601 con offset -06:00" },
        },
        required: ["After", "Before"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "Agendar_cita",
      description:
        "Agenda una cita nueva. Antes debes verificar disponibilidad con Consultar_agenda. El resumen debe ser 'Servicio - Nombre del cliente'.",
      parameters: {
        type: "object",
        properties: {
          Summary: { type: "string" },
          Description: { type: "string" },
          Start: { type: "string", description: "ISO 8601 con offset -06:00" },
          End: { type: "string", description: "ISO 8601 con offset -06:00" },
        },
        required: ["Summary", "Start", "End"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "Registrar_en_hoja_de_citas",
      description:
        "Registra una fila en la hoja de control. Obligatoria despues de cada accion sobre una cita.",
      parameters: {
        type: "object",
        properties: {
          ID: { type: "string" },
          Estatus: { type: "string", description: "agendado, actualizado o cancelado" },
          Nombre: { type: "string" },
          Servicio: { type: "string" },
          Precio: { type: "string" },
          Dia: { type: "string", description: "AAAA-MM-DD" },
          Hora: { type: "string", description: "HH:MM:SS 24h" },
        },
        required: ["ID", "Estatus", "Nombre", "Servicio", "Dia", "Hora"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "Notificar_al_encargado",
      description:
        "Avisa al encargado por WhatsApp cuando piden descuento, se quejan o piden algo fuera del catalogo.",
      parameters: {
        type: "object",
        properties: { text: { type: "string" } },
        required: ["text"],
      },
    },
  },
];

// --- Simulacion del calendario -------------------------------------------
const CITAS = [
  { id: "ev-1", summary: "Corte desvanecido - Luis", start: "2026-05-14T11:00:00-06:00",
    end: "2026-05-14T11:40:00-06:00" },
];
const REGISTRO = [];
const AVISOS = [];

// Detector de empalmes: si el agente reserva encima de otra cita, se registra.
const EMPALMES = [];

function empalma(a, b) {
  return new Date(a.start) < new Date(b.end) && new Date(b.start) < new Date(a.end);
}

function ejecutar(nombre, args) {
  if (nombre === "Consultar_agenda") {
    return { citas: CITAS };
  }
  if (nombre === "Agendar_cita") {
    // Verificar empalme antes de aceptar (como debe hacer el agente)
    for (const c of CITAS) {
      if (empalma({ start: args.Start, end: args.End }, c)) {
        EMPALMES.push({ nueva: args, con: c });
        return { error: "El horario se empalma con otra cita", cita_existente: c };
      }
    }
    const id = "ev-" + (CITAS.length + 1);
    CITAS.push({ id, summary: args.Summary, start: args.Start, end: args.End });
    return { ok: true, id, summary: args.Summary, start: args.Start, end: args.End };
  }
  if (nombre === "Registrar_en_hoja_de_citas") {
    REGISTRO.push(args);
    return { ok: true, fila: REGISTRO.length };
  }
  if (nombre === "Notificar_al_encargado") {
    AVISOS.push(args.text);
    return { ok: true, avisado: true };
  }
  return { error: "herramienta desconocida" };
}

async function turno(key, modelo, mensajes) {
  const r = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": key },
    body: JSON.stringify({
      model: modelo,
      messages: mensajes,
      tools: TOOLS,
      tool_choice: "auto",
      max_tokens: 900,
    }),
  });
  if (!r.ok) throw new Error("HTTP " + r.status + " " + (await r.text()).slice(0, 200));
  const j = await r.json();
  return j.choices?.[0]?.message;
}

async function correrCaso(key, modelo, titulo, mensajeUsuario) {
  console.log("\n" + "=".repeat(72));
  console.log("CASO: " + titulo);
  console.log("CLIENTE: " + mensajeUsuario);
  console.log("=".repeat(72));
  const mensajes = [
    { role: "system", content: SYSTEM_PROMPT.replace("{{ $now }}", "2026-05-13T10:00:00-06:00") },
    { role: "user", content: mensajeUsuario },
  ];
  const usadas = [];
  for (let paso = 1; paso <= 6; paso++) {
    const msg = await turno(key, modelo, mensajes);
    mensajes.push(msg);
    const calls = msg.tool_calls || [];
    if (!calls.length) {
      console.log(`\n[RESPUESTA FINAL al cliente]\n${msg.content}`);
      return { usadas, respuesta: msg.content, mensajes };
    }
    for (const c of calls) {
      let args = {};
      try { args = JSON.parse(c.function.arguments || "{}"); } catch {}
      usadas.push(c.function.name);
      console.log(`\n[PASO ${paso}] -> ${c.function.name}(${JSON.stringify(args)})`);
      const res = ejecutar(c.function.name, args);
      console.log(`           <- ${JSON.stringify(res).slice(0, 200)}`);
      mensajes.push({ role: "tool", tool_call_id: c.id, content: JSON.stringify(res) });
    }
  }
  return { usadas, respuesta: "(sin respuesta final)", mensajes };
}

(async () => {
  const key = process.env.UNC_KEY;
  if (!key) { console.error("Falta UNC_KEY"); process.exit(2); }
  const modelo = process.argv[2] || "gpt-4o";

  const resultados = [];
  resultados.push(await correrCaso(key, modelo, "Agendar corte",
    "Hola, quiero un corte mañana a las 4 de la tarde, me llamo Juan"));
  resultados.push(await correrCaso(key, modelo, "Preguntar precio",
    "cuanto cuesta el corte de dama y el peinado?"));
  resultados.push(await correrCaso(key, modelo, "Descuento (debe escalar)",
    "me haces precio si llevo a mis 3 hijos?"));
  resultados.push(await correrCaso(key, modelo, "Depilacion (precio por zona)",
    "cuanto cuesta la depilacion?"));
  resultados.push(await correrCaso(key, modelo, "Horario ocupado (no debe empalmar)",
    "quiero corte manana a las 11 de la manana, soy Pedro"));

  console.log("\n" + "#".repeat(72));
  console.log("# RESUMEN");
  console.log("#".repeat(72));
  const esperado = {
    "Agendar corte": ["Consultar_agenda", "Agendar_cita", "Registrar_en_hoja_de_citas"],
    "Preguntar precio": [],
    "Descuento (debe escalar)": ["Notificar_al_encargado"],
    "Depilacion (precio por zona)": [],
    "Horario ocupado (no debe empalmar)": ["Consultar_agenda"],
  };
  let ok = 0;
  const titulos = ["Agendar corte", "Preguntar precio", "Descuento (debe escalar)",
    "Depilacion (precio por zona)", "Horario ocupado (no debe empalmar)"];
  resultados.forEach((r, i) => {
    const t = titulos[i];
    const exp = esperado[t];
    const cumple = exp.every((e) => r.usadas.includes(e));
    if (cumple) ok++;
    console.log(`\n${cumple ? "PASS" : "REVISAR"}  ${t}`);
    console.log(`      herramientas: ${r.usadas.join(" -> ") || "(ninguna)"}`);
    console.log(`      respuesta   : ${String(r.respuesta).replace(/\s+/g, " ").slice(0, 150)}`);
  });
  console.log("\n" + "=".repeat(72));
  console.log(`CASOS CORRECTOS: ${ok} de ${resultados.length}`);
  console.log("Citas en el calendario simulado:", JSON.stringify(CITAS, null, 1));
  console.log("Filas registradas en la hoja:", REGISTRO.length);
  console.log("Avisos al encargado:", AVISOS.length);
  console.log("Empalmes detectados:", EMPALMES.length);
  // Un empalme es un fallo grave: el agente reservo encima de otra cita.
  if (EMPALMES.length === 0) {
    console.log("Sin doble reserva: OK");
  } else {
    console.log("DOBLE RESERVA DETECTADA:", JSON.stringify(EMPALMES));
  }
})();