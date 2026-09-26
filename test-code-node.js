// Prueba de comportamiento del Code node del flujo 2 con casos reales.
const fs = require("fs");

// El cuerpo del Code node, extraido del workflow generado.
const flow = JSON.parse(
  fs.readFileSync("G:/Barberia/BarberiaAgenteFLUJO-2-RECORDATORIOS.json", "utf8")
);
const code = flow.nodes.find((n) => n.name === "Code").parameters.jsCode;
const run = new Function("items", code);

let pass = 0;
let fail = 0;
function check(cond, msg) {
  if (cond) {
    pass++;
    console.log("  PASS  " + msg);
  } else {
    fail++;
    console.log("  FAIL  " + msg);
  }
}

// Offset real de Mexico: -06:00 todo el ano (sin horario de verano desde 2022).
console.log("=== Caso 1: cita futura (permite ambos recordatorios) ===");
const futuro = new Date(Date.now() + 5 * 24 * 3600 * 1000);
const iso = new Date(futuro.getTime() - 6 * 3600 * 1000)
  .toISOString()
  .slice(0, 10);
const out1 = run([{ json: { "Día ": iso, Hora: "16:00:00" } }])[0].json;
check(out1.mandar24 === true, "mandar24 = true con 5 dias de anticipacion");
check(out1.mandar1 === true, "mandar1 = true con 5 dias de anticipacion");
check(out1.fechaISO.endsWith("Z"), "fechaISO en UTC: " + out1.fechaISO);
// 16:00 en Mexico (-06:00) = 22:00 UTC
check(out1.fechaISO.includes("T22:00:00"), "16:00 -06:00 se convierte a 22:00Z");
const d24 = new Date(out1.recordatorio24ISO);
const cita = new Date(out1.fechaISO);
check(cita - d24 === 24 * 3600 * 1000, "El recordatorio de 24 h es exactamente 24 h antes");
const d1 = new Date(out1.recordatorio1ISO);
check(cita - d1 === 3600 * 1000, "El recordatorio de 1 h es exactamente 1 h antes");

console.log("\n=== Caso 2: cita en 3 horas (solo recordatorio de 1 h) ===");
const pronto = new Date(Date.now() + 3 * 3600 * 1000);
const iso2 = new Date(pronto.getTime() - 6 * 3600 * 1000)
  .toISOString()
  .slice(0, 10);
const hora2 = new Date(pronto.getTime() - 6 * 3600 * 1000)
  .toISOString()
  .slice(11, 19);
const out2 = run([{ json: { "Día ": iso2, Hora: hora2 } }])[0].json;
check(out2.mandar24 === false, "mandar24 = false (ya no se puede avisar con 24 h)");
check(out2.mandar1 === true, "mandar1 = true (la cita es en 3 h)");

console.log("\n=== Caso 3: hora de un digito y nombre de campo sin espacio ===");
const out3 = run([{ json: { "Día": iso, Hora: "9:05" } }])[0].json;
check(out3.fechaISO.includes("T15:05:00"), "9:05 y 'Dia' sin espacio -> 15:05Z (hora rellenada con cero)");

console.log("\n=== Caso 4: fecha invalida debe fallar ===");
try {
  run([{ json: { "Día ": "no-es-fecha", Hora: "10:00:00" } }]);
  check(false, "Fecha invalida lanza error");
} catch (e) {
  check(/invalida/i.test(e.message), "Fecha invalida lanza error: " + e.message);
}

console.log("\n=== Caso 5: hora invalida debe fallar ===");
try {
  run([{ json: { "Día ": iso, Hora: "25-99" } }]);
  check(false, "Hora invalida lanza error");
} catch (e) {
  check(true, "Hora invalida lanza error: " + e.message);
}

console.log("\n" + "=".repeat(50));
if (fail) {
  console.log(`RESULTADO: ${fail} de ${pass + fail} FALLARON`);
  process.exit(1);
}
console.log(`RESULTADO: ${pass} de ${pass} PASARON`);