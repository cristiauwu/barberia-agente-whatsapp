# -*- coding: utf-8 -*-
"""Supabase: determinar si RLS esta activo y si las tablas tienen datos. SOLO LECTURA."""
import io, json, sys, ssl, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ctx = ssl.create_default_context()
buf = []
def w(*a):
    line = " ".join(str(x) for x in a)
    buf.append(line); print(line)

REF = "zucgrcyzofelmiorvxhb"
BASE = "https://%s.supabase.co" % REF
K = "sb_publishable_vTcYIYR7h7n357m9dohntQ_lEPaJENw"

def http(url, headers=None, method="GET"):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, ("ERR %r" % (e,)).encode()

TABLES = ["barber_clientes","barber_citas","barber_servicios","barber_operadores",
          "barber_conocimiento","barber_pausas","barber_bloqueos","barber_escalaciones"]

w("### Conteo exacto (Prefer: count=exact) y Content-Range por tabla")
w("### Si Content-Range dice N>0 y el cuerpo es []  ->  RLS esta filtrando")
for t in TABLES:
    st, h, body = http(BASE + "/rest/v1/%s?select=*&limit=1" % t,
        {"apikey": K, "Accept": "application/json", "Prefer": "count=exact",
         "Range-Unit": "items", "Range": "0-0"})
    w("  %-22s HTTP %-4s Content-Range=%-12s Content-Profile=%s" % (
        t, st, h.get("Content-Range"), h.get("Content-Profile")))
    w("      cuerpo=%r" % body[:200].decode("utf-8","replace"))

w("\n### Intento de listar el catalogo de tablas por /rest/v1/<tabla_inexistente>")
st, h, body = http(BASE + "/rest/v1/zzz_no_existe?select=*",
                   {"apikey": K, "Accept": "application/json"})
w("  HTTP %s  %r" % (st, body[:300].decode("utf-8","replace")))

w("\n### ¿Existe el esquema 'graphql' publico (introspection anonima)?")
st, h, body = http(BASE + "/graphql/v1", {"apikey": K, "Accept": "application/json"})
w("  HTTP %s  %r" % (st, body[:300].decode("utf-8","replace")))

w("\n### Cabeceras de una respuesta 200 (para ver rol/policies)")
st, h, body = http(BASE + "/rest/v1/barber_servicios?select=*&limit=1", {"apikey": K})
for kk in sorted(h):
    if kk.lower().startswith(("content-","x-","server","date","transfer")):
        w("    %s: %s" % (kk, h[kk]))

with io.open(r"G:\Barberia\_audit\_sec_supabase2.txt","w",encoding="utf-8") as f:
    f.write("\n".join(buf))