#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sincroniza los archivos JSON del repo con el estado real de n8n.

Motivo: se aplicaron correcciones directamente en n8n (Switch de estados,
filtro de aviso, Evolution local, credencial). Los archivos del repositorio
quedaron desactualizados, y las pruebas leen los ARCHIVOS. Hay que
reflejar el estado real para que las pruebas validen lo que de verdad corre.

Exporta ambos workflows y los guarda con el mismo formato que los originales.
"""
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
TMP = r"G:\Barberia\archivos"

MAPA = {
    "barberiaAgenteUncensored": "BarberiaAgenteFLUJO-1-UNCENSORED.json",
    "barberiaRecordatorios": "BarberiaAgenteFLUJO-2-RECORDATORIOS.json",
}


def exportar(wid):
    remoto = f"/tmp/{wid}-sync.json"
    local = os.path.join(TMP, f"sync-{wid}.json")
    subprocess.run([DOCKER, "exec", "barberia-n8n", "n8n", "export:workflow",
                    f"--id={wid}", f"--output={remoto}"], capture_output=True)
    subprocess.run([DOCKER, "cp", f"barberia-n8n:{remoto}", local],
                   capture_output=True)
    if not os.path.exists(local):
        return None
    d = json.load(open(local, encoding="utf-8"))
    return d[0] if isinstance(d, list) else d


def main():
    for wid, destino in MAPA.items():
        wf = exportar(wid)
        if not wf:
            print(f"  {wid}: no se pudo exportar")
            continue

        ruta = os.path.join(r"G:\Barberia", destino)
        # Respaldo del archivo previo
        import shutil
        shutil.copy(ruta, os.path.join(TMP, f"ANTES-sync-{destino}"))

        # Limpiar los datos que no son del flujo
        wf.pop("pinData", None)
        wf["active"] = False   # en el repo se guarda inactivo a proposito

        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)
            f.write("\n")

        txt = json.dumps(wf, ensure_ascii=False)
        print(f"  {destino}")
        print(f"     nodos: {len(wf['nodes'])}  conexiones: {len(wf['connections'])}")
        print(f"     clave del vendedor: "
              f"{'SI <-- problema' if 'DC64CCC' in txt else 'no'}")
        print(f"     servidor del vendedor: "
              f"{'SI <-- problema' if 'easypanel.host' in txt else 'no'}")

    print()
    print("=== VERIFICACION: el Switch en el ARCHIVO ===")
    d = json.load(open(os.path.join(r"G:\Barberia", MAPA["barberiaRecordatorios"]),
                      encoding="utf-8"))
    wf = d[0] if isinstance(d, list) else d
    sw = next(n for n in wf["nodes"] if n["name"] == "Switch")
    for v in sw["parameters"]["rules"]["values"]:
        vals = [c["rightValue"] for c in v["conditions"]["conditions"]]
        print(f"  {v.get('outputKey'):<12} acepta {vals}")
    return 0


if __name__ == "__main__":
    sys.exit(main())