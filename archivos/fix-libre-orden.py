#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mueve la rama LIBRE al lugar correcto en 'Formatear agenda'.

PROBLEMA del primer intento:
  Inserté la rama LIBRE justo antes de `} else if (entrada.esRango) {`, pero
  ese punto está DENTRO del bloque `if (!eventos.length) { ... }`. Resultado:
  - Si no hay citas, el código retorna antes de llegar a la rama LIBRE.
  - Si hay citas, cae en el `if (!eventos.length)` = false y salta al `else
    if (esRango)`, que imprime la agenda.

  Por eso LIBRE seguía mostrando la agenda.

SOLUCIÓN: mover la rama LIBRE para que se evalúe ANTES de cualquier
comprobación sobre las citas. El comando LIBRE debe calcular huecos
SIEMPRE, haya citas o no (más bien: los huecos dependen de las citas).

Enfoque: reescribir el nodo completo con la estructura correcta:
  1. Calcular `eventos` y helpers.
  2. Si comando === 'LIBRE'  -> calcular huecos y retornar.
  3. Si no hay citas         -> decir que no hay citas.
  4. Si es rango             -> agrupar por día.
  5. Si es un solo día       -> lista + huecos.
"""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"

CODIGO = r"""// Arma la respuesta de WhatsApp con la agenda o los huecos.
//
// ORDEN IMPORTANTE: el comando LIBRE se evalúa PRIMERO, antes de cualquier
// comprobación sobre las citas. Antes estaba dentro del bloque de "no hay
// citas" y nunca llegaba a ejecutarse.
const TZ = 'America/Mexico_City';
const entrada = $('Preparar rango de fechas').first().json;
const todos = $input.all().map(i => i.json);

const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
               'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

