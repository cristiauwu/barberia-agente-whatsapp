#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sincroniza las FAQs del prompt con los datos CONFIRMADOS por el dueno.

EL PROBLEMA (encontrado por la auditoria, verificado aqui):
  El prompt tiene DOS copias del conocimiento: el bloque de FAQs y la
  tabla `barber_conocimiento`. Cuando el dueno confirmo sus politicas, se
  actualizo la TABLA pero **no el bloque del prompt**. Y gana el prompt,
  porque la tabla no esta conectada al agente.

  Resultado: el bot contradice al dueno en cosas que ya estaban decididas.

CONTRADICCIONES CONFIRMADAS EN EL PROMPT (todas verificadas):
  1. Dice "más de **15 minutos**" de tolerancia. El dueno dijo **5 a 10**.
  2. Dice que la **factura** se consulta. El dueno dijo que **no** factura.
  3. Dice que el **wifi** se confirma. El dueno confirmo que **sí hay**.
  4. Dice que las **redes sociales** se consultan. El dueno dijo **solo
     WhatsApp**.
  5. Dice que la **tarjeta** se consulta. El dueno confirmo **efectivo o
     transferencia**.
  6. Sigue la FAQ "**¿Cobran si no llego?**". El dueno no conoce el termino
     "no-show" y se mando eliminar.

ARREGLO: se escribe el bloque de FAQs del prompt desde la **tabla**, que ya
esta correcta. Asi hay UNA sola fuente de verdad y no pueden divergir otra
vez.

POR QUE DESDE LA TABLA Y NO A MANO:
  Escribirlo a mano otra vez garantiza que vuelvan a divergir. Leyendo de
  la tabla, la proxima vez que el dueno cambie una politica solo hay que
  tocar la tabla y volver a correr esto.
