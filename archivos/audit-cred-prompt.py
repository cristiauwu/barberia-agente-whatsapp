#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1) Compara el prompt del AI Agent en n8n vs el entregado (hash).
2) Lista las credenciales reales de n8n con sus IDs y tipos.
3) Verifica que cada credencial referenciada por los workflows exista.
"""
import hashlib
import json
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
BASE = r"G:\Barberia"
TMP = r"G:\Barberia\archivos"


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def export(wid):
    remote = f"/tmp/{wid}x.json"
    local = os.path.join(TMP, f"export-{wid}.json")
    subprocess.run([DOCKER, "exec", "barberia-n8n", "n8n", "export:workflow",
                    f"--id={wid}", f"--output={remote}"],
                   capture_output=True, text=True)
    subprocess.run([DOCKER, "cp", f"barberia-n8n:{remote}", local],
                   capture_output=True, text=True)
    data = json.load(open(local, encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def main():
    print("=" * 74)
    print("1) PROMPT DEL AI AGENT")
    print("=" * 74)
    data = export("barberiaAgenteUncensored")
    agent = next(n for n in data["nodes"] if n["name"] == "AI Agent")
    p_n8n = agent["parameters"]["options"]["systemMessage"]
    mine = json.load(open(os.path.join(BASE, "BarberiaAgenteFLUJO-1-UNCENSORED.json"),
                          encoding="utf-8"))
    m_agent = next(n for n in mine["nodes"] if n["name"] == "AI Agent")
    p_mio = m_agent["parameters"]["options"]["systemMessage"]

    print(f"  en n8n   : {len(p_n8n)} chars | sha1 {hashlib.sha1(p_n8n.encode()).hexdigest()[:12]}")
    print(f"  entregado: {len(p_mio)} chars | sha1 {hashlib.sha1(p_mio.encode()).hexdigest()[:12]}")
    print("  IDENTICOS" if p_n8n == p_mio else "  DIFERENTES <-- requiere atencion")

    print()
    print("=" * 74)
    print("2) CREDENCIALES REALES EN N8N")
    print("=" * 74)
    out = psql("SELECT id || ' | ' || name || ' | ' || type FROM credentials_entity ORDER BY name;")
    reales = {}
    for line in out.splitlines():
        if "|" not in line:
            continue
        cid, cname, ctype = [x.strip() for x in line.split("|", 2)]
        reales[cid] = (cname, ctype)
        print(f"  {cid}  {cname}  [{ctype}]")

    print()
    print("=" * 74)
    print("3) CADA REFERENCIA DE CREDENCIAL: EXISTE O NO")
    print("=" * 74)
    for wid in ("barberiaAgenteUncensored", "barberiaRecordatorios"):
        d = export(wid)
        print(f"\n  --- {wid} ---")
        for n in d.get("nodes", []):
            for ctype, c in (n.get("credentials") or {}).items():
                cid = c.get("id")
                existe = cid in reales
                estado = "OK " if existe else "FALTA"
                print(f"    {estado} {n['name']:<36} {ctype:<30} {cid} ({c.get('name')})")
                if not existe:
                    print(f"          ^^ ESTA CREDENCIAL NO EXISTE: el nodo fallara")
    return 0


if __name__ == "__main__":
    sys.exit(main())