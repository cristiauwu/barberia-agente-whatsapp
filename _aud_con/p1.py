import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, dump

print("== VERSION ==")
print(q("SELECT version()")[1])

print("== TABLAS ==")
dump(q("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")[1])

print("== COUNT CONOCIMIENTO ==")
dump(q("SELECT count(*) FROM barber_conocimiento")[1])

print("== ORIGEN ==")
dump(q("SELECT origen, count(*) FROM barber_conocimiento GROUP BY 1 ORDER BY 2 DESC")[1])

print("== COLUMNAS ==")
dump(q("SELECT column_name, data_type FROM information_schema.columns "
       "WHERE table_name='barber_conocimiento' ORDER BY ordinal_position")[1])

print("== SERVICIOS ==")
dump(q("SELECT * FROM barber_servicios ORDER BY 1")[1])

print("== FUNCIONES ==")
dump(q("SELECT p.proname, pg_get_function_arguments(p.oid), "
       "pg_get_function_result(p.oid) FROM pg_proc p JOIN pg_namespace n "
       "ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE '%conocimiento%' OR p.proname LIKE '%barber_buscar%'")[1])

print("== INDICES ==")
dump(q("SELECT indexname, indexdef FROM pg_indexes "
       "WHERE tablename='barber_conocimiento'")[1])