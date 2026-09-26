#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla el comando LIBRE: debe dar HUECOS, no la agenda del rango.

BUG (verificado en vivo):
  El dueño manda `LIBRE` y recibe:
      *Agenda de hoy y los siguientes 2 días*
      *domingo 27 de septiembre*
      3:00 p.m. Cristia Ñ — Corte desvanecido o tijera
      *1 cita en el periodo · $150 estimado*
  Es decir: le da la AGENDA (las citas ocupadas), cuando `LIBRE` debe dar
  los HUECOS DISPONIBLES.

CAUSA:
  En 'Preparar rango de fechas', LIBRE fija `hasta = hoy + 2 días`, así que
  `desde !== hasta` y `esRango = true`. En 'Formatear agenda', la rama
  `esRango` agrupa por día y **nunca imprime la línea "Huecos:"**. La rama
  que sí calcula huecos solo corre cuando `desde === hasta` (HOY o MAÑANA).

  Es decir: LIBRE caía en la rama de "vista de rango" y los huecos nunca
  se calculaban.

SOLUCIÓN:
  Dar a LIBRE su propio camino de formateo. En 'Formatear agenda', si el
  comando es LIBRE, calcular los huecos de CADA día del rango y mostrarlos
  agrupados. No mostrar las citas ocupadas (eso ya lo dan HOY/SEMANA).

FORMATO (WhatsApp): *un asterisco*, sin marcos, máximo ~12 líneas, y si un
día está lleno decirlo.
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

# Reemplazo del bloque LIBRE dentro de 'Formatear agenda'.
# Se añade una rama específica ANTES de la rama `esRango`.
NUEVA_RAMA = r"""  // LIBRE: mostrar HUECOS disponibles, no la agenda de citas.
  // Antes caía en la rama esRango y nunca calculaba huecos.
  if (entrada.comando === 'LIBRE') {
    const dur = 40;                      // duración de referencia
    const AP = 10 * 60, CI = 20 * 60;    // 10:00 a 20:00 en minutos
    const ahora = new Date(entrada.ahoraISO);
    const AHOY = new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(ahora);
    const pAhora = {};
    for (const { type, value } of new Intl.DateTimeFormat('en-CA',
      { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false })
      .formatToParts(ahora)) pAhora[type] = value;
    const ahoraMin = Number(pAhora.hour === '24' ? '0' : pAhora.hour) * 60
                   + Number(pAhora.minute);

    const porFecha = {};
    for (const e of eventos) (porFecha[e.fecha] = porFecha[e.fecha] || []).push(e);

    const lineasLibre = [`*Huecos disponibles (${dur} min)*`];
    let totalHuecos = 0;

    for (let f = entrada.desde; f <= entrada.hasta; f = sumarDias(f, 1)) {
      const dow = new Date(f + 'T12:00:00Z').getUTCDay();
      if (dow === 0) {                   // domingo: cerrado
        continue;
      }
      const ocupados = porFecha[f] || [];
      const libres = [];
      for (let t = AP; t + dur <= CI; t += 30) {
        const fin = t + dur;
        const choca = ocupados.some(e => e.fin !== null &&
          t < e.fin + 10 && e.ini - 10 < fin);
        if (choca) continue;
        if (f === AHOY && t <= ahoraMin) continue;   // ya pasó
        libres.push(t);
        if (libres.length >= 8) break;
      }
      totalHuecos += libres.length;
      lineasLibre.push('');
      const etiqueta = f === AHOY ? 'Hoy' : fechaCorta(f);
      lineasLibre.push(`*${etiqueta}*`);
      lineasLibre.push(libres.length
        ? libres.map(a12h).join(', ')
        : 'Sin huecos libres.');
    }

    lineasLibre.push('');
    lineasLibre.push(totalHuecos
      ? `Total: *${totalHuecos} huecos* en el periodo.`
      : 'No hay huecos en el periodo.');
    return [{ json: { respuesta: lineasLibre.join('\n') } }];
  }

"""


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-libre.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    n = next((x for x in wf["nodes"] if x["name"] == "Formatear agenda"), None)
    if not n:
        print("no existe 'Formatear agenda'")
        return 1
    cod = n["parameters"]["jsCode"]
    if "LIBRE: mostrar HUECOS" in cod:
        print("ya estaba aplicado")
        return 0

    # Insertar la rama LIBRE justo antes de la rama esRango.
    # OJO: la indentación real es de 2 espacios, no 4 (el código va dentro
    # de una función async que n8n envuelve). Se busca la variante exacta.
    marca = None
    for cand in ("  } else if (entrada.esRango) {",
                 "} else if (entrada.esRango) {",
                 "} else if (entrada.esRango){"):
        if cand in cod:
            marca = cand
            break
    if not marca:
        print("no encontré el punto de inserción; reviso el código:")
        for i, l in enumerate(cod.split("\n")):
            if "esRango" in l:
                print(f"  linea {i}: {l!r}")
        return 1
    print(f"  marca encontrada: {marca!r}")

    cod_nuevo = cod.replace(marca, NUEVA_RAMA + marca, 1)
    n["parameters"]["jsCode"] = cod_nuevo

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificar la sintaxis del JS con node
    import subprocess
    ruta = r"G:\Barberia\archivos\_chk_agenda.js"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("(async function () {\n" + cod_nuevo + "\n})();\n")
    p = subprocess.run([r"C:\Program Files\nodejs\node.exe", "--check", ruta],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    print(f"  sintaxis JS: {'OK' if p.returncode == 0 else 'ERROR'}")
    if p.returncode != 0:
        print(" ", (p.stderr or "")[:300])
    os.remove(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())