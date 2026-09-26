#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de nodos n8n para el workflow `barberiaAgenteUncensored`.

Objetivo: que el DUEÑO de la barberia pueda mandar comandos por WhatsApp y
recibir respuesta SIN pasar por el modelo de IA (cero costo de tokens).

Este script NO modifica ningun workflow: solo construye la estructura JSON
parcial (`nodes` + `connections`) lista para pegar/importar en n8n.

Nodos generados (4):
    1. `¿Es operador?`              -> n8n-nodes-base.if            (typeVersion 2.2)
    2. `Router de comandos`         -> n8n-nodes-base.switch        (typeVersion 3.2)
    3. `Responder al operador`      -> n8n-nodes-base.httpRequest   (typeVersion 4.2)
    4. `Armar respuesta COMANDOS`   -> n8n-nodes-base.set           (typeVersion 3.4)

Uso:
    uv run python "G:\\Barberia\\archivos\\generar-nodos-comandos.py"
"""

from __future__ import annotations

import json
import uuid

# --------------------------------------------------------------------------
# Constantes de configuracion
# --------------------------------------------------------------------------

# JIDs autorizados a operar el bot (whitelist de operadores).
OPERADORES = ["5215520894522@s.whatsapp.net"]

# Comandos soportados: orden EXACTO de las salidas del Switch.
# El fallback ("No es comando") va SIEMPRE al final.
COMANDOS = [
    "HOY",
    "MAÑANA",
    "SEMANA",
    "LIBRE",
    "CLIENTE",
    "BLOQUEAR",
    "CERRAR",
    "ABRIR",
    "PRECIO",
    "PAUSA",
    "ESTADO",
    "COMANDOS",
]

# Expresion que extrae el primer token en MAYUSCULAS del mensaje.
EXPR_PRIMER_TOKEN = "={{ $json.message_content.trim().toUpperCase().split(' ')[0] }}"

# Nombre de los nodos (exactos, tal como se exige).
NODO_IF = "¿Es operador?"
NODO_ROUTER = "Router de comandos"
NODO_HTTP = "Responder al operador"
NODO_MENU = "Armar respuesta COMANDOS"

# Menu de comandos en texto plano.
# Formato WhatsApp: *negrita* con UN asterisco. Nunca **dos asteriscos**.
MENU_COMANDOS = "\n".join(
    [
        "*COMANDOS DISPONIBLES*",
        "",
        "*AGENDA*",
        "HOY - agenda de hoy",
        "MAÑANA - agenda de mañana",
        "SEMANA - agenda de la semana",
        "LIBRE - huecos disponibles",
        "",
        "*CLIENTES*",
        "CLIENTE 5214501111805 - ficha del cliente",
        "PAUSA 5214501111805 2h - pausa el bot para ese cliente",
        "",
        "*AGENDA MANUAL*",
        "BLOQUEAR 14:00-15:30 motivo - bloquea un rango",
        "CERRAR 24 dic - cierra un dia completo",
        "ABRIR - quita el cierre",
        "",
        "*PRECIOS*",
        "PRECIO corte 150 - actualiza el precio del servicio",
        "",
        "*SISTEMA*",
        "ESTADO - salud del sistema",
        "COMANDOS - este menu",
    ]
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _nuevo_id() -> str:
    """Devuelve un id unico (UUID4) para un nodo o condicion."""
    return str(uuid.uuid4())


def _opciones_condicion() -> dict:
    """Bloque `options` comun a las condiciones de IF/Switch (filter v2)."""
    return {
        "caseSensitive": True,
        "leftValue": "",
        "typeValidation": "strict",
        "version": 2,
    }


def _condicion(left_value: str, right_value: str) -> dict:
    """Condicion simple de igualdad de strings."""
    return {
        "id": _nuevo_id(),
        "leftValue": left_value,
        "rightValue": right_value,
        "operator": {
            "type": "string",
            "operation": "equals",
        },
    }


def _conexion(nombre_nodo: str) -> dict:
    """Destino de una conexion en el bloque `connections`."""
    return {"node": nombre_nodo, "type": "main", "index": 0}


# --------------------------------------------------------------------------
# Constructores de nodos
# --------------------------------------------------------------------------


def _nodo_if_operador() -> dict:
    """IF: el remitente esta en la whitelist de operadores."""
    condiciones = [_condicion("={{ $json.user_number }}", jid) for jid in OPERADORES]
    return {
        "parameters": {
            "conditions": {
                "options": _opciones_condicion(),
                "conditions": condiciones,
                "combinator": "or",
            },
            "options": {},
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [-500, 180],
        "id": _nuevo_id(),
        "name": NODO_IF,
    }


def _nodo_router_comandos() -> dict:
    """Switch: un output por comando + fallback 'No es comando' al final."""
    valores = []
    for comando in COMANDOS:
        valores.append(
            {
                "conditions": {
                    "options": _opciones_condicion(),
                    "conditions": [_condicion(EXPR_PRIMER_TOKEN, comando)],
                    "combinator": "and",
                },
                "renameOutput": True,
                "outputKey": comando,
            }
        )

    return {
        "parameters": {
            "rules": {"values": valores},
            "options": {
                "fallbackOutput": "extra",
                "renameFallbackOutput": "No es comando",
            },
        },
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3.2,
        "position": [-300, 180],
        "id": _nuevo_id(),
        "name": NODO_ROUTER,
    }


def _nodo_responder_operador() -> dict:
    """HTTP Request: envia el texto de vuelta por Evolution API."""
    return {
        "parameters": {
            "method": "POST",
            "url": (
                "={{ $('Normalizacion').item.json.instance_server_url }}"
                "/message/sendText/"
                "{{ $('Normalizacion').item.json.instance_name }}"
            ),
            "sendHeaders": True,
            "headerParameters": {
                "parameters": [
                    {
                        "name": "apikey",
                        "value": "={{ $('Normalizacion').item.json.instance_apikey }}",
                    }
                ]
            },
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": (
                "={{ JSON.stringify({"
                " number: $('Normalizacion').item.json.user_number,"
                " text: $json.respuesta,"
                " delay: 1000"
                " }) }}"
            ),
            "options": {},
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [100, 180],
        "id": _nuevo_id(),
        "name": NODO_HTTP,
    }


def _nodo_armar_menu() -> dict:
    """Set: arma el campo `respuesta` con el menu de comandos."""
    return {
        "parameters": {
            "assignments": {
                "assignments": [
                    {
                        "id": _nuevo_id(),
                        "name": "respuesta",
                        "value": MENU_COMANDOS,
                        "type": "string",
                    }
                ]
            },
            "options": {},
        },
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [-100, 400],
        "id": _nuevo_id(),
        "name": NODO_MENU,
    }


# --------------------------------------------------------------------------
# Estructura final
# --------------------------------------------------------------------------


def construir_nodos() -> dict:
    """Devuelve {'nodes': [...], 'connections': {...}} con los 4 nodos nuevos."""
    nodes = [
        _nodo_if_operador(),
        _nodo_router_comandos(),
        _nodo_responder_operador(),
        _nodo_armar_menu(),
    ]

    # --- Salidas del Router de comandos -----------------------------------
    # Orden: COMANDOS en el mismo orden de la constante + fallback AL FINAL.
    salidas_router = []
    for comando in COMANDOS:
        if comando == "COMANDOS":
            salidas_router.append([_conexion(NODO_MENU)])
        else:
            # Se implementaran mas adelante: por ahora sin destino.
            salidas_router.append([])
    # Fallback ("No es comando") -> sin destino: el flujo de cliente continua aparte.
    salidas_router.append([])

    connections = {
        # IF: salida 0 (true) -> Router ; salida 1 (false) -> sin conectar.
        NODO_IF: {
            "main": [
                [_conexion(NODO_ROUTER)],
                [],
            ]
        },
        NODO_ROUTER: {"main": salidas_router},
        # Menu -> responder al operador.
        NODO_MENU: {"main": [[_conexion(NODO_HTTP)]]},
    }

    return {"nodes": nodes, "connections": connections}


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------


def _walk_strings(obj):
    """Recorre recursivamente y devuelve todos los strings encontrados."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for clave, valor in obj.items():
            yield clave if isinstance(clave, str) else ""
            yield from _walk_strings(valor)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from _walk_strings(item)


