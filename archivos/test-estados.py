#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de la maquina de estados de las citas de la barberia.

Verifica cuatro cosas:
  1. Que el vocabulario de estados del script coincida con los valores que
     comparan las expresiones del workflow 2 (BarberiaAgenteFLUJO-2-RECORDATORIOS.json),
     leyendo nodes[].parameters.rules.values[].conditions.conditions[].rightValue.
  2. El BUG CONOCIDO: el Switch del flujo de recordatorios solo reconoce
     'agendado' y 'eliminado' (comparacion literal y caseSensitive), pero el
     agente escribe 'agendado', 'actualizado' y 'cancelado'.
  3. Que las transiciones de estado permitidas esten bien definidas.
  4. Que los estados se normalicen a un valor canonico antes de compararlos.

Es un archivo de solo lectura: NO modifica ningun entregable del proyecto.
Devuelve exit code 1 si alguna prueba falla. El fallo del punto 2 es ESPERADO
mientras el bug del Switch no se corrija en el workflow.

Uso:  uv run python archivos/test-estados.py
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(r"G:\Barberia")
if not BASE.is_dir():
    BASE = pathlib.Path(__file__).resolve().parent.parent
F1 = BASE / "BarberiaAgenteFLUJO-1-UNCENSORED.json"
F2 = BASE / "BarberiaAgenteFLUJO-2-RECORDATORIOS.json"

fails = []
checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if cond:
        print("  PASS  " + msg)
    else:
        print("  FAIL  " + msg)
        fails.append(msg)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def nodo(f, nombre):
    for n in f["nodes"]:
        if n["name"] == nombre:
            return n
    return None


# --------------------------------------------------------------------------
# Vocabulario canonico de estados de una cita.
# --------------------------------------------------------------------------
ESTADOS_VALIDOS = [
    "agendado",
    "confirmado",
    "atendido",
    "no_show",
    "cancelado",
    "reprogramado",
]

# Estados terminales: una vez alcanzados, la cita ya no se mueve.
ESTADOS_TERMINALES = ("atendido", "no_show", "cancelado")

# Transiciones permitidas: origen -> destinos alcanzables.
#
#  agendado     -> el cliente confirma, llega, no llega, cancela o mueve.
#  confirmado   -> el cliente ya dijo que si: puede llegar, no llegar,
#                  cancelar o mover otra vez.
#  reprogramado -> estado transitorio tras mover la cita; vuelve a entrar
#                  al circuito normal (confirmar, atender, no llegar, cancelar).
#  atendido / no_show / cancelado -> terminales, sin transiciones.
#
# Rechazos deliberados (casos 5 y 6 de la seccion [3]): un estado terminal
# NO puede volver a 'agendado' ni a 'cancelado'. Una cita ya atendida no se
# "reagenda" y una inasistencia ya no se cancela: si eso ocurre, el registro
# de la hoja esta corrupto y el Switch volveria a mandar recordatorios.
TRANSICIONES = {
    "agendado": ("confirmado", "atendido", "no_show", "cancelado", "reprogramado"),
    "confirmado": ("atendido", "no_show", "cancelado", "reprogramado"),
    "reprogramado": ("confirmado", "atendido", "no_show", "cancelado"),
    "atendido": (),
    "no_show": (),
    "cancelado": (),
}


def transicion_valida(origen, destino):
    return destino in TRANSICIONES.get(origen, ())


