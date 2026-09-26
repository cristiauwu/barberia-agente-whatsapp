#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Añade las FAQs que faltan y afina el ranking de la búsqueda.

HALLAZGOS de la prueba de 12 preguntas:
  1. Faltaba una FAQ de DURACIÓN. "cuanto tarda un corte" no encontraba
     nada útil porque no existe la pregunta "¿Cuánto dura el corte?".
  2. El ranking devolvía "mod cut" por encima de precio cuando se
     preguntaba por duración: el peso de la palabra "corte" domina y
     arrastra cualquier FAQ que hable de cortes.

SOLUCIÓN:
  - Añadir las FAQs que faltan (duración por servicio, y otras que la
    gente pregunta de verdad).
  - En la función de búsqueda, subir el peso de coincidir con la PALABRA
    CLAVE de la intención (duracion, precio, horario...) frente a
    coincidir solo con el tema (corte, barba). Se hace con un bonus por
    coincidencia en la columna `sinonimos`.

Todo sigue siendo gratis y nativo de Postgres.
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

# FAQs nuevas: (pregunta, respuesta, categoria, sinonimos, origen)
NUEVAS = [
    ("¿Cuánto dura el corte?",
     "El *corte desvanecido o tijera* dura *40 minutos*. Deja tiempo extra "
     "si vienes en hora pico.",
     "servicios",
     "duracion dura tarda tiempo minutos cuanto tarda el corte",
     "contexto"),
    ("¿Cuánto dura cada servicio?",
     "Corte 40 min · Barba 20 min · Ceja 10 min · Mascarilla 20 min · "
     "Dama 50 min · Planchado 30 min · Peinado 45 min · Depilación 30 min.",
     "servicios",
     "duracion duraciones tiempo tarda minutos cada servicio cuanto",
     "contexto"),
    ("¿Cuánto dura la barba?",
     "El *arreglo de barba* dura *20 minutos*.",
     "servicios",
     "duracion dura barba tarda tiempo minutos cuanto",
     "contexto"),
    ("¿Puedo agendar el mismo día?",
     "Sí, si queda hueco. Dime la hora y lo reviso al momento.",
     "citas",
     "mismo dia hoy ahora urgente inmediato disponible hueco",
     "contexto"),
    ("¿Qué pasa si voy a llegar tarde?",
     "Avísame por aquí. Si te pasas mucho del horario puede que tenga que "
     "recortar el servicio o mover tu cita.",
     "citas",
     "tarde retraso demora llegar puntualidad avisar",
     "contexto"),
    ("¿Puedo llevar a mi hijo?",
     "Sí, sin problema. El corte para niño se hace con el mismo corte "
     "desvanecido o tijera de *$150*.",
     "general",
     "nino hijo menor edad acompanante",
     "contexto"),
    ("¿Tienen wifi?",
     "Te confirmo ese dato con el encargado en un momento.",
     "general",
     "wifi internet conexion",
     "propuesta"),
    ("¿Cuánto tiempo antes debo llegar?",
     "Con llegar *5 minutos antes* es suficiente. Así arrancamos puntuales.",
     "citas",
     "tiempo antes llegar anticipacion puntualidad cuanto",
     "contexto"),
]

