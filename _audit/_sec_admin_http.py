# -*- coding: utf-8 -*-
"""Pruebas HTTP contra el servidor del panel admin (127.0.0.1:8765).
Solo lectura / peticiones que no modifican nada. No se intenta adivinar la contrasena."""
import http.client, io, json, ssl, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOST = "127.0.0.1"; PORT = 8765
buf = []
def w(*a):
    s = " ".join(str(x) for x in a); buf.append(s); print(s)

def req(method, path, headers=None, body=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=15)
    try:
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read(4000)
        return r.status, dict(r.getheaders()), data
    except Exception as e:
        return None, {}, ("ERR %r" % (e,)).encode()
    finally:
        c.close()

w("#" * 80); w("# 1. Rutas SIN autenticacion"); w("#" * 80)
for path in ("/", "/admin", "/admin/", "/api/admin/sesion", "/api/admin/resumen",
             "/api/admin/clientes", "/api/admin/citas", "/api/admin/reportes",
             "/api/admin/servicios", "/api/admin/version", "/api/admin/../.env-admin",
             "/../../.env-admin", "/archivos/admin/.env-admin", "/.env",
             "/../.env", "/archivos/admin/.pwd-sitio.txt", "/api/admin/mensajes",
             "/dashboard.html", "/index.html", "/favicon.ico"):
    st, h, b = req("GET", path, {"Host": f"localhost:{PORT}"})
    w("  GET %-38s -> HTTP %-5s len=%-6d %s" % (path, st, len(b), b[:130].decode("utf-8","replace").replace("\n"," ")))

w("\n" + "#" * 80); w("# 2. Errores: ¿se filtra DSN, ruta o traza?"); w("#" * 80)
for method, path, body, hdr in (
    ("POST", "/api/admin/login", b"{", {"Content-Type": "application/json"}),
    ("POST", "/api/admin/login", b'{"password": 12345}', {"Content-Type": "application/json"}),
    ("POST", "/api/admin/login", b'{"password": "a"*2000}', {"Content-Type": "application/json"}),
    ("POST", "/api/admin/login", b'{"password":"x"}', {"Content-Type": "text/plain"}),
    ("POST", "/api/admin/login", b'{"password":"' + b"x"*5000 + b'"}', {"Content-Type": "application/json"}),
    ("GET", "/api/admin/clientes?page=abc", None, {}),
    ("GET", "/api/admin/clientes?page=99999999999999999999&pageSize=99999", None, {}),
    ("GET", "/api/admin/clientes?buscar=" + "a"*500, None, {}),
    ("GET", "/api/admin/citas?fecha=2026-13-99", None, {}),
    ("GET", "/api/admin/citas?fecha=' OR 1=1--", None, {}),
    ("POST", "/api/admin/servicios/precio", b'{"clave":"corte","precio":"150","version":1}', {"Content-Type": "application/json"}),
    ("POST", "/api/admin/mensajes", b'{"jid":"5214501111805@s.whatsapp.net","texto":"x","idempotencyKey":"abcdefghij1234567"}', {"Content-Type": "application/json"}),
    ("POST", "/api/admin/logout", b'{}', {"Content-Type": "application/json"}),
    ("DELETE", "/api/admin/clientes", None, {}),
    ("POST", "/api/admin/noexiste", b'{}', {"Content-Type": "application/json"}),
):
    st, h, b = req(method, path, dict(hdr, **{"Host": f"localhost:{PORT}"}), body)
    txt = b[:400].decode("utf-8", "replace")
    leak = any(k in txt for k in ("postgresql://", "barber_admin", "scrypt:", "ADMIN_", "Traceback", "File \"", "/home/", "C:\\", "G:\\", "sends.sqlite3", "Dlc2b2it"))
    w("  %-6s %-42s -> HTTP %-5s LEAK=%s\n       %s" % (method, path[:42], st, leak, txt.replace("\n"," ")))

w("\n" + "#" * 80); w("# 3. Cookies de sesion"); w("#" * 80)
st, h, b = req("POST", "/api/admin/login", {"Content-Type": "application/json", "Host": f"localhost:{PORT}"}, b'{"password":"contrasena-incorrecta-de-prueba-1234"}')
w("  POST login (password incorrecta) -> HTTP %s" % st)
w("  Set-Cookie: %s" % h.get("Set-Cookie"))
w("  cuerpo: %s" % b[:250].decode("utf-8","replace"))

w("\n" + "#" * 80); w("# 4. Cabeceras de seguridad y CSRF/Host/Origin"); w("#" * 80)
st, h, b = req("GET", "/", {"Host": f"localhost:{PORT}"})
for k in sorted(h):
    if k.lower() in ("content-security-policy","x-frame-options","x-content-type-options",
                     "referrer-policy","strict-transport-security","cache-control",
                     "set-cookie","server","content-type"):
        w("  %s: %s" % (k, h[k]))

w("\n  -- Host invalido --")
st, h, b = req("GET", "/api/admin/sesion", {"Host": "evil.example.com"})
w("  GET /api/admin/sesion con Host: evil.example.com -> HTTP %s  %s" % (st, b[:200].decode("utf-8","replace")))

w("\n  -- Origin invalido en POST --")
st, h, b = req("POST", "/api/admin/logout", {"Content-Type":"application/json","Host": f"localhost:{PORT}","Origin":"https://evil.example.com"}, b'{}')
w("  POST /api/admin/logout con Origin malo -> HTTP %s  %s" % (st, b[:200].decode("utf-8","replace")))

w("\n  -- Cookie de sesion inventada --")
st, h, b = req("GET", "/api/admin/resumen", {"Host": f"localhost:{PORT}", "Cookie": "admin_session=inventado123"})
w("  GET /api/admin/resumen con cookie inventada -> HTTP %s  %s" % (st, b[:200].decode("utf-8","replace")))

w("\n" + "#" * 80); w("# 5. Metodos peligrosos"); w("#" * 80)
for m in ("PUT","PATCH","DELETE","HEAD","OPTIONS","TRACE"):
    try:
        st, h, b = req(m, "/api/admin/clientes", {"Host": f"localhost:{PORT}"})
        w("  %-7s /api/admin/clientes -> HTTP %s" % (m, st))
    except Exception as e:
        w("  %-7s -> %r" % (m, e))

io.open(r"G:\Barberia\_audit\_sec_admin_http.txt","w",encoding="utf-8").write("\n".join(buf))
print("\n[escrito]")