# --------------------------------------------------------------------------
# Normalizacion de estados.
#
# DECISION DOCUMENTADA: `eliminado` -> `cancelado`.
# El prompt viejo del agente (PROCESO B, paso 5) le ordena registrar la fila
# anterior con `Estatus: eliminado` cuando reprograma una cita, y el Switch
# del flujo 2 fue escrito contra ese literal. Pero para el negocio una cita
# que se borra del calendario ES una cita cancelada: no hay dos formas de
# "dejar de atender" a un cliente. Mantener dos etiquetas ('eliminado' y
# 'cancelado') para el mismo hecho es justamente lo que rompe el Switch, asi
# que ambos se mapean al canonico `cancelado`. Igual criterio para:
#   borrado     -> cancelado     (sinonimo en espanol)
#   cancelada   -> cancelado     (genero)
#   actualizado -> reprogramado  (valor que el tool $fromAI ofrece al modelo)
#   reagendado  -> reprogramado  (sinonimo)
# --------------------------------------------------------------------------
ALIAS_ESTADO = {
    "agendado": "agendado",
    "agenda": "agendado",
    "confirmado": "confirmado",
    "confirmada": "confirmado",
    "atendido": "atendido",
    "atendida": "atendido",
    "no show": "no_show",
    "noshow": "no_show",
    "no asiste": "no_show",
    "cancelado": "cancelado",
    "cancelada": "cancelado",
    "eliminado": "cancelado",
    "eliminada": "cancelado",
    "borrado": "cancelado",
    "borrada": "cancelado",
    "reprogramado": "reprogramado",
    "reprogramada": "reprogramado",
    "reagendado": "reprogramado",
    "actualizado": "reprogramado",
}


def normalizar_estado(texto):
    """Convierte cualquier variante de estado a un estado canonico.

    Devuelve None si el texto no corresponde a ningun estado conocido.
    """
    if texto is None:
        return None
    clave = re.sub(r"[\s_\-]+", " ", str(texto).strip().lower()).strip()
    return ALIAS_ESTADO.get(clave)


# Estados que el agente puede escribir en la hoja, segun el workflow 1:
#   - prompt del sistema: `Estatus: agendado`, `Estatus: eliminado`, `Estatus: cancelado`
#   - herramienta "Registrar en hoja de citas":
#     $fromAI('Estatus', 'agendado, actualizado o cancelado, segun la accion realizada')
ESTADOS_QUE_EL_AGENTE_ESCRIBE = ["agendado", "actualizado", "cancelado"]


def estados_del_switch(f2):
    """rightValue de cada condicion de los nodos Switch (comparacion literal)."""
    encontrados = []
    for n in f2["nodes"]:
        if "switch" in n.get("type", "").lower():
            reglas = n.get("parameters", {}).get("rules", {}).get("values", [])
            for regla in reglas:
                conds = regla.get("conditions", {}).get("conditions", [])
                for c in conds:
                    if isinstance(c.get("rightValue"), str):
                        encontrados.append(c["rightValue"])
    return encontrados


def left_values_del_switch(f2):
    """leftValue de cada condicion de los nodos Switch."""
    valores = []
    for n in f2["nodes"]:
        if "switch" in n.get("type", "").lower():
            reglas = n.get("parameters", {}).get("rules", {}).get("values", [])
            for regla in reglas:
                conds = regla.get("conditions", {}).get("conditions", [])
                for c in conds:
                    if isinstance(c.get("leftValue"), str):
                        valores.append(c["leftValue"])
    return valores


def estados_escritos_segun_workflow1(raw):
    """Extrae, del JSON crudo del flujo 1, los estados que el agente escribe.

    Los tokens se normalizan, de modo que 'eliminado' cuenta como 'cancelado'.
    """
    encontrados = set()
    for m in re.finditer(r"Estatus:\s*([A-Za-z_]+)", raw):
        canonico = normalizar_estado(m.group(1))
        if canonico:
            encontrados.add(canonico)
    for m in re.finditer(r"\$fromAI\('Estatus',\s*'([^']+)'", raw):
        for token in re.findall(r"[A-Za-z_]+", m.group(1)):
            canonico = normalizar_estado(token)
            if canonico:
                encontrados.add(canonico)
    return encontrados


# ==========================================================================
print("=" * 70)
print("PRUEBAS DE LA MAQUINA DE ESTADOS DE LAS CITAS")
print("=" * 70)

# ------------------------------------------------------- archivos y parseo
print("\n[1] Carga de workflows y vocabulario de estados")
check(F1.exists(), "Existe BarberiaAgenteFLUJO-1-UNCENSORED.json")
check(F2.exists(), "Existe BarberiaAgenteFLUJO-2-RECORDATORIOS.json")
f1 = load(F1)
f2 = load(F2)
check(isinstance(f2.get("nodes"), list) and len(f2["nodes"]) > 0,
      "El workflow 2 parsea y tiene nodos (%d)" % len(f2["nodes"]))