FUNCION = """
-- ---------------------------------------------------------------------------
-- Función de búsqueda afinada.
-- Mejora sobre la versión anterior: da un BONUS a las coincidencias en la
-- columna `sinonimos`, que es donde vive la INTENCIÓN (duracion, precio,
-- horario). Así "cuanto tarda un corte" encuentra la FAQ de duración en
-- lugar de una que solo habla de cortes.
-- Sigue siendo gratis, nativa y rápida.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION barber_buscar(p_texto text, p_limite int DEFAULT 3)
RETURNS TABLE (pregunta text, respuesta text, categoria text, rank real)
LANGUAGE sql STABLE AS $fn$
  WITH terminos AS (
    SELECT plainto_tsquery('spanish_unaccent', t) AS q
    FROM unnest(regexp_split_to_array(
           trim(regexp_replace(coalesce(p_texto, ''), '[^[:alnum:] ]', ' ', 'g')),
           '\\s+')) AS t
    WHERE length(t) > 2
      AND t NOT IN ('que','los','las','del','por','para','con','una','uno',
                    'como','donde','cuando','cuanto','esta','estan','hay',
                    'son','sus','mas','muy','puedo','quiere','quiero','tienen',
                    'tiene','sin','sobre','desde','hasta','pero','algo','alguien')
  ),
  consulta AS (
    SELECT to_tsquery('spanish_unaccent', string_agg(q::text, ' | ')) AS q
    FROM terminos
  )
  SELECT k.pregunta, k.respuesta, k.categoria,
         (ts_rank(k.tsv, c.q)
          + 0.5 * ts_rank(to_tsvector('spanish_unaccent',
                                      coalesce(k.sinonimos, '')), c.q)
         )::real AS rank
  FROM barber_conocimiento k, consulta c
  WHERE k.activo
    AND c.q IS NOT NULL AND c.q::text <> ''
    AND k.tsv @@ c.q
  ORDER BY rank DESC, k.pregunta
  LIMIT p_limite;
$fn$;
"""


def psql(sql):
    args = [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
            "-d", "barberia", "-t", "-A", "-F", " | "]
    if sql.startswith("@@file:"):
        args += ["-f", sql.split("@@file:", 1)[1]]
    else:
        args += ["-c", sql]
    p = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def esc(s):
    return s.replace("'", "''")


def main():
    print("=" * 72)
    print("1) AÑADIR FAQs QUE FALTABAN")
    print("=" * 72)
    for preg, resp, cat, sins, origen in NUEVAS:
        sql = ("INSERT INTO barber_conocimiento "
               "(pregunta, respuesta, categoria, sinonimos, origen) VALUES "
               f"('{esc(preg)}','{esc(resp)}','{esc(cat)}','{esc(sins)}',"
               f"'{esc(origen)}') "
               "ON CONFLICT (pregunta) DO UPDATE SET "
               "respuesta = excluded.respuesta, "
               "sinonimos = excluded.sinonimos, "
               "categoria = excluded.categoria, "
               "actualizado_en = now() RETURNING pregunta;")
        out, err = psql(sql)
        if err and "ERROR" in err:
            print(f"  AVISO {preg[:40]}: {err[:100]}")
        else:
            print(f"  OK  {preg[:52]}")
    out, _ = psql("SELECT count(*) FROM barber_conocimiento;")
    print(f"\n  total de FAQs: {out}")

    print()
    print("=" * 72)
    print("2) AFINAR LA FUNCION DE BUSQUEDA")
    print("=" * 72)
    ruta = r"G:\Barberia\archivos\_fn2.sql"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(FUNCION)
    subprocess.run([DOCKER, "cp", ruta,
                    "barberia-postgres:/tmp/_fn2.sql"], capture_output=True)
    out, err = psql("@@file:/tmp/_fn2.sql")
    if "ERROR" in err:
        print("  ERROR:", err[:300])
        return 1
    print("  función actualizada")
    os.remove(ruta)

    print()
    print("=" * 72)
    print("3) PRUEBA (14 preguntas, incluidas las que fallaban)")
    print("=" * 72)
    pruebas = [
        "donde estan ubicados", "a que hora abren", "tienen estacionamiento",
        "cuanto cuesta el corte", "se puede cancelar",
        "hay que hacer cita o puedo llegar directo", "abren el domingo?",
        "cuanto tarda un corte", "cuanto dura el corte",
        "cuanto tiempo tarda el peinado", "aceptan tarjeta?",
        "hacen corte para niño", "quiero mover mi cita", "hay descuento?",
    ]
    aciertos = 0
    for q in pruebas:
        out, err = psql(
            f"SELECT pregunta, round(rank::numeric,3) "
            f"FROM barber_buscar('{esc(q)}', 1);")
        if out:
            aciertos += 1
            print(f"  OK    {q!r}")
            print(f"          -> {out}")
        else:
            print(f"  FALLA {q!r}")

    print()
    print("=" * 72)
    print(f"RESULTADO: {aciertos} de {len(pruebas)} encontraron respuesta")
    print("=" * 72)
    return 0 if aciertos == len(pruebas) else 1


if __name__ == "__main__":
    sys.exit(main())