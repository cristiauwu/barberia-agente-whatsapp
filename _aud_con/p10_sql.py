import sys, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, conn

out = []

def add(s):
    out.append(str(s))

add("== 1) LA TABLA SIGUE VIVA TRAS LOS INTENTOS DE INYECCION ==")
add(q("SELECT count(*) FROM barber_conocimiento")[1])

add("")
add("== 2) EJECUTAR LA INYECCION COMO PARAMETRIZADA (asi la usa n8n con $1) ==")
for payload in ["' OR 1=1 --", "'; DROP TABLE barber_conocimiento; --",
                "1'; SELECT pg_sleep(10); --"]:
    try:
        cols, rows = q("SELECT count(*) FROM public.barber_buscar_conocimiento(%s, 3)",
                       (payload,))
        add("payload=%r -> %s filas devueltas (SIN error)" % (payload, rows[0][0]))
    except Exception as e:
        add("payload=%r -> ERROR %s: %s" % (payload, type(e).__name__, e))
add("tabla tras todo: " + str(q("SELECT count(*) FROM barber_conocimiento")[1]))

add("")
add("== 3) EXPLAIN: consulta CON resultados ==")
for r in q("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM "
           "public.barber_buscar_conocimiento('cuanto cuesta el corte', 3)")[1]:
    add("  " + r[0])

add("")
add("== 4) EXPLAIN de la consulta desnuda que hace la funcion (plan del planner) ==")
for r in q("""EXPLAIN (ANALYZE, BUFFERS)
SELECT c.id, ts_rank(c.tsv, to_tsquery('public.spanish_unaccent','cort')) rank
FROM public.barber_conocimiento c
WHERE c.activo
  AND c.tsv @@ to_tsquery('public.spanish_unaccent','cort')
ORDER BY rank DESC, c.prioridad DESC, c.id ASC LIMIT 3""")[1]:
    add("  " + r[0])

add("")
add("== 5) Forzar seqscan vs indice: probar CON enable_seqscan=off ==")
try:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SET enable_seqscan = off")
            cur.execute("""EXPLAIN SELECT c.id FROM public.barber_conocimiento c
                WHERE c.tsv @@ to_tsquery('public.spanish_unaccent','cort')""")
            for r in cur.fetchall():
                add("  " + r[0])
except Exception as e:
    add("ERROR " + str(e))

add("")
add("== 6) La funcion es STABLE / no volatil? ==")
add(q("SELECT proname, provolatile, prosecdef, proisstrict "
      "FROM pg_proc WHERE proname IN ('barber_buscar_conocimiento','barber_buscar')")[1])

add("")
add("== 7) Definicion literal de la funcion EN VIVO ==")
add(q("SELECT pg_get_functiondef(oid) FROM pg_proc "
      "WHERE proname='barber_buscar_conocimiento'")[1][0][0])

add("")
add("== 8) config de texto en vivo ==")
add(q("SELECT cfgname, cfgnamespace::regnamespace FROM pg_ts_config "
      "WHERE cfgname LIKE 'spanish%'")[1])
add(q("SELECT t.alias, m.mapdict::regdictionary FROM pg_ts_config_map m "
      "JOIN pg_ts_config c ON c.oid=m.mapcfg "
      "JOIN ts_token_type('default') t ON t.tokid=m.maptokentype "
      "WHERE c.cfgname='spanish_unaccent' AND t.alias IN ('word','hword','hword_part') "
      "ORDER BY t.alias")[1])

add("")
add("== 9) unaccent funciona en ambos sentidos (prueba directa) ==")
add("depilacion encuentra depilación: " + str(q(
    "SELECT to_tsvector('public.spanish_unaccent','depilación') @@ "
    "to_tsquery('public.spanish_unaccent','depilacion')")[1]))
add("depilación encuentra depilacion: " + str(q(
    "SELECT to_tsvector('public.spanish_unaccent','depilacion') @@ "
    "to_tsquery('public.spanish_unaccent','depilación')")[1]))
add("config spanish DE FABRICA, sin acento: " + str(q(
    "SELECT to_tsvector('spanish','depilación') @@ to_tsquery('spanish','depilacion')")[1]))

add("")
add("== 10) limite fuera de rango ==")
for lim in [0, -5, 1, 21, 1000]:
    try:
        f, _ = q("SELECT count(*) FROM public.barber_buscar_conocimiento('corte', %s)",
                 (lim,))
        add("limite=%s -> %s filas" % (lim, f[0][0]))
    except Exception as e:
        add("limite=%s -> ERROR %s" % (lim, e))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\sqlcheck.txt", "w", encoding="utf-8").write(txt)
print("escrito")