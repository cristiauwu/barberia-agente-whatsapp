#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla el fallo grave: el agente INVENTA el dia de la semana.

HALLAZGO (medido en la exec 1139 del trafico real, no reproducido a mano):
  Al listar las citas de un cliente, el agente escribio "miércoles 27 de
  septiembre" cuando el `dateTime` era DOMINGO 27, y "jueves 28" cuando era
  LUNES 28. Comprobado con `datetime.weekday()`.

CAUSA RAIZ:
  El agente recibe los eventos con su fecha en ISO
  (`2026-09-27T15:00:00-06:00`). Para nombrar el dia tendria que calcularlo
  el mismo, y los modelos de lenguaje son malos en aritmetica de calendario.
  Los COMANDOS DEL DUENO aciertan porque su nodo `Formatear agenda` tiene una
  tabla `DIAS` y usa `getDay()`. El agente no tenia nada equivalente.

ARREGLO: se le da al agente una HERRAMIENTA DETERMINISTA que traduce.
  Nodo nuevo: `Que dia es` (`@n8n/n8n-nodes-langchain.toolCode`).
  El modelo le pasa una fecha (ISO o texto) y recibe el dia ya calculado.
  Asi deja de adivinar: consulta.

  Ademas:
   - Se anade al prompt la regla de usar la herramienta y no calcular.
   - Se refuerza el tope de formato para LISTAS (el fallo traia 24 lineas
     cuando el tope es 10).

POR QUE UNA HERRAMIENTA Y NO SOLO PROMPT:
  El prompt ya pedia leer el dia del ISO y aun asi fallo 2 de 2 veces en esa
  ejecucion. Pedirle a un modelo que no haga aritmetica es fragil; darle una
  calculadora es robusto. Esto es lo mismo que hace el nodo Calculator, pero
  para fechas.
"""
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
PROMPT = r"G:\Barberia\prompt-sistema-agente-barberia.txt"
WID = "barberiaAgenteUncensored"

# ---------------------------------------------------------------------------
#  La herramienta: traduce una fecha al dia de la semana, en espanol
# ---------------------------------------------------------------------------
CODIGO = r"""
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
"""


def api(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(N8N + ruta, data=datos, method=metodo)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def guardar(wf, wid):
    """PUT con el ciclo desactivar/activar que exige n8n."""
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{wid}/deactivate", {})
    st, r = api("PUT", f"/workflows/{wid}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {})})
    if st not in (200, 201):
        print(f"  MAL PUT HTTP {st}: {str(r)[:200]}")
        return False
    if activo:
        api("POST", f"/workflows/{wid}/activate", {})
    return True


def main():
    print("=" * 68)
    print("ARREGLAR: EL AGENTE INVENTA EL DIA DE LA SEMANA")
    print("=" * 68)

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print(f"  MAL no pude leer el workflow: {st}")
        return 1

    # ------------------------------------------------------------- 1
    print("\n[1] ANADIR LA HERRAMIENTA DETERMINISTA 'Que dia es'")
    if any(n["name"] == "Que dia es" for n in wf["nodes"]):
        print("  ya existe")
    else:
        nodo = {
            "id": "tool-que-dia-es",
            "name": "Que dia es",
            "type": "@n8n/n8n-nodes-langchain.toolCode",
            "typeVersion": 1.3,
            "position": [1300, 1180],
            "parameters": {
                "description": (
                    "Traduce una fecha al dia de la semana, en espanol. "
                    "USALA SIEMPRE que necesites nombrar un dia ('el "
                    "miercoles', 'que dia cae'). Pasale la fecha tal como "
                    "viene de Google Calendar (2026-09-27T15:00:00-06:00) o "
                    "escrita ('27 de septiembre de 2026'). Devuelve el dia "
                    "ya calculado. NUNCA deduzcas tu el dia de la semana: "
                    "equivocarte hace que el cliente llegue el dia "
                    "equivocado y pierda su cita."),
                "language": "javaScript",
                "jsCode": CODIGO,
            },
            "notes": ("Herramienta determinista: calcula el dia de la semana "
                      "con el motor de fechas, no con el modelo. Existe "
                      "porque el agente inventaba el dia (exec 1139: dijo "
                      "miercoles por domingo)."),
        }
        wf["nodes"].append(nodo)
        con = wf.setdefault("connections", {})
        con["Que dia es"] = {"ai_tool": [[{"node": "AI Agent",
                                           "type": "ai_tool", "index": 0}]]}
        print("  OK  nodo creado y conectado al AI Agent como ai_tool")
        if not guardar(wf, WID):
            return 1

    # ------------------------------------------------------------- 2
    print("\n[2] ANADIR LA REGLA AL PROMPT")
    texto = open(PROMPT, encoding="utf-8").read()
    if "NUNCA CALCULES EL DIA DE LA SEMANA" in texto:
        print("  ya estaba")
    else:
        regla = """

