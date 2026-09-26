
'use strict';
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
const casos=['2026-09-27','2026','12345','2026-13-01','9999-99-99','27 septiembre','20260927'];
for (const s of casos) {
  const iso=new Date(s);
  const valido=!isNaN(iso.getTime());
  const m=String(s).toLowerCase().match(/(\d{1,2})\s*(?:de\s+)?([a-záéíóú]+)?\s*(?:de\s+)?(\d{4})?/);
  console.log(JSON.stringify({entrada:s, isoValido:valido,
     isoUTC: valido? iso.toISOString(): null,
     isoEnMexico: valido? new Intl.DateTimeFormat('en-CA',{timeZone:'America/Mexico_City',year:'numeric',month:'2-digit',day:'2-digit'}).format(iso):null,
     regexMatch: m? m.slice(0,4): null,
     salida: herramienta(s)}));
}