def validar(estructura: dict) -> None:
    """Ejecuta los asserts de validacion sobre la estructura generada."""
    nodes = estructura["nodes"]
    connections = estructura["connections"]

    # 1) Exactamente 4 nodos.
    assert len(nodes) == 4, "Se esperaban 4 nodos, hay %d" % len(nodes)

    # 2) Nombres esperados.
    nombres = [n["name"] for n in nodes]
    esperados = [NODO_IF, NODO_ROUTER, NODO_HTTP, NODO_MENU]
    assert nombres == esperados, "Nombres inesperados: %r" % (nombres,)

    # 3) Campos obligatorios en cada nodo.
    for nodo in nodes:
        for campo in ("id", "type", "position", "parameters", "typeVersion", "name"):
            assert campo in nodo, "Nodo %s sin campo %s" % (nodo.get("name"), campo)
        assert isinstance(nodo["parameters"], dict)

    # 4) El router tiene 13 salidas: 12 comandos + fallback.
    router = next(n for n in nodes if n["name"] == NODO_ROUTER)
    valores = router["parameters"]["rules"]["values"]
    assert len(valores) == 12, "El router deberia tener 12 reglas, tiene %d" % len(valores)
    assert router["parameters"]["options"]["fallbackOutput"] == "extra"
    assert router["parameters"]["options"]["renameFallbackOutput"] == "No es comando"
    assert len(connections[NODO_ROUTER]["main"]) == 13, (
        "El router deberia tener 13 salidas conectadas, tiene %d"
        % len(connections[NODO_ROUTER]["main"])
    )
    claves = [v["outputKey"] for v in valores]
    assert claves == COMANDOS, "Orden de comandos inesperado: %r" % (claves,)

    # 5) Ninguna expresion/string contiene '**' (negrita WhatsApp = un asterisco).
    for texto in _walk_strings(estructura):
        assert "**" not in texto, "Se encontro '**' en: %r" % (texto[:120],)

    # 6) Serializable a JSON y conexiones coherentes.
    json.dumps(estructura, ensure_ascii=False)
    existentes = {n["name"] for n in nodes}
    for origen, salidas in connections.items():
        assert origen in existentes, "Conexion desde nodo inexistente: %s" % origen
        for salida in salidas["main"]:
            for destino in salida:
                assert destino["node"] in existentes, (
                    "Conexion hacia nodo inexistente: %s" % destino["node"]
                )


if __name__ == "__main__":
    estructura = construir_nodos()
    validar(estructura)

    print(json.dumps(estructura, indent=2, ensure_ascii=False))
    print("")
    print("Nodos generados: %d" % len(estructura["nodes"]))
    print(
        "Salidas del router: %d (12 comandos + 1 fallback)"
        % len(estructura["connections"][NODO_ROUTER]["main"])
    )
    print("OK")