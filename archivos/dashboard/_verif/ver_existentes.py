import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar
SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset pager off
\echo === CITAS EXISTENTES ===
SELECT id, jid, nombre, servicio, precio, inicio, fin, estado, creado_en FROM barber_citas ORDER BY inicio;
\echo === CLIENTES EXISTENTES ===
SELECT jid, nombre, telefono, primera_visita, visitas, ultima_visita, ticket_promedio, no_shows, etiqueta FROM barber_clientes ORDER BY jid;
\echo === PAUSAS ===
SELECT * FROM barber_pausas;
"""
rc,out,err = ejecutar(SQL)
print(out); print("ERR:", err); print("RC:", rc)
