#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera los nodos de los comandos del dueño para el flujo del agente.

ENRUTADO (ya existe el router con 12 salidas + fallback):
  Router de comandos
     COMANDOS  -> Armar respuesta -> Responder        (ya funcionando)
     HOY --+
     MANANA+---> 1 nodo compartido: preparar rango -> Calendar -> formatear
     SEMANA+
     LIBRE --+
     BLOQUEAR -+
     CERRAR  --+-> 1 nodo compartido: parsear -> Calendar (crear/borrar)
     ABRIR   --+
     CLIENTE  --> Postgres -> formatear ficha
     PAUSA    --> Postgres -> responder
     PRECIO   --> Postgres -> responder
     ESTADO   --> Postgres -> formatear salud
     No es comando (fallback) -> IF - No es del bot   (ya funcionando)

Se comparten nodos donde el trabajo es el mismo, para no multiplicar
nodos. El comando original viaja en el campo `comando`.

Todos los textos usan formato WhatsApp: *un asterisco*, nunca **dos**.
"""
import json
import sys
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CAL = "b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c09143c@group.calendar.google.com"
CAL_NOMBRE = "BARBER"
CRED_CAL = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                        "name": "Google Calendar account"}}
CRED_PG = {"postgres": {"id": "NUrqrDWN8OsBFmgV", "name": "Postgres account"}}


def nid():
    return str(uuid.uuid4())


def nodo_set(nombre, asignaciones, pos, notas=None):
    return {
        "parameters": {
            "assignments": {"assignments": [
                {"id": nid(), "name": k,
                 "value": v, "type": "string"}
                for k, v in asignaciones.items()]},
            "options": {},
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": pos,
        "id": nid(),
        "name": nombre,
        **({"notes": notas, "notesInFlow": True} if notas else {}),
    }


def nodo_code(nombre, codigo, pos, notas=None):
    return {
        "parameters": {"jsCode": codigo},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": pos,
        "id": nid(),
        "name": nombre,
        **({"notes": notas, "notesInFlow": True} if notas else {}),
    }


def nodo_cal_get(nombre, pos):
    return {
        "parameters": {
            "operation": "getAll",
            "calendar": {"__rl": True, "value": CAL, "mode": "list",
                         "cachedResultName": CAL_NOMBRE},
            "returnAll": False,
            "limit": 50,
            "timeMin": "={{ $json.timeMin }}",
            "timeMax": "={{ $json.timeMax }}",
            "options": {"singleEvents": True, "orderBy": "startTime"},
        },
        "type": "n8n-nodes-base.googleCalendar",
        "typeVersion": 1.3,
        "position": pos,
        "id": nid(),
        "name": nombre,
        "credentials": CRED_CAL,
    }


def nodo_cal_create(nombre, pos):
    return {
        "parameters": {
            "operation": "create",
            "calendar": {"__rl": True, "value": CAL, "mode": "list",
                         "cachedResultName": CAL_NOMBRE},
            "start": "={{ $json.inicioISO }}",
            "end": "={{ $json.finISO }}",
            "additionalFields": {
                "summary": "={{ $json.summary }}",
                "description": "={{ $json.description }}",
            },
            "options": {},
        },
        "type": "n8n-nodes-base.googleCalendar",
        "typeVersion": 1.3,
        "position": pos,
        "id": nid(),
        "name": nombre,
        "credentials": CRED_CAL,
    }


def nodo_pg(nombre, query, pos, opciones=None):
    return {
        "parameters": {
            "operation": "executeQuery",
            "query": query,
            "options": opciones or {},
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": pos,
        "id": nid(),
        "name": nombre,
        "credentials": CRED_PG,
    }


def construir():
    nodos = []

    # ------------------------------------------------------------------
    # A. HOY / MANANA / SEMANA / LIBRE
    # ------------------------------------------------------------------
    nodos.append(nodo_code("Preparar rango de fechas", r"""// Calcula el rango a consultar en hora de MEXICO (UTC-6 fijo).
// OJO: si se usara la hora del servidor (UTC), a las 22:00 de Mexico
// "HOY" devolveria el dia siguiente.
const TZ = 'America/Mexico_City';
const item = $input.first().json;
const comando = String(item.comando || 'HOY').toUpperCase();

