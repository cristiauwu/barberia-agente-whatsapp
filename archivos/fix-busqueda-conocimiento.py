#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla la búsqueda de la base de conocimiento.

PROBLEMA ENCONTRADO (probado en vivo):
  La búsqueda de texto completo acierta en la mayoría de preguntas, pero
  FALLA en dos casos reales:

      "donde estan ubicados"  -> sin resultados
      "a que hora abren"      -> sin resultados

  CAUSA: el stemming del español reduce de forma distinta según la forma
  de la palabra:
      'ubicados'   -> 'ubic'
      'ubicacion'  -> 'ubicacion'   <- NO coincide con 'ubic'
      'abren'      -> 'abren'
      'horario'    -> 'horari'      <- NO coincide con 'abren'

  Es decir: la consulta del cliente y la FAQ usan palabras distintas para
  lo mismo. El `tsvector` usa `spanish_unaccent` y está bien; el problema
  es de VOCABULARIO, no de configuración.

SOLUCIÓN (dos capas, ambas gratis):

  1. AMPLIAR los sinónimos de cada FAQ con las variantes que la gente usa
     de verdad ("ubicacion", "direccion", "donde estan", "como llego").
     La columna `sinonimos` ya existe y ya entra en el tsvector con peso A.

  2. BUSCAR CON OR: en lugar de exigir que TODAS las palabras coincidan
     (`plainto_tsquery` las une con AND), usar una consulta que acepte
     cualquiera de los términos relevantes. Así "a que hora abren"
     encuentra la FAQ del horario aunque solo coincida "horario".

Se añade una función SQL `barber_buscar(pregunta, limite)` que encapsula la
búsqueda bien hecha, para que n8n solo tenga que llamarla.
"""
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

# Sinónimos a añadir por tema. Se añaden a la FAQ existente que coincida.
SINONIMOS = [
    ("ubicad", "ubicacion direccion llegar como llego domicilio donde local"),
    ("horari", "horario abren abierto cierran cerrado horas atienden"),
    ("estacionamiento", "estacionamiento parking coche carro auto"),
    ("cancelar", "cancelar cancelacion anular no puedo ir"),
    ("cambiar mi cita", "cambiar mover reprogramar reagendar otro dia"),
    ("cuesta", "precio cuesta costo cuanto vale tarifa"),
    ("domingo", "domingo cerrado descanso"),
    ("reservar", "reservar agendar apartar cita turno espacio"),
    ("pago", "pago pagar efectivo transferencia tarjeta"),
    ("depilacion", "depilacion depilar ceja bigote nariz oreja axila pierna"),
    ("barba", "barba perfilado afeitado"),
    ("corte", "corte cabello pelo tijera desvanecido fade"),
    ("mascarilla", "mascarilla facial tratamiento cara"),
    ("peinado", "peinado planchado alaciado estilo"),
    ("duracion", "duracion cuanto tarda tiempo minutos"),
    ("puntualidad", "puntualidad retraso tarde llegar"),
    ("nino", "nino menor edad infantil"),
    ("descuento", "descuento promocion oferta rebaja"),
    ("walk", "walkin sin cita llegar directo"),
    ("gracias", "gracias agradecer despedida"),
]

FUNCION = """
-- ---------------------------------------------------------------------------
-- Función de búsqueda bien hecha.
-- Encapsula: OR de los términos + ranking + límite. Gratis, nativa, rápida.
-- La usa n8n con: SELECT pregunta, respuesta FROM barber_buscar('...', 3);
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION barber_buscar(p_texto text, p_limite int DEFAULT 3)
RETURNS TABLE (pregunta text, respuesta text, categoria text, rank real)
LANGUAGE sql STABLE AS $fn$
  WITH terminos AS (
    -- Cada palabra útil del texto del cliente, como consulta separada
    SELECT plainto_tsquery('spanish_unaccent', t) AS q
    FROM unnest(regexp_split_to_array(
           trim(regexp_replace(coalesce(p_texto, ''), '[^[:alnum:] ]', ' ', 'g')),
           '\\s+')) AS t
    WHERE length(t) > 2
      -- palabras vacías del español que no aportan
      AND t NOT IN ('que','los','las','del','por','para','con','una','uno',
                    'como','donde','cuando','cuanto','esta','estan','hay',
                    'son','sus','mas','muy','puedo','quiere','quiero','tienen',
                    'tiene','los','las','sin','sobre','desde','hasta','pero')
  ),
  consulta AS (
    SELECT to_tsquery('spanish_unaccent',
             string_agg(q::text, ' | ')) AS q
    FROM terminos
  )
  SELECT k.pregunta, k.respuesta, k.categoria,
         ts_rank(k.tsv, c.q) AS rank
  FROM barber_conocimiento k, consulta c
  WHERE k.activo
    AND c.q IS NOT NULL
    AND c.q::text <> ''
    AND k.tsv @@ c.q
  ORDER BY rank DESC, k.pregunta
  LIMIT p_limite;
