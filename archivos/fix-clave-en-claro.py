#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Saca la API key de Evolution del texto plano de los workflows.

PROBLEMA (MEJORAS-BARBERIA.md seccion 12):
  La clave CLAVE_DEL_PROVEEDOR-... aparece EN CLARO en 5 lugares de los dos
  workflows. Quien vea el JSON puede enviar WhatsApp como el negocio.

ESTRATEGIA (por capas, de menor a mayor alcance):

  1. En n8n, la clave se guarda en una CREDENCIAL de tipo 'httpHeaderAuth'.
     Asi el workflow solo referencia el id de la credencial, no el secreto.
  2. Los nodos pasan a usar `authentication: genericCredentialType` con
     `genericAuthType: httpHeaderAuth` en lugar del header literal.
  3. Los archivos del repo se sanean: la clave se sustituye por un
     marcador y se documenta que vive en .env.evolution.

Nota: los nodos de tipo `toolHttpRequest` (herramienta del agente) soportan
credencial generica igual que httpRequest. Se aplica a ambos.
"""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
ENV_EVO = r"G:\Barberia\.env.evolution"
WIDS = ["barberiaAgenteUncensored", "barberiaRecordatorios"]
NOMBRE_CRED = "Evolution API"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def clave_evolution():
    """Lee la clave del .env.evolution (fuente unica de verdad)."""
    for linea in open(ENV_EVO, encoding="utf-8"):
        if linea.startswith("AUTHENTICATION_API_KEY="):
            return linea.split("=", 1)[1].strip()
    return None


def main():
    secreto = clave_evolution()
    if not secreto:
        print("no encontre AUTHENTICATION_API_KEY en", ENV_EVO)
        return 1
    print(f"clave leida de .env.evolution ({len(secreto)} chars) - no se imprime")

    # --- 1. Crear la credencial httpHeaderAuth si no existe -------------
    st, creds = api("GET", "/credentials")
    existente = None
    if st == 200:
        for c in creds.get("data", []):
            if c.get("name") == NOMBRE_CRED:
                existente = c
                break

    if existente:
        cred_id = existente["id"]
        print(f"  credencial ya existe: {cred_id}")
    else:
        st, res = api("POST", "/credentials", {
            "name": NOMBRE_CRED,
            "type": "httpHeaderAuth",
            "data": {"name": "apikey", "value": secreto},
        })
        print(f"  crear credencial -> HTTP {st}")
        if st not in (200, 201):
            print("  detalle:", str(res)[:300])
            return 1
        cred_id = res.get("id")
        print(f"  credencial creada: {cred_id}")

    # --- 2. Recablear los nodos ----------------------------------------
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            print(f"  {wid}: no se pudo leer")
            continue
        activo = wf.get("active")
        json.dump(wf, open(rf"G:\Barberia\archivos\ANTES-credencial-{wid}.json",
                           "w", encoding="utf-8"), ensure_ascii=False, indent=2)

        cambios = 0
        for n in wf["nodes"]:
            p = n.get("parameters", {})
            # Solo nodos HTTP que usan la clave literal
            if not ("httpRequest" in n["type"] or "toolHttpRequest" in n["type"]):
                continue
            params = (p.get("headerParameters") or {}).get("parameters") or []
            tiene_clave = any(
                (h.get("name") or "").lower() == "apikey"
                and secreto in str(h.get("value") or "")
                for h in params
            )
            if not tiene_clave:
                continue
            # Quitar el header literal y usar credencial generica
            p["headerParameters"] = {
                "parameters": [h for h in params
                               if (h.get("name") or "").lower() != "apikey"]
            }
            p["authentication"] = "genericCredentialType"
            p["genericAuthType"] = "httpHeaderAuth"
            n.setdefault("credentials", {})["httpHeaderAuth"] = {
                "id": cred_id, "name": NOMBRE_CRED}
            cambios += 1
            print(f"  {wid} :: {n['name']} -> usa la credencial")

        if not cambios:
            print(f"  {wid}: sin cambios")
            continue

        if activo:
            api("POST", f"/workflows/{wid}/deactivate", {})
        st2, res = api("PUT", f"/workflows/{wid}", {
            "name": wf["name"], "nodes": wf["nodes"],
            "connections": wf["connections"],
            "settings": wf.get("settings", {}),
        })
        print(f"  {wid} PUT -> HTTP {st2}")
        if st2 not in (200, 201):
            print("  detalle:", str(res)[:300])
            continue
        if activo:
            api("POST", f"/workflows/{wid}/activate", {})
            print(f"  {wid} reactivado")

    # --- 3. Verificacion: la clave ya no debe estar en los nodos --------
    print("\n=== VERIFICACION EN N8N ===")
    for wid in WIDS:
        st, wf = api("GET", f"/workflows/{wid}")
        if st != 200:
            continue
        txt = json.dumps(wf.get("nodes", []), ensure_ascii=False)
        n_veces = txt.count(secreto)
        print(f"  {'OK  ' if n_veces == 0 else 'MAL '} {wid}: clave en claro "
              f"{n_veces} veces")
    return 0


if __name__ == "__main__":
    sys.exit(main())