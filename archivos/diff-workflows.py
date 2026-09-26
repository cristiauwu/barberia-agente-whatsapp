#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporta los workflows de n8n y los compara con los archivos entregados.

Sirve para saber EXACTAMENTE que cambio antes de tocar nada.
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
    "barberiaRecordatorios": "BarberiaAgenteFLUJO-2-RECORDATORIOS.json",
}


def sh(*args):
    p = subprocess.run([DOCKER, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def export(wid):
    """Exporta un workflow del contenedor al host."""
    remote = f"/tmp/{wid}.json"
    local = os.path.join(TMP, f"export-{wid}.json")
    sh("exec", "barberia-n8n", "n8n", "export:workflow", f"--id={wid}",
       f"--output={remote}")
    sh("cp", f"barberia-n8n:{remote}", local)
    if not os.path.exists(local):
        return None
    data = json.load(open(local, encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def norm_params(node):
    """Parametros comparables: sin credenciales ni posiciones."""
    return json.dumps(node.get("parameters", {}), sort_keys=True,
                      ensure_ascii=False)


def main():
    for wid, fname in WF.items():
        print("=" * 70)
        print("WORKFLOW:", wid)
        print("=" * 70)
        exported = export(wid)
        if not exported:
            print("  No se pudo exportar")
            continue
        mine = json.load(open(os.path.join(BASE, fname), encoding="utf-8"))

        en = {n["name"]: n for n in exported.get("nodes", [])}
        mn = {n["name"]: n for n in mine.get("nodes", [])}

        solo_n8n = sorted(set(en) - set(mn))
        solo_mio = sorted(set(mn) - set(en))
        print(f"  nodos en n8n: {len(en)} | en mi archivo: {len(mn)}")
        if solo_n8n:
            print("  SOLO EN N8N:", solo_n8n)
        if solo_mio:
            print("  SOLO EN MI ARCHIVO:", solo_mio)

        print("\n  -- Nodos con parametros DISTINTOS --")
        dif = 0
        for name in sorted(set(en) & set(mn)):
            if norm_params(en[name]) != norm_params(mn[name]):
                dif += 1
                print(f"\n  [{name}]")
                # Mostrar que claves cambian
                pe = en[name].get("parameters", {})
                pm = mn[name].get("parameters", {})
                for k in sorted(set(pe) | set(pm)):
                    if json.dumps(pe.get(k), sort_keys=True) != \
                       json.dumps(pm.get(k), sort_keys=True):
                        print(f"     clave distinta: {k}")
        if not dif:
            print("     (ninguno)")

        print("\n  -- Credenciales referenciadas en n8n --")
        for n in exported.get("nodes", []):
            creds = n.get("credentials") or {}
            if creds:
                for ctype, c in creds.items():
                    print(f"     {n['name']:<38} {ctype} -> {c.get('id')} ({c.get('name')})")


if __name__ == "__main__":
    sys.exit(main())