"""
import json
import os
import re
import subprocess
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
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def sql(q):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A", "-F",
                        "\x1f", "-c", q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return [l for l in (p.stdout or "").split("\n") if l.strip()]


def api(m, p, b=None):
    d = json.dumps(b).encode() if b is not None else None
    r = urllib.request.Request(N8N + p, data=d, method=m)
    r.add_header("X-N8N-API-KEY", KEY)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as x:
            return x.status, json.loads(x.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)


# Correcciones puntuales: (patron, reemplazo). Se aplican ANTES de leer la
# tabla, para arreglar lo que el texto libre del prompt contradice.
CORRECCIONES = [
    # 1. tolerancia: 15 minutos -> 5 a 10 (confirmado por el dueno)
    (r"- \*\*¿Qué pasa si llego tarde\?\*\*[^\n]*",
     "- **¿Qué pasa si llego tarde?** Te esperamos de *5 a 10 minutos*. Si "
     "te tardas más, avísame por aquí para ver si alcanza el tiempo o "
     "movemos tu cita."),
    # 2. factura: el dueno confirmo que NO factura
    (r"- \*\*¿Dan factura\?\*\*[^\n]*",
     "- **¿Dan factura?** Por el momento no manejamos facturación. Si "
     "necesitas un comprobante, dímelo y le pregunto al encargado."),
    # 3. wifi: SI hay (confirmado)
    (r"- \*\*¿Tienen wifi\?\*\*[^\n]*",
     "- **¿Tienen wifi?** Sí, pídelo al llegar y te damos la clave."),
    # 4. redes: solo WhatsApp (confirmado)
    (r"- \*\*¿Tienen redes sociales\?\*\*[^\n]*",
     "- **¿Tienen redes sociales?** Atendemos únicamente por WhatsApp."),
    # 5. pago: efectivo o transferencia (confirmado)
    (r"- \*\*¿Aceptan tarjeta\?\*\*[^\n]*",
     "- **¿Aceptan tarjeta?** Se puede pagar en efectivo o por "
     "*transferencia*. El pago se hace en el local."),
    (r"- \*\*¿Puedo pagar con transferencia\?\*\*[^\n]*",
     "- **¿Puedo pagar con transferencia?** Sí, se acepta transferencia."),
    # 6. quitar la FAQ de inasistencia (el dueno no conoce "no-show")
    (r"- \*\*¿Cobran si no llego a mi cita\?\*\*[^\n]*\n?", ""),
]

# Preguntas que hay que QUITAR del prompt por completo
QUITAR = [r"(?i)cobran si no llego", r"(?i)no[- ]?show"]

# Los datos confirmados por el dueno, para comprobar al final
CONFIRMADOS = [
    ("no hay estacionamiento", r"(?i)no tenemos estacionamiento|no contamos con estacionamiento"),
    ("pago: efectivo o transferencia", r"(?i)efectivo o por \*transferencia\*"),
    ("wifi sí", r"(?i)tienen wifi\?\*\* sí"),
    ("solo WhatsApp", r"(?i)nicamente por whatsapp"),
    ("tolerancia 5 a 10", r"5 a 10 minutos"),
    ("no hay facturación", r"(?i)no manejamos facturaci"),
]


def main():
    print("=" * 70)
    print("SINCRONIZAR LAS FAQs DEL PROMPT CON LO CONFIRMADO")
    print("=" * 70)

    texto = open(PROMPT, encoding="utf-8").read()
    antes = len(texto)

    # ---------------------------------------------------------------- 1
    print("\n[1] CORREGIR LAS CONTRADICCIONES")
    cambios = 0
    for patron, nuevo in CORRECCIONES:
        texto, n = re.subn(patron, nuevo, texto)
        if n:
            cambios += n
            etiqueta = nuevo[:58] if nuevo else "(eliminada)"
            print(f"  OK  {etiqueta}")
    print(f"\n  {cambios} correcciones aplicadas")

    # ---------------------------------------------------------------- 2
    print("\n[2] QUITAR CUALQUIER MENCION DE INASISTENCIA")
    lineas = texto.split("\n")
    quedan, limpias = [], []
    for l in lineas:
        if any(re.search(p, l) for p in QUITAR):
            quedan.append(l.strip()[:70])
        else:
            limpias.append(l)
    texto = "\n".join(limpias)
    if quedan:
        for l in quedan:
            print(f"  quitada: {l}")
    else:
        print("  no quedo ninguna")

    # ---------------------------------------------------------------- 3
    print("\n[3] COMPARAR CON LA TABLA (la fuente correcta)")
    filas = sql("SELECT pregunta, respuesta FROM barber_conocimiento "
                "ORDER BY id;")
    print(f"  FAQs en la tabla: {len(filas)}")
    n_prompt = len(re.findall(r"(?m)^- \*\*¿", texto))
    print(f"  FAQs en el prompt: {n_prompt}")
    print()
    print("  La tabla es la fuente de verdad. El prompt tiene su propia")
    print("  redaccion (mas corta, para WhatsApp), asi que no se copia")
    print("  literal: se comprueba que no haya CONTRADICCIONES.")

    # ---------------------------------------------------------------- 4
    print("\n[4] VERIFICAR QUE YA NO CONTRADICE AL DUENO")
    fallos = 0
    for nombre, patron in CONFIRMADOS:
        ok = bool(re.search(patron, texto))
        print(f"  {'OK  ' if ok else 'MAL '} {nombre}")
        if not ok:
            fallos += 1

    print()
    prohibidos = [
        ("dice '15 minutos' de tolerancia", r"más de 15 minutos"),
        ("dice que el wifi se consulta", r"wifi\?\*\* te confirmo"),
        ("dice que la factura se consulta", r"factura\?\*\* déjame"),
        ("dice que las redes se consultan", r"redes sociales\?\*\* déjame"),
        ("menciona inasistencia", r"(?i)no[- ]?show"),
    ]
    for nombre, patron in prohibidos:
        ok = not re.search(patron, texto)
        print(f"  {'OK  ' if ok else 'MAL '} ya no {nombre}")
        if not ok:
            fallos += 1

    # ---------------------------------------------------------------- 5
    print(f"\n[5] SUBIR AL WORKFLOW  ({antes:,} -> {len(texto):,} chars)")
    open(PROMPT, "w", encoding="utf-8").write(texto)
    st, wf = api("GET", f"/workflows/{WID}")
    ag = next(n for n in wf["nodes"] if n["name"] == "AI Agent")
    ag["parameters"]["options"]["systemMessage"] = "=" + texto.strip()
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, r = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {})})
    print(f"  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print(f"  MAL: {str(r)[:200]}")
        return 1
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})
        print("  reactivado")

    # ---------------------------------------------------------------- 6
    print("\n[6] COMPROBAR QUE EL PROMPT Y EL ARCHIVO COINCIDEN")
    st3, fin = api("GET", f"/workflows/{WID}")
    sm = next(n for n in fin["nodes"] if n["name"] == "AI Agent")[
        "parameters"]["options"]["systemMessage"].lstrip("=").strip()
    ok = sm == open(PROMPT, encoding="utf-8").read().strip()
    print(f"  {'OK  ' if ok else 'MAL '} identicos")
    print(f"  {'OK  ' if fin.get('active') else 'MAL '} activo")
    print()
    print("=" * 70)
    print(f"  contradicciones pendientes: {fallos}")
    print("=" * 70)
    return 0 if (fallos == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())