function fechaMexico(d) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(d);
}
function sumarDias(f, n) {
  const [a, m, dd] = f.split('-').map(Number);
  const t = Date.UTC(a, m - 1, dd) + n * 86400000;
  const g = new Date(t);
  return `${g.getUTCFullYear()}-${String(g.getUTCMonth() + 1).padStart(2, '0')}-${String(g.getUTCDate()).padStart(2, '0')}`;
}
function fechaCorta(f) {
  const [a, m, dd] = f.split('-').map(Number);
  const dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
  const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const wd = new Date(Date.UTC(a, m - 1, dd)).getUTCDay();
  return `${dias[wd]} ${dd} de ${meses[m - 1]}`;
}

const ahora = new Date();
const hoy = fechaMexico(ahora);
let desde = hoy, hasta = hoy, titulo = '';

if (comando === 'HOY') {
  titulo = `hoy, ${fechaCorta(hoy)}`;
} else if (comando === 'MAÑANA' || comando === 'MANANA') {
  desde = sumarDias(hoy, 1); hasta = desde;
  titulo = `mañana, ${fechaCorta(desde)}`;
} else if (comando === 'SEMANA') {
  hasta = sumarDias(hoy, 7);
  titulo = `los próximos 7 días (desde ${fechaCorta(hoy)})`;
} else if (comando === 'LIBRE') {
  hasta = sumarDias(hoy, 2);
  titulo = 'hoy y los siguientes 2 días';
}

return [{ json: {
  comando,
  desde, hasta, titulo,
  timeMin: `${desde}T00:00:00-06:00`,
  timeMax: `${hasta}T23:59:00-06:00`,
  ahoraISO: ahora.toISOString(),
} }];""", [-520, 560],
        "Traduce HOY / MAÑANA / SEMANA / LIBRE al rango ISO en hora de\n"
        "México (UTC-6). El offset es fijo: México no usa horario de verano."))

    nodos.append(nodo_cal_get("Leer agenda del rango", [-320, 560]))

    nodos.append(nodo_code("Formatear agenda", r"""// Arma la respuesta de WhatsApp con la agenda del rango.
const TZ = 'America/Mexico_City';
const entrada = $('Preparar rango de fechas').first().json;
const todos = $input.all().map(i => i.json);

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
function esTodoElDia(s) { return !!(s && s.date && !s.dateTime); }