check(set(ESTADOS_VALIDOS) == {
    "agendado", "confirmado", "atendido", "no_show", "cancelado", "reprogramado"},
    "La lista de estados validos es exactamente la de 6 estados del negocio")
check(len(ESTADOS_VALIDOS) == len(set(ESTADOS_VALIDOS)),
      "La lista de estados validos no tiene duplicados")
for e in ESTADOS_VALIDOS:
    check(normalizar_estado(e) == e,
          "El estado canonico '%s' se normaliza a si mismo" % e)

# --- 1. Coincidencia entre el script y las expresiones del workflow 2 -------
switch_estados = estados_del_switch(f2)
check(bool(switch_estados),
      "Se encontraron rightValue en las condiciones del Switch (%s)"
      % sorted(set(switch_estados)))
check(all(normalizar_estado(e) in ESTADOS_VALIDOS for e in switch_estados),
      "Todo estado que compara el Switch pertenece al vocabulario del sistema (%s)"
      % sorted(set(switch_estados)))

switch_reconoce = set(switch_estados)
for e in sorted(switch_reconoce):
    canonico = normalizar_estado(e)
    nota = canonico if canonico == e else "%s (alias de %s)" % (e, canonico)
    print("  INFO  El Switch reconoce: %s" % nota)

lefts = left_values_del_switch(f2)
check(any("Estatus" in v for v in lefts),
      "Las condiciones del Switch leen la columna 'Estatus' de la hoja")

# --------------------------------------- 2. BUG: desajuste agente vs Switch
print("\n[2] BUG CONOCIDO: el agente escribe estados que el Switch no reconoce")
f1_raw = F1.read_text(encoding="utf-8")
escritos = estados_escritos_segun_workflow1(f1_raw)
for e in sorted(escritos):
    print("  INFO  El agente puede escribir: %s" % e)
check({"agendado", "cancelado"} <= escritos,
      "El workflow 1 escribe 'agendado' y 'cancelado' (eliminado cuenta como cancelado): %s"
      % sorted(escritos))
check("actualizado" in f1_raw,
      "El tool $fromAI('Estatus') sigue ofreciendo el valor 'actualizado'")
check(escritos <= set(ESTADOS_VALIDOS),
      "Todo estado escrito por el agente es un estado valido del vocabulario: %s"
      % sorted(escritos))

# El Switch compara de forma literal: solo cubre lo que esta escrito en el JSON.
switch_sin_reconocer = sorted(
    e for e in ESTADOS_QUE_EL_AGENTE_ESCRIBE
    if normalizar_estado(e) not in {normalizar_estado(s) for s in switch_reconoce}
)
check(not switch_sin_reconocer,
      "Todo estado que el agente puede escribir esta contemplado por el Switch "
      "(NO contemplados: %s)" % (switch_sin_reconocer or "ninguno"))

# Prueba directa del sintoma, para que el fallo sea inequivoco.
for estado in ESTADOS_QUE_EL_AGENTE_ESCRIBE:
    cubierto = estado in switch_reconoce
    check(cubierto,
          "El Switch contempla el estado '%s' que el agente escribe" % estado)

if switch_sin_reconocer:
    print("  IMPACTO  Los estados %s caen a la salida de respaldo 'Otro' del Switch."
          % switch_sin_reconocer)
    print("  IMPACTO  El flujo NUNCA ejecuta 'QUITAR RECORDATORIO' ni "
          "'OBTENER INFO DE CITA ELIMINADA'.")
    print("  IMPACTO  Los Wait de 24 h y 1 h siguen armados: el cliente recibe "
          "avisos de una cita que ya cancelo (o de una cita que ya movio) y el "
          "encargado ve una agenda sucia.")

# ---------------------------------------------------- 3. transiciones validas
print("\n[3] Transiciones de estado")
check(all(o in ESTADOS_VALIDOS for o in TRANSICIONES),
      "Todo origen de TRANSICIONES es un estado valido")
