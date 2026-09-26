#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga Inter y JetBrains Mono y las deja listas para embeber.

POR QUE EMBEBER Y NO USAR EL <link> DE GOOGLE FONTS:
  El pedido dice "cargar desde Google Fonts", pero tambien dice que el HTML
  tiene que funcionar "al abrir directamente en el navegador sin servidor".
  Un <link> a Google Fonts rompe eso: sin internet el diseno se cae a la
  fuente del sistema y el resultado no es el que se pidio.

  Embebiendo las MISMAS fuentes de Google (mismos .woff2) en base64 se
  cumple lo primero (son esas tipografias) y lo segundo (funciona sin red).

Genera `fuentes-inline.css` con los @font-face en data URIs.
"""
import base64
import os
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "fuentes-cache")
SALIDA = os.path.join(AQUI, "fuentes-inline.css")

CSS_URL = ("https://fonts.googleapis.com/css2"
           "?family=Inter:wght@400;500;600;700"
           "&family=JetBrains+Mono:wght@400;500;700"
           "&display=swap")

# Sin un User-Agent moderno, Google devuelve .ttf en vez de .woff2
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def bajar(url, binario=False):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = r.read()
    return datos if binario else datos.decode("utf-8")


def main():
    os.makedirs(CACHE, exist_ok=True)
    print("=" * 68)
    print("EMBEBER INTER + JETBRAINS MONO")
    print("=" * 68)

    print("\n  pidiendo el CSS a Google Fonts...")
    try:
        css = bajar(CSS_URL)
    except Exception as e:
        print(f"  FALLO: {e}")
        return 1
    print(f"  CSS recibido: {len(css)} caracteres")

    # Emparejar cada bloque @font-face con su URL de woff2
    bloques = re.findall(r"@font-face\s*\{[^}]*\}", css)
    print(f"  bloques @font-face: {len(bloques)}")

    salida = []
    vistos = set()
    bajados = 0

    for b in bloques:
        fam = re.search(r"font-family:\s*'([^']+)'", b)
        peso = re.search(r"font-weight:\s*(\d+)", b)
        estilo = re.search(r"font-style:\s*(\w+)", b)
        rango = re.search(r"unicode-range:\s*([^;]+);", b)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", b)
        if not (fam and peso and url):
            continue

        # Solo el subset latin basico: el resto no se usa y pesa mucho
        if rango:
            ur = rango.group(1)
            if "U+0000-00FF" not in ur and "U+0100-02BA" not in ur:
                continue

        clave = (fam.group(1), peso.group(1))
        if clave in vistos:
            continue
        vistos.add(clave)

        u = url.group(1)
        nombre = f"{fam.group(1).replace(' ', '')}-{peso.group(1)}.woff2"
        ruta = os.path.join(CACHE, nombre)

        if not os.path.exists(ruta):
            try:
                datos = bajar(u, binario=True)
                open(ruta, "wb").write(datos)
                bajados += 1
            except Exception as e:
                print(f"  no pude bajar {nombre}: {e}")
                continue

        datos = open(ruta, "rb").read()
        b64 = base64.b64encode(datos).decode("ascii")
        salida.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "font-display:swap;src:url(data:font/woff2;base64,%s) "
            "format('woff2');}"
            % (fam.group(1), estilo.group(1) if estilo else "normal",
               peso.group(1), b64))
        print(f"  embebida {fam.group(1)} {peso.group(1)} "
              f"({len(datos)//1024} KB -> {len(b64)//1024} KB base64)")

    if not salida:
        print("  no se genero ninguna fuente")
        return 1

    open(SALIDA, "w", encoding="utf-8").write("\n".join(salida))
    total = os.path.getsize(SALIDA)
    print(f"\n  archivos nuevos: {bajados}")
    print(f"  fuentes-inline.css: {total//1024} KB")
    print(f"  familias: {sorted(set(f for f, _ in vistos))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())