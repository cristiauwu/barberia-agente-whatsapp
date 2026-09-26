#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PASO 1: volcar el estado ORIGINAL (filas no-verif) con fidelidad total.

No borra nada. Guarda un JSON con todos los campos y sus timestamps en ISO.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar

SALIDA = Path(r"G:\Barberia\archivos\dashboard\_verif\original-fiel.json")

SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@citas@@===
SELECT id, COALESCE(jid,'') AS jid, COALESCE(nombre,'') AS nombre,
       COALESCE(servicio,'') AS servicio,
       COALESCE(precio::text,'') AS precio,
       COALESCE(to_char(inicio, 'YYYY-MM-DD"T"HH24:MI:SS.MS OF'),'') AS inicio,
       COALESCE(to_char(fin,    'YYYY-MM-DD"T"HH24:MI:SS.MS OF'),'') AS fin,
       COALESCE(estado,'') AS estado,
       COALESCE(to_char(creado_en,      'YYYY-MM-DD"T"HH24:MI:SS.MS OF'),'') AS creado_en,
       COALESCE(to_char(actualizado_en, 'YYYY-MM-DD"T"HH24:MI:SS.MS OF'),'') AS actualizado_en
  FROM barber_citas
 WHERE id NOT LIKE 'verif-%'
 ORDER BY id;
\echo ===@@clientes@@===
SELECT jid, COALESCE(nombre,'') AS nombre, COALESCE(telefono,'') AS telefono,
       COALESCE(to_char(primera_visita,'YYYY-MM-DD"T"HH24:MI:SS.MS'),'') AS primera_visita,
       visitas::text AS visitas,
       COALESCE(to_char(ultima_visita,'YYYY-MM-DD"T"HH24:MI:SS.MS'),'') AS ultima_visita,
       COALESCE(ticket_promedio::text,'') AS ticket_promedio,
       no_shows::text AS no_shows,
       cancelaciones_tardias::text AS cancelaciones_tardias,
       COALESCE(servicio_habitual,'') AS servicio_habitual,
       COALESCE(barbero_preferido,'') AS barbero_preferido,
       COALESCE(nota_interna,'') AS nota_interna,
       COALESCE(fecha_nacimiento::text,'') AS fecha_nacimiento,
       marketing_ok::text AS marketing_ok,
       COALESCE(etiqueta,'') AS etiqueta,
       COALESCE(to_char(creado_en,'YYYY-MM-DD"T"HH24:MI:SS.MS'),'') AS creado_en
  FROM barber_clientes
 WHERE jid NOT LIKE 'verif-%'
 ORDER BY jid;
\echo ===@@resumen@@===
SELECT
  (SELECT count(*) FROM barber_citas)                                   AS citas_total,
  (SELECT count(*) FROM barber_citas WHERE id LIKE 'verif-%')           AS citas_verif,
  (SELECT count(*) FROM barber_clientes)                                AS cli_total,
  (SELECT count(*) FROM barber_clientes WHERE jid LIKE 'verif-%')       AS cli_verif,
  (SELECT count(*) FROM barber_pausas)                                  AS pausas;
"""

s = consultar(SQL)
datos = {"citas": s["citas"], "clientes": s["clientes"]}
SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                  encoding="utf-8")
print("volcado en", SALIDA)
print("  citas originales   :", len(datos["citas"]))
print("  clientes originales:", len(datos["clientes"]))
print("  resumen:", s["resumen"])
print()
print("--- citas originales ---")
print(json.dumps(datos["citas"], ensure_ascii=False, indent=2))
print("--- clientes originales ---")
print(json.dumps(datos["clientes"], ensure_ascii=False, indent=2))