
'use strict';
const CASOS = [{"id": "7d-lunes", "entrada": "'2026-09-28'", "esperado": "2026-09-28", "nota": "lunes"}, {"id": "7d-martes", "entrada": "'2026-09-29'", "esperado": "2026-09-29", "nota": "martes"}, {"id": "7d-miercoles", "entrada": "'2026-09-30'", "esperado": "2026-09-30", "nota": "miercoles"}, {"id": "7d-jueves", "entrada": "'2026-10-01'", "esperado": "2026-10-01", "nota": "jueves"}, {"id": "7d-viernes", "entrada": "'2026-10-02'", "esperado": "2026-10-02", "nota": "viernes"}, {"id": "7d-sabado", "entrada": "'2026-10-03'", "esperado": "2026-10-03", "nota": "sabado"}, {"id": "7d-domingo", "entrada": "'2026-09-27'", "esperado": "2026-09-27", "nota": "domingo (el dia del fallo)"}, {"id": "tz-1900-mx-offset", "entrada": "'2026-09-28T19:00:00-06:00'", "esperado": "2026-09-28", "nota": "19:00 Mexico con offset explicito"}, {"id": "tz-1900-mx-z", "entrada": "'2026-09-29T01:00:00Z'", "esperado": "2026-09-28", "nota": "la MISMA cita en UTC (ya es dia 29 en UTC)"}, {"id": "tz-1900-mx-utc-off", "entrada": "'2026-09-29T01:00:00+00:00'", "esperado": "2026-09-28", "nota": "la MISMA cita en UTC con offset +00:00"}, {"id": "tz-1859-mx", "entrada": "'2026-09-28T18:59:00-06:00'", "esperado": "2026-09-28", "nota": "18:59 Mexico"}, {"id": "tz-2000-mx", "entrada": "'2026-09-28T20:00:00-06:00'", "esperado": "2026-09-28", "nota": "20:00 Mexico"}, {"id": "tz-0000-utc", "entrada": "'2026-09-28T06:00:00Z'", "esperado": "2026-09-28", "nota": "00:00 Mexico expresado en UTC"}, {"id": "mid-0000-mx", "entrada": "'2026-09-28T00:00:00-06:00'", "esperado": "2026-09-28", "nota": "00:00:00 Mexico"}, {"id": "mid-0001-mx", "entrada": "'2026-09-28T00:01:00-06:00'", "esperado": "2026-09-28", "nota": "00:01 Mexico"}, {"id": "mid-2359-mx", "entrada": "'2026-09-28T23:59:00-06:00'", "esperado": "2026-09-28", "nota": "23:59 Mexico"}, {"id": "mid-2359utc", "entrada": "'2026-09-29T05:59:00Z'", "esperado": "2026-09-28", "nota": "23:59 Mexico expresado en UTC"}, {"id": "mid-0000utc", "entrada": "'2026-09-29T06:00:00Z'", "esperado": "2026-09-29", "nota": "00:00 del dia 29 en Mexico (en UTC ya es dia 29 tambien)"}, {"id": "mes-31ago", "entrada": "'2026-08-31T10:00:00-06:00'", "esperado": "2026-08-31", "nota": "31 de agosto"}, {"id": "mes-01sep", "entrada": "'2026-09-01T10:00:00-06:00'", "esperado": "2026-09-01", "nota": "1 de septiembre"}, {"id": "mes-31ago-2359", "entrada": "'2026-08-31T23:59:00-06:00'", "esperado": "2026-08-31", "nota": "31 ago 23:59 Mexico (1 sep en UTC)"}, {"id": "mes-01sep-0000utc", "entrada": "'2026-09-01T06:00:00Z'", "esperado": "2026-09-01", "nota": "1 sep 00:00 Mexico"}, {"id": "anio-31dic", "entrada": "'2026-12-31T22:00:00-06:00'", "esperado": "2026-12-31", "nota": "31 dic 2026 22:00"}, {"id": "anio-31dic-utc", "entrada": "'2027-01-01T04:00:00Z'", "esperado": "2026-12-31", "nota": "la misma, en UTC ya es 1 ene 2027"}, {"id": "anio-01ene", "entrada": "'2027-01-01T00:30:00-06:00'", "esperado": "2027-01-01", "nota": "1 ene 2027 00:30"}, {"id": "bisiesto-2028", "entrada": "'2028-02-29T12:00:00-06:00'", "esperado": "2028-02-29", "nota": "29 feb 2028 (bisiesto)"}, {"id": "bisiesto-2028-utc", "entrada": "'2028-02-29T18:00:00Z'", "esperado": "2028-02-29", "nota": "29 feb 2028 mediodia Mexico en UTC"}, {"id": "iso-con-offset", "entrada": "'2026-09-27T15:00:00-06:00'", "esperado": "2026-09-27", "nota": "ISO con offset"}, {"id": "iso-sin-offset", "entrada": "'2026-09-27T15:00:00'", "esperado": "2026-09-27", "nota": "ISO sin offset (se interpreta en la zona del proceso)"}, {"id": "iso-sin-offset-noche", "entrada": "'2026-09-27T23:00:00'", "esperado": "2026-09-27", "nota": "ISO sin offset a las 23:00"}, {"id": "iso-solo-fecha", "entrada": "'2026-09-27'", "esperado": "2026-09-27", "nota": "solo YYYY-MM-DD"}, {"id": "txt-completo", "entrada": "'27 de septiembre de 2026'", "esperado": "2026-09-27", "nota": "texto largo"}, {"id": "txt-corto", "entrada": "'27 septiembre'", "esperado": null, "nota": "sin anio: comportamiento a documentar"}, {"id": "txt-barras", "entrada": "'27/09/2026'", "esperado": null, "nota": "formato con barras"}, {"id": "txt-acentos", "entrada": "'27 de septiembre'", "esperado": null, "nota": "sin anio, con mes"}, {"id": "txt-domingo", "entrada": "'domingo 27 de septiembre de 2026'", "esperado": null, "nota": "texto con dia de la semana delante"}, {"id": "bas-vacio", "entrada": "''", "esperado": null, "nota": "cadena vacia"}, {"id": "bas-hola", "entrada": "'hola'", "esperado": null, "nota": "texto sin fecha"}, {"id": "bas-3213", "entrada": "'32/13/2026'", "esperado": null, "nota": "dia y mes fuera de rango"}, {"id": "bas-null", "entrada": "null", "esperado": null, "nota": "null"}, {"id": "bas-undefined", "entrada": "undefined", "esperado": null, "nota": "undefined"}, {"id": "bas-9999", "entrada": "'9999-99-99'", "esperado": null, "nota": "fecha imposible ISO"}, {"id": "bas-solo-num", "entrada": "'12345'", "esperado": null, "nota": "solo digitos"}];
const TZINFO = Intl.DateTimeFormat().resolvedOptions().timeZone;
const OFFSET = new Date().getTimezoneOffset();
const NODE = process.version;

