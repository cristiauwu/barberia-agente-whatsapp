# -*- coding: utf-8 -*-
"""Comprobaciones SOLO LECTURA: Supabase RLS/REST y Google Sheets publico."""
import json, ssl, urllib.request, urllib.error, io

ctx = ssl.create_default_context()
buf = []
def w(*a):
    line = " ".join(str(x) for x in a)
    buf.append(line)
    print(line)

def http(url, headers=None, method="GET"):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, ("ERROR: %r" % (e,)).encode()

REF = "zucgrcyzofelmiorvxhb"
BASE = "https://%s.supabase.co" % REF
KEYS = {
  "publishable_A": "sb_publishable_vTcYIYR7h7n357m9dohntQ_lEPaJENw",
  "publishable_B": "sb_publishable_lXrbroKwpGHTqqCYoMpb3w_9FUwRjiM",
}

w("#" * 78)
w("# 1. SUPABASE — /rest/v1/ con claves publishable (SOLO LECTURA)")
w("#" * 78)

for kname, k in KEYS.items():
    w("\n===== clave: %s (%s...) =====" % (kname, k[:24]))
    for hdr_name, hdr_val in (("apikey", k), ("Authorization", "Bearer " + k)):
        st, h, body = http(BASE + "/rest/v1/", {hdr_name: hdr_val, "Accept": "application/json"})
        w("  [%s] GET /rest/v1/ -> HTTP %s" % (hdr_name, st))
        w("     body[:400] = %r" % body[:400].decode("utf-8", "replace"))

# descubrir tablas via OpenAPI
w("\n===== Descubrimiento de tablas via /rest/v1/ (OpenAPI) =====")
for kname, k in KEYS.items():
    st, h, body = http(BASE + "/rest/v1/", {"apikey": k, "Authorization": "Bearer " + k})
    if st == 200:
        try:
            doc = json.loads(body.decode("utf-8"))
            paths = sorted(doc.get("paths", {}).keys())
            w("  [%s] paths (%d): %s" % (kname, len(paths), paths))
        except Exception as e:
            w("  [%s] no parseable: %r" % (kname, e))
    else:
        w("  [%s] HTTP %s" % (kname, st))

TABLES = ["barber_clientes","barber_citas","barber_servicios","barber_operadores",
          "barber_consentimiento","barber_conocimiento","barber_pausas",
          "barber_bloqueos","barber_escalaciones","barber_auditoria",
          "barber_lista_espera","n8n_chat_histories"]

w("\n===== SELECT * FROM cada tabla (solo lectura) =====")
for kname, k in KEYS.items():
    for t in TABLES:
        st, h, body = http(BASE + "/rest/v1/%s?select=*&limit=3" % t,
                           {"apikey": k, "Authorization": "Bearer " + k,
                            "Accept": "application/json", "Range": "0-2"})
        txt = body[:500].decode("utf-8", "replace")
        w("  [%s] %-24s HTTP %-4s %s" % (kname, t, st, txt))

w("\n" + "#" * 78)
w("# 2. GOOGLE SHEETS — acceso publico a la hoja de citas")
w("#" * 78)
SID = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
urls = [
  ("csv export (anonimo)", "https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=941506024" % SID),
  ("gviz csv (anonimo)",   "https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&gid=941506024" % SID),
  ("htmlview (anonimo)",   "https://docs.google.com/spreadsheets/d/%s/htmlview" % SID),
  ("xlsx export (anonimo)", "https://docs.google.com/spreadsheets/d/%s/export?format=xlsx" % SID),
]
for name, u in urls:
    st, h, body = http(u, {"User-Agent": "Mozilla/5.0"})
    w("\n-- %s -> HTTP %s  (%d bytes)" % (name, st, len(body)))
    if st == 200:
        w("   primeras lineas:\n%s" % body[:900].decode("utf-8", "replace"))

with io.open(r"G:\Barberia\_audit\_sec_supabase_sheets.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(buf))