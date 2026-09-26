#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica las respuestas del dueno a las FAQs del negocio.

El dueno confirmo (respuestas textuales):
  - "no hay estacionamiento"          -> no hay
  - "transferencia"                   -> SI aceptan transferencia
  - "no se que es no show"            -> ELIMINAR esa FAQ del prompt: si el
                                         dueno no conoce el termino, el bot
                                         no debe usarlo con el cliente.
  - "5-10 minutos de tolerancia"      -> 5 a 10 minutos
  - "hay wifi"                        -> SI hay
  - "Solo whatsapp"                   -> el unico canal es WhatsApp

QUE HACE:
  1. Actualiza la tabla barber_conocimiento en Postgres (fuente de verdad).
  2. Actualiza el bloque de FAQs del prompt con esos datos.
  3. Quita las marcas de "propuesta" y las reemplaza por datos confirmados.
  4. Elimina toda mencion de "no-show" en el prompt del agente (el dueno no
     lo conoce, asi que el bot no debe mencionarlo al cliente).

Los estados del comando ESTADO del dueno SI pueden decir "no-shows": eso es
panel interno, no conversacion con el cliente.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"
PROMPT = r"G:\Barberia\prompt-sistema-agente-barberia.txt"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
ENV = r"G:\Barberia\.env"

# (patron de la pregunta, respuesta nueva) — datos CONFIRMADOS por el dueno
CONFIRMADAS = [
    (r"estacionamiento",
     "No tenemos estacionamiento. Puedes dejar el coche sobre la misma calle, "
     "junto al local.",
     "contexto"),
    (r"tarjeta|transferencia|forma de pago|m[eé]todo de pago|c[oó]mo pago",
     "Se puede pagar en efectivo o por *transferencia*. El pago se hace "
     "directo en el local.",
     "contexto"),
    (r"wifi",
     "Sí, tenemos wifi. Pídelo al llegar y te damos la clave.",
     "contexto"),
    (r"redes sociales|instagram|facebook|whatsapp oficial|canal",
     "Atendemos únicamente por WhatsApp. Aquí mismo puedes agendar y "
     "preguntar lo que necesites.",
     "contexto"),
    (r"tolerancia|llego tarde|voy a llegar tarde|retraso|puntual",
     "Te esperamos de *5 a 10 minutos*. Si te vas a tardar más, avísame por "
     "aquí para ver si alcanza el tiempo o movemos tu cita.",
     "contexto"),
    (r"ni[nñ]o|hijo|menor",
     "Sí, puedes traer a tu hijo. Se le hace el mismo corte desvanecido o "
     "tijera de *$150*.",
     "contexto"),
    (r"factura|facturaci[oó]n",
     "Por el momento no manejamos facturación. Si necesitas un comprobante, "
     "dímelo y le pregunto al encargado.",
     "contexto"),
]

# Preguntas que se ELIMINAN del prompt porque el dueno no las reconoce
ELIMINAR = [r"no[- ]?show", r"no llego a mi cita", r"cobran si no llego"]


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)


def sql(consulta):
    """Ejecuta SQL en el Postgres local."""
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
    pwd = ""
    if os.path.exists(ENV):
        for l in open(ENV, encoding="utf-8"):
            if l.startswith("POSTGRES_PASSWORD="):
                pwd = l.split("=", 1)[1].strip()
    p = subprocess.run([DOCKER, "exec", "-e", f"PGPASSWORD={pwd}",
                        "barberia-postgres", "psql", "-U", "barberia",
                        "-d", "barberia", "-t", "-A", "-c", consulta],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120, env=env)
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def esc(s):
    return s.replace("'", "''")


