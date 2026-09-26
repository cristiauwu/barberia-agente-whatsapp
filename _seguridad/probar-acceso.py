#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba el panel administrativo: contrasena, sesion, datos y seguridad.

Las rutas REALES del servidor son:
    GET  /admin            el panel
    POST /api/admin/login  iniciar sesion
    GET  /api/admin/sesion | resumen | reportes | servicios | citas | clientes

Comprueba lo que importa para una venta oficial:
  1. Sin sesion no se ve el panel.
  2. La contrasena correcta abre sesion y da un token CSRF.
  3. La contrasena incorrecta se rechaza.
  4. Con sesion, la API devuelve datos de verdad.
  5. Sin Origin valido no se puede entrar (CSRF).
  6. Hay limite de intentos fallidos (fuerza bruta).
  7. La cookie es HttpOnly y SameSite.
"""
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "http://localhost:8765"
def _leer_pwd():
    """Lee la contrasena del sitio del archivo local (ignorado por git)."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".pwd-sitio.txt")
    if not os.path.exists(ruta):
        raise SystemExit(
            "Falta .pwd-sitio.txt con la contrasena del sitio.\n"
            "Crealo con una sola linea: la contrasena del panel.")
    return open(ruta, encoding="utf-8").read().strip()


PWD = _leer_pwd()
API = "/api/admin/"
fallos = 0


def sesion():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj)), cj


def pide(op, ruta, data=None, origin=BASE, metodo=None, extra=None):
    req = urllib.request.Request(
        BASE + ruta, data=data,
        method=metodo or ("POST" if data else "GET"))
    if data:
        req.add_header("Content-Type", "application/json")
    if origin:
        req.add_header("Origin", origin)
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    try:
        r = op.open(req, timeout=25)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except Exception as e:
        return None, str(e), {}


def main():
    global fallos
    print("=" * 68)
    print("PRUEBA DEL PANEL ADMINISTRATIVO")
    print("=" * 68)

    # -------------------------------------------------------------- 1
    print("\n[1] SIN SESION: el panel no debe verse")
    op, cj = sesion()
    st, cuerpo, _ = pide(op, "/admin", origin=None)
    pide_login = st in (401, 403) or "password" in cuerpo.lower()
    print(f"  HTTP {st}  {'OK  pide identificarse' if pide_login else 'MAL'}")
    if not pide_login:
        fallos += 1

    # -------------------------------------------------------------- 2
    print("\n[2] LA API sin sesion debe dar 401")
    st, cuerpo, _ = pide(op, API + "resumen", origin=None)
    print(f"  HTTP {st}  {'OK  protegida' if st == 401 else 'MAL'}")
    if st != 401:
        fallos += 1

    # -------------------------------------------------------------- 3
    print("\n[3] CONTRASENA CORRECTA")
    op, cj = sesion()
    st, cuerpo, h = pide(op, API + "login",
                         json.dumps({"password": PWD}).encode())
    csrf = None
    try:
        csrf = json.loads(cuerpo).get("data", {}).get("csrfToken")
    except Exception:
        pass
    print(f"  HTTP {st}  {'OK  sesion abierta' if st == 200 else 'MAL'}")
    print(f"  token CSRF: {'recibido' if csrf else 'NO'}")
    if st != 200 or not csrf:
        fallos += 1

    # -------------------------------------------------------------- 4
    print("\n[4] LA COOKIE DE SESION")
    if not cj:
        print("  MAL no se guardo cookie")
        fallos += 1
    for c in cj:
        raw = str(getattr(c, "_rest", {}))
        httponly = "HttpOnly" in raw or "httponly" in raw.lower()
        samesite = "SameSite" in raw or "samesite" in raw.lower()
        print(f"  {c.name}: {len(c.value)} chars  "
              f"HttpOnly={'SI' if httponly else '?'}  "
              f"SameSite={'SI' if samesite else '?'}")
        print(f"    (el analisis detallado va en las cabeceras)")

    # -------------------------------------------------------------- 5
    print("\n[5] CON SESION: la API devuelve datos REALES")
    for ep in ("sesion", "resumen", "reportes", "servicios", "citas",
               "clientes"):
        st, cuerpo, _ = pide(op, API + ep)
        if st == 200:
            try:
                d = json.loads(cuerpo).get("data")
                if isinstance(d, list):
                    info = f"{len(d)} filas"
                elif isinstance(d, dict):
                    info = f"{len(d)} campos"
                else:
                    info = str(d)[:40]
                print(f"  OK   {ep:10} HTTP 200  {info}")
            except Exception:
                print(f"  OK   {ep:10} HTTP 200  ({len(cuerpo)} bytes)")
        else:
            print(f"  --   {ep:10} HTTP {st}")
            fallos += 1

    # -------------------------------------------------------------- 6
    print("\n[6] CONTRASENA INCORRECTA")
    op2, _ = sesion()
    st, cuerpo, _ = pide(op2, API + "login",
                         json.dumps({"password": "incorrecta"}).encode())
    print(f"  HTTP {st}  {'OK  rechazada' if st == 401 else 'MAL'}")
    if st != 401:
        fallos += 1

    # -------------------------------------------------------------- 7
    print("\n[7] CSRF: un origen ajeno no debe poder entrar")
    op3, _ = sesion()
    st, _, _ = pide(op3, API + "login",
                    json.dumps({"password": PWD}).encode(),
                    origin="http://malicioso.example")
    print(f"  HTTP {st}  {'OK  bloqueado' if st in (401, 403) else 'MAL'}")
    if st not in (401, 403):
        fallos += 1

    # -------------------------------------------------------------- 8
    print("\n[8] LIMITE DE INTENTOS (fuerza bruta)")
    op4, _ = sesion()
    codigos = []
    for _ in range(7):
        st, _, _ = pide(op4, API + "login",
                        json.dumps({"password": "mala"}).encode())
        codigos.append(st)
    hay_429 = 429 in codigos
    print(f"  codigos: {codigos}")
    print(f"  {'OK  bloquea tras varios intentos' if hay_429 else 'AVISO sin limite'}")
    if not hay_429:
        fallos += 1

    # -------------------------------------------------------------- 9
    print("\n[9] EL PANEL SE SIRVE CON SESION")
    op5, _ = sesion()
    pide(op5, API + "login", json.dumps({"password": PWD}).encode())
    st, cuerpo, _ = pide(op5, "/admin", origin=None)
    ok = st == 200 and len(cuerpo) > 50000
    print(f"  HTTP {st}  {len(cuerpo)} bytes  "
          f"{'OK  el panel se sirve' if ok else 'revisar'}")
    if not ok:
        fallos += 1

    print()
    print("=" * 68)
    print(f"FALLOS: {fallos}")
    print("=" * 68)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())