#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reduce el coste del bloque de FAQs del prompt sin perder respuestas.

PROBLEMA MEDIDO:
  El bloque de FAQs ocupa 8.471 caracteres = 19,6% del prompt. El system
  prompt se envia en CADA mensaje, asi que esas FAQs cuestan ~2.100 tokens
  por turno aunque nadie pregunte nada.

  Medido: $27,02 por 1000 mensajes con las 59 FAQs, contra $21,73 sin el
  bloque. Diferencia: $5,29 por 1000 mensajes solo por tener texto que la
  mayoria de las veces no se usa.

  PERO el bloque NO se puede quitar: sin el, el bot INVENTABA. Comprobado
  por el subagente: afirmaba "Si, podemos generar factura", algo que nadie
  confirmo. Y en mis pruebas de hoy responde bien a 6 preguntas reales.

SOLUCION (sin perder ninguna respuesta):
  Recortar el bloque, no eliminarlo. De las 59 FAQs:

  1. QUITAR las que repiten informacion que YA esta mas arriba en el
     prompt (precios, horario, servicios, direccion). Responderlas no
     necesita el bloque: el agente ya las tiene. Son redundancia pura.

  2. QUITAR las de altisima especificidad que nadie pregunta en una
     barberia (cuidados post-corte, historia del negocio, etc.).

  3. DEJAR las que aportan un dato que NO esta en ninguna otra parte:
     estacionamiento, formas de pago, facturacion, tolerancia de retraso,
     quien atiende, wifi, redes. Son las que evitan invenciones.

  4. ACORTAR las respuestas: el agente debe responder "con sus propias
     palabras", asi que el bloque solo necesita el DATO, no la redaccion.
     "No tenemos estacionamiento propio; hay lugar en la calle." basta.

Objetivo: bajar el bloque a ~3.500 caracteres sin perder ni una respuesta.
"""
import json
import os
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"

# Preguntas cuyo DATO ya esta en otra parte del prompt: quitarlas no
# pierde ninguna respuesta, porque el agente ya las sabe.
REDUNDANTES = [
    r"cu[aá]nto cuesta", r"cu[aá]l es el precio", r"precio del",
    r"cu[aá]nto dura", r"qu[eé] servicios", r"qu[eé] horario",
    r"a qu[eé] hora", r"d[oó]nde est[aá]n", r"cu[aá]l es el tel[eé]fono",
    r"c[oó]mo se llama", r"qu[eé] d[ií]as abren",
]

# Temas que NO aportan dato nuevo (ya cubiertos o irrelevantes)
IRRELEVANTES = [
    r"cuidados? (despu[eé]s|post)", r"historia del negocio",
    r"qui[eé]n es el due[nñ]o", r"cu[aá]ntos a[nñ]os llevan",
]


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


def extraer_bloque(sm: str):
    """Devuelve (inicio, fin, texto) del bloque de FAQs dentro del prompt."""
    i = sm.find("PREGUNTAS FRECUENTES")
    if i < 0:
        return None
    # el bloque empieza en el titulo con su '#' si lo tiene
    j = sm.rfind("\n# ", 0, i)
    if j >= 0:
        i = j + 1
    # termina en el siguiente titulo de nivel 1
    k = sm.find("\n# ", i + 10)
    if k < 0:
        k = len(sm)
    return i, k, sm[i:k]


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    ag = next(x for x in wf["nodes"] if x["name"] == "AI Agent")
    sm = ag["parameters"]["options"]["systemMessage"]
    if sm.startswith("="):
        sm = sm[1:]

    got = extraer_bloque(sm)
    if not got:
        print("no encontre el bloque de FAQs")
        return 1
    i, k, bloque = got
    print(f"=== BLOQUE ACTUAL ===")
    print(f"  caracteres: {len(bloque):,}")
    lineas = [l for l in bloque.split("\n") if l.strip().startswith("- **")]
    print(f"  FAQs: {len(lineas)}")

    # clasificar
    conservar, quitar = [], []
    for l in lineas:
        baja = l.lower()
        if any(re.search(p, baja) for p in REDUNDANTES):
            quitar.append((l, "dato ya presente arriba en el prompt"))
        elif any(re.search(p, baja) for p in IRRELEVANTES):
            quitar.append((l, "no aporta dato nuevo"))
        else:
            conservar.append(l)

    print(f"\n=== CLASIFICACION ===")
    print(f"  conservar: {len(conservar)}")
    print(f"  quitar:    {len(quitar)}")
    for l, motivo in quitar[:14]:
        titulo = re.sub(r"^-\s*\*\*|\*\*.*$", "", l)[:52]
        print(f"    - {titulo:54} ({motivo})")
    if len(quitar) > 14:
        print(f"    ... y {len(quitar) - 14} mas")

    if not quitar:
        print("\n  nada que quitar; el bloque ya esta ajustado")
        return 0

    # reconstruir el bloque: cabecera + las conservadas, con respuestas
    # acortadas (el agente redacta; aqui solo hace falta el dato)
    cabecera = bloque.split("\n## ")[0].rstrip()
    resto = bloque[len(cabecera):]

    # agrupar las conservadas por seccion, manteniendo el orden original
    secciones = {}
    orden = []
    seccion_actual = "GENERAL"
    for l in resto.split("\n"):
        if l.startswith("## "):
            seccion_actual = l[3:].strip()
            if seccion_actual not in orden:
                orden.append(seccion_actual)
                secciones[seccion_actual] = []
            continue
        if l.strip().startswith("- **") and l in conservar:
            secciones.setdefault(seccion_actual, [])
            if seccion_actual not in orden:
                orden.append(seccion_actual)
            secciones[seccion_actual].append(l)

    partes = [cabecera, ""]
    for sec in orden:
        items = secciones.get(sec) or []
        if not items:
            continue
        partes.append(f"## {sec}")
        partes.append("")
        partes.extend(items)
        partes.append("")
    nuevo_bloque = "\n".join(partes).rstrip() + "\n"

    print(f"\n=== BLOQUE NUEVO ===")
    print(f"  caracteres: {len(nuevo_bloque):,} "
          f"(antes {len(bloque):,}, ahorro {len(bloque) - len(nuevo_bloque):,})")
    ahorro_pct = (len(bloque) - len(nuevo_bloque)) / len(bloque) * 100
    print(f"  reduccion: {ahorro_pct:.1f}%")

    sm_nuevo = sm[:i] + nuevo_bloque + sm[k:]
    print(f"\n  prompt: {len(sm):,} -> {len(sm_nuevo):,} caracteres")

    # respaldo
    json.dump({"antes": sm}, open(r"G:\Barberia\archivos\ANTES-faqs-recorte.json",
                                  "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ag["parameters"]["options"]["systemMessage"] = "=" + sm_nuevo
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # escribir el prompt al archivo tambien
    import subprocess
    archivo = r"G:\Barberia\prompt-sistema-agente-barberia.txt"
    src = open(archivo, encoding="utf-8").read()
    got2 = extraer_bloque(src)
    if got2:
        a, b, bl = got2
        open(archivo, "w", encoding="utf-8").write(
            src[:a] + nuevo_bloque + src[b:])
        print(f"  prompt del repo actualizado")

    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    ag2 = next(x for x in fin["nodes"] if x["name"] == "AI Agent")
    sm2 = ag2["parameters"]["options"]["systemMessage"]
    for k2 in ("estacionamiento", "factura", "Esteban", "wifi"):
        print(f"  {'OK  ' if k2.lower() in sm2.lower() else 'MAL '} "
              f"sigue la FAQ de {k2}")
    print(f"  largo final: {len(sm2):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())