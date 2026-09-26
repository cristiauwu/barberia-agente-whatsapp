import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar

SQL = """
SET TIME ZONE 'America/Mexico_City';
\\pset footer off
SELECT 'atendido' AS estado,
       COALESCE(SUM(precio) FILTER (WHERE precio IS NOT NULL), 0) AS dinero,
       COUNT(*) AS n
  FROM barber_citas
 WHERE estado = 'atendido'
   AND inicio::date >= date_trunc('month', current_date)::date
UNION ALL
SELECT 'no_show', COALESCE(SUM(precio) FILTER (WHERE precio IS NOT NULL),0), COUNT(*)
  FROM barber_citas
 WHERE estado = 'no_show'
   AND inicio::date >= date_trunc('month', current_date)::date
UNION ALL
SELECT 'cancelado', COALESCE(SUM(precio) FILTER (WHERE precio IS NOT NULL),0), COUNT(*)
  FROM barber_citas
 WHERE estado = 'cancelado'
   AND inicio::date >= date_trunc('month', current_date)::date;
"""
rc,out,err = ejecutar(SQL)
print(out); print("ERR:",err); print("RC:",rc)
