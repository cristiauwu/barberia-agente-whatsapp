#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Casos de conversacion en vivo. uso: vivo.py <id_caso>

El texto vive aqui (no en la linea de comandos) para no pelearse con el
paso de argumentos de PowerShell y los acentos.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"G:\Barberia\archivos\_verif-fechas")

CASOS = {
    # --- 2. uso conversacional de 'Que dia es' ---
    "c1": "¿Qué día cae el 27 de septiembre de 2026?",
    "c2": "¿Qué día es el 1 de octubre de 2026?",
    "c3": "Quiero un corte el viernes a las 4",
    "c4": "¿Qué día de la semana es mañana?",
    "c5": "Agéndame un corte el 30 de septiembre a las 3",
    "c6": "muéstrame mis próximas citas",

    # --- 3. horarios del negocio ---
    "h1": "Quiero un corte el lunes 28 de septiembre a las 19:30",
    "h2": "Quiero un corte el lunes 28 de septiembre a las 20:00",
    "h3": "Quiero un corte el lunes 28 de septiembre a las 9:00",
    "h4": "Quiero un corte el domingo 27 de septiembre a las 12:00",
    "h5": "Quiero un corte el jueves 24 de septiembre a las 4",

    # --- sondeos del parser de la herramienta (formatos no-ISO) ---
    "x1": "¿qué día de la semana cae el 27/12/2026?",
    "x2": "¿qué día cae el 05/01/2027?",
}

if __name__ == "__main__":
    cid = sys.argv[1]
    espera = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    texto = CASOS[cid]
    import enviar

    import runpy
    sys.argv = ["enviar.py", texto, cid, str(espera)]
    runpy.run_path(r"G:\Barberia\archivos\_verif-fechas\enviar.py",
                   run_name="__main__")