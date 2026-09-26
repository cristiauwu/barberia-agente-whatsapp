import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar
SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
SELECT
  count(*) FILTER (WHERE estado='atendido') AS atendidas_todas,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date) AS con_precio,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NULL AND inicio::date >= date_trunc('month',current_date)::date) AS sin_precio,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NULL) AS sin_precio_total
FROM barber_citas;
SELECT servicio, count(*) AS n_sin_precio FROM barber_citas
 WHERE estado='atendido' AND precio IS NULL AND inicio IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;
"""
rc,out,err = ejecutar(SQL)
print(out); print("ERR:",err); print("RC:",rc)
