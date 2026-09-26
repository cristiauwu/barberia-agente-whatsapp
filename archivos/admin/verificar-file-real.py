#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que el panel funcione SIN servidor, midiendo de verdad.

CORRECCION METODOLOGICA: la sonda anterior metia el file:// dentro de un
iframe servido por http. Chrome bloquea eso (un iframe http no puede leer
un documento file://), asi que devolvia ceros y parecia un fallo. Era un
falso negativo de MI prueba, no del panel.

La forma correcta: cargar el PROPIO archivo con file:// y volcar el DOM
con --dump-dom. Asi lo que se lee es el documento real.

Se comprueba:
  1. Que el DOM volcado tiene el contenido (KPIs, citas, barras).
  2. Que las fuentes embebidas cargan (via un script inyectado).
  3. Que las barras tienen altura real.
"""
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
HTML = os.path.join(AQUI, "barber-chinos-admin.html")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Se copia el panel a un temporal con un script de medicion añadido al
# final. Asi se mide el documento REAL cargado por file://.
MEDIDOR = """
<script>
(function(){
  function medir(){
    var salida = [];
    var v = document.querySelector(".vista.activa");
    salida.push("vista=" + (v ? v.dataset.vistaPanel : "NINGUNA"));
    salida.push("texto=" + (v ? v.innerText.length : 0));
    salida.push("kpis=" + (v ? v.querySelectorAll(".kpi").length : 0));
    salida.push("citas=" + (v ? v.querySelectorAll(".cita").length : 0));
    var b = v ? v.querySelectorAll(".barra-col") : [];
    var conAlto = 0;
    b.forEach(function(x){
      if(parseFloat(getComputedStyle(x).height) > 1) conAlto++;
    });
    salida.push("barras=" + b.length + "/" + conAlto + "conAltura");
    var h1 = document.querySelector(".display");
    salida.push("fuenteTitulo=" + (h1 ? getComputedStyle(h1).fontFamily : "-"));
    salida.push("pesoTitulo=" + (h1 ? getComputedStyle(h1).fontWeight : "-"));
    salida.push("anchoTitulo=" + (h1 ? Math.round(h1.getBoundingClientRect().width) : 0));
    salida.push("fuentesCargadas=" + (document.fonts ? document.fonts.size : "?"));
    if(document.fonts){
      document.fonts.forEach(function(f){
        salida.push("font=" + f.family + "|" + f.weight + "|" + f.status);
      });
    }
    salida.push("anchoViewport=" + document.documentElement.clientWidth);
    var pre = document.getElementById("preloader");
    var ps = pre ? getComputedStyle(pre) : null;
    salida.push("preloader=" + (!pre || (ps.visibility === "hidden" &&
      parseFloat(ps.opacity) < 0.1) ? "oculto" : "VISIBLE"));
    var d = document.createElement("div");
    d.id = "MEDICION";
    d.textContent = salida.join(" ;; ");
    document.body.appendChild(d);
  }
  if(document.readyState === "complete") setTimeout(medir, 5200);
  else window.addEventListener("load", function(){ setTimeout(medir, 5200); });
})();
</script>
"""


def main():
    fallos = 0

    print("=" * 68)
    print("VERIFICACION SIN SERVIDOR (file://)")
    print("=" * 68)

    original = open(HTML, encoding="utf-8").read()
    temporal = os.path.join(AQUI, "_medir-file.html")
    open(temporal, "w", encoding="utf-8").write(
        original.replace("</body>", MEDIDOR + "</body>"))
    print(f"  copia de medicion creada")

    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--allow-file-access-from-files",
                        "--virtual-time-budget=15000", "--dump-dom",
                        "--window-size=1500,1700",
                        "file:///" + temporal.replace("\\", "/")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=220)

    m = re.search(r'<div id="MEDICION">(.*?)</div>', p.stdout or "", re.S)
    if not m:
        print("  MAL: no se pudo medir el documento cargado con file://")
        fallos += 1
        os.remove(temporal)
        return 1

    datos = {}
    for parte in m.group(1).split(" ;; "):
        parte = parte.strip()
        if "=" in parte:
            k, v = parte.split("=", 1)
            datos[k] = v
        elif parte.startswith("font="):
            datos.setdefault("fuentes", []).append(parte[5:])

    print()
    print("  --- lo que se midio con file:// ---")
    # OJO: los dias sin venta ($0) DEBEN quedarse a cero; no son un fallo.
    # Solo se comprueba que las barras con valor tengan altura.
    barras_txt = datos.get("barras", "")
    m2 = re.match(r"(\d+)/(\d+)conAltura", barras_txt)
    con_alto = int(m2.group(2)) if m2 else 0
    total_b = int(m2.group(1)) if m2 else 0
    pruebas = [
        ("el panel se renderiza",
         datos.get("vista") == "dashboard"),
        ("tiene texto", int(datos.get("texto", "0") or 0) > 800),
        ("tiene los 8 KPIs", datos.get("kpis") == "8"),
        ("tiene las 5 citas", datos.get("citas") == "5"),
        ("las barras con venta tienen altura (21 de 30: las otras 9 son "
         "domingos de $0)", total_b == 30 and con_alto == 21),
        ("la fuente del titulo es Inter",
         "Inter" in datos.get("fuenteTitulo", "")),
        ("el titulo pesa 700", datos.get("pesoTitulo") == "700"),
        ("las fuentes estan cargadas",
         int(datos.get("fuentesCargadas", "0") or 0) >= 4),
        ("el preloader ya no tapa el panel",
         datos.get("preloader", "") == "oculto"),
    ]
    for nombre, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {nombre}")
        if not ok:
            fallos += 1

    print()
    print(f"  vista activa      : {datos.get('vista')}")
    print(f"  caracteres        : {datos.get('texto')}")
    print(f"  KPIs / citas      : {datos.get('kpis')} / {datos.get('citas')}")
    print(f"  barras con altura : {datos.get('barras')}")
    print(f"  fuente del titulo : {datos.get('fuenteTitulo')}")
    print(f"  ancho del titulo  : {datos.get('anchoTitulo')}px")
    print(f"  fuentes cargadas  : {datos.get('fuentesCargadas')}")
    for f in datos.get("fuentes", []):
        print(f"     {f}")

    # captura real con file://
    archivo = os.path.join(AQUI, "capturas", "sin-servidor.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--allow-file-access-from-files",
                    "--virtual-time-budget=12000", "--window-size=1500,1800",
                    f"--screenshot={archivo}",
                    "file:///" + HTML.replace("\\", "/")],
                   capture_output=True, timeout=200)
    kb = os.path.getsize(archivo) // 1024 if os.path.exists(archivo) else 0
    print(f"\n  captura con file://: {kb} KB")
    if kb < 120:
        print("  MAL: demasiado liviana")
        fallos += 1

    os.remove(temporal)
    print()
    print("=" * 68)
    print(f"FALLOS: {fallos}")
    print("=" * 68)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())