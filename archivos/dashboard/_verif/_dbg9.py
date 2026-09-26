import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar, consultar
SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\echo ===@@a@@===
SELECT
  count(*) FILTER (WHERE estado='atendido') AS atendidas_mes_todas
  FROM barber_citas;
"""
s = consultar(SQL)
print("consultar ->", s)
rc,out,err = ejecutar(SQL)
print("--- ejecutar out ---"); print(out)
print("--- err ---"); print(err); print("rc",rc)
