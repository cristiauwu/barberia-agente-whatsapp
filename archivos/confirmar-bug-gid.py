#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirma el bug de n8n: getSheetId no maneja el formato 'gid=N'.

getSheetId(value):
    if (value === 'gid=0') return 0;
    return parseInt(value);     <-- parseInt('gid=941506024') === NaN

Con 'gid=0' funciona por el caso especial. Con cualquier otro gid, NaN.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get_sheet_id_como_n8n(value):
    """Replica la funcion getSheetId de n8n."""
    if value == "gid=0":
        return 0
    # Equivalente a parseInt de JS: toma los digitos iniciales
    s = value.lstrip()
    num = ""
    for i, ch in enumerate(s):
        if ch.isdigit() or (i == 0 and ch in "+-"):
            num += ch
        else:
            break
    return int(num) if num and num not in ("+", "-") else float("nan")


def main():
    print("=" * 72)
    print("SIMULACION DE getSheetId() DE N8N")
    print("=" * 72)
    for v in ["gid=0", "0", "gid=941506024", "941506024", "another-sheet"]:
        r = get_sheet_id_como_n8n(v)
        estado = "OK" if not (isinstance(r, float) and r != r) else "NaN -> NOT FOUND"
        print(f"  getSheetId({v!r}) = {r}   {estado}")

    print()
    print("=" * 72)
    print("CONCLUSION")
    print("=" * 72)
    print("  'gid=0' funciona SOLO por el caso especial del codigo.")
    print("  Cualquier otro 'gid=N' produce NaN -> n8n busca una pestana")
    print("  con id NaN y responde 'Sheet with ID gid=N not found'.")
    print()
    print("  SOLUCION: poner el gid en crudo ('941506024'), sin el 'gid='.")
    return 0


if __name__ == "__main__":
    sys.exit(main())