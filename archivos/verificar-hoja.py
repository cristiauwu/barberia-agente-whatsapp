#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica el estado REAL de la hoja de citas SIN MODIFICARLA.

Metodo por defecto: descarga del export CSV publico de la hoja (solo lectura,
cero efectos secundarios). Metodo alternativo `--metodo n8n`: crea un workflow
temporal con webhook que hace un GET a la API de Sheets y lo BORRA al terminar
(util si la hoja deja de ser publica).

Comprobaciones:
  1. La hoja responde y el encabezado se lee.
  2. El encabezado real coincide EXACTAMENTE (mismo orden) con el `schema` del
     nodo 'Append or update row in sheet' (workflow barberiaRecordatorios).
  3. Todas las columnas del `schema` del nodo 'Registrar en hoja de citas'
     (workflow barberiaAgenteUncensored) existen en el encabezado real.
  4. 'Execution ID' existe. Es CRITICO: sin ella el flujo de recordatorios
     muere con "Column names were updated after the node's setup".
  5. Ninguna cabecera lleva espacios sobrantes, SALVO la excepcion
     documentada 'Día ' (D + i-acentuada + a + un espacio final): es
     intencional porque asi la referencian los nodos y el Code del flujo 2.
  6. No hay cabeceras vacias ni duplicadas.
  7. Los ID existentes parecen IDs de evento de Google Calendar
     (20+ caracteres, minusculas y digitos, sin espacios ni acentos).
  8. Avisos de calidad de datos (celdas criticas vacias, ID sospechoso).

Uso:
    uv run python verificar-hoja.py
    uv run python verificar-hoja.py --metodo n8n

Salida: OK/FALLO por comprobacion + resumen. Sale con 0 si todo pasa.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

# ---------------------------------------------------------------- constantes

HOJA_ID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
GID = "941506024"
NOMBRE_PESTANA = "Hoja 1"
CSV_PUBLICO = (
    f"https://docs.google.com/spreadsheets/d/{HOJA_ID}"
    f"/export?format=csv&gid={GID}"
)

N8N = "http://localhost:5678/api/v1"
N8N_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJjYmQ1ZGQ2Yi05NzJlLTRlZmYtYWVlNC03MTAzOWJmM2E5MDIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmZkZmNiNDQtZmRiMi00MDUwLTg3MWMtMGJkMDI5NGRiOTYwIiwiaWF0IjoxNzkwMjk4ODczfQ."
    "s04weO8S72yEn6ip2rCGE4wCt-wPw22xVWJij-lF4wc"
)

# Los 2 nodos con esquema de columnas. Los otros 2 (el trigger y el lector)
# no guardan esquema: el trigger lee TODAS las columnas y el lector filtra
# por el valor de 'ID'.
NODOS_CON_ESQUEMA = (
    ("agente", "barberiaAgenteUncensored", "Registrar en hoja de citas"),
    ("recordatorios", "barberiaRecordatorios", "Append or update row in sheet"),
)
NODOS_SIN_ESQUEMA = (
    ("barberiaRecordatorios", "Google Sheets Trigger"),
    ("barberiaRecordatorios", "OBTENER INFO DE CITA ELIMINADA"),
)

# La UNICA cabecera que puede (y debe) terminar en espacio. Es intencional.
EXCEPCION_ESPACIO = "D\u00eda "          # 'Día '

# IDs de relleno vistos en pruebas; NO son IDs de Calendar.
IDS_SOSPECHOSOS = {"provisional", "unique_id_placeholder", "placeholder",
                   "test", "prueba", "cita", "sin-id", "n/a"}

# Un ID de evento de Google Calendar es base32hex en minusculas, sin separadores.
RE_ID_CALENDAR = re.compile(r"^[a-z0-9]{20,}$")

COLUMNAS_CRITICAS = ("ID", "Estatus", "Nombre", "Servicio", "D\u00eda ", "Hora")

# ---------------------------------------------------------------- estado

_fallos: list[str] = []
_avisos: list[str] = []
_total = 0


def check(cond: bool, msg: str) -> bool:
    global _total
    _total += 1
    print(("  OK    " if cond else "  FALLO ") + msg)
    if not cond:
        _fallos.append(msg)
    return bool(cond)


def aviso(msg: str) -> None:
    _avisos.append(msg)
    print("  AVISO " + msg)


