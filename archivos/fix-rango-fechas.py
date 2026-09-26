#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla 'Preparar rango de fechas': siempre respondía como HOY.

BUG ENCONTRADO (ejecuciones 644/645/646):
  HOY, SEMANA y LIBRE devolvieron EXACTAMENTE el mismo texto
  ("Agenda de hoy, viernes 25 de septiembre").

CAUSA:
  El nodo leía el comando así:
      const comando = String(item.comando || 'HOY').toUpperCase();
  pero `item.comando` no existe: el Router de comandos enruta por el
  mensaje, no añade un campo. Al ser undefined, SIEMPRE caía en el
  valor por defecto 'HOY'.

SOLUCIÓN:
  Extraer el comando del propio mensaje (message_content), que es lo que
  el router usa para enrutar. Así cada comando recibe su rango real.

Además se mejora el formateo para rangos de varios días: antes, con
SEMANA, solo listaba el día de hoy en vez de agrupar por día.
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


# --- Nuevo código de 'Preparar rango de fechas' -------------------------
CODIGO_RANGO = r"""// Calcula el rango a consultar en hora de MEXICO (UTC-6 fijo).
//
// OJO: el comando se saca del MENSAJE, no de un campo `comando`. El Router
// enruta por el texto y no añade campos; leer item.comando devolvía
// undefined y todo caía en 'HOY' por defecto.
const TZ = 'America/Mexico_City';
const item = $input.first().json;
const texto = String(item.message_content || '').trim();
const comando = (texto.split(/\s+/)[0] || 'HOY').toUpperCase();

function fechaMexico(d) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(d);
}
function sumarDias(f, n) {
  const [a, m, dd] = f.split('-').map(Number);
  const t = Date.UTC(a, m - 1, dd) + n * 86400000;
  const g = new Date(t);
  return `${g.getUTCFullYear()}-${String(g.getUTCMonth() + 1).padStart(2, '0')}-${String(g.getUTCDate()).padStart(2, '0')}`;
}
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
               'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
function fechaCorta(f) {
  const [a, m, dd] = f.split('-').map(Number);
  const wd = new Date(Date.UTC(a, m - 1, dd)).getUTCDay();
  return `${DIAS[wd]} ${dd} de ${MESES[m - 1]}`;
}

const ahora = new Date();
const hoy = fechaMexico(ahora);
let desde = hoy, hasta = hoy, titulo = '';

if (comando === 'SEMANA') {
  hasta = sumarDias(hoy, 7);
  titulo = `los próximos 7 días (desde ${fechaCorta(hoy)})`;
} else if (comando === 'LIBRE') {
  hasta = sumarDias(hoy, 2);
  titulo = 'hoy y los siguientes 2 días';
} else if (comando === 'MAÑANA' || comando === 'MANANA') {
  desde = sumarDias(hoy, 1); hasta = desde;
  titulo = `mañana, ${fechaCorta(desde)}`;
} else if (comando === 'HOY') {
  titulo = `hoy, ${fechaCorta(hoy)}`;
} else {
  // Por si LIBRE/SEMANA llegan con otro alias
  titulo = `hoy, ${fechaCorta(hoy)}`;
}

return [{ json: {
  comando,
  desde, hasta, titulo,
  esRango: desde !== hasta,
  timeMin: `${desde}T00:00:00-06:00`,
  timeMax: `${hasta}T23:59:00-06:00`,
  ahoraISO: ahora.toISOString(),
} }];"""


