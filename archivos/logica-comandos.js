/**
 * Lógica de los comandos del dueño para n8n.
 *
 * Cada función se pega en un nodo Code de n8n (modo "Run Once for All Items"),
 * pero están escritas como funciones puras para poder probarlas con Node.
 *
 * ZONA HORARIA — el punto más delicado:
 * México abolió el horario de verano en 2022, así que America/Mexico_City es
 * UTC-06:00 TODO el año. Se fija el offset de forma explícita y NUNCA se
 * depende de la zona del servidor. Si se usara la hora local del contenedor
 * (que corre en UTC), "HOY" a las 22:00 de México devolvería el día siguiente.
 *
 * Ejecutar las pruebas:  node logica-comandos.js
 */

const TZ = 'America/Mexico_City';
const OFFSET = '-06:00';          // offset fijo de México, sin DST
const APERTURA = 10 * 60;         // 10:00 en minutos
const CIERRE = 20 * 60;           // 20:00 en minutos
const MARGEN = 10;                // minutos entre citas
const PASO = 30;                  // tamaño del bloque al ofrecer huecos
const MAX_HUECOS = 6;
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves',
              'viernes', 'sábado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre',
               'diciembre'];
const MESES_ABREV = { ene: 1, feb: 2, mar: 3, abr: 4, may: 5, jun: 6,
                      jul: 7, ago: 8, sep: 9, oct: 10, nov: 11, dic: 12 };

// ---------------------------------------------------------------------------
// Utilidades de fecha
// ---------------------------------------------------------------------------

/** Partes de fecha/hora EN MÉXICO de un instante dado. */
function partesMexico(instante) {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
  const p = {};
  for (const { type, value } of fmt.formatToParts(instante)) p[type] = value;
  return {
    anio: Number(p.year), mes: Number(p.month), dia: Number(p.day),
    hora: Number(p.hour === '24' ? '0' : p.hour), minuto: Number(p.minute),
  };
}

/** 'AAAA-MM-DD' del día mexicano de un instante. */
function fechaMexico(instante) {
  const p = partesMexico(instante);
  return `${p.anio}-${String(p.mes).padStart(2, '0')}-` +
         `${String(p.dia).padStart(2, '0')}`;
}

/** Suma días a una fecha 'AAAA-MM-DD' (aritmética de calendario, sin TZ). */
function sumarDias(fecha, dias) {
  const [a, m, d] = fecha.split('-').map(Number);
  const t = Date.UTC(a, m - 1, d) + dias * 86400000;
  const f = new Date(t);
  return `${f.getUTCFullYear()}-${String(f.getUTCMonth() + 1).padStart(2, '0')}` +
         `-${String(f.getUTCDate()).padStart(2, '0')}`;
}

/** Día de la semana (0=domingo) de una fecha 'AAAA-MM-DD'. */
function diaSemana(fecha) {
  const [a, m, d] = fecha.split('-').map(Number);
  return new Date(Date.UTC(a, m - 1, d)).getUTCDay();
}

/** Texto humano: "jueves 25 de septiembre de 2026". */
function fechaLarga(fecha) {
  const [a, m, d] = fecha.split('-').map(Number);
  return `${DIAS[diaSemana(fecha)]} ${d} de ${MESES[m - 1]} de ${a}`;
}

/** Texto corto: "jueves 25 de septiembre". */
function fechaCorta(fecha) {
  const [a, m, d] = fecha.split('-').map(Number);
  return `${DIAS[diaSemana(fecha)]} ${d} de ${MESES[m - 1]}`;
}

/** 'HH:MM' -> minutos desde medianoche. */
function aMinutos(hhmm) {
  const [h, m] = String(hhmm).split(':').map(Number);
  return h * 60 + m;
}

