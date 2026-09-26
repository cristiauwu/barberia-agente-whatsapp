#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper para operar el stack de n8n desde Windows sin problemas de quoting.

Uso:
  uv run python docker-helper.py ps
  uv run python docker-helper.py logs n8n
  uv run python docker-helper.py sql "SELECT key FROM settings LIMIT 5;"
  uv run python docker-helper.py mcp-status
  uv run python docker-helper.py mcp-enable
"""
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
DOCKER_CONFIG = r"G:\Barberia\.docker"

os.environ["DOCKER_CONFIG"] = DOCKER_CONFIG


def run(*args, check=True):
    """Ejecuta docker con una lista de argumentos (sin quoting del shell)."""
    cmd = [DOCKER, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if check and p.returncode != 0:
        print(f"[exit {p.returncode}] {' '.join(args)}")
        if p.stderr.strip():
            print(p.stderr.strip())
    return p.returncode, p.stdout, p.stderr


def psql(sql):
    """Ejecuta SQL en el contenedor de Postgres."""
    return run("exec", "barberia-postgres", "psql", "-U", "barberia",
               "-d", "barberia", "-t", "-A", "-F", "|", "-c", sql)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]

    if cmd == "ps":
        rc, out, err = run("compose", "ps", "--format",
                           "{{.Name}}|{{.Status}}|{{.Ports}}",
                           cwd_ok=True) if False else run(
            "compose", "ps", "--format", "{{.Name}}|{{.Status}}|{{.Ports}}")
        print(out or err)
        return rc

    if cmd == "logs":
        svc = sys.argv[2] if len(sys.argv) > 2 else "n8n"
        rc, out, err = run("compose", "logs", "--tail", "40", svc)
        print(out or err)
        return rc

    if cmd == "sql":
        rc, out, err = psql(sys.argv[2])
        print(out or err)
        return rc

    if cmd == "sqlb64":
        # El SQL viaja en base64 porque Start-Process de PowerShell re-parte
        # los argumentos por espacios.
        import base64
        sql = base64.b64decode(sys.argv[2]).decode("utf-8")
        rc, out, err = psql(sql)
        print(out or err)
        return rc

    if cmd == "mcp-status":
        rc, out, _ = psql("SELECT key, value FROM settings WHERE key LIKE '%mcp%';")
        print("=== settings.mcp ===")
        print(out.strip() or "(sin filas: MCP no configurado)")
        # Comprobar el endpoint
        import urllib.request
        import json as _json
        body = _json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "probe", "version": "1"}},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:5678/mcp-server/http", data=body,
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                print("endpoint -> HTTP", r.status)
                print(r.read(300).decode(errors="replace"))
        except Exception as e:
            code = getattr(e, "code", None)
            print(f"endpoint -> {'HTTP ' + str(code) if code else e}")
        return 0

    if cmd == "mcp-enable":
        rc, out, err = psql(
            "INSERT INTO settings (key, value, load_on_startup) "
            "VALUES ('mcp.access.enabled', 'true', true) "
            "ON CONFLICT (key) DO UPDATE SET value = 'true';")
        print(out or err or "activado")
        return rc

    if cmd == "raw":
        rc, out, err = run(*sys.argv[2:])
        print(out or err)
        return rc

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())