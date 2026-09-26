#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica la sintaxis del JS de los nodos Code tal como n8n lo ejecuta.

n8n envuelve el código en una función async, así que el `return` de nivel
superior es válido. Mi verificador anterior lo metía dentro de otra función
sin cerrarla, de ahí el "Unexpected end of input".
"""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
NODE = r"C:\Program Files\nodejs\node.exe"


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def main():
    wf = api("/workflows/barberiaAgenteUncensored")
    codes = [n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.code"]
    print(f"nodos Code: {len(codes)}")
    print()
    fallos = 0
    for n in codes:
        cod = n["parameters"].get("jsCode", "")
        # n8n envuelve así: (async function () { <codigo> })()
        envuelto = ("(async function () {\n" + cod + "\n})();\n"
                    "console.log('OK');\n")
        ruta = rf"G:\Barberia\archivos\_syn_{n['id'][:8]}.js"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(envuelto)
        p = subprocess.run([NODE, "--check", ruta], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        ok = p.returncode == 0
        if not ok:
            fallos += 1
        print(f"  {'OK  ' if ok else 'MAL '}{n['name']}")
        if not ok:
            for l in (p.stderr or "").splitlines()[:4]:
                print(f"        {l[:120]}")
        os.remove(ruta)

    print()
    print(f"nodos con error de sintaxis: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())