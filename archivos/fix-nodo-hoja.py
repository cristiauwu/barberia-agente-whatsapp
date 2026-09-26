#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el nodo de Google Sheets del workflow activo en n8n.

Problema detectado: al reseleccionar la credencial, n8n reseteo los
resource locators dependientes (documento y calendario) y se perdio el
mapeo de columnas y la toolDescription.

Este script toma el workflow exportado de n8n y restaura SOLO:
  1. Nodo "Registrar en hoja de citas"  -> documento/columnas/toolDescription
  2. Nodo "Agendar cita"                -> calendario (quedo vacio)
  3. Nodo "AI Agent"                    -> system prompt actualizado
Mantiene intactas las credenciales reales que ya existen en n8n.
"""
import json
import os
import shutil
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
BASE = r"G:\Barberia"
TMP = r"G:\Barberia\archivos"
WID = "barberiaAgenteUncensored"
ENTREGADO = os.path.join(BASE, "BarberiaAgenteFLUJO-1-UNCENSORED.json")


def sh(*args):
    p = subprocess.run([DOCKER, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def exportar(wid, destino):
    remoto = f"/tmp/{wid}-fix.json"
    rc, out, err = sh("exec", "barberia-n8n", "n8n", "export:workflow",
                      f"--id={wid}", f"--output={remoto}")
    if rc != 0:
        print("export fallo:", err[:300])
        return None
    sh("cp", f"barberia-n8n:{remoto}", destino)
    if not os.path.exists(destino):
        return None
    d = json.load(open(destino, encoding="utf-8"))
    return d[0] if isinstance(d, list) else d


def nodo(wf, nombre):
    for n in wf["nodes"]:
        if n["name"] == nombre:
            return n
    raise KeyError(nombre)


def main():
    # --- 1. Respaldo de lo que hay ahora -------------------------------
    backup = os.path.join(TMP, f"ANTES-{WID}.json")
    actual = exportar(WID, backup)
    if not actual:
        print("No pude exportar el workflow. Abortado.")
        return 1
    print(f"Respaldo guardado en: {backup}")

    mio = json.load(open(ENTREGADO, encoding="utf-8"))
    cambios = []

    # --- 2. Restaurar el nodo de Google Sheets ------------------------
    n_act = nodo(actual, "Registrar en hoja de citas")
    n_ref = nodo(mio, "Registrar en hoja de citas")
    antes_doc = (n_act["parameters"].get("documentId") or {}).get("value")
    n_act["parameters"] = json.loads(json.dumps(n_ref["parameters"]))
    despues_doc = n_act["parameters"]["documentId"]["value"]
    cambios.append(f"Registrar en hoja de citas: documento {antes_doc} -> {despues_doc}")
    cambios.append(f"  columnas restauradas: {list(n_act['parameters']['columns']['value'].keys())}")
    cambios.append("  toolDescription restaurada")

    # --- 3. Restaurar el calendario de "Agendar cita" ------------------
    n_act = nodo(actual, "Agendar cita")
    n_ref = nodo(mio, "Agendar cita")
    antes_cal = (n_act["parameters"].get("calendar") or {}).get("value")
    n_act["parameters"]["calendar"] = json.loads(
        json.dumps(n_ref["parameters"]["calendar"]))
    cambios.append(f"Agendar cita: calendario '{antes_cal}' -> BARBER")

    # --- 4. Restaurar el system prompt ---------------------------------
    n_act = nodo(actual, "AI Agent")
    n_ref = nodo(mio, "AI Agent")
    antes_len = len(n_act["parameters"]["options"]["systemMessage"])
    n_act["parameters"]["options"]["systemMessage"] = \
        n_ref["parameters"]["options"]["systemMessage"]
    despues_len = len(n_act["parameters"]["options"]["systemMessage"])
    cambios.append(f"AI Agent: prompt {antes_len} -> {despues_len} chars")

    print()
    print("=== CAMBIOS A APLICAR ===")
    for c in cambios:
        print("  " + c)

    # --- 5. Escribir y reimportar --------------------------------------
    salida = os.path.join(TMP, f"FIX-{WID}.json")
    json.dump([actual], open(salida, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    remoto = "/files/FIX-uno.json"
    dest = os.path.join(BASE, "archivos", "FIX-uno.json")
    shutil.copy(salida, dest)

    rc, out, err = sh("exec", "barberia-n8n", "n8n", "import:workflow",
                      f"--input=/files/{os.path.basename(dest)}")
    print()
    print("=== IMPORTACION ===")
    print((out + err).strip()[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())