def cabecera(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# ---------------------------------------------------------------- transporte


def http_json(url: str, headers: dict | None = None, timeout: int = 60):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def api_n8n(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", N8N_KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:  # noqa: BLE001
        return None, str(e)


# ---------------------------------------------------------------- lecturas


def leer_por_csv() -> tuple[list[str], list[list[str]]]:
    """Export CSV publico. Solo lectura, no toca la hoja."""
    req = urllib.request.Request(CSV_PUBLICO,
                                 headers={"User-Agent": "verificador-hoja/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        texto = r.read().decode("utf-8-sig")
    filas = list(csv.reader(io.StringIO(texto)))
    enc = filas[0] if filas else []
    datos = [f for f in filas[1:] if any(c.strip() for c in f)]
    return enc, datos


def leer_por_n8n() -> tuple[list[str], list[list[str]]]:
    """Workflow temporal de SOLO LECTURA (GET) que se borra al terminar."""
    ruta = "ver" + uuid.uuid4().hex[:8]
    cred = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                     "name": "Google Sheets account"}}
    wf = {
        "name": "_verificar-hoja-tmp",
        "nodes": [
            {"parameters": {"httpMethod": "POST", "path": ruta,
                            "responseMode": "lastNode", "options": {}},
             "type": "n8n-nodes-base.webhook", "typeVersion": 2,
             "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
             "webhookId": str(uuid.uuid4())},
            {"parameters": {
                "method": "GET",
                "url": (f"https://sheets.googleapis.com/v4/spreadsheets/"
                        f"{HOJA_ID}/values/'{NOMBRE_PESTANA}'!A1:Z1000"),
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [220, 0], "id": str(uuid.uuid4()),
             "name": "Leer hoja", "credentials": cred},
        ],
        "connections": {"Webhook": {"main": [[{"node": "Leer hoja",
                                               "type": "main", "index": 0}]]}},
        "settings": {"executionOrder": "v1"},
    }
    st, creado = api_n8n("POST", "/workflows", wf)
    if st not in (200, 201):
        raise RuntimeError(f"no pude crear el workflow temporal: {st} {creado}")
    wid = creado["id"]
    try:
        api_n8n("POST", f"/workflows/{wid}/activate", {})
        time.sleep(5)
        req = urllib.request.Request(f"http://localhost:5678/webhook/{ruta}",
                                     data=b"{}", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as r:
            datos = json.loads(r.read().decode())
        filas = datos.get("values") or []
        enc = filas[0] if filas else []
        return enc, [f for f in filas[1:] if any(str(c).strip() for c in f)]
    finally:
        api_n8n("POST", f"/workflows/{wid}/deactivate", {})
        time.sleep(1)
        api_n8n("DELETE", f"/workflows/{wid}")


def leer_esquemas() -> dict:
    """GET de los workflows; extrae el `schema` de los 2 nodos de Sheets."""
    out = {}
    for clave, wf_id, nodo in NODOS_CON_ESQUEMA:
        st, wf = api_n8n("GET", f"/workflows/{wf_id}")
        if st != 200:
            raise RuntimeError(f"no pude leer {wf_id}: {st} {wf}")
        n = next((x for x in wf["nodes"] if x["name"] == nodo), None)
        if n is None:
            raise RuntimeError(f"{wf_id} no tiene el nodo {nodo!r}")
        cols = (n.get("parameters") or {}).get("columns") or {}
        out[clave] = {
            "workflow": wf_id,
            "nodo": nodo,
            "tipo": n["type"],
            "operacion": (n.get("parameters") or {}).get("operation"),
            "sheet": ((n.get("parameters") or {}).get("sheetName") or {}).get("value"),
            "schema": [s["id"] for s in (cols.get("schema") or [])],
            "escribe": sorted((cols.get("value") or {}).keys()),
        }
    return out


# ---------------------------------------------------------------- principal


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verifica la hoja de citas sin modificarla.")
    ap.add_argument("--metodo", choices=["csv", "n8n"], default="csv",
                    help="csv = export publico (por defecto); n8n = webhook temporal")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    cabecera("VERIFICACION DE LA HOJA DE CITAS — SOLO LECTURA, NO SE MODIFICA NADA")
    print(f"  Hoja     : {HOJA_ID}")
    print(f"  Pestana  : gid={GID}  ('{NOMBRE_PESTANA}')")
    print(f"  Metodo   : {args.metodo}")
    print(f"  Excepcion: la cabecera {EXCEPCION_ESPACIO!r} termina en espacio "
          f"A PROPOSITO")

    # ---- 0. esquemas de n8n (referencia) ------------------------------
    cabecera("0. ESQUEMAS GUARDADOS EN LOS NODOS DE N8N (referencia)")
    try:
        esq = leer_esquemas()
    except Exception as e:  # noqa: BLE001
        print(f"  FALLO no pude leer los esquemas de n8n: {e}")
        _fallos.append("leer los esquemas de n8n")
        esq = None
    if esq:
        for clave, _, _ in NODOS_CON_ESQUEMA:
            d = esq[clave]
            print()
            print(f"  - {d['nodo']!r}  [{d['workflow']}]")
            print(f"      tipo={d['tipo']}  operacion={d['operacion']}  "
                  f"sheet={d['sheet']!r}")
            print(f"      schema ({len(d['schema'])}): {d['schema']}")
            print(f"      escribe: {d['escribe']}")
        print()
        print("  Nodos SIN esquema guardado (por eso no se les compara):")
        for wf_id, nodo in NODOS_SIN_ESQUEMA:
            print(f"      - {nodo!r} [{wf_id}]")

    # ---- 1. encabezado real -------------------------------------------
    cabecera("1. ENCABEZADO REAL DE LA HOJA")
    try:
        enc, filas = (leer_por_n8n() if args.metodo == "n8n" else leer_por_csv())
    except Exception as e:  # noqa: BLE001
        print(f"  FALLO no pude leer la hoja: {e}")
        print()
        print("RESULTADO: no se pudo verificar.")
        return 1

    if not check(bool(enc), f"la hoja responde y tiene encabezado "
                            f"({len(enc)} columnas)"):
        print()
        print("RESULTADO: la hoja no devolvio encabezado.")
        return 1
    for i, c in enumerate(enc):
        print(f"      {i + 1:>2}. {c!r}")
    print(f"  filas de datos leidas: {len(filas)}")

    # ---- 2. vs schema del flujo de recordatorios ----------------------
    cabecera("2. ENCABEZADO VS NODO 'Append or update row in sheet' (flujo 2)")
    if esq:
        esperado = esq["recordatorios"]["schema"]
        check(enc == esperado,
              "el encabezado coincide EXACTAMENTE (mismo orden) con el schema")
        if enc != esperado:
            solo_hoja = [c for c in enc if c not in esperado]
            solo_nodo = [c for c in esperado if c not in enc]
            if solo_hoja:
                print(f"      en la hoja y NO en el schema: {solo_hoja}")
            if solo_nodo:
                print(f"      en el schema y NO en la hoja: {solo_nodo} "
                      f"<-- esto causa 'Column names were updated after the node's setup'")
            if set(enc) == set(esperado):
                print("      (mismas columnas, ORDEN distinto)")

    # ---- 3. vs schema del agente --------------------------------------
    cabecera("3. ESQUEMA DEL NODO 'Registrar en hoja de citas' (flujo 1)")
    if esq:
        esp_a = esq["agente"]["schema"]
        faltan = [c for c in esp_a if c not in enc]
        check(not faltan,
              f"las {len(esp_a)} columnas que espera el agente existen en la hoja")
        if faltan:
            print(f"      FALTAN en la hoja: {faltan}")
        check(enc[:len(esp_a)] == esp_a,
              "las primeras columnas coinciden 1:1 y en orden con el agente")

    # ---- 4. Execution ID ----------------------------------------------
    cabecera("4. COLUMNA CRITICA 'Execution ID' (recordatorios)")
    tiene_exec = "Execution ID" in enc
    check(tiene_exec, "'Execution ID' existe en el encabezado")
    if not tiene_exec:
        print("      SIN esta columna el flujo de recordatorios FALLA siempre")
        print("      con: \"Column names were updated after the node's setup\".")

    if esq:
        usa_exec = "Execution ID" in esq["recordatorios"]["schema"]
        check(usa_exec, "el nodo del flujo 2 declara 'Execution ID' en su schema")

    # ---- 5. espacios sobrantes ----------------------------------------
    cabecera("5. ESPACIOS SOBRANTES EN LOS ENCABEZADOS")
    mal = [c for c in enc if c != EXCEPCION_ESPACIO and c != c.strip()]
    check(not mal, "ninguna cabecera tiene espacios al inicio/fin "
                   f"(excepto la excepcion {EXCEPCION_ESPACIO!r})")
    if mal:
        for c in mal:
            print(f"      con espacios sobrantes: {c!r}")
    check(EXCEPCION_ESPACIO in enc,
          f"la excepcion {EXCEPCION_ESPACIO!r} esta presente (esperada)")
    if EXCEPCION_ESPACIO in enc:
        print(f"      {EXCEPCION_ESPACIO!r} = 'D'+i-acentuada+'a'+ESPACIO -> "
              f"bytes={EXCEPCION_ESPACIO.encode('utf-8')}")
    dobles = [c for c in enc if "  " in c or "\t" in c]
    check(not dobles, "ninguna cabecera tiene espacios dobles ni tabuladores")

    # ---- 6. duplicados / vacias ---------------------------------------
    cabecera("6. CABECERAS VACIAS O DUPLICADAS")
    vacias = [i for i, c in enumerate(enc) if not c.strip()]
    check(not vacias, "no hay cabeceras vacias")
    if vacias:
        print(f"      indices vacios: {[i + 1 for i in vacias]}")
    dup = sorted({c for c in enc if enc.count(c) > 1})
    check(not dup, f"no hay cabeceras duplicadas (encontradas: {dup})")

    # ---- 7. IDs tipo Google Calendar ----------------------------------
    cabecera("7. LOS 'ID' PARECEN IDs DE EVENTO DE GOOGLE CALENDAR")
    col_id = enc.index("ID") if "ID" in enc else 0
    ids = [(i + 2, f[col_id] if col_id < len(f) else "")
           for i, f in enumerate(filas)]
    buenos, malos, raros = [], [], []
    for num, v in ids:
        v = (v or "").strip()
        if not v:
            raros.append((num, v, "vacio"))
        elif v.lower() in IDS_SOSPECHOSOS:
            malos.append((num, v, "relleno de prueba"))
        elif RE_ID_CALENDAR.match(v):
            buenos.append((num, v))
        else:
            malos.append((num, v, "no es base32hex de 20+"))

    print(f"  IDs en la hoja: {len(ids)}  |  validos: {len(buenos)}  |  "
          f"invalidos: {len(malos)}  |  vacios: {len(raros)}")
    for num, v, why in malos:
        print(f"      fila {num}: {v!r}  ({why})")
    for num, v, why in raros:
        print(f"      fila {num}: {v!r}  ({why})")
    if ids:
        check(not malos, "todos los 'ID' no vacios parecen IDs de Google Calendar")
        check(not raros, "ningun 'ID' esta vacio")
    else:
        aviso("la hoja no tiene filas de datos: no se pudo comprobar el formato de ID")

    # ---- 8. calidad de datos (avisos) ---------------------------------
    cabecera("8. AVISOS DE CALIDAD DE DATOS (no son fallos de esquema)")
    idx = {c: i for i, c in enumerate(enc)}
    for col in COLUMNAS_CRITICAS:
        if col not in idx:
            continue
        j = idx[col]
        n = sum(1 for f in filas if not (f[j] if j < len(f) else "").strip())
        if n:
            aviso(f"{n} fila(s) con {col!r} vacio")
    if "Execution ID" in idx:
        j = idx["Execution ID"]
        n = sum(1 for f in filas if not (f[j] if j < len(f) else "").strip())
        if filas and n == len(filas):
            aviso(f"'Execution ID' esta vacio en TODAS las filas ({n}): "
                  f"los recordatorios no se podran cancelar/quitar")
        elif n:
            aviso(f"'Execution ID' vacio en {n} de {len(filas)} filas")
    j = idx.get("Numero celular")
    if j is not None:
        n = sum(1 for f in filas if not (f[j] if j < len(f) else "").strip())
        if n:
            aviso(f"{n} fila(s) sin 'Numero celular': no recibiran recordatorios")
    if not _avisos:
        print("  sin avisos.")

    # ---- resumen -------------------------------------------------------
    cabecera("RESUMEN")
    print(f"  Comprobaciones : {_total}")
    print(f"  OK             : {_total - len(_fallos)}")
    print(f"  FALLOS         : {len(_fallos)}")
    print(f"  Avisos         : {len(_avisos)}")
    if _fallos:
        print()
        print("  FALLOS:")
        for f in _fallos:
            print(f"    - {f}")
    print()
    if _fallos:
        print(f"RESULTADO: {len(_fallos)} de {_total} comprobaciones FALLARON")
        return 1
    print(f"RESULTADO: {_total} de {_total} comprobaciones PASARON")
    if _avisos:
        print(f"           (con {len(_avisos)} aviso(s) de calidad de datos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())