// Google Calendar puede devolver los eventos vacios (dia sin citas)
const eventos = todos.filter(e => e && (e.summary || e.start))
  .map(e => ({
    ini: e.start ? (esTodoElDia(e.start) ? -1 : minutos(e.start.dateTime)) : null,
    fin: e.end ? minutos(e.end.dateTime) : null,
    resumen: e.summary || '',
    desc: e.description || '',
  }))
  .filter(e => e.ini !== null && e.ini >= 0)
  .sort((a, b) => a.ini - b.ini);

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
  lineas.push('No hay citas agendadas.');
} else {
  let total = 0, conPrecio = 0;
  for (const e of eventos) {
    const cli = nombreCliente(e);
    const sv = servicio(e);
    const pr = precio(e);
    if (pr !== null) { total += pr; conPrecio++; }
    let l = `${a12h(e.ini)} ${cli}`;
    if (sv) l += ` — ${sv}`;
    if (pr !== null) l += ` · $${pr}`;
    lineas.push(l);
  }
  lineas.push('');
  lineas.push(`*${eventos.length} cita${eventos.length === 1 ? '' : 's'}` +
    (conPrecio ? ` · $${total} estimado` : '') + '*');

  // Huecos libres: solo tiene sentido si el rango es de un dia
  if (entrada.desde === entrada.hasta) {
    const dur = 40, AP = 600, CI = 1200;
    const ahora = new Date(entrada.ahoraISO);
    const p = {};
    for (const { type, value } of new Intl.DateTimeFormat('en-CA',
      { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false })
      .formatToParts(ahora)) p[type] = value;
    const ahoraMin = Number(p.hour === '24' ? '0' : p.hour) * 60 + Number(p.minute);
    const hoy = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(ahora);
    const libres = [];
    for (let t = AP; t + dur <= CI; t += 30) {
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
}

return [{ json: { respuesta: lineas.join('\n') } }];""", [-120, 560]))

    # ------------------------------------------------------------------
    # B. BLOQUEAR / CERRAR / ABRIR
    # ------------------------------------------------------------------
    nodos.append(nodo_code("Parsear bloqueo", r"""// Interpreta BLOQUEAR / CERRAR / ABRIR y prepara el evento de Calendar.
const item = $input.first().json;
const texto = String(item.message_content || '').trim();
const partes = texto.split(/\s+/);
const comando = (partes[0] || '').toUpperCase();
const resto = partes.slice(1);

const TZ = 'America/Mexico_City';
function fechaMexico(d) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(d);
}
function sumarDias(f, n) {
  const [a, m, dd] = f.split('-').map(Number);
  const t = Date.UTC(a, m - 1, dd) + n * 86400000;
  const g = new Date(t);
  return `${g.getUTCFullYear()}-${String(g.getUTCMonth() + 1).padStart(2, '0')}-${String(g.getUTCDate()).padStart(2, '0')}`;
}
const MESES = { ene: 1, feb: 2, mar: 3, abr: 4, may: 5, jun: 6,
                jul: 7, ago: 8, sep: 9, oct: 10, nov: 11, dic: 12 };
const ahora = new Date();
const hoy = fechaMexico(ahora);

function fallo(msg) {
  return [{ json: { ...item, respuesta: msg, saltar: true } }];
}

if (comando === 'BLOQUEAR') {
  let fecha = hoy, idx = 0;
  if (resto[0] && /^\d{4}-\d{2}-\d{2}$/.test(resto[0])) { fecha = resto[0]; idx = 1; }
  const rango = resto[idx];
  if (!rango || !/^\d{1,2}:\d{2}-\d{1,2}:\d{2}$/.test(rango)) {
    return fallo('Formato: *BLOQUEAR 14:00-15:30 motivo*');
  }
  const [d, h] = rango.split('-');
  const aMin = s => { const [a, b] = s.split(':').map(Number); return a * 60 + b; };
  if (aMin(h) <= aMin(d)) {
    return fallo('La hora final debe ser mayor que la inicial.');
  }
  const motivo = resto.slice(idx + 1).join(' ') || 'ocupado';
  return [{ json: { ...item, comando, saltar: false, accion: 'crear',
    fecha, inicioISO: `${fecha}T${d.padStart(5, '0')}:00-06:00`,
    finISO: `${fecha}T${h.padStart(5, '0')}:00-06:00`,
    summary: `Bloqueado: ${motivo}`,
    description: 'Bloqueo creado por el dueño desde WhatsApp',
    ok_msg: `Listo. Bloqueé *${d} a ${h}* (${motivo}).` } }];
}

if (comando === 'CERRAR' || comando === 'ABRIR') {
  const arg = resto.join(' ').trim();
  if (!arg) return fallo(`Formato: *${comando} 24 dic*`);
  let fecha = null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(arg)) fecha = arg;
  else if (/^hoy$/i.test(arg)) fecha = hoy;
  else if (/^mañana$/i.test(arg)) fecha = sumarDias(hoy, 1);
  else {
    const m = /^(\d{1,2})\s+([a-záéíóú]{3,})$/i.exec(arg);
    if (m) {
      const mes = MESES[m[2].slice(0, 3).toLowerCase()];
      const dia = Number(m[1]);
      if (mes) {
        const p = {};
        for (const { type, value } of new Intl.DateTimeFormat('en-CA',
          { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
          .formatToParts(ahora)) p[type] = value;
        let anio = Number(p.year);
        if (mes < Number(p.month) || (mes === Number(p.month) && dia < Number(p.day))) anio++;
        fecha = `${anio}-${String(mes).padStart(2, '0')}-${String(dia).padStart(2, '0')}`;
      }
    }
  }
  if (!fecha) return fallo('No entendí la fecha. Ejemplo: *CERRAR 24 dic*');
  const esCerrar = comando === 'CERRAR';
  return [{ json: { ...item, comando, saltar: false, accion: 'crear',
    fecha,
    inicioISO: `${fecha}T00:00:00-06:00`,
    finISO: `${fecha}T23:59:00-06:00`,
    summary: esCerrar ? 'CERRADO' : 'ABIERTO',
    description: esCerrar ? 'Día cerrado desde WhatsApp' : 'Día reabierto desde WhatsApp',
    ok_msg: esCerrar
      ? `Listo. Marqué el *${fecha}* como cerrado.`
      : `Listo. El *${fecha}* vuelve a estar abierto.` } }];
}

return fallo('Comando de bloqueo no reconocido.');""", [-520, 760],
        "Interpreta BLOQUEAR / CERRAR / ABRIR y deja listo el evento.\n"
        "Si el formato es inválido responde con la ayuda y marca saltar=true."))

    nodos.append(nodo_cal_create("Crear bloqueo en calendario", [-320, 760]))

    nodos.append(nodo_set("Respuesta de bloqueo", {
        "respuesta": "={{ $json.ok_msg }}",
    }, [-120, 760]))

    # ------------------------------------------------------------------
    # C. CLIENTE
    # ------------------------------------------------------------------
    nodos.append(nodo_code("Buscar cliente", r"""// Extrae el numero a buscar del comando CLIENTE.
const item = $input.first().json;
const partes = String(item.message_content || '').trim().split(/\s+/);
const busqueda = (partes[1] || '').replace(/\D/g, '');
return [{ json: { ...item, busqueda, busquedaOk: busqueda.length >= 6 } }];""",
        [-520, 960]))

    nodos.append(nodo_pg("Leer ficha del cliente", """SELECT
  cl.nombre,
  cl.etiqueta,
  cl.visitas,
  cl.no_shows,
  cl.ticket_promedio,
  cl.servicio_habitual,
  to_char(cl.ultima_visita AT TIME ZONE 'America/Mexico_City', 'DD/MM/YYYY') AS ultima,
  cl.nota_interna,
  (SELECT count(*) FROM barber_citas c
    WHERE c.jid = cl.jid AND c.inicio > now()
      AND c.estado IN ('agendado','confirmado')) AS futuras
FROM barber_clientes cl
WHERE right(regexp_replace(split_part(cl.jid,'@',1),'\\D','','g'),10)
        = right('{{ $json.busqueda }}',10)
   OR right(regexp_replace(cl.telefono,'\\D','','g'),10)
        = right('{{ $json.busqueda }}',10)
LIMIT 1;""", [-320, 960]))

    nodos.append(nodo_code("Formatear ficha", r"""// Arma la ficha del cliente en formato WhatsApp.
const item = $('Buscar cliente').first().json;
const filas = $input.all().map(i => i.json).filter(f => f && f.nombre);

if (!item.busquedaOk) {
  return [{ json: { respuesta: 'Formato: *CLIENTE 4521206246*' } }];
}
if (!filas.length) {
  return [{ json: { respuesta: `No encontré ninguna ficha para el *${item.busqueda}*.\n\nEse número no ha agendado con nosotros.` } }];
}
const c = filas[0];
const l = [`*${c.nombre}*`];
if (c.etiqueta) l.push(`Etiqueta: ${c.etiqueta}`);
l.push(`Visitas: ${c.visitas || 0}`);
if (Number(c.no_shows) > 0) l.push(`No-shows: ${c.no_shows}`);
if (c.ticket_promedio) l.push(`Ticket promedio: $${Math.round(c.ticket_promedio)}`);
if (c.servicio_habitual) l.push(`Suele pedir: ${c.servicio_habitual}`);
if (c.ultima) l.push(`Última visita: ${c.ultima}`);
l.push(`Citas próximas: ${c.futuras || 0}`);
if (c.nota_interna) l.push(`Nota: ${c.nota_interna}`);
return [{ json: { respuesta: l.join('\n') } }];""", [-120, 960]))

    # ------------------------------------------------------------------
    # D. PAUSA
    # ------------------------------------------------------------------
    nodos.append(nodo_code("Parsear pausa", r"""// PAUSA 4521206246 2h  ->  deja de contestarle ese cliente.
const item = $input.first().json;
const partes = String(item.message_content || '').trim().split(/\s+/);
const numero = (partes[1] || '').replace(/\D/g, '');
const horasTxt = (partes[2] || '').toLowerCase();
const m = /^(\d{1,2})h?$/.exec(horasTxt);
const horas = m ? Number(m[1]) : null;

if (numero.length < 6 || horas === null || horas <= 0 || horas > 72) {
  return [{ json: { ...item, pausaOk: false,
    respuesta: 'Formato: *PAUSA 4521206246 2h* (de 1 a 72 horas)' } }];
}
return [{ json: { ...item, pausaOk: true, numero, horas } }];""",
        [-520, 1160]))

    nodos.append(nodo_pg("Aplicar pausa", """INSERT INTO barber_pausas (jid, hasta, motivo)
SELECT jid, now() + interval '{{ $json.horas }} hours', 'comando del dueño'
FROM barber_clientes
WHERE right(regexp_replace(split_part(jid,'@',1),'\\D','','g'),10)
        = right('{{ $json.numero }}',10)
ON CONFLICT (jid) DO UPDATE
  SET hasta = excluded.hasta, motivo = excluded.motivo
RETURNING jid, hasta;""", [-320, 1160]))

    nodos.append(nodo_code("Formatear pausa", r"""// Confirma la pausa o avisa si el cliente no existe.
const item = $('Parsear pausa').first().json;
if (!item.pausaOk) return [{ json: { respuesta: item.respuesta } }];

const filas = $input.all().map(i => i.json).filter(f => f && f.jid);
if (!filas.length) {
  return [{ json: { respuesta: `No encontré un cliente con el número *${item.numero}*.\n\nLa pausa solo aplica a clientes que ya existen en el sistema.` } }];
}
const hasta = new Date(filas[0].hasta);
const hora = new Intl.DateTimeFormat('es-MX', {
  timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit', hour12: true }).format(hasta);
return [{ json: { respuesta: `Pausado por *${item.horas} h*.\n\nEl bot no le contestará hasta las *${hora}*.\n\nReanuda solo.` } }];""",
        [-120, 1160]))

    # ------------------------------------------------------------------
    # E. PRECIO
    # ------------------------------------------------------------------
    nodos.append(nodo_code("Parsear precio", r"""// PRECIO ceja 40  -> actualiza el catálogo.
const item = $input.first().json;
const partes = String(item.message_content || '').trim().split(/\s+/);
const clave = (partes[1] || '').toLowerCase();
const precio = Number(partes[2]);
const duracion = partes[3] ? Number(partes[3]) : null;

if (!clave || !partes[2] || Number.isNaN(precio) || precio < 0) {
  return [{ json: { ...item, precioOk: false,
    respuesta: 'Formato: *PRECIO ceja 40*' } }];
}
return [{ json: { ...item, precioOk: true, clave, precio, duracion } }];""",
        [-520, 1360]))

    nodos.append(nodo_pg("Actualizar precio", """UPDATE barber_servicios
   SET precio = {{ $json.precio }},
       duracion_min = COALESCE({{ $json.duracion || 'NULL' }}, duracion_min),
       actualizado_en = now()
 WHERE clave = '{{ $json.clave }}'
RETURNING clave, nombre, precio, duracion_min;""", [-320, 1360]))

    nodos.append(nodo_code("Formatear precio", r"""// Confirma el cambio de precio, o lista el catálogo si la clave no existe.
const item = $('Parsear precio').first().json;
const filas = $input.all().map(i => i.json).filter(f => f && f.clave);

if (!item.precioOk) return [{ json: { respuesta: item.respuesta } }];
if (!filas.length) {
  return [{ json: { respuesta: `No tengo un servicio con la clave *${item.clave}*.\n\nClaves válidas: corte, barba, ceja, mascarilla, dama, planchado, peinado, depilacion.` } }];
}
const s = filas[0];
let r = `Listo. *${s.nombre}* ahora cuesta *$${Math.round(s.precio)}*.`;
if (s.duracion_min) r += `\nDuración: ${s.duracion_min} min.`;
return [{ json: { respuesta: r } }];""", [-120, 1360]))

    # ------------------------------------------------------------------
    # F. ESTADO
    # ------------------------------------------------------------------
    nodos.append(nodo_pg("Leer estado del sistema", """SELECT
  (SELECT count(*) FROM barber_citas
    WHERE inicio >= (now() AT TIME ZONE 'America/Mexico_City')::date
      AND inicio <  (now() AT TIME ZONE 'America/Mexico_City')::date + interval '1 day'
      AND estado IN ('agendado','confirmado')) AS citas_hoy,
  (SELECT count(*) FROM barber_citas
    WHERE inicio >= now() AND inicio < now() + interval '7 days'
      AND estado IN ('agendado','confirmado')) AS citas_semana,
  (SELECT count(*) FROM barber_escalaciones
    WHERE coalesce(estado,'abierta') = 'abierta') AS escalaciones,
  (SELECT count(*) FROM barber_pausas WHERE hasta > now()) AS pausas,
  (SELECT count(*) FROM barber_operadores WHERE activo) AS operadores;""",
        [-320, 1560]))

    nodos.append(nodo_code("Formatear estado", r"""// Salud del sistema en formato WhatsApp.
const e = $input.first().json;
const l = ['*Estado del sistema*', ''];
l.push(`Citas hoy: ${e.citas_hoy || 0}`);
l.push(`Citas esta semana: ${e.citas_semana || 0}`);
l.push(`Escalaciones abiertas: ${e.escalaciones || 0}`);
l.push(`Pausas activas: ${e.pausas || 0}`);
l.push(`Operadores: ${e.operadores || 0}`);
l.push('');
l.push('Bot activo ✅');
return [{ json: { respuesta: l.join('\n') } }];""", [-120, 1560]))

    # ------------------------------------------------------------------
    # G. FILTRO: ayuda para comandos con formato inválido
    # ------------------------------------------------------------------
    nodos.append({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": False, "leftValue": "",
                            "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "saltarchk0001",
                    "leftValue": "={{ $json.saltar }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [-320, 660],
        "id": nid(),
        "name": "IF - Bloqueo invalido",
        "notes": ("Si el formato del bloqueo es inválido, responde la ayuda\n"
                  "y NO llama a Calendar."),
        "notesInFlow": True,
    })

    return {"nodes": nodos}


if __name__ == "__main__":
    piezas = construir()
    nodos = piezas["nodes"]
    nombres = [n["name"] for n in nodos]

    # --- Validaciones -------------------------------------------------
    errores = []
    if len(set(n["id"] for n in nodos)) != len(nodos):
        errores.append("hay ids duplicados")
    for n in nodos:
        for campo in ("parameters", "type", "typeVersion", "position",
                      "id", "name"):
            if campo not in n:
                errores.append(f"{n.get('name')}: falta {campo}")

    # El formato de WhatsApp: nunca ** en el texto que ve el usuario
    for n in nodos:
        s = json.dumps(n, ensure_ascii=False)
        # Se permiten ** solo si no van dentro de un texto de respuesta;
        # aquí simplemente comprobamos que no haya ** en los jsCode.
        code = n.get("parameters", {}).get("jsCode", "")
        if "**" in code:
            errores.append(f"{n['name']}: contiene ** (markdown de WhatsApp)")

    print("=" * 70)
    print("NODOS GENERADOS PARA LOS COMANDOS DEL DUEÑO")
    print("=" * 70)
    for n in nodos:
        print(f"  {n['name']:<34} {n['type'].replace('n8n-nodes-base.','')}")
    print()
    print(f"total: {len(nodos)} nodos")
    print()
    if errores:
        print("ERRORES:")
        for e in errores:
            print("  -", e)
        sys.exit(1)
    print("VALIDACION: OK")

    # Guardar el JSON para inspección
    with open(r"G:\Barberia\archivos\nodos-comandos.json", "w",
              encoding="utf-8") as f:
        json.dump(piezas, f, ensure_ascii=False, indent=2)
    print("guardado: nodos-comandos.json")