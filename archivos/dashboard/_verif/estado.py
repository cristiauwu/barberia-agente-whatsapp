#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estado inicial + esquema real + rol de conexion."""
import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar, ejecutar

SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@reloj@@===
SELECT now() AS ahora_local,
       current_date::text AS fecha_local,
       (now() AT TIME ZONE 'UTC')::text AS utc_now,
       current_setting('TimeZone') AS zona;
\echo ===@@conteos@@===
SELECT (SELECT count(*) FROM barber_citas) AS citas,
       (SELECT count(*) FROM barber_clientes) AS clientes,
       (SELECT count(*) FROM barber_pausas) AS pausas;
\echo ===@@cols_citas@@===
SELECT ordinal_position AS pos, column_name, data_type, is_nullable, column_default
  FROM information_schema.columns WHERE table_name='barber_citas' ORDER BY ordinal_position;
\echo ===@@cols_clientes@@===
SELECT ordinal_position AS pos, column_name, data_type, is_nullable
  FROM information_schema.columns WHERE table_name='barber_clientes' ORDER BY ordinal_position;
\echo ===@@tablas@@===
SELECT table_name FROM information_schema.tables
 WHERE table_schema='public' AND table_name LIKE 'barber%' ORDER BY 1;
\echo ===@@rol@@===
SELECT current_user AS usuario_actual, session_user AS sesion,
       (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) AS es_superusuario,
       (SELECT rolcreatedb FROM pg_roles WHERE rolname=current_user) AS puede_crear_db,
       (SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user) AS bypass_rls;
\echo ===@@grant_tabla@@===
SELECT grantee, privilege_type FROM information_schema.role_table_grants
 WHERE table_name='barber_citas' ORDER BY grantee, privilege_type;
\echo ===@@servicios_tabla@@===
SELECT to_regclass('public.barber_servicios')::text AS existe_servicios;
\echo ===@@catalogo_servicios@@===
SELECT * FROM barber_servicios ORDER BY 1;
"""
rc, out, err = ejecutar(SQL)
print(out)
print("ERR:", err)
print("RC:", rc)