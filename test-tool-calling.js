// Prueba de soporte de function calling contra la API de Uncensored AI.
// La llave se lee de process.env.UNC_KEY y NUNCA se escribe en disco.
const BASE = "https://api.uncensored.com/api/v1/chat/completions";

const TOOLS = [{
  type: "function",
  function: {
    name: "consultar_agenda",
    description: "Consulta las citas ocupadas de la barberia en un dia.",
    parameters: {
      type: "object",
      properties: {
        dia: { type: "string", description: "Fecha en formato AAAA-MM-DD" },
      },
      required: ["dia"],
    },
  },
}];

const MODELOS = process.argv.slice(2);

async function probar(modelo, header) {
  const body = {
    model: modelo,
    messages: [
      { role: "system", content: "Eres el recepcionista de una barberia." },
      { role: "user", content: "¿Tienes libre el 14 de mayo de 2026? Revisa la agenda." },
    ],
    tools: TOOLS,
    tool_choice: "auto",
    max_tokens: 500,
  };
  const t0 = Date.now();
  try {
    const r = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...header },
      body: JSON.stringify(body),
    });
    const ms = Date.now() - t0;
    const txt = await r.text();
    if (!r.ok) {
      return { modelo, estado: r.status, ms, veredicto: "ERROR HTTP", detalle: txt.slice(0, 200) };
    }
    let j;
    try { j = JSON.parse(txt); } catch { return { modelo, estado: r.status, ms, veredicto: "NO-JSON", detalle: txt.slice(0, 150) }; }
    const msg = j?.choices?.[0]?.message;
    const tc = msg?.tool_calls;
    if (Array.isArray(tc) && tc.length) {
      const f = tc[0].function || {};
      let args = f.arguments;
      try { args = JSON.stringify(JSON.parse(f.arguments)); } catch {}
      return {
        modelo, estado: r.status, ms,
        veredicto: "SOPORTA TOOLS",
        llamo: f.name,
        args,
      };
    }
    return {
      modelo, estado: r.status, ms,
      veredicto: "SIN TOOLS",
      detalle: String(msg?.content ?? "").replace(/\s+/g, " ").slice(0, 120),
    };
  } catch (e) {
    return { modelo, estado: "-", ms: Date.now() - t0, veredicto: "EXCEPCION", detalle: e.message };
  }
}

(async () => {
  const key = process.env.UNC_KEY;
  if (!key) { console.error("Falta UNC_KEY en el entorno."); process.exit(2); }

  // 1) Confirmar que cabecera de autenticacion acepta la API.
  console.log("=== Autenticacion ===");
  for (const [nombre, header] of [
    ["x-api-key", { "x-api-key": key }],
    ["Authorization: Bearer", { Authorization: "Bearer " + key }],
  ]) {
    const r = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...header },
      body: JSON.stringify({ model: "gpt-4o", messages: [{ role: "user", content: "di ok" }], max_tokens: 5 }),
    });
    console.log(`  ${nombre.padEnd(22)} -> HTTP ${r.status}${r.ok ? "  (aceptada)" : "  (rechazada)"}`);
  }

  // 2) Soporte de function calling por modelo.
  console.log("\n=== Soporte de function calling ===");
  const header = { "x-api-key": key };
  const result = [];
  for (const m of MODELOS) {
    const r = await probar(m, header);
    result.push(r);
    console.log(`  ${r.modelo.padEnd(30)} ${r.veredicto.padEnd(15)} ${r.ms}ms  ${r.llamo ? "-> " + r.llamo + "(" + r.args + ")" : (r.detalle || "")}`);
  }

  const ok = result.filter((r) => r.veredicto === "SOPORTA TOOLS");
  console.log("\n" + "=".repeat(60));
  console.log(`SOPORTAN TOOLS: ${ok.length} de ${result.length}`);
  console.log(ok.map((r) => "  - " + r.modelo).join("\n"));
  console.log("\nSIN SOPORTE:");
  console.log(result.filter((r) => r.veredicto !== "SOPORTA TOOLS")
    .map((r) => `  - ${r.modelo} [${r.veredicto}]`).join("\n"));
})();