function a12h(min) {
  const h = Math.floor(min / 60), m = min % 60;
  const suf = h < 12 ? 'a.m.' : 'p.m.';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, '0')} ${suf}`;
}
function minutos(dt) {
  const m = /T(\d{2}):(\d{2})/.exec(dt || '');
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}
function fechaDe(dt) {
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(dt || '');
  return m ? m[1] : null;
}
function fechaCorta(f) {
  const [a, m, dd] = f.split('-').map(Number);
  const wd = new Date(Date.UTC(a, m - 1, dd)).getUTCDay();
  return `${DIAS[wd]} ${dd} de ${MESES[m - 1]}`;
}
function sumarDias(f, n) {
  const [a, m, dd] = f.split('-').map(Number);
  const t = Date.UTC(a, m - 1, dd) + n * 86400000;
  const g = new Date(t);
  return `${g.getUTCFullYear()}-${String(g.getUTCMonth() + 1).padStart(2, '0')}-${String(g.getUTCDate()).padStart(2, '0')}`;
}
function nombreCliente(e) {
  const m = /Nombre:\s*([^\n]+)/i.exec(e.desc);
  if (m) return m[1].trim();
  const partes = e.resumen.split(/\s+[—–-]\s+/);
  return partes.length > 1 ? partes[partes.length - 1].trim() : e.resumen;
}
function servicio(e) {
  const partes = e.resumen.split(/\s+[—–-]\s+/);
  return partes.length > 1 ? partes[0].trim() : '';
}
function precio(e) {
  const m = /\$\s*(\d+)|Precio\s*:\s*(\d+)/i.exec(e.desc);
  return m ? Number(m[1] || m[2]) : null;
}

// Normaliza los eventos del calendario
const eventos = todos.filter(e => e && (e.summary || e.start))
  .map(e => {
    const dt = e.start ? (e.start.dateTime || e.start.date || '') : '';
    return {
      ini: e.start && e.start.date && !e.start.dateTime ? -1 : minutos(dt),
      fin: e.end ? minutos(e.end.dateTime || e.end.date || '') : null,
      fecha: fechaDe(dt),
      resumen: e.summary || '',
      desc: e.description || '',
    };
  })
  .filter(e => e.ini !== null && e.ini >= 0 && e.fecha)
  .sort((a, b) => (a.fecha + String(a.ini).padStart(4, '0'))
        .localeCompare(b.fecha + String(b.ini).padStart(4, '0')));

const ahora = new Date(entrada.ahoraISO);
const AHOY = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(ahora);
const pA = {};
for (const { type, value } of new Intl.DateTimeFormat('en-CA',
  { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false })
  .formatToParts(ahora)) pA[type] = value;
const ahoraMin = Number(pA.hour === '24' ? '0' : pA.hour) * 60 + Number(pA.minute);

// ------------------------------------------------------------------
// 1. LIBRE -> huecos disponibles. PRIMERO, siempre.
// ------------------------------------------------------------------
if (entrada.comando === 'LIBRE') {
  const dur = 40;                      // duración de referencia
  const AP = 10 * 60, CI = 20 * 60;    // 10:00 a 20:00
  const porFecha = {};
  for (const e of eventos) (porFecha[e.fecha] = porFecha[e.fecha] || []).push(e);

  const l = [`*Huecos disponibles (${dur} min)*`];
  let total = 0;

  for (let f = entrada.desde; f <= entrada.hasta; f = sumarDias(f, 1)) {
    const dow = new Date(f + 'T12:00:00Z').getUTCDay();
    if (dow === 0) continue;                       // domingo, cerrado
    const ocupados = porFecha[f] || [];
    const libres = [];
    for (let t = AP; t + dur <= CI; t += 30) {
      const fin = t + dur;
      const choca = ocupados.some(e => e.fin !== null &&
        t < e.fin + 10 && e.ini - 10 < fin);
      if (choca) continue;
      if (f === AHOY && t <= ahoraMin) continue;
      libres.push(t);
      if (libres.length >= 8) break;
    }
    total += libres.length;
    l.push('');
    l.push(`*${f === AHOY ? 'Hoy' : fechaCorta(f)}*`);
    l.push(libres.length ? libres.map(a12h).join(', ') : 'Sin huecos libres.');
  }

  l.push('');
  l.push(total ? `Total: *${total} huecos* disponibles.`
               : 'No hay huecos en el periodo.');
  return [{ json: { respuesta: l.join('\n') } }];
}

// ------------------------------------------------------------------
// 2. Sin citas -> decirlo
// ------------------------------------------------------------------
const lineas = [`*Agenda de ${entrada.titulo}*`];
if (!eventos.length) {
  lineas.push('');
  lineas.push('No hay citas agendadas en ese periodo.');
  return [{ json: { respuesta: lineas.join('\n') } }];
}

// ------------------------------------------------------------------
// 3. Rango de varios días -> agrupar por día
// ------------------------------------------------------------------
if (entrada.esRango) {
  const porDia = {};
  for (const e of eventos) (porDia[e.fecha] = porDia[e.fecha] || []).push(e);
  let totalP = 0, conPrecio = 0;
  for (const f of Object.keys(porDia).sort()) {
    lineas.push('');
    lineas.push(`*${fechaCorta(f)}*`);
    for (const e of porDia[f]) {
      const pr = precio(e);
      if (pr !== null) { totalP += pr; conPrecio++; }
      let x = `${a12h(e.ini)} ${nombreCliente(e)}`;
      const sv = servicio(e);
      if (sv) x += ` — ${sv}`;
      lineas.push(x);
    }
  }
  lineas.push('');
  lineas.push(`*${eventos.length} cita${eventos.length === 1 ? '' : 's'} en el periodo` +
    (conPrecio ? ` · $${totalP} estimado` : '') + '*');
  return [{ json: { respuesta: lineas.join('\n') } }];
}

// ------------------------------------------------------------------
// 4. Un solo día -> lista + huecos
// ------------------------------------------------------------------
let totalD = 0, conP = 0;
for (const e of eventos) {
  const pr = precio(e);
  if (pr !== null) { totalD += pr; conP++; }
  let x = `${a12h(e.ini)} ${nombreCliente(e)}`;
  const sv = servicio(e);
  if (sv) x += ` — ${sv}`;
  if (pr !== null) x += ` · $${pr}`;
  lineas.push(x);
}
lineas.push('');
lineas.push(`*${eventos.length} cita${eventos.length === 1 ? '' : 's'}` +
  (conP ? ` · $${totalD} estimado` : '') + '*');

const dur2 = 40, libres2 = [];
for (let t = 600; t + dur2 <= 1200; t += 30) {
  const fin = t + dur2;
  const choca = eventos.some(e => e.fin !== null &&
    t < e.fin + 10 && e.ini - 10 < fin);
  if (choca) continue;
  if (entrada.desde === AHOY && t <= ahoraMin) continue;
  libres2.push(t);
  if (libres2.length >= 6) break;
}
lineas.push(libres2.length
  ? `Huecos: ${libres2.map(a12h).join(', ')}`
  : 'Sin huecos disponibles ese día.');

return [{ json: { respuesta: lineas.join('\n') } }];"""


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-libre2.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    # Verificar sintaxis ANTES de subir
    import subprocess
    ruta = r"G:\Barberia\archivos\_chk_agenda2.js"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("(async function () {\n" + CODIGO + "\n})();\n")
    p = subprocess.run([r"C:\Program Files\nodejs\node.exe", "--check", ruta],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    os.remove(ruta)
    if p.returncode != 0:
        print("SINTAXIS INVALIDA, no subo nada:")
        print((p.stderr or "")[:400])
        return 1
    print("  sintaxis JS: OK")

    n = next((x for x in wf["nodes"] if x["name"] == "Formatear agenda"), None)
    if not n:
        print("no existe 'Formatear agenda'")
        return 1
    n["parameters"]["jsCode"] = CODIGO

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificar el orden
    st4, fin = api("GET", f"/workflows/{WID}")
    n2 = next(x for x in fin["nodes"] if x["name"] == "Formatear agenda")
    c = n2["parameters"]["jsCode"]
    i_libre = c.find("entrada.comando === 'LIBRE'")
    i_vacio = c.find("if (!eventos.length)")
    i_rango = c.find("if (entrada.esRango)")
    print("\n=== ORDEN DE LAS RAMAS ===")
    print(f"  LIBRE  en posicion {i_libre}")
    print(f"  vacio  en posicion {i_vacio}")
    print(f"  rango  en posicion {i_rango}")
    ok = 0 < i_libre < i_vacio < i_rango
    print(f"  {'OK  ' if ok else 'MAL '} LIBRE va ANTES de 'no hay citas' "
          f"y de 'esRango'")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())