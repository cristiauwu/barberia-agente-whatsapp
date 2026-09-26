# -*- coding: utf-8 -*-
"""Auditoria de datos personales en Postgres/Evolution. SOLO LECTURA."""
import os, sys, subprocess, io
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
env = dict(os.environ); env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
buf = []
def w(*a):
    line = " ".join(str(x) for x in a)
    buf.append(line); print(line)

def psql(container, user, db, sql):
    p = subprocess.run([DOCKER, "exec", "-i", container, "psql", "-U", user, "-d", db,
                        "-t", "-A", "-F", "|"],
                       input=sql, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180, env=env)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    return out, err

w("#" * 78); w("# CONTENEDORES"); w("#" * 78)
p = subprocess.run([DOCKER, "ps", "--format", "{{.Names}}|{{.Image}}|{{.Ports}}|{{.Status}}"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
w(p.stdout or p.stderr)

w("\n" + "#" * 78); w("# 1. n8n_chat_histories  (la memoria del agente)"); w("#" * 78)
q = """
SELECT 'FILAS_TOTAL = ' || count(*) FROM n8n_chat_histories;
SELECT 'SESIONES_DISTINTAS = ' || count(DISTINCT session_id) FROM n8n_chat_histories;
SELECT 'TAMANO = ' || pg_size_pretty(pg_total_relation_size('n8n_chat_histories'));
SELECT 'MAS_ANTIGUO = ' || min(created_at)::text FROM n8n_chat_histories;
"""
out, err = psql("barberia-postgres", "barberia", "barberia", q)
w(out); w("[err] " + err if err else "")

w("\n--- filas por numero (session_id) ---")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT session_id || ' -> ' || count(*) || ' filas' FROM n8n_chat_histories GROUP BY session_id ORDER BY count(*) DESC;")
w(out); w("[err] " + err if err else "")

w("\n--- estructura de la tabla ---")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT column_name || ' | ' || data_type FROM information_schema.columns WHERE table_name='n8n_chat_histories' ORDER BY ordinal_position;")
w(out); w("[err] " + err if err else "")

w("\n--- ¿hay datos personales en el texto? (busqueda de digitos de telefono, nombres, direcciones) ---")
out, err = psql("barberia-postgres", "barberia", "barberia", r"""
SELECT 'filas_con_10digitos = ' || count(*) FROM n8n_chat_histories WHERE message::text ~ '[0-9]{10}';
SELECT 'filas_con_calle = ' || count(*) FROM n8n_chat_histories WHERE message::text ILIKE '%calle%';
SELECT 'filas_con_direccion = ' || count(*) FROM n8n_chat_histories WHERE message::text ILIKE '%direcci%';
SELECT 'filas_con_correo = ' || count(*) FROM n8n_chat_histories WHERE message::text ~* '[a-z0-9._]+@[a-z0-9.]+';
SELECT 'filas_con_pinz = ' || count(*) FROM n8n_chat_histories WHERE message::text ILIKE '%pinz%';
SELECT 'filas_con_tarjeta = ' || count(*) FROM n8n_chat_histories WHERE message::text ~ '[0-9]{13,16}';
""")
w(out); w("[err] " + err if err else "")

w("\n--- muestra de 6 mensajes (recortados a 300 caracteres) ---")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT '>>> ' || left(replace(message::text, E'\\n', ' '), 300) FROM n8n_chat_histories ORDER BY id DESC LIMIT 6;")
w(out); w("[err] " + err if err else "")

w("\n" + "#" * 78); w("# 2. Tablas del negocio: conteos"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT relname || ' = ' || n_live_tup FROM pg_stat_user_tables WHERE relname LIKE 'barber%' OR relname LIKE 'n8n%' ORDER BY relname;")
w(out); w("[err] " + err if err else "")

w("\n" + "#" * 78); w("# 3. Contenido de barber_clientes (datos personales)"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT jid || ' | ' || coalesce(nombre,'(sin nombre)') || ' | tel=' || coalesce(telefono,'-') || ' | visitas=' || visitas || ' | etiqueta=' || coalesce(etiqueta,'-') || ' | nota=' || coalesce(left(nota_interna,60),'-') FROM barber_clientes ORDER BY creado_en;")
w(out); w("[err] " + err if err else "")

w("\n--- datos sensibles en barber_clientes: fecha_nacimiento / marketing_ok ---")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT jid || ' | nac=' || coalesce(fecha_nacimiento::text,'-') || ' | marketing_ok=' || coalesce(marketing_ok::text,'NULL') || ' | nota_interna=' || coalesce(nota_interna,'(vacia)') FROM barber_clientes;")
w(out); w("[err] " + err if err else "")

w("\n" + "#" * 78); w("# 4. barber_consentimiento (¿se usa?)"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'filas=' || count(*) FROM barber_consentimiento;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT jid || ' | marketing_ok=' || marketing_ok || ' | ts=' || ts FROM barber_consentimiento LIMIT 20;")
w(out); w("[err] " + err if err else "")

w("\n" + "#" * 78); w("# 5. ¿Se borra algo? politicas de retencion / jobs"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'barber_auditoria=' || count(*) FROM barber_auditoria;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT jobname || ' | ' || schedule || ' | ' || command FROM cron.job;")
w("[cron.job] " + out); w("[err] " + (err[:400] if err else ""))

w("\n" + "#" * 78); w("# 6. Evolution: mensajes guardados en su Postgres"); w("#" * 78)
out, err = psql("evolution_postgres", "evolution", "evolution_db",
    "SELECT table_name FROM information_schema.tables WHERE table_schema='evolution_api' ORDER BY 1;")
w(out); w("[err] " + (err[:300] if err else ""))
for t in ("Message", "\"Message\"", "Chat", "Contact", "IsOnWhatsapp"):
    out, err = psql("evolution_postgres", "evolution", "evolution_db",
        'SELECT \'%s = \' || count(*) FROM "evolution_api".%s;' % (t, t))
    w(out or ("[%s err] %s" % (t, err[:200])))

w("\n" + "#" * 78); w("# 7. Tabla 'settings'/credenciales de n8n (¿secretos en claro?)"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'credentials_entity filas = ' || count(*) FROM credentials_entity;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT name || ' | ' || type || ' | data_len=' || length(data) FROM credentials_entity ORDER BY name;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT substring(data from 1 for 60) FROM credentials_entity WHERE name ILIKE '%uncensored%' OR type ILIKE '%openai%';")
w("[muestra cifrada] " + out); w("[err] " + err if err else "")

w("\n" + "#" * 78); w("# 8. execute data guardado por n8n (¿mensajes en execution_data?)"); w("#" * 78)
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'execution_entity filas=' || count(*) FROM execution_entity;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'execution_data filas=' || count(*) || ' | tamano=' || pg_size_pretty(pg_total_relation_size('execution_data')) FROM execution_data;")
w(out); w("[err] " + err if err else "")
out, err = psql("barberia-postgres", "barberia", "barberia",
    "SELECT 'with chat text: ' || count(*) FROM execution_data WHERE data::text ILIKE '%pushName%';")
w(out); w("[err] " + err if err else "")

io.open(r"G:\Barberia\_audit\_sec_db.txt", "w", encoding="utf-8").write("\n".join(buf))
print("\n[escrito] G:\\Barberia\\_audit\\_sec_db.txt")