def main():
    print("=" * 68)
    print("1. ACTUALIZAR LA TABLA DE CONOCIMIENTO")
    print("=" * 68)
    n = 0
    for patron, resp, origen in CONFIRMADAS:
        out, err = sql(
            "UPDATE barber_conocimiento "
            f"SET respuesta = '{esc(resp)}', origen = '{origen}', "
            "actualizado_en = now() "
            f"WHERE pregunta ~* '{esc(patron)}' "
            "RETURNING pregunta;")
        if err and "ERROR" in err:
            print(f"  AVISO {patron[:24]}: {err[:90]}")
        elif out:
            for l in out.splitlines():
                print(f"  actualizada: {l[:60]}")
            n += 1
        else:
            print(f"  sin coincidencia: {patron[:30]}")

    print()
    print("=== eliminar las de 'no show' (el dueno no conoce el termino) ===")
    for pat in ELIMINAR:
        out, err = sql("DELETE FROM barber_conocimiento "
                       f"WHERE pregunta ~* '{esc(pat)}' RETURNING pregunta;")
        if out:
            for l in out.splitlines():
                print(f"  eliminada: {l[:60]}")

    out, _ = sql("SELECT count(*) FROM barber_conocimiento;")
    print(f"\n  FAQs en la tabla: {out}")

    print()
    print("=" * 68)
    print("2. ACTUALIZAR EL BLOQUE DE FAQs DEL PROMPT")
    print("=" * 68)
    if not os.path.exists(PROMPT):
        print("  no existe el prompt")
        return 1
    texto = open(PROMPT, encoding="utf-8").read()
    orig = texto

    # reemplazos directos de las respuestas viejas por las confirmadas
    REEMPLAZOS = [
        # estacionamiento
        (r"- \*\*¿Tienen estacionamiento\?\*\*[^\n]*",
         "- **¿Tienen estacionamiento?** No tenemos. Puedes dejar el coche "
         "sobre la misma calle, junto al local."),
        # tarjeta / transferencia
        (r"- \*\*¿Aceptan tarjeta\?\*\*[^\n]*",
         "- **¿Aceptan tarjeta?** Se puede pagar en efectivo o por "
         "*transferencia*. El pago se hace en el local."),
        (r"- \*\*¿Puedo pagar con transferencia\?\*\*[^\n]*",
         "- **¿Puedo pagar con transferencia?** Sí, se acepta transferencia."),
        # wifi
        (r"- \*\*¿Tienen wifi\?\*\*[^\n]*",
         "- **¿Tienen wifi?** Sí, pídelo al llegar y te damos la clave."),
        # redes
        (r"- \*\*¿Tienen redes sociales\?\*\*[^\n]*",
         "- **¿Tienen redes sociales?** Atendemos únicamente por WhatsApp."),
        # tolerancia
        (r"- \*\*¿Qué pasa si voy a llegar tarde\?\*\*[^\n]*",
         "- **¿Qué pasa si voy a llegar tarde?** Te esperamos de *5 a 10 "
         "minutos*. Si te tardas más, avísame por aquí."),
        (r"- \*\*¿Qué pasa si llego tarde\?\*\*[^\n]*",
         "- **¿Qué pasa si llego tarde?** Te esperamos de *5 a 10 minutos*."),
    ]
    for pat, nuevo in REEMPLAZOS:
        texto, k = re.subn(pat, nuevo, texto)
        if k:
            print(f"  actualizada: {nuevo[:64]}")

    # eliminar las lineas de no-show y cobro por inasistencia
    print()
    print("=== quitar menciones de no-show del prompt ===")
    lineas = texto.split("\n")
    fuera = []
    conservar = []
    for l in lineas:
        if re.search(r"no[- ]?show|si no llego|no llego a mi cita",
                     l, re.IGNORECASE):
            fuera.append(l.strip()[:70])
        else:
            conservar.append(l)
    texto = "\n".join(conservar)
    for f in fuera:
        print(f"  quitada: {f}")

    if texto == orig:
        print("\n  el prompt no cambio")
    else:
        open(PROMPT, "w", encoding="utf-8").write(texto)
        print(f"\n  prompt actualizado: {len(orig)} -> {len(texto)} caracteres")

    print()
    print("=" * 68)
    print("3. SUBIR EL PROMPT AL WORKFLOW")
    print("=" * 68)
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("  no pude leer el workflow")
        return 1
    ag = next(x for x in wf["nodes"] if x["name"] == "AI Agent")
    ag["parameters"]["options"]["systemMessage"] = "=" + texto.strip()
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, _ = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"  PUT -> HTTP {st2}")
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})
        print("  reactivado")

    print()
    print("=" * 68)
    print("4. VERIFICACION")
    print("=" * 68)
    st3, fin = api("GET", f"/workflows/{WID}")
    ag2 = next(x for x in fin["nodes"] if x["name"] == "AI Agent")
    sm = ag2["parameters"]["options"]["systemMessage"]
    pruebas = [
        ("estacionamiento confirmado", "No tenemos" in sm and
         "estacionamiento" in sm.lower()),
        ("transferencia mencionada", "transferencia" in sm.lower()),
        ("tolerancia 5 a 10", "5 a 10" in sm),
        ("wifi confirmado", "wifi" in sm.lower()),
        ("solo WhatsApp", "nicamente por WhatsApp" in sm),
        ("sin marca de propuesta", "(propuesta)" not in sm.lower()),
        ("SIN no-show en el prompt", "no-show" not in sm.lower()
         and "no show" not in sm.lower()),
    ]
    fallos = 0
    for nombre, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {nombre}")
        if not ok:
            fallos += 1
    print(f"\n  largo del prompt: {len(sm):,} caracteres")
    print(f"  FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())