## EL DIA DE LA SEMANA SE PREGUNTA, NO SE CALCULA

**Tienes la herramienta `Que dia es`.** Usala cada vez que necesites nombrar
un dia de la semana. No lo deduzcas tu: ya te equivocaste (dijiste
"miércoles" de un domingo) y eso hace que el cliente llegue el dia
equivocado y pierda su cita.

- Antes de escribir "el miércoles" o "el jueves", llama a `Que dia es` con
  la fecha de la cita y copia lo que te devuelva.
- Si no puedes llamarla, escribe **solo la fecha en números**: "el 27/09 a
  las 3:00 p.m.". Nunca un dia calculado por ti.
- Si el cliente pregunta "¿qué día es?", usa la herramienta y responde con
  lo que devuelva.

## EL FORMATO DE LAS LISTAS

Cuando enumeres varias citas (la agenda de alguien, varios horarios), el
tope de **10 líneas** también aplica. Si son muchas, agrupa:

> *Tus próximas citas*
> - Corte — 27/09 a las 3:00 p.m.
> - Barba — 28/09 a las 2:20 p.m.
> - Ceja — 30/09 a las 6:00 p.m.
> ¿Te muevo alguna?

Sin sangría al inicio de los renglones, sin líneas en blanco de más, y
nunca más de 10 líneas en total.
"""
        ancla = "\n## Privacidad"
        if ancla in texto:
            texto = texto.replace(ancla, regla + ancla, 1)
        else:
            texto = texto.rstrip() + regla
        open(PROMPT, "w", encoding="utf-8").write(texto)
        print(f"  OK  regla anadida (prompt: {len(texto):,} caracteres)")

    # subir el prompt al workflow
    st, wf = api("GET", f"/workflows/{WID}")
    ag = next(n for n in wf["nodes"] if n["name"] == "AI Agent")
    sm = ag["parameters"]["options"]["systemMessage"]
    if sm.startswith("="):
        sm = sm[1:]
    if "NUNCA CALCULES EL DIA DE LA SEMANA" not in sm:
        ag["parameters"]["options"]["systemMessage"] = "=" + texto.strip()
        print("  subiendo el prompt...")
        if not guardar(wf, WID):
            return 1
        print("  OK")
    else:
        print("  el workflow ya tenia la regla")

    # ------------------------------------------------------------- 3
    print("\n[3] MEJORAR LA DESCRIPCION DE 'Consultar agenda'")
    st, wf = api("GET", f"/workflows/{WID}")
    n = next(x for x in wf["nodes"] if x["name"] == "Consultar agenda")
    desc = n["parameters"].get("toolDescription", "")
    extra = (" IMPORTANTE: para nombrar el dia de una cita, pasale su fecha a "
             "la herramienta `Que dia es`. No calcules tu el dia.")
    if "Que dia es" not in desc:
        n["parameters"]["toolDescription"] = desc.rstrip() + extra
        if not guardar(wf, WID):
            return 1
        print("  OK  descripcion actualizada")
    else:
        print("  ya estaba")

    # ------------------------------------------------------------- 4
    print("\n[4] VERIFICACION")
    st, wf = api("GET", f"/workflows/{WID}")
    sm = next(n for n in wf["nodes"] if n["name"] == "AI Agent")[
        "parameters"]["options"]["systemMessage"]
    arch = open(PROMPT, encoding="utf-8").read().strip()
    herramienta = next((n for n in wf["nodes"] if n["name"] == "Que dia es"),
                       None)
    conectada = any(
        d["node"] == "AI Agent"
        for ramas in (wf["connections"].get("Que dia es") or {}).values()
        for rama in ramas for d in rama)
    pruebas = [
        ("existe la herramienta 'Que dia es'", herramienta is not None),
        ("esta conectada al AI Agent como ai_tool", conectada),
        ("la regla esta en el prompt del workflow",
         "NUNCA CALCULES EL DIA DE LA SEMANA" in sm),
        ("el prompt del archivo y el del workflow coinciden",
         sm.lstrip("=").strip() == arch),
        ("el workflow sigue activo", wf.get("active") is True),
        ("el numero de nodos es 48", len(wf["nodes"]) == 48),
    ]
    fallos = 0
    for nombre, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {nombre}")
        if not ok:
            fallos += 1
    print(f"\n  nodos: {len(wf['nodes'])}   "
          f"prompt: {len(arch):,} caracteres")
    print(f"  FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())