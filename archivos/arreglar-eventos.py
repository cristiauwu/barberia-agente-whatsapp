#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reescribe la seccion de eventos del webhook en .env.evolution.

PROBLEMA detectado: solo estaban definidos 6 eventos; el resto quedaba con
el valor por defecto de la imagen (true), asi que llegaban en masa eventos
como chats.upsert, contacts.upsert, presence.update... Cada uno disparaba
una ejecucion en n8n.

SOLUCION: declarar EXPLICITAMENTE todos los eventos soportados, con solo
MESSAGES_UPSERT en true. Asi no queda ninguno al azar.
"""
import re
import sys

ENV = r"G:\Barberia\.env.evolution"

# Todos los eventos que soporta Evolution API v2 (del .env.example oficial)
EVENTOS = [
    "APPLICATION_STARTUP", "CALL", "CHATS_DELETE", "CHATS_SET",
    "CHATS_UPDATE", "CHATS_UPSERT", "CONNECTION_UPDATE", "CONTACTS_SET",
    "CONTACTS_UPDATE", "CONTACTS_UPSERT", "GROUP_PARTICIPANTS_UPDATE",
    "GROUP_UPDATE", "GROUPS_UPSERT", "LABELS_ASSOCIATION", "LABELS_EDIT",
    "LOGOUT_INSTANCE", "MESSAGES_DELETE", "MESSAGES_SET", "MESSAGES_UPDATE",
    "MESSAGES_UPSERT", "PRESENCE_UPDATE", "QRCODE_UPDATED",
    "REMOVE_INSTANCE", "SEND_MESSAGE", "TYPEBOT_CHANGE_START",
    "TYPEBOT_CHANGE_STATUS", "TYPEBOT_START",
]

# El unico que el agente necesita
ACTIVOS = {"MESSAGES_UPSERT"}


def main():
    with open(ENV, encoding="utf-8") as f:
        lineas = f.read().splitlines()

    # Quitar cualquier WEBHOOK_EVENTS_* previo
    limpias = [l for l in lineas if not l.startswith("WEBHOOK_EVENTS_")]

    # Insertar el bloque completo tras WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS
    salida = []
    insertado = False
    for l in limpias:
        salida.append(l)
        if l.startswith("WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS") and not insertado:
            salida.append("")
            salida.append("# Todos los eventos declarados EXPLICITAMENTE.")
            salida.append("# Solo MESSAGES_UPSERT (mensajes entrantes) va en true:")
            salida.append("# el resto generaria ejecuciones inutiles en n8n.")
            for ev in EVENTOS:
                val = "true" if ev in ACTIVOS else "false"
                salida.append(f"WEBHOOK_EVENTS_{ev}={val}")
            insertado = True

    if not insertado:
        print("No encontre WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS; abortado")
        return 1

    with open(ENV, "w", encoding="utf-8") as f:
        f.write("\n".join(salida) + "\n")

    print(f"Declarados {len(EVENTOS)} eventos; activos: {sorted(ACTIVOS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())