/** minutos -> 'HH:MM' en formato 12 h con a.m./p.m. */
function a12h(minutos) {
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  const suf = h < 12 ? 'a.m.' : 'p.m.';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, '0')} ${suf}`;
}

/** ISO con offset de México para una fecha y minutos dados. */
function isoMexico(fecha, minutos) {
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return `${fecha}T${String(h).padStart(2, '0')}:` +
         `${String(m).padStart(2, '0')}:00${OFFSET}`;
}

// ---------------------------------------------------------------------------
// 1. prepararRango
// ---------------------------------------------------------------------------

/**
 * Convierte el comando en el rango de fechas a consultar.
 * @param {string} comando HOY | MAÑANA | SEMANA | LIBRE
 * @param {string} ahoraIsoStr instante actual en ISO (con o sin offset)
 */
function prepararRango(comando, ahoraIsoStr) {
  const ahora = ahoraIsoStr ? new Date(ahoraIsoStr) : new Date();
  const hoy = fechaMexico(ahora);
  const cmd = String(comando || '').trim().toUpperCase();

  let desde = hoy;
  let hasta = hoy;
  let titulo = '';

  if (cmd === 'HOY') {
    titulo = `hoy, ${fechaCorta(hoy)}`;
  } else if (cmd === 'MAÑANA' || cmd === 'MANANA') {
    desde = sumarDias(hoy, 1);
    hasta = desde;
    titulo = `mañana, ${fechaCorta(desde)}`;
  } else if (cmd === 'SEMANA') {
    hasta = sumarDias(hoy, 7);
    titulo = `los próximos 7 días (hoy ${fechaCorta(hoy)})`;
  } else if (cmd === 'LIBRE') {
    hasta = sumarDias(hoy, 2);
    titulo = `hoy y los siguientes 2 días`;
  } else {
    desde = hoy;
    titulo = `hoy, ${fechaCorta(hoy)}`;
  }

  return {
    comando: cmd,
    desde,
    hasta,
    titulo,
    timeMin: isoMexico(desde, 0),
    timeMax: isoMexico(hasta, 23 * 60 + 59),
  };
}

// ---------------------------------------------------------------------------
// 2. formatearAgenda
// ---------------------------------------------------------------------------

/** Extrae inicio (minutos) de un evento de Calendar. */
function inicioEvento(ev) {
  const dt = (ev.start && (ev.start.dateTime || ev.start.date)) || '';
  if (ev.start && ev.start.date && !ev.start.dateTime) return -1; // todo el día
  const m = /T(\d{2}):(\d{2})/.exec(dt);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

/** Extrae fin (minutos) de un evento. */
function finEvento(ev) {
  const dt = (ev.end && (ev.end.dateTime || ev.end.date)) || '';
  const m = /T(\d{2}):(\d{2})/.exec(dt);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

/** Nombre del cliente: del resumen "Servicio — Nombre" o de la descripción. */
function nombreCliente(ev) {
  const desc = ev.description || '';
  const m = /Nombre:\s*([^\n]+)/i.exec(desc);
  if (m) return m[1].trim();
  const res = ev.summary || '';
  const partes = res.split(/\s+[—–-]\s+/);
  return partes.length > 1 ? partes[partes.length - 1].trim() : res.trim();
}

/** Servicio a partir del resumen (la parte antes del separador). */
function servicioEvento(ev) {
  const res = ev.summary || '';
  const partes = res.split(/\s+[—–-]\s+/);
  return partes.length > 1 ? partes[0].trim() : '';
}

/** Precio declarado en la descripción ("$150" o "Precio: 150"). */
function precioEvento(ev) {
  const desc = ev.description || '';
  const m = /\$\s*(\d+)|Precio\s*:\s*(\d+)/i.exec(desc);
  if (!m) return null;
  return Number(m[1] || m[2]);
}

function formatearAgenda(eventos, rango, ahoraIsoStr) {
  const ahora = ahoraIsoStr ? new Date(ahoraIsoStr) : new Date();
  const hoy = fechaMexico(ahora);
  const lista = (eventos || [])
    .map((ev) => ({ ev, ini: inicioEvento(ev), fin: finEvento(ev) }))
    .filter((x) => x.ini !== null && x.ini >= 0)
    .sort((a, b) => a.ini - b.ini);

  const lineas = [];
  lineas.push(`*Agenda de ${rango && rango.titulo ? rango.titulo : 'hoy'}*`);

  if (!lista.length) {
    lineas.push('');
    lineas.push('No hay citas agendadas.');
    // Si el rango cubre un día que es domingo, avisarlo
    if (rango && rango.desde === rango.hasta && diaSemana(rango.desde) === 0) {
      lineas.push('Los domingos estamos cerrados.');
    }
    return lineas.join('\n');
  }

  let total = 0;
  let conPrecio = 0;
  for (const { ev, ini } of lista) {
    const cliente = nombreCliente(ev);
    const servicio = servicioEvento(ev);
    const precio = precioEvento(ev);
    if (precio !== null) { total += precio; conPrecio++; }
    let linea = `${a12h(ini)} ${cliente}`;
    if (servicio) linea += ` — ${servicio}`;
    if (precio !== null) linea += ` · $${precio}`;
    lineas.push(linea);
  }

  lineas.push('');
  let resumen = `*${lista.length} cita${lista.length === 1 ? '' : 's'}`;
  if (conPrecio) resumen += ` · $${total} estimado`;
  resumen += '*';
  lineas.push(resumen);

  // Huecos del día de hoy, solo si el rango es de un día
  if (rango && rango.desde === rango.hasta) {
    const huecos = calcularHuecosInterno(eventos, rango.desde, 40, ahora);
    if (huecos.length) {
      lineas.push(`Huecos: ${huecos.slice(0, 6).map(a12h).join(', ')}`);
    } else {
      lineas.push('Sin huecos disponibles ese día.');
    }
  } else if (rango) {
    const dom = [];
    for (let f = rango.desde; f <= rango.hasta; f = sumarDias(f, 1)) {
      if (diaSemana(f) === 0) dom.push(fechaCorta(f));
    }
    if (dom.length) lineas.push(`Cerrado: ${dom.join(', ')}`);
  }
  return lineas.join('\n');
}

// ---------------------------------------------------------------------------
// 3. calcularHuecos
// ---------------------------------------------------------------------------

/** Devuelve los minutos de inicio de los huecos libres de un día. */
function calcularHuecosInterno(eventos, fecha, duracionMin, ahora) {
  const ocupados = (eventos || [])
    .map((ev) => ({ ini: inicioEvento(ev), fin: finEvento(ev) }))
    .filter((x) => x.ini !== null && x.ini >= 0 && x.fin !== null)
    .sort((a, b) => a.ini - b.ini);

  const dur = Math.max(Number(duracionMin) || 40, 10);
  const huecos = [];
  // El último inicio posible: el servicio debe TERMINAR antes del cierre
  for (let t = APERTURA; t + dur <= CIERRE; t += PASO) {
    const fin = t + dur;
    // ¿Choca con algún evento? (con margen)
    const choca = ocupados.some((o) => t < o.fin + MARGEN && o.ini - MARGEN < fin);
    if (choca) continue;
    // ¿Ya pasó? (solo aplica si el día es hoy en México)
    if (fecha === fechaMexico(ahora)) {
      const p = partesMexico(ahora);
      if (t <= p.hora * 60 + p.minuto) continue;
    }
    huecos.push(t);
    if (huecos.length >= MAX_HUECOS) break;
  }
  return huecos;
}

function calcularHuecos(eventos, rango, duracionMin, ahoraIsoStr) {
  const ahora = ahoraIsoStr ? new Date(ahoraIsoStr) : new Date();
  const dur = Number(duracionMin) || 40;
  const fechas = [];
  for (let f = rango.desde; f <= rango.hasta; f = sumarDias(f, 1)) fechas.push(f);

  const bloques = [];
  let huboDomingo = false;
  for (const fecha of fechas) {
    if (diaSemana(fecha) === 0) { huboDomingo = true; continue; }
    const h = calcularHuecosInterno(eventos, fecha, dur, ahora);
    if (!h.length) continue;
    const etiqueta = fecha === rango.desde ? 'Hoy' : fechaCorta(fecha);
    bloques.push(`${etiqueta}: ${h.map(a12h).join(', ')}`);
  }

  const lineas = [`*Huecos para ${dur} min*`];
  if (!bloques.length) {
    lineas.push('');
    lineas.push('No hay huecos libres en ese rango.');
  } else {
    lineas.push('');
    lineas.push(...bloques);
  }
  if (huboDomingo) lineas.push('');
  if (huboDomingo) lineas.push('Los domingos estamos cerrados.');
  return lineas.join('\n');
}

// ---------------------------------------------------------------------------
// 4. parsearGestion
// ---------------------------------------------------------------------------

function error(msg) {
  return { ok: false, error: msg };
}

/** 'AAA-MM-DD' del día mexicano actual, más offset de días. */
function hoyMas(dias, ahora) {
  return sumarDias(fechaMexico(ahora || new Date()), dias);
}

function parsearGestion(texto, ahoraIsoStr) {
  const ahora = ahoraIsoStr ? new Date(ahoraIsoStr) : new Date();
  const t = String(texto || '').trim();
  const partes = t.split(/\s+/);
  const cmd = (partes[0] || '').toUpperCase();
  const resto = partes.slice(1);

  if (cmd === 'BLOQUEAR') {
    // BLOQUEAR 14:00-15:30 motivo   |   BLOQUEAR 2026-09-26 14:00-15:30 motivo
    let fecha = hoyMas(0, ahora);
    let idx = 0;
    if (resto[0] && /^\d{4}-\d{2}-\d{2}$/.test(resto[0])) {
      fecha = resto[0]; idx = 1;
    }
    const rango = resto[idx];
    if (!rango || !/^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$/.test(rango)) {
      return error('Formato: BLOQUEAR 14:00-15:30 motivo');
    }
    const [d, h] = rango.split('-').map((s) => s.trim());
    if (aMinutos(h) <= aMinutos(d)) {
      return error('La hora final debe ser mayor que la inicial.');
    }
    const motivo = resto.slice(idx + 1).join(' ') || 'ocupado';
    return { ok: true, comando: cmd,
             datos: { fecha, desde: d, hasta: h, motivo,
                      inicioMin: aMinutos(d), finMin: aMinutos(h) } };
  }

  if (cmd === 'CERRAR' || cmd === 'ABRIR') {
    const arg = resto.join(' ').trim();
    if (!arg) return error(`Formato: ${cmd} 24 dic  o  ${cmd} 2026-12-24`);
    let fecha = null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(arg)) {
      fecha = arg;
    } else if (/^(hoy|mañana|manana)$/i.test(arg)) {
      fecha = hoyMas(/^hoy$/i.test(arg) ? 0 : 1, ahora);
    } else {
      const m = /^(\d{1,2})\s+([a-záéíóú]{3,})$/i.exec(arg);
      if (m) {
        const mes = MESES_ABREV[m[2].slice(0, 3).toLowerCase()];
        const dia = Number(m[1]);
        if (mes && dia >= 1 && dia <= 31) {
          // Si el mes ya pasó este año, se asume el próximo
          const p = partesMexico(ahora);
          let anio = p.anio;
          if (mes < p.mes || (mes === p.mes && dia < p.dia)) anio++;
          fecha = `${anio}-${String(mes).padStart(2, '0')}-` +
                  `${String(dia).padStart(2, '0')}`;
        }
      }
    }
    if (!fecha) return error('No entendí la fecha. Ejemplo: CERRAR 24 dic');
    return { ok: true, comando: cmd, datos: { fecha } };
  }

  if (cmd === 'PAUSA') {
    const quien = resto[0];
    if (!quien) return error('Formato: PAUSA 4521206246 2h');
    const horasTxt = (resto[1] || '').toLowerCase();
    let horas = null;
    if (/^(\d+)\s*h$/.test(horasTxt)) horas = Number(/(\d+)/.exec(horasTxt)[1]);
    if (horas === null || horas <= 0 || horas > 72) {
      return error('Indica la duración: PAUSA 4521206246 2h (máx 72h)');
    }
    return { ok: true, comando: cmd, datos: { busqueda: quien, horas } };
  }

  if (cmd === 'PRECIO') {
    const servicio = resto[0];
    const precio = Number(resto[1]);
    if (!servicio) return error('Formato: PRECIO ceja 40');
    if (!resto[1] || Number.isNaN(precio) || precio < 0) {
      return error('Falta un precio válido. Ejemplo: PRECIO ceja 40');
    }
    const duracion = resto[2] ? Number(resto[2]) : null;
    return { ok: true, comando: cmd,
             datos: { servicio, precio, duracion } };
  }

  if (cmd === 'CLIENTE') {
    if (!resto[0]) return error('Formato: CLIENTE 4521206246');
    return { ok: true, comando: cmd, datos: { busqueda: resto[0] } };
  }

  return error(`Comando "${cmd}" no reconocido.`);
}

// ---------------------------------------------------------------------------
// Pruebas
// ---------------------------------------------------------------------------

function correrPruebas() {
  let pass = 0, fail = 0;
  const fallos = [];
  function check(cond, msg) {
    if (cond) { pass++; console.log('  PASS  ' + msg); }
    else { fail++; fallos.push(msg); console.log('  FAIL  ' + msg); }
  }

  console.log('='.repeat(70));
  console.log('PRUEBAS DE LA LOGICA DE COMANDOS');
  console.log('='.repeat(70));

  // Instante donde UTC y México difieren de día: 2026-09-26T02:30Z
  // En México es 2026-09-25 20:30 (UTC-6) -> el día debe ser 25, no 26.
  const ahora = '2026-09-26T02:30:00Z';

  console.log('\n[1] prepararRango (la trampa de la zona horaria)');
  const rHoy = prepararRango('HOY', ahora);
  check(rHoy.desde === '2026-09-25',
        'HOY usa el dia de MEXICO (25) y no el de UTC (26)');
  check(rHoy.timeMin === '2026-09-25T00:00:00-06:00',
        'timeMin con offset -06:00: ' + rHoy.timeMin);
  check(rHoy.timeMax === '2026-09-25T23:59:00-06:00',
        'timeMax cierra el dia: ' + rHoy.timeMax);
  check(rHoy.titulo.includes('viernes'),
        'titulo dice el dia correcto (viernes): ' + rHoy.titulo);

  const rMan = prepararRango('MAÑANA', ahora);
  check(rMan.desde === '2026-09-26', 'MAÑANA es el 26: ' + rMan.desde);

  const rSem = prepararRango('SEMANA', ahora);
  check(rSem.hasta === '2026-10-02', 'SEMANA cubre 7 dias: ' + rSem.hasta);

  const rLib = prepararRango('LIBRE', ahora);
  check(rLib.hasta === '2026-09-27', 'LIBRE cubre 2 dias: ' + rLib.hasta);

  console.log('\n[2] formatearAgenda');
  const vacia = formatearAgenda([], rHoy, ahora);
  check(vacia.includes('No hay citas'), 'agenda vacia lo dice');
  check(!vacia.includes('**'), 'sin doble asterisco');

  const unEv = [{
    summary: 'Corte desvanecido — Cristia',
    description: 'Nombre: Cristia\nPrecio: 150',
    start: { dateTime: '2026-09-25T13:00:00-06:00' },
    end: { dateTime: '2026-09-25T13:40:00-06:00' },
  }];
  const una = formatearAgenda(unEv, rHoy, ahora);
  check(una.includes('Cristia'), 'aparece el nombre del cliente');
  check(una.includes('1:00 p.m.'), 'hora en formato 12h: 1:00 p.m.');
  check(una.includes('$150'), 'aparece el precio');
  check(!una.includes('**'), 'sin doble asterisco');

  const tres = formatearAgenda([
    unEv[0],
    { summary: 'Arreglo de barba — Juan', description: 'Precio: 100',
      start: { dateTime: '2026-09-25T16:30:00-06:00' },
      end: { dateTime: '2026-09-25T16:50:00-06:00' } },
    { summary: 'Ceja — Ana', description: 'Precio: 30',
      start: { dateTime: '2026-09-25T18:00:00-06:00' },
      end: { dateTime: '2026-09-25T18:10:00-06:00' } },
  ], rHoy, ahora);
  check(tres.includes('3 citas'), 'cuenta 3 citas');
  check(tres.includes('$280'), 'suma total 280 (150+100+30)');
  const pos1 = tres.indexOf('Cristia'), pos2 = tres.indexOf('Juan'),
        pos3 = tres.indexOf('Ana');
  check(pos1 < pos2 && pos2 < pos3, 'ordenadas por hora ascendente');

  console.log('\n[3] calcularHuecos');
  // OJO: el instante de arriba (02:30Z) son las 20:30 en Mexico: el dia ya
  // cerro, asi que NO habria huecos. Para probar los huecos hace falta un
  // instante de manana. 14:00Z = 08:00 en Mexico.
  const manana = '2026-09-25T14:00:00Z';
  const libreTodo = calcularHuecos([], rHoy, 40, manana);
  check(libreTodo.includes('10:00'), 'dia vacio ofrece desde las 10:00');
  check(!libreTodo.includes('**'), 'sin doble asterisco');
  check(libreTodo.includes('14:30') || libreTodo.includes('2:30 p.m.'),
        'ofrece bloques cada 30 min');

  const ocupado = calcularHuecos([{
    start: { dateTime: '2026-09-25T12:00:00-06:00' },
    end: { dateTime: '2026-09-25T14:00:00-06:00' },
  }], rHoy, 40, manana);
  check(!ocupado.includes('12:00') && !ocupado.includes('1:00 p.m.'),
        'no ofrece el rango ocupado (12:00-14:00)');
  // Margen de 10 min: con cita hasta 14:00, el primer hueco es 14:30
  check(ocupado.includes('2:30 p.m.'),
        'respeta el margen y reanuda a las 2:30 p.m.');
  check(!ocupado.includes('2:10 p.m.'),
        'no ofrece un hueco pegado al margen (2:10 p.m.)');

  // Si el dia ya cerro, no debe inventar huecos
  const cerrado = calcularHuecos([], rHoy, 40, ahora);
  check(!cerrado.includes('10:00'),
        'a las 20:30 no ofrece huecos de un dia ya cerrado');

  const domingo = calcularHuecos([], prepararRango('HOY', '2026-09-27T18:00:00Z'),
                                 40, '2026-09-27T18:00:00Z');
  check(domingo.includes('domingos'), 'avisa que el domingo esta cerrado');

  console.log('\n[4] parsearGestion');
  const v1 = parsearGestion('BLOQUEAR 14:00-15:30 comida', ahora);
  check(v1.ok && v1.datos.desde === '14:00' && v1.datos.hasta === '15:30'
        && v1.datos.motivo === 'comida', 'BLOQUEAR con motivo');
  const v2 = parsearGestion('BLOQUEAR 2026-09-28 09:00-10:00 junta', ahora);
  check(v2.ok && v2.datos.fecha === '2026-09-28', 'BLOQUEAR con fecha explicita');
  const v3 = parsearGestion('CERRAR 24 dic', ahora);
  check(v3.ok && /^2026-12-24$/.test(v3.datos.fecha),
        'CERRAR 24 dic -> 2026-12-24 (y no 2027)');
  const v4 = parsearGestion('CERRAR 2026-12-25', ahora);
  check(v4.ok && v4.datos.fecha === '2026-12-25', 'CERRAR con fecha ISO');
  const v5 = parsearGestion('PAUSA 4521206246 2h', ahora);
  check(v5.ok && v5.datos.horas === 2, 'PAUSA 2h');
  const v6 = parsearGestion('PAUSA 4521206246 24h', ahora);
  check(v6.ok && v6.datos.horas === 24, 'PAUSA 24h');
  const v7 = parsearGestion('PRECIO ceja 40', ahora);
  check(v7.ok && v7.datos.precio === 40, 'PRECIO ceja 40');
  const v8 = parsearGestion('CLIENTE 4521206246', ahora);
  check(v8.ok && v8.datos.busqueda === '4521206246', 'CLIENTE por numero');

  const i1 = parsearGestion('BLOQUEAR 14:00', ahora);
  check(!i1.ok && i1.error.includes('Formato'), 'BLOQUEAR sin rango da error claro');
  const i2 = parsearGestion('PAUSA 4521206246', ahora);
  check(!i2.ok && i2.error.includes('duración'), 'PAUSA sin horas da error claro');
  const i3 = parsearGestion('PRECIO ceja', ahora);
  check(!i3.ok && i3.error.includes('precio'), 'PRECIO sin valor da error claro');
  const i4 = parsearGestion('CERRAR', ahora);
  check(!i4.ok, 'CERRAR sin fecha da error');
  const i5 = parsearGestion('BLOQUEAR 15:00-14:00 x', ahora);
  check(!i5.ok, 'BLOQUEAR con horas invertidas se rechaza');

  console.log('\n' + '='.repeat(70));
  if (fail) {
    console.log(`RESULTADO: ${fail} de ${pass + fail} FALLARON`);
    fallos.forEach((f) => console.log('  - ' + f));
    return 1;
  }
  console.log(`RESULTADO: ${pass} de ${pass} PASARON`);
  console.log('='.repeat(70));
  return 0;
}

if (require.main === module) process.exit(correrPruebas());

module.exports = {
  prepararRango, formatearAgenda, calcularHuecos, parsearGestion,
  fechaMexico, fechaCorta, fechaLarga, a12h, sumarDias, diaSemana,
};