function herramienta(query) {

// Devuelve el dia de la semana de una fecha, calculado, no adivinado.
//
// El modelo pasa la fecha que viene de Google Calendar (ISO) o escrita a
// mano ("27 de septiembre de 2026"), y recibe el dato ya resuelto. Asi no
// tiene que calcular nada.
const TZ = 'America/Mexico_City';
const DIAS = ['domingo', 'lunes', 'martes', 'miercoles', 'jueves',
              'viernes', 'sabado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre',
               'diciembre'];

const entrada = String(query == null ? '' : query).trim();
if (!entrada) {
  return 'Error: no me diste ninguna fecha. Pasame una fecha en formato ' +
         '2026-09-27T15:00:00-06:00 o "27 de septiembre de 2026".';
}

// 1. Intentar el formato ISO, que es el que manda Google Calendar.
let d = new Date(entrada);
let comoSeLeyo = 'ISO';

// 2. Si no es ISO, intentar "27 de septiembre de 2026" / "27 septiembre".
if (isNaN(d.getTime())) {
  const m = entrada.toLowerCase().match(
    /(\d{1,2})\s*(?:de\s+)?([a-záéíóú]+)?\s*(?:de\s+)?(\d{4})?/);
  if (m) {
    const dia = parseInt(m[1], 10);
    let mes = null;
    if (m[2]) {
      const idx = MESES.findIndex(function (x) {
        return x.startsWith(m[2].substring(0, 3));
      });
      if (idx >= 0) mes = idx;
    }
    const anio = m[3] ? parseInt(m[3], 10) : new Date().getFullYear();
    if (mes === null) mes = new Date().getMonth();
    // mediodia: evita que un cambio de zona mueva la fecha un dia
    d = new Date(Date.UTC(anio, mes, dia, 18, 0, 0));
    comoSeLeyo = 'texto';
  }
}

if (isNaN(d.getTime())) {
  return 'Error: no pude entender "' + entrada + '". Usa el formato ' +
         '2026-09-27T15:00:00-06:00.';
}

// El negocio vive en Mexico: el dia se calcula en SU zona, no en UTC.
// Esto es lo que rompia: a las 19:00 de Mexico ya es el dia siguiente en UTC.
const partes = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
  weekday: 'long'
}).formatToParts(d);

const get = function (t) {
  const p = partes.find(function (x) { return x.type === t; });
  return p ? p.value : '';
};
const anio = get('year');
const mes2 = parseInt(get('month'), 10);
const dia2 = parseInt(get('day'), 10);

// El nombre del dia lo da el propio motor de fechas: no se calcula a mano.
const enIngles = get('weekday');
const ORDEN = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
               'Friday', 'Saturday'];
const indice = ORDEN.indexOf(enIngles);

const resultado = {
  dia_semana: DIAS[indice],
  fecha: anio + '-' + String(mes2).padStart(2, '0') + '-' +
         String(dia2).padStart(2, '0'),
  fecha_larga: DIAS[indice] + ' ' + dia2 + ' de ' + MESES[mes2 - 1] +
               ' de ' + anio,
  zona: TZ,
  comoSeLeyo: comoSeLeyo
};

// Se devuelve como texto plano: es lo que el modelo sabe leer mejor.
return resultado.fecha_larga + ' (' + resultado.fecha + ')';

}

const res = [];
for (const c of CASOS) {
  let entrada;
  try { entrada = eval(c.entrada); } catch (e) { entrada = '__EVALERR__'; }
  let salida;
  try {
    salida = herramienta(entrada);
  } catch (e) {
    salida = '__THROW__: ' + e.message;
  }
  res.push({id: c.id, entrada_js: c.entrada, entrada_repr: JSON.stringify(entrada),
            esperado: c.esperado, nota: c.nota, salida: salida});
}
console.log(JSON.stringify({node: NODE, tz: TZINFO, offset: OFFSET, res: res},
                           null, 1));
