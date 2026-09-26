#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra el valor concreto de cada parametro que difiere, para separar
ruido de normalizacion de n8n de cambios reales.
"""
import json
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
BASE = r"G:\Barberia"
TMP = r"G:\Barberia\archivos"

WF = {
    "barberiaAgenteUncensored": "BarberiaAgenteFLUJO-1-UNCENSORED.json",
}


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
    if not os.path.exists(local):
        return None
    data = json.load(open(local, encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def short(v, n=260):
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= n else s[:n] + " ...[cortado]"


def main():
    wid = "barberiaAgenteUncensored"
    exported = export(wid)
    mine = json.load(open(os.path.join(BASE, WF[wid]), encoding="utf-8"))
    en = {n["name"]: n for n in exported.get("nodes", [])}
    mn = {n["name"]: n for n in mine.get("nodes", [])}

    for name in sorted(set(en) & set(mn)):
        pe = en[name].get("parameters", {})
        pm = mn[name].get("parameters", {})
        difs = [k for k in sorted(set(pe) | set(pm))
                if json.dumps(pe.get(k), sort_keys=True, ensure_ascii=False) !=
                   json.dumps(pm.get(k), sort_keys=True, ensure_ascii=False)]
        if not difs:
            continue
        print("=" * 72)
        print("NODO:", name)
        print("=" * 72)
        for k in difs:
            print(f"\n  CLAVE: {k}")
            print(f"    EN N8N  : {short(pe.get(k))}")
            print(f"    ENTREGADO: {short(pm.get(k))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())