$fn$;

COMMENT ON FUNCTION barber_buscar(text, int) IS
  'Busca la FAQ mas parecida. Une los terminos con OR (no AND), asi que
   encuentra la respuesta aunque el cliente use otras palabras.';
"""


def psql(sql, params=None):
    """Ejecuta SQL. Los ERRORES van a stderr: hay que leer ambos.

    Si `sql` empieza con '@@file:' se ejecuta el archivo indicado con -f
    (para DDL con muchas líneas). Si no, se pasa con -c.
    """
    args = [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
            "-d", "barberia", "-t", "-A", "-F", " | "]
    for k, v in (params or {}).items():
        args += ["-v", f"{k}={v}"]
    if sql.startswith("@@file:"):
        args += ["-f", sql.split("@@file:", 1)[1]]
    else:
        args += ["-c", sql]
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 72)
    print("1) AMPLIAR SINONIMOS")
    print("=" * 72)
    for patron, sins in SINONIMOS:
        out, err = psql(
            "UPDATE barber_conocimiento "
            "SET sinonimos = trim(coalesce(sinonimos,'') || ' ' || %s) "
            "WHERE pregunta ILIKE %s "
            "RETURNING pregunta;",
        )
        # psql -c no admite parámetros; se construye con comillas seguras
        sql = ("UPDATE barber_conocimiento "
               f"SET sinonimos = trim(coalesce(sinonimos,'') || ' {sins}') "
               f"WHERE pregunta ILIKE '%{patron}%' RETURNING pregunta;")
        out, err = psql(sql)
        if err and "ERROR" in err:
            print(f"  AVISO {patron}: {err[:90]}")
        elif out:
            print(f"  {patron:<22} -> {len(out.splitlines())} FAQ(s)")

    print()
    print("=" * 72)
    print("2) CREAR LA FUNCION DE BUSQUEDA")
    print("=" * 72)
    ruta = r"G:\Barberia\archivos\_fn_buscar.sql"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(FUNCION)
    subprocess.run([DOCKER, "cp", ruta,
                    "barberia-postgres:/tmp/_fn.sql"], capture_output=True)
    out, err = psql("@@file:/tmp/_fn.sql")
    if "ERROR" in err:
        print("  ERROR:", err[:300])
        return 1
    print("  función 'barber_buscar' creada")
    os.remove(ruta)

    print()
    print("=" * 72)
    print("3) PRUEBA CON PREGUNTAS REALES")
    print("=" * 72)
    pruebas = [
        "donde estan ubicados",
        "a que hora abren",
        "tienen estacionamiento",
        "cuanto cuesta el corte",
        "se puede cancelar",
        "hay que hacer cita o puedo llegar directo",
        "abren el domingo?",
        "cuanto tarda un corte",
        "aceptan tarjeta?",
        "hacen corte para niño",
        "quiero mover mi cita",
        "hay descuento?",
    ]
    aciertos = 0
    for q in pruebas:
        sql = ("SELECT pregunta, left(respuesta,60), round(rank::numeric,3) "
               f"FROM barber_buscar('{q.replace(chr(39), chr(39)*2)}', 1);")
        out, err = psql(sql)
        if out:
            aciertos += 1
            print(f"  OK   {q!r}")
            print(f"         -> {out}")
        else:
            print(f"  FALLA {q!r}")
            if err and "ERROR" in err:
                print(f"         {err[:110]}")

    print()
    print("=" * 72)
    print(f"RESULTADO: {aciertos} de {len(pruebas)} preguntas encontraron respuesta")
    print("=" * 72)
    return 0 if aciertos >= len(pruebas) - 1 else 1


if __name__ == "__main__":
    sys.exit(main())