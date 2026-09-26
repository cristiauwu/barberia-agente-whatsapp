import sys, io
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar
SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@citas@@===
SELECT id, jid, nombre, servicio, precio, to_char(inicio,'YYYY-MM-DD HH24:MI:SS') AS inicio, to_char(fin,'YYYY-MM-DD HH24:MI:SS') AS fin, estado FROM barber_citas ORDER BY id;
\echo ===@@clientes@@===
SELECT jid, nombre, telefono, visitas, etiqueta, COALESCE(ticket_promedio::text,'NULL') AS ticket, no_shows, cancelaciones_tardias, COALESCE(servicio_habitual,'NULL') AS srv, marketing_ok::text AS mkt, COALESCE(nota_interna,'NULL') AS nota FROM barber_clientes ORDER BY jid;
"""
s = consultar(SQL)
import json
Path = r"G:\Barberia\archivos\dashboard\_verif\backup-antes.json"
with open(Path,"w",encoding="utf-8") as f:
    json.dump({"citas":s["citas"],"clientes":s["clientes"]}, f, ensure_ascii=False, indent=2)
print(json.dumps(s["citas"], ensure_ascii=False, indent=2))
print(json.dumps(s["clientes"], ensure_ascii=False, indent=2))
print("guardado en", Path)
