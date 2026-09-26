#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita todos los resource locators (calendarios, hojas) del workflow activo
y los compara con lo entregado, para saber el alcance real del dano.
"""
import json
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
BASE = r"G:\Barberia"
TMP = r"G:\Barberia\archivos"

CAL_ESPERADO = ("391cc272be5989fd77b45438f2f61e9c754501eb5d1b3a4a76d57a9da3083918"
                "@group.calendar.google.com")
SHEET_ESPERADO = "17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY"


def sh(*args):
    p = subprocess.run([DOCKER, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def export(wid):
    remote = f"/tmp/{wid}.json"
    local = os.path.join(TMP, f"export-{wid}.json")
    sh("exec", "barberia-n8n", "n8n", "export:workflow", f"--id={wid}",
       f"--output={remote}")
    sh("cp", f"barberia-n8n:{remote}", local)
    data = json.load(open(local, encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def loc(v):
    if isinstance(v, dict) and v.get("__rl"):
        val = v.get("value")
        return f"value='{val}' name='{v.get('cachedResultName')}'"
    return f"(no es locator: {type(v).__name__})"


def main():
    data = export("barberiaAgenteUncensored")
    mine = json.load(open(os.path.join(BASE, "BarberiaAgenteFLUJO-1-UNCENSORED.json"),
                          encoding="utf-8"))
    mn = {n["name"]: n for n in mine["nodes"]}

    print("=" * 74)
    print("CALENDARIOS (Google Calendar)")
    print("=" * 74)
    for n in data["nodes"]:
        if "googleCalendarTool" not in n.get("type", ""):
            continue
        cal = n["parameters"].get("calendar")
        ok = isinstance(cal, dict) and cal.get("value") == CAL_ESPERADO
        print(f"  {'OK ' if ok else 'MAL'}  {n['name']:<20} {loc(cal)}")

    print()
    print("=" * 74)
    print("HOJAS DE CALCULO (Google Sheets)")
    print("=" * 74)
    for n in data["nodes"]:
        if "googleSheets" not in n.get("type", ""):
            continue
        if "Trigger" in n.get("type", ""):
            continue
        doc = n["parameters"].get("documentId")
        ok = isinstance(doc, dict) and doc.get("value") == SHEET_ESPERADO
        print(f"  {'OK ' if ok else 'MAL'}  {n['name']:<34} {loc(doc)}")

    print()
    print("=" * 74)
    print("DETALLE DEL NODO DE REGISTRO")
    print("=" * 74)
    nodo = next((n for n in data["nodes"]
                 if n["name"] == "Registrar en hoja de citas"), None)
    if nodo:
        prm = nodo["parameters"]
        cols = prm.get("columns", {})
        print("  toolDescription:", "PRESENTE" if prm.get("toolDescription") else "AUSENTE")
        print("  matchingColumns:", cols.get("matchingColumns"))
        print("  columnas con valor asignado:")
        vals = cols.get("value") or {}
        if not vals:
            print("     (NINGUNA: se escribirian filas vacias)")
        for k, v in vals.items():
            print(f"     - {k!r} = {str(v)[:70]}")
        print("  esquema (columnas que espera):")
        for s in cols.get("schema", []):
            print(f"     - {s.get('id')!r}")

    print()
    print("=" * 74)
    print("HERRAMIENTA DE ESCALAMIENTO")
    print("=" * 74)
    nt = next((n for n in data["nodes"]
               if n["name"] == "Notificar al encargado"), None)
    if nt:
        prm = nt["parameters"]
        for k in ("authentication", "specifyBody", "specifyHeaders", "method", "url"):
            print(f"  {k}: {json.dumps(prm.get(k), ensure_ascii=False)}")
        body = (prm.get("parametersBody") or {}).get("values", [])
        print("  campos del body:")
        for b in body:
            print(f"     - {b.get('name')}: valueProvider={b.get('valueProvider')!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())