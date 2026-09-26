#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Añade a verify.py las verificaciones de los comandos del dueño.

Nueva sección [12]: comprueba en los ARCHIVOS del repo que:
  - el router tiene las 12 salidas + fallback
  - cada salida apunta al nodo correcto
  - cada cadena termina en 'Responder al operador'
  - '¿Es operador?' lee la tabla, no un número fijo
  - no queda el número del vendedor como destino
"""
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RUTA = r"G:\Barberia\verify.py"
W1 = r"G:\Barberia\BarberiaAgenteFLUJO-1-UNCENSORED.json"

BLOQUE = '''

print("\\n[12] Comandos del dueño (flujo 1)")
# El dueño manda comandos por WhatsApp que NO pasan por el modelo.
# Se verifica el enrutado completo en el archivo del repo.
COMANDOS_ORDEN = ["HOY", "MAÑANA", "SEMANA", "LIBRE", "CLIENTE",
                  "BLOQUEAR", "CERRAR", "ABRIR", "PRECIO", "PAUSA",
                  "ESTADO", "COMANDOS"]
DESTINO_ESPERADO = {
    "HOY": "Preparar rango de fechas",
    "MAÑANA": "Preparar rango de fechas",
    "SEMANA": "Preparar rango de fechas",
    "LIBRE": "Preparar rango de fechas",
    "CLIENTE": "Buscar cliente",
    "BLOQUEAR": "Parsear bloqueo",
    "CERRAR": "Parsear bloqueo",
    "ABRIR": "Parsear bloqueo",
    "PRECIO": "Parsear precio",
    "PAUSA": "Parsear pausa",
    "ESTADO": "Leer estado del sistema",
    "COMANDOS": "Armar respuesta COMANDOS",
}

router = node(f1, "Router de comandos")
check(router is not None, "Existe el nodo 'Router de comandos'")
if router:
    salidas = f1["connections"].get("Router de comandos", {}).get("main", [])
    check(len(salidas) == 13,
          "El router tiene 13 salidas (12 comandos + respaldo): %d"
          % len(salidas))
    for i, cmd in enumerate(COMANDOS_ORDEN):
        if i >= len(salidas):
            break
        dest = salidas[i][0]["node"] if salidas[i] else "(vacio)"
        esperado = DESTINO_ESPERADO[cmd]
        check(dest == esperado,
              "Salida '%s' del router -> %s (esperado %s)"
              % (cmd, dest, esperado))
    # El respaldo debe devolver el mensaje al flujo normal del agente
    if len(salidas) > 12:
        ult = salidas[12][0]["node"] if salidas[12] else "(vacio)"
        check(ult == "IF - No es del bot",
              "El respaldo del router va al flujo normal del agente: %s" % ult)

# El IF de operador debe leer la tabla, no tener un numero fijo
op = node(f1, "¿Es operador?")
check(op is not None, "Existe el nodo '¿Es operador?'")
if op:
    conds = (op["parameters"].get("conditions") or {}).get("conditions") or []
    txt = json.dumps(conds, ensure_ascii=False)
    check("es_operador" in txt,
          "El IF de operador usa el campo calculado 'es_operador'")
    check("5215520894522" not in txt,
          "El IF de operador NO tiene el numero del vendedor hardcodeado")

# El operador se decide leyendo la tabla
check(node(f1, "Leer operadores") is not None,
      "Existe 'Leer operadores' (lee la tabla barber_operadores)")
check(node(f1, "Comprobar operador") is not None,
      "Existe 'Comprobar operador' (tolera 52+10 y 52+1+10)")
cad = f1["connections"]
check(cad.get("Normalizacion", {}).get("main", [[{}]])[0][0]["node"]
      == "Leer operadores",
      "Normalizacion alimenta a 'Leer operadores'")
check(cad.get("Leer operadores", {}).get("main", [[{}]])[0][0]["node"]
      == "Comprobar operador",
      "'Leer operadores' alimenta a 'Comprobar operador'")
check(cad.get("Comprobar operador", {}).get("main", [[{}]])[0][0]["node"]
      == "¿Es operador?",
      "'Comprobar operador' alimenta a '¿Es operador?'")

# Los nodos que pueden devolver 0 filas deben seguir el flujo
for nm in ("Leer agenda del rango", "Leer ficha del cliente",
           "Actualizar precio", "Aplicar pausa", "Leer operadores"):
    n = node(f1, nm)
    check(n is not None and n.get("alwaysOutputData") is True,
          "'%s' tiene alwaysOutputData (no corta la cadena sin datos)" % nm)

# Cada cadena de comando debe terminar en el nodo que responde
CADENAS = {
    "Preparar rango de fechas": ["Leer agenda del rango", "Formatear agenda",
                                 "Responder al operador"],
    "Buscar cliente": ["Leer ficha del cliente", "Formatear ficha",
                       "Responder al operador"],
    "Parsear precio": ["Actualizar precio", "Formatear precio",
                       "Responder al operador"],
    "Parsear pausa": ["Aplicar pausa", "Formatear pausa",
                      "Responder al operador"],
    "Leer estado del sistema": ["Formatear estado", "Responder al operador"],
}
for inicio, cadena in CADENAS.items():
    n = inicio
    ok = True
    for esperado in cadena:
        paso = cad.get(n, {}).get("main", [[]])
        if not paso or not paso[0]:
            ok = False
            break
        n = paso[0][0]["node"]
        if n != esperado:
            ok = False
            break
    check(ok, "Cadena de '%s' termina en el nodo que responde" % inicio)

# El bloqueo se valida antes de tocar el calendario
check(node(f1, "IF - Bloqueo invalido") is not None,
      "Existe 'IF - Bloqueo invalido' (valida antes de crear el evento)")
check(node(f1, "Crear bloqueo en calendario") is not None,
      "Existe 'Crear bloqueo en calendario'")

# El destino de los avisos debe ser el dueño, no el vendedor
txt1 = json.dumps(f1, ensure_ascii=False)
check("5215520894522" not in txt1,
      "Flujo 1 sin el numero del vendedor")
check("524521206246" in txt1,
      "Flujo 1 avisa al numero del dueño")

# Los textos de los comandos no deben usar markdown de dos asteriscos
for n in f1["nodes"]:
    cod = (n.get("parameters") or {}).get("jsCode")
    if cod:
        check("**" not in cod,
              "'%s' no usa ** (WhatsApp solo lee un asterisco)" % n["name"])
'''


def main():
    src = open(RUTA, encoding="utf-8").read()
    if "[12] Comandos del dueño" in src:
        print("verify.py ya tiene la seccion [12]")
        return 0

    # Insertar antes del resumen final
    marca = "print(\"\\n\" + \"=\" * 70)\nprint(\"RESUMEN\""
    if marca in src:
        idx = src.index(marca)
        src = src[:idx] + BLOQUE + "\n" + src[idx:]
    else:
        # Buscar el bloque final de resumen de otra forma
        import re
        m = list(re.finditer(r"\nprint\(.*RESULTADO", src))
        if not m:
            print("no encontre donde insertar; añadiendo al final")
            src += BLOQUE
        else:
            idx = m[-1].start()
            src = src[:idx] + BLOQUE + "\n" + src[idx:]

    with open(RUTA, "w", encoding="utf-8") as f:
        f.write(src)
    print("verify.py actualizado con la seccion [12]")
    return 0


if __name__ == "__main__":
    sys.exit(main())