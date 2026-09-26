#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que los 5 patrones del repo de referencia estan en el panel."""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

h = Path(r"G:\Barberia\archivos\dashboard\dashboard.html").read_text(
    encoding="utf-8")

print("=" * 70)
print("LOS 5 PATRONES DEL REPO, EN EL PANEL")
print("=" * 70)

print("\n1. Breakpoint con OR de orientacion (el dueno gira el telefono)")
ok1 = "orientation:portrait" in h
print(f"   {'SI' if ok1 else 'NO'}  @media (max-width:1100px), (orientation:portrait)")

print("\n2. Caption diminuto + cifra enorme")
ok2 = bool(re.search(r"\.kpi-t\{[^}]*color:var\(--tenue\)", h)) and \
      bool(re.search(r"\.kpi-v\{[^}]*font-size:clamp", h))
print(f"   {'SI' if ok2 else 'NO'}  .kpi-t (etiqueta tenue) + .kpi-v (cifra clamp)")

print("\n3. Acento unico en varias opacidades")
ops = sorted(set(re.findall(r"rgba\(223,99,65,\.(\d+)\)", h)))
print(f"   {'SI' if len(ops) >= 3 else 'NO'}  opacidades del naranja: "
      f"{', '.join('.' + o for o in ops)}")

print("\n4. Radios anidados decrecientes")
r1 = re.search(r"--radio:(\d+)px", h)
r2 = re.search(r"--radio-int:(\d+)px", h)
ok4 = r1 and r2 and int(r1.group(1)) >= int(r2.group(1))
print(f"   {'SI' if ok4 else 'NO'}  --radio:{r1.group(1) if r1 else '?'}px  "
      f"--radio-int:{r2.group(1) if r2 else '?'}px")

print("\n5. Ceros visibles en el estado vacio (no display:none)")
ok5 = ".vacio{" in h and "display:none" not in h.split(".vacio{")[1][:200]
print(f"   {'SI' if ok5 else 'NO'}  .vacio presente y visible")

print()
print("=" * 70)
print("DETALLES QUE EL INFORME DESTACA")
print("=" * 70)
detalles = [
    ("tabular-nums (cifras que no bailan)", "tabular-nums" in h),
    ("barras con altura minima (1.5% no 0%)", "max(1.5, " in h or
     "min-height:3px" in h),
    ("prefers-reduced-motion respetado", "prefers-reduced-motion" in h),
    ("fuentes embebidas", "data:font/woff2;base64" in h),
    ("cero refs externas", not re.search(r"https?://", h)),
    ("cero script/link externos", not re.search(r"<script src|<link", h)),
]
for nombre, ok in detalles:
    print(f"  {'OK  ' if ok else 'MAL '} {nombre}")

todos = [ok1, ok2, len(ops) >= 3, ok4, ok5] + [v for _, v in detalles]
print()
print("=" * 70)
print(f"RESULTADO: {sum(todos)} de {len(todos)} comprobaciones OK")
print("=" * 70)