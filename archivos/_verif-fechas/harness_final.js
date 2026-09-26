
'use strict';
const CASOS = [{"id": "1a", "entrada": "'2026-09-28T12:00:00-06:00'", "esperado": "2026-09-28", "nota": "lunes 28 sep 2026"}, {"id": "1b", "entrada": "'2026-09-29T12:00:00-06:00'", "esperado": "2026-09-29", "nota": "martes 29 sep 2026"}, {"id": "1c", "entrada": "'2026-09-30T12:00:00-06:00'", "esperado": "2026-09-30", "nota": "miercoles 30 sep 2026"}, {"id": "1d", "entrada": "'2026-10-01T12:00:00-06:00'", "esperado": "2026-10-01", "nota": "jueves 1 oct 2026"}, {"id": "1e", "entrada": "'2026-10-02T12:00:00-06:00'", "esperado": "2026-10-02", "nota": "viernes 2 oct 2026"}, {"id": "1f", "entrada": "'2026-10-03T12:00:00-06:00'", "esperado": "2026-10-03", "nota": "sabado 3 oct 2026"}, {"id": "1g", "entrada": "'2026-09-27T12:00:00-06:00'", "esperado": "2026-09-27", "nota": "domingo 27 sep 2026 (EL DIA DEL FALLO)"}, {"id": "2a", "entrada": "'2026-09-28T19:00:00-06:00'", "esperado": "2026-09-28", "nota": "19:00 Mexico, offset explicito"}, {"id": "2b", "entrada": "'2026-09-29T01:00:00Z'", "esperado": "2026-09-28", "nota": "LA MISMA cita en UTC (en UTC es el 29)"}, {"id": "2c", "entrada": "'2026-09-29T01:00:00+00:00'", "esperado": "2026-09-28", "nota": "LA MISMA cita, offset +00:00"}, {"id": "2d", "entrada": "'2026-09-29T01:00:00.000Z'", "esperado": "2026-09-28", "nota": "LA MISMA cita, con milisegundos"}, {"id": "2e", "entrada": "'2026-09-28T18:59:00-06:00'", "esperado": "2026-09-28", "nota": "18:59 Mexico"}, {"id": "2f", "entrada": "'2026-09-28T20:00:00-06:00'", "esperado": "2026-09-28", "nota": "20:00 Mexico"}, {"id": "2g", "entrada": "'2026-09-28T06:00:00Z'", "esperado": "2026-09-28", "nota": "00:00 Mexico en UTC"}, {"id": "2h", "entrada": "'2026-09-27T19:00:00-06:00'", "esperado": "2026-09-27", "nota": "19:00 Mexico un DOMINGO"}, {"id": "2i", "entrada": "'2026-09-28T01:00:00Z'", "esperado": "2026-09-27", "nota": "01:00Z = 19:00 del 27 en Mexico"}, {"id": "3a", "entrada": "'2026-09-28T00:00:00-06:00'", "esperado": "2026-09-28", "nota": "00:00:00 Mexico"}, {"id": "3b", "entrada": "'2026-09-28T23:59:00-06:00'", "esperado": "2026-09-28", "nota": "23:59 Mexico"}, {"id": "3c", "entrada": "'2026-09-29T05:59:00Z'", "esperado": "2026-09-28", "nota": "23:59 Mexico en UTC"}, {"id": "3d", "entrada": "'2026-09-29T06:00:00Z'", "esperado": "2026-09-29", "nota": "00:00 del 29 en Mexico"}, {"id": "3e", "entrada": "'2026-09-29T05:59:59Z'", "esperado": "2026-09-28", "nota": "23:59:59 Mexico en UTC"}, {"id": "4a", "entrada": "'2026-08-31T10:00:00-06:00'", "esperado": "2026-08-31", "nota": "31 agosto"}, {"id": "4b", "entrada": "'2026-09-01T10:00:00-06:00'", "esperado": "2026-09-01", "nota": "1 septiembre"}, {"id": "4c", "entrada": "'2026-08-31T23:59:00-06:00'", "esperado": "2026-08-31", "nota": "31 ago 23:59 Mexico (1 sep en UTC)"}, {"id": "4d", "entrada": "'2026-09-01T06:00:00Z'", "esperado": "2026-09-01", "nota": "1 sep 00:00 Mexico"}, {"id": "4e", "entrada": "'2026-09-30T23:00:00-06:00'", "esperado": "2026-09-30", "nota": "30 sep 23:00 Mexico (1 oct en UTC)"}, {"id": "4f", "entrada": "'2026-10-01T05:00:00Z'", "esperado": "2026-09-30", "nota": "la misma, en UTC"}, {"id": "5a", "entrada": "'2026-12-31T22:00:00-06:00'", "esperado": "2026-12-31", "nota": "31 dic 22:00"}, {"id": "5b", "entrada": "'2027-01-01T04:00:00Z'", "esperado": "2026-12-31", "nota": "la misma en UTC (1 ene 2027)"}, {"id": "5c", "entrada": "'2027-01-01T00:30:00-06:00'", "esperado": "2027-01-01", "nota": "1 ene 2027 00:30"}, {"id": "5d", "entrada": "'2026-12-31T23:59:00-06:00'", "esperado": "2026-12-31", "nota": "31 dic 23:59 Mexico"}, {"id": "6a", "entrada": "'2028-02-29T12:00:00-06:00'", "esperado": "2028-02-29", "nota": "29 feb 2028"}, {"id": "6b", "entrada": "'2028-02-29T18:00:00Z'", "esperado": "2028-02-29", "nota": "29 feb 2028 en UTC"}, {"id": "6c", "entrada": "'2028-02-28T23:00:00-06:00'", "esperado": "2028-02-28", "nota": "28 feb 2028 (vispera)"}, {"id": "6d", "entrada": "'2028-03-01T02:00:00-06:00'", "esperado": "2028-03-01", "nota": "1 mar 2028"}, {"id": "7a", "entrada": "'2026-09-27T15:00:00-06:00'", "esperado": "2026-09-27", "nota": "ISO con offset -06:00"}, {"id": "7b", "entrada": "'2026-09-27T15:00:00'", "esperado": "2026-09-27", "nota": "ISO SIN offset, 15:00"}, {"id": "7c", "entrada": "'2026-09-27T23:00:00'", "esperado": "2026-09-27", "nota": "ISO SIN offset, 23:00"}, {"id": "7d", "entrada": "'2026-09-27T00:30:00'", "esperado": "2026-09-27", "nota": "ISO SIN offset, 00:30"}, {"id": "7e", "entrada": "'2026-09-27T15:00:00.000-06:00'", "esperado": "2026-09-27", "nota": "ISO con milisegundos"}, {"id": "7f", "entrada": "'2026-09-27'", "esperado": "2026-09-27", "nota": "SOLO FECHA (evento de dia completo de Google Calendar)"}, {"id": "8a", "entrada": "'27 de septiembre de 2026'", "esperado": "2026-09-27", "nota": "texto largo"}, {"id": "8b", "entrada": "'27 septiembre'", "esperado": null, "nota": "sin anio"}, {"id": "8c", "entrada": "'27/09/2026'", "esperado": "2026-09-27", "nota": "dd/mm/aaaa"}, {"id": "8d", "entrada": "'27 de septiembre'", "esperado": "2026-09-27", "nota": "sin anio, con mes"}, {"id": "8e", "entrada": "'domingo 27 de septiembre de 2026'", "esperado": "2026-09-27", "nota": "con el dia delante"}, {"id": "8f", "entrada": "'27 de sep de 2026'", "esperado": "2026-09-27", "nota": "mes abreviado"}, {"id": "8g", "entrada": "'septiembre 27 de 2026'", "esperado": "2026-09-27", "nota": "mes delante"}, {"id": "8h", "entrada": "'27/12/2026'", "esperado": "2026-12-27", "nota": "dd/mm con mes 12"}, {"id": "8i", "entrada": "'05/01/2027'", "esperado": "2027-01-05", "nota": "dd/mm con dia 05"}, {"id": "8j", "entrada": "'1 de octubre de 2026'", "esperado": "2026-10-01", "nota": "texto sin cero a la izquierda"}, {"id": "9a", "entrada": "''", "esperado": null, "nota": "cadena vacia"}, {"id": "9b", "entrada": "'hola'", "esperado": null, "nota": "texto sin fecha"}, {"id": "9c", "entrada": "'32/13/2026'", "esperado": null, "nota": "dia 32, mes 13"}, {"id": "9d", "entrada": "null", "esperado": null, "nota": "null"}, {"id": "9e", "entrada": "undefined", "esperado": null, "nota": "undefined"}, {"id": "9f", "entrada": "'   '", "esperado": null, "nota": "solo espacios"}, {"id": "9g", "entrada": "'2026-13-01'", "esperado": null, "nota": "mes 13 en ISO"}, {"id": "9h", "entrada": "'9999-99-99'", "esperado": null, "nota": "ISO imposible"}, {"id": "9i", "entrada": "'2026'", "esperado": null, "nota": "solo el anio"}, {"id": "9j", "entrada": "20260927", "esperado": null, "nota": "numero, no texto"}];
const INFO = {node: process.version,
              tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
              offset: new Date().getTimezoneOffset(),
              ahora: new Date().toISOString()};
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
  let entrada; try { entrada = eval(c.entrada); } catch(e) { entrada = '__EVALERR__'; }
  let salida; try { salida = herramienta(entrada); } catch(e) { salida = '__THROW__: ' + e.message; }
  res.push({id:c.id, entrada_js:c.entrada, entrada_repr:JSON.stringify(entrada),
            esperado:c.esperado, nota:c.nota, salida:salida});
}
console.log(JSON.stringify({info:INFO, res:res}));
