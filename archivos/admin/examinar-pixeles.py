#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recorta la zona del grafico de la captura y la examina pixel a pixel.

La sonda dice que las barras miden 75px de alto, pero en la captura el
grafico se ve vacio. En vez de suponer, se mira el color real de los
pixeles en la banda donde deberian estar las barras.

El cobre es #C8956C. Si la banda tiene pixeles de ese color, las barras
estan dibujadas y el problema es de la captura, no del panel.
"""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import struct
import zlib


def leer_png(ruta):
    """Lee un PNG sin depender de librerias externas."""
    d = open(ruta, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es PNG")
    pos = 8
    ancho = alto = None
    prof = tipo = None
    idat = b""
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tipo = d[pos + 4:pos + 8]
        datos = d[pos + 8:pos + 8 + ln]
        if tipo == b"IHDR":
            ancho, alto, prof, tipo_col = struct.unpack(">IIBB", datos[:10])
        elif tipo == b"IDAT":
            idat += datos
        elif tipo == b"IEND":
            break
        pos += 12 + ln
    crudo = zlib.decompress(idat)
    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[tipo_col]
    # deshacer el filtro por linea
    paso = ancho * canales
    salida = bytearray()
    previa = bytearray(paso)
    p = 0
    for _ in range(alto):
        f = crudo[p]
        p += 1
        linea = bytearray(crudo[p:p + paso])
        p += paso
        if f == 1:
            for i in range(canales, paso):
                linea[i] = (linea[i] + linea[i - canales]) & 255
        elif f == 2:
            for i in range(paso):
                linea[i] = (linea[i] + previa[i]) & 255
        elif f == 3:
            for i in range(paso):
                a = linea[i - canales] if i >= canales else 0
                linea[i] = (linea[i] + ((a + previa[i]) >> 1)) & 255
        elif f == 4:
            for i in range(paso):
                a = linea[i - canales] if i >= canales else 0
                c = previa[i - canales] if i >= canales else 0
                b = previa[i]
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linea[i] = (linea[i] + pr) & 255
        salida += linea
        previa = linea
    return ancho, alto, canales, salida


def pixel(ancho, canales, datos, x, y):
    i = (y * ancho + x) * canales
    return datos[i], datos[i + 1], datos[i + 2]


def main():
    ruta = r"G:\Barberia\archivos\admin\capturas\escritorio.png"
    ancho, alto, canales, datos = leer_png(ruta)
    print("=" * 68)
    print("EXAMEN DE PIXELES DE LA CAPTURA")
    print("=" * 68)
    print(f"  imagen: {ancho}x{alto}, {canales} canales")

    # El grafico esta aproximadamente entre y=850 y y=1215 segun la captura
    print("\n  buscando pixeles de color cobre (#C8956C) en cada banda:")
    COBRE = (200, 149, 108)

    def parecido(p, q, tol=45):
        return all(abs(a - b) <= tol for a, b in zip(p, q))

    for y0, y1, nombre in ((820, 900, "arriba del grafico"),
                           (900, 1000, "zona alta del grafico"),
                           (1000, 1100, "zona media"),
                           (1100, 1215, "zona baja (base)"),
                           (1225, 1290, "leyenda bajo el grafico")):
        n = 0
        total = 0
        muestra = None
        for y in range(y0, min(y1, alto)):
            for x in range(300, 1520, 4):
                total += 1
                p = pixel(ancho, canales, datos, x, y)
                if parecido(p, COBRE, 40):
                    n += 1
                    if muestra is None:
                        muestra = (x, y, p)
        pct = n / total * 100 if total else 0
        extra = f"  primer pixar cobre en {muestra}" if muestra else ""
        print(f"  y {y0:>4}-{y1:<4} {nombre:24} "
              f"{n:>6} pixeles cobre ({pct:5.2f}%){extra}")

    print()
    print("  colores mas frecuentes en la banda del grafico (y 900-1200):")
    from collections import Counter
    c = Counter()
    for y in range(900, min(1200, alto), 6):
        for x in range(300, 1520, 6):
            c[pixel(ancho, canales, datos, x, y)] += 1
    for col, n in c.most_common(8):
        print(f"    #{col[0]:02X}{col[1]:02X}{col[2]:02X}  x{n}")


if __name__ == "__main__":
    main()