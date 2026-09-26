# -*- coding: utf-8 -*-
"""Pruebas dirigidas del panel: login con Origin correcto, rate limit, cookie flags,
y verificacion de coherencia del hash (SIN adivinar la contrasena)."""
import base64, hashlib, http.client, io, json, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOST, PORT = "127.0.0.1", 8765
ORIGIN = "http://localhost:8765"
HOSTHDR = "localhost:8765"
buf = []
def w(*a):
    s = " ".join(str(x) for x in a); buf.append(s); print(s)

def req(method, path, headers=None, body=None):
    c = http.client.HTTPConnection(HOST, PORT, timeout=15)
    try:
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, dict(r.getheaders()), r.read(3000)
    except Exception as e:
        return None, {}, ("ERR %r" % (e,)).encode()
    finally:
        c.close()

BASE = {"Host": HOSTHDR, "Origin": ORIGIN, "Content-Type": "application/json"}

w("#" * 80); w("# 1. Rate limit de login (5 intentos por IP / 15 min)"); w("#" * 80)
for i in range(1, 8):
    st, h, b = req("POST", "/api/admin/login", BASE,
                   json.dumps({"password": "contrasena-falsa-de-auditoria-%d-abcdefgh" % i}).encode())
    w("  intento %d -> HTTP %-4s %s | Set-Cookie=%s" % (
        i, st, b[:150].decode("utf-8","replace"), h.get("Set-Cookie")))

w("\n" + "#" * 80)
w("# 2. Coherencia del hash (SIN adivinar: se compara el hash guardado con la")
w("#    contrasena del archivo local .pwd-sitio.txt que el proyecto documenta)")
w("#" * 80)
env = {}
for line in io.open(r"G:\Barberia\archivos\admin\.env-admin", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k] = v
h = env.get("ADMIN_PASSWORD_HASH", "")
w("  ADMIN_PASSWORD_HASH = %s..." % h[:40])
w("  ADMIN_SESSION_SECRET longitud = %d (minimo exigido: 64) -> %s" % (
    len(env.get("ADMIN_SESSION_SECRET","")), len(env.get("ADMIN_SESSION_SECRET","")) >= 64))
w("  ADMIN_DB_DSN usa rol = %s" % env.get("ADMIN_DB_DSN","").split("//")[1].split(":")[0] if "//" in env.get("ADMIN_DB_DSN","") else "?")
w("  ADMIN_PRICE_DB_DSN usa rol = %s" % env.get("ADMIN_PRICE_DB_DSN","").split("//")[1].split(":")[0] if "//" in env.get("ADMIN_PRICE_DB_DSN","") else "?")
w("  ADMIN_BIND = %s   ADMIN_PORT = %s" % (env.get("ADMIN_BIND"), env.get("ADMIN_PORT")))
w("  ADMIN_PUBLIC_ORIGIN = %s" % env.get("ADMIN_PUBLIC_ORIGIN"))
w("  ADMIN_PRICE_UPDATES_ENABLED = %s" % env.get("ADMIN_PRICE_UPDATES_ENABLED"))

try:
    pwd = io.open(r"G:\Barberia\archivos\admin\.pwd-sitio.txt", encoding="utf-8").read().strip()
    kind, n, r, p, salt, expected = h.split(":")
    got = hashlib.scrypt(pwd.encode(), salt=base64.urlsafe_b64decode(salt), n=16384, r=8, p=1)
    w("  scrypt(contenido de .pwd-sitio.txt) coincide con ADMIN_PASSWORD_HASH -> %s" % (
        base64.urlsafe_b64encode(got).decode() == expected))
except Exception as e:
    w("  no se pudo verificar: %r" % (e,))

w("\n" + "#" * 80); w("# 3. Cookie: flags (analisis estatico sobre codigo + respuesta real)"); w("#" * 80)
w("  issue() en servidor-admin.py:214 -> 'admin_session=<tok>; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800'")
w("  + '; Secure' SOLO si self.secure (ADMIN_PUBLIC_ORIGIN https).")
w("  ADMIN_PUBLIC_ORIGIN actual = %s -> self.secure = False -> Secure AUSENTE." % env.get("ADMIN_PUBLIC_ORIGIN"))
w("  Justificacion en el codigo: HTTP solo se permite en localhost (App.__init__, linea 175).")

w("\n" + "#" * 80); w("# 4. Dashboard de produccion (puerto 8099): ¿tiene autenticacion?"); w("#" * 80)
def req2(port, method, path, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        c.request(method, path, headers=headers or {})
        r = c.getresponse(); return r.status, dict(r.getheaders()), r.read(2000)
    except Exception as e:
        return None, {}, ("ERR %r" % (e,)).encode()
    finally:
        c.close()

for port in (8099, 8101):
    for path in ("/", "/dashboard.html", "/archivos/admin/.env-admin", "/../.env"):
        st, h, b = req2(port, "GET", path)
        w("  puerto %-5s GET %-28s -> HTTP %-5s len=%s" % (port, path, st, len(b)))

st, h, b = req2(8099, "GET", "/")
w("\n  ¿El HTML servido en 8099 contiene datos personales de clientes?")
txt = b.decode("utf-8", "replace")
import re
w("  muestra de nombres/telefonos encontrados en los primeros 2000 bytes: %s" %
  re.findall(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", txt)[:10])

# descargar completo para buscar datos personales
c = http.client.HTTPConnection("127.0.0.1", 8099, timeout=30)
c.request("GET", "/")
r = c.getresponse(); full = r.read(2_000_000).decode("utf-8", "replace")
c.close()
w("  tamano completo del panel = %d bytes" % len(full))
nombres = sorted(set(re.findall(r"verif-cli\d+", full)))
telefonos = sorted(set(re.findall(r"\b\d{10}@s\.whatsapp\.net", full)))
w("  apariciones de jid 'verif-cli*' = %d" % len(nombres))
w("  apariciones de 'numero@s.whatsapp.net' = %d" % len(telefonos))
w("  ¿contiene la palabra 'telefono'/'celular'? %s" % ("si" if ("telefono" in full.lower() or "celular" in full.lower()) else "no"))
w("  cabeceras: %s" % {k: v for k, v in h.items() if k.lower() in ("cache-control","content-type","server")})

io.open(r"G:\Barberia\_audit\_sec_admin_http2.txt", "w", encoding="utf-8").write("\n".join(buf))
print("\n[escrito]")