# --- Nuevo código de 'Formatear agenda' (agrupa por día) ----------------
CODIGO_FORMATO = r"""// Arma la respuesta de WhatsApp con la agenda del rango.
// Si el rango cubre varios días, agrupa las citas por día.
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

const lineas = [`*Agenda de ${entrada.titulo}*`];

if (!eventos.length) {
  lineas.push('');
  lineas.push('No hay citas agendadas en ese periodo.');
} else if (entrada.esRango) {
  // Agrupar por día (solo los días que tienen citas)
  const porDia = {};
  for (const e of eventos) (porDia[e.fecha] = porDia[e.fecha] || []).push(e);
  let total = 0, conPrecio = 0;
  for (const f of Object.keys(porDia).sort()) {
    lineas.push('');
    lineas.push(`*${fechaCorta(f)}*`);
    for (const e of porDia[f]) {
      const pr = precio(e);
      if (pr !== null) { total += pr; conPrecio++; }
      let l = `${a12h(e.ini)} ${nombreCliente(e)}`;
      const sv = servicio(e);
      if (sv) l += ` — ${sv}`;
      lineas.push(l);
    }
  }
  lineas.push('');
  lineas.push(`*${eventos.length} cita${eventos.length === 1 ? '' : 's'} en el periodo` +
    (conPrecio ? ` · $${total} estimado` : '') + '*');
} else {
  let total = 0, conPrecio = 0;
  for (const e of eventos) {
    const pr = precio(e);
    if (pr !== null) { total += pr; conPrecio++; }
    let l = `${a12h(e.ini)} ${nombreCliente(e)}`;
    const sv = servicio(e);
    if (sv) l += ` — ${sv}`;
    if (pr !== null) l += ` · $${pr}`;
    lineas.push(l);
  }
  lineas.push('');
  lineas.push(`*${eventos.length} cita${eventos.length === 1 ? '' : 's'}` +
    (conPrecio ? ` · $${total} estimado` : '') + '*');

  // Huecos libres del día
  const dur = 40;
  const ahora = new Date(entrada.ahoraISO);
  const p = {};
  for (const { type, value } of new Intl.DateTimeFormat('en-CA',
    { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false })
    .formatToParts(ahora)) p[type] = value;
  const ahoraMin = Number(p.hour === '24' ? '0' : p.hour) * 60 + Number(p.minute);
  const hoy = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(ahora);
  const libres = [];
  for (let t = 600; t + dur <= 1200; t += 30) {
    const fin = t + dur;
    const choca = eventos.some(e => e.fin !== null &&
      t < e.fin + 10 && e.ini - 10 < fin);
    if (choca) continue;
    if (entrada.desde === hoy && t <= ahoraMin) continue;
    libres.push(t);
    if (libres.length >= 6) break;
  }
  lineas.push(libres.length
    ? `Huecos: ${libres.map(a12h).join(', ')}`
    : 'Sin huecos disponibles ese día.');
}

return [{ json: { respuesta: lineas.join('\n') } }];"""


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-rango.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    n1 = next((n for n in wf["nodes"]
               if n["name"] == "Preparar rango de fechas"), None)
    n2 = next((n for n in wf["nodes"] if n["name"] == "Formatear agenda"), None)
    if not n1 or not n2:
        print("no encontré los nodos")
        return 1

    n1["parameters"]["jsCode"] = CODIGO_RANGO
    n2["parameters"]["jsCode"] = CODIGO_FORMATO
    print("  Preparar rango de fechas: lee el comando del mensaje")
    print("  Formatear agenda: agrupa por día en rangos")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\nPUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificar sintaxis del JS con node
    import subprocess
    for nombre, cod in (("rango", CODIGO_RANGO), ("formato", CODIGO_FORMATO)):
        ruta = rf"G:\Barberia\archivos\_chk_{nombre}.js"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("function _c(){ const $input={first:()=>({json:{}})},"
                    "$=()=>({first:()=>({json:{}})});" + cod +
                    "\ntry { _c(); } catch(e) { if(!/is not defined|Cannot read/.test(e.message)) { console.error('SYNTAX', e.message); process.exit(1);} }"
                    "\nconsole.log('sintaxis OK');\n")
        p = subprocess.run([r"C:\Program Files\nodejs\node.exe", ruta],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        print(f"  {nombre}: {(p.stdout or p.stderr).strip()[:80]}")
        os.remove(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())