check(all(d in ESTADOS_VALIDOS for ds in TRANSICIONES.values() for d in ds),
      "Todo destino de TRANSICIONES es un estado valido")
check(all(o not in ds for o, ds in TRANSICIONES.items()),
      "Ningun estado se transiciona a si mismo")
check(all(TRANSICIONES[t] == () for t in ESTADOS_TERMINALES),
      "Los estados terminales %s no tienen salida" % (ESTADOS_TERMINALES,))
check(all(o in TRANSICIONES for o in ESTADOS_VALIDOS),
      "Todos los estados validos estan definidos en TRANSICIONES")

# Casos explicitos: 4 aceptados y 2 RECHAZADOS.
casos_transicion = [
    ("agendado", "confirmado", True, "el cliente confirma"),
    ("agendado", "cancelado", True, "el cliente cancela"),
    ("confirmado", "atendido", True, "el cliente llega y se le atiende"),
    ("confirmado", "reprogramado", True, "el cliente mueve la cita"),
    ("atendido", "agendado", False, "RECHAZADO: una cita ya atendida no se reagenda"),
    ("no_show", "cancelado", False, "RECHAZADO: la inasistencia es terminal"),
]
for origen, destino, esperado, motivo in casos_transicion:
    obtenido = transicion_valida(origen, destino)
    check(obtenido is esperado,
          "%s -> %s es %s (%s)"
          % (origen, destino, "valida" if esperado else "invalida", motivo))
check(sum(1 for c in casos_transicion if not c[2]) >= 2,
      "Se probaron al menos 2 transiciones RECHAZADAS")

destinos_esperados = {"agendado", "confirmado", "atendido", "no_show",
                      "cancelado", "reprogramado"}
destinos_definidos = {d for ds in TRANSICIONES.values() for d in ds}
check(destinos_definidos <= destinos_esperados,
      "Los destinos usado en TRANSICIONES existen en el vocabulario")

# --------------------------------------------------- 4. normalizacion
print("\n[4] Normalizacion de estados a un valor canonico")
casos_norm = [
    ("Cancelado", "cancelado", "Capitalizado"),
    ("cancelado ", "cancelado", "Con espacio al final"),
    ("  CANCELADO  ", "cancelado", "Mayusculas y espacios a los lados"),
    ("eliminado", "cancelado", "Alias heredado del prompt viejo"),
    ("borrado", "cancelado", "Sinonimo en espanol"),
    ("  AGENDADO", "agendado", "Mayusculas sin espacio inicial"),
    ("Actualizado", "reprogramado", "Valor del tool $fromAI"),
    ("no_show", "no_show", "Estado canonico con guion bajo"),
    ("No Show", "no_show", "Variante con espacio"),
    ("cita-fantasma", None, "Texto que no es un estado -> None"),
]
check(len(casos_norm) >= 6,
      "Se probaron al menos 6 entradas de normalizacion (%d)" % len(casos_norm))
for texto, esperado, nota in casos_norm:
    obtenido = normalizar_estado(texto)
    check(obtenido == esperado,
          "normalizar_estado(%r) == %r (%s)" % (texto, esperado, nota))

# La normalizacion es idempotente y no depende de mayusculas.
for e in ESTADOS_VALIDOS:
    check(normalizar_estado(normalizar_estado(e.upper())) == e,
          "Normalizar dos veces '%s' sigue dando '%s'" % (e.upper(), e))

# El mapeo clave del bug: 'eliminado' y 'cancelado' son el MISMO estado.
check(normalizar_estado("eliminado") == normalizar_estado("cancelado"),
      "Decision documentada: 'eliminado' se mapea a 'cancelado' (mismo hecho de negocio)")

# ------------------------------------------------------------- veredicto
print("\n" + "=" * 70)
if fails:
    print("RESULTADO: %d de %d verificaciones FALLARON" % (len(fails), checks))
    for m_ in fails:
        print("  - " + m_)
    print("=" * 70)
    sys.exit(1)
print("RESULTADO: %d de %d verificaciones PASARON" % (checks, checks))
print("=" * 70)