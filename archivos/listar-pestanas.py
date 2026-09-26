#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obtiene la lista REAL de pestanas (nombre + gid) de la hoja del usuario.

El gid de la URL es el de la pestana que estabas viendo, que puede no ser
la primera. n8n necesita el gid de la pestana correcta.
"""
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SHEET_ID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"


def main():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("no pude leer la hoja:", e)
        return 1

    print("=" * 74)
    print("PESTANAS ENCONTRADAS (nombre -> gid)")
    print("=" * 74)

    # En el HTML de Sheets las pestanas salen como pares nombre/gid
    # Patron habitual: ["nombre",gid] dentro del JSON de configuracion
    pares = re.findall(r'\[\"([^\"]{1,60})\",(\d+)\]', html)
    vistos = set()
    for nombre, gid in pares:
        if gid in vistos:
            continue
        vistos.add(gid)
        print(f"  {nombre!r}  ->  gid={gid}")

    if not vistos:
        print("  no encontre pestanas con ese patron; busco ids sueltos...")
        for gid in sorted(set(re.findall(r'"gid[^0-9]{0,4}(\d{6,})', html))):
            print(f"  gid candidato: {gid}")

    print()
    # Probar el export CSV con cada gid para ver cual tiene los encabezados
    print("=" * 74)
    print("CUAL DE ELLAS TIENE LOS ENCABEZADOS DEL AGENTE")
    print("=" * 74)
    candidatos = sorted(vistos) or sorted(set(
        re.findall(r'"gid[^0-9]{0,4}(\d{6,})', html)))
    for gid in candidatos:
        u = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
             f"/export?format=csv&gid={gid}")
        try:
            rq = urllib.request.Request(u)
            rq.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(rq, timeout=30) as r:
                txt = r.read().decode("utf-8-sig", errors="replace")
            primera = txt.splitlines()[0] if txt.strip() else "(vacia)"
            ok = "ID" in primera and "Estatus" in primera
            print(f"  {'>>> ' if ok else '    '}gid={gid}: {primera[:80]}")
        except Exception as e:
            print(f"      gid={gid}: error {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())