# -*- coding: utf-8 -*-
"""Auditoria de la BUSQUEDA de conocimiento: 50+ consultas reales."""
import sys, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, buscar

# (consulta, id_esperado, ids_aceptables, nota)
CASOS = [
    # --- como escribe la gente: sin acentos, minusculas, con faltas ---
    ("q precio tiene el corte", 23, {23, 25}, "minusculas, abreviado"),
    ("cuanto vale la barba", 26, {26, 12}, "sin acentos"),
    ("hacen cita pa hoy", 212, {212, 32, 4}, "abreviado 'pa'"),
    ("donde estan ubicados", 1, {1}, "sin acentos"),
    ("a que hora abren", 6, {6}, "sin acentos"),
    ("kual es el orario", 6, {6}, "faltas de ortografia"),
    ("tienen estoacionamiento", 3, {3}, "falta de ortografia"),
    ("q dias abren", 6, {6, 7}, ""),
    ("abren domingo", 7, {7, 6}, ""),
    ("cuanto cuesta el corte", 23, {23}, ""),
    ("cuanto cuesta el corte de dama", 24, {24, 11}, ""),
    ("cuanto cuesta la ceja", 27, {27, 13}, ""),
    ("cuanto cuesta la depilacion", 17, {17}, "sin acento"),
    ("cuanto cuesta la depilación", 17, {17}, "con acento"),
    ("depilacion", 17, {17}, "una palabra, sin acento"),
    ("depilación", 17, {17}, "una palabra, con acento"),
    ("DEPILACION", 17, {17}, "mayusculas"),
    ("depilasion", 17, {17}, "falta de ortografia s/c"),
    ("me dan la lista de precios", 25, {25}, ""),
    ("precio de todo", 25, {25, 10}, ""),
    ("que servicios tienen", 10, {10}, ""),
    ("hacen tinte", 18, {18}, ""),
    ("me pueden pintar el pelo", 18, {18}, "sinonimo"),
    ("hacen planchado", 15, {15}, ""),
    ("hacen peinado", 16, {16}, ""),
    ("hacen las cejas", 13, {13}, ""),
    ("arreglan la barba", 12, {12, 26}, ""),
    ("corte para dama", 11, {11, 24}, ""),
    ("corte para nino", 20, {20, 5, 214}, ""),
    ("corte para niño", 20, {20, 5, 214}, ""),
    ("puedo llevar a mi hijo", 214, {214, 5, 20}, ""),
    ("aceptan ninos", 5, {5, 214, 20}, ""),
    # --- duracion ---
    ("cuanto tarda un corte", 209, {209, 210}, ""),
    ("cuanto dura el corte", 209, {209, 210}, ""),
    ("cuanto dura cada servicio", 210, {210}, ""),
    ("cuanto dura la barba", 211, {211, 12, 26}, ""),
    ("duracion del peinado", 210, {210, 16}, ""),
    # --- pagos / politicas ---
    ("aceptan tarjeta", 30, {30, 31}, ""),
    ("puedo pagar con transferencia", 31, {31, 30}, ""),
    ("se puede pagar con efectivo", 30, {30, 31}, ""),
    ("como pago", 30, {30, 31}, ""),
    ("dan factura", 48, {48}, ""),
    ("necesito factura", 48, {48}, "sinonimo"),
    ("hay descuento", 28, {28, 29}, ""),
    ("me hacen precio si llevo a mi amigo", 29, {29, 28, 35}, ""),
    ("puedo cancelar mi cita", 38, {38, 42}, ""),
    ("quiero mover mi cita", 39, {39}, ""),
    ("puedo reprogramar", 39, {39}, "sinonimo"),
    ("que pasa si llego tarde", 40, {40, 213}, ""),
    ("cobran si no llego", 42, {42, 38}, "HUECO real en BD"),
    ("hay garantia", 43, {43}, ""),
    # --- instalaciones / general ---
    ("tienen wifi", 215, {215}, ""),
    ("hay wifi", 215, {215}, ""),
    ("tienen instagram", 51, {51}, ""),
    ("venden shampoo", 49, {49}, ""),
    ("puedo poner una queja", 50, {50}, ""),
    ("quien me atiende", 45, {45}, ""),
    ("hay otro barbero", 46, {46}, ""),
    ("atienden a domicilio", 37, {37}, ""),
    ("puedo ir sin cita", 4, {4, 44}, ""),
    ("necesito cita para la ceja", 44, {44, 4}, ""),
    ("hasta que hora puedo agendar", 8, {8}, ""),
    ("atienden en dias festivos", 9, {9}, ""),
    ("puedo agendar el mismo dia", 212, {212}, ""),
    ("con cuanto tiempo de anticipacion agendo", 36, {36}, ""),
    ("cuanto tiempo antes debo llegar", 34, {34, 40}, ""),
    ("cual es la politica de cancelacion", 42, {42, 38}, ""),
    ("puedo apartar dos citas", 35, {35}, ""),
    ("cual es el telefono", 2, {2}, ""),
    ("cual es el horario", 6, {6}, ""),
    ("prefiero un bob", 21, {21, 10}, "estilo fuera de catalogo"),
    ("que es la mascarilla", 14, {14}, ""),
    ("trabajan con maquina o navaja", 19, {19, 23}, ""),
    ("que me recomiendas si es mi primera vez", 22, {22, 23}, ""),
    ("tienen evento para boda", 52, {52, 16}, ""),
]

# --- casos borde: deben devolver 0 filas SIN error ---
BORDE = [
    ("", "cadena vacia"),
    ("   ", "solo espacios"),
    ("?", "solo signo"),
    ("!", "solo signo"),
    ("12345", "solo numeros"),
    ("0", "un digito"),
    ("😀😀😀", "solo emojis"),
    ("🔥💈✂️", "emojis barberia"),
    ("a", "una letra"),
    ("..", "puntos"),
    ("'" + "x" * 500, "500 caracteres de basura + comilla"),
    ("basura" * 80, "480 caracteres repetidos"),
    ("' OR 1=1 --", "intento de inyeccion SQL"),
    ("'; DROP TABLE barber_conocimiento; --", "intento DROP TABLE"),
    ("%", "comodin LIKE"),
    ("$_$", "simbolos"),
    ("\u0000null", "NUL"),
    ("que como donde cuando", "solo palabras vacias"),
    ("<script>alert(1)</script>", "html"),
]

out = []
out.append("=" * 78)
out.append("AUDITORIA DE LA BUSQUEDA  barber_buscar_conocimiento(texto, limite)")
out.append("=" * 78)

n = aciertos = 0
fallos = []
for texto, esperado, acept, nota in CASOS:
    filas, err = buscar(texto, 3)
    n += 1
    primero = filas[0]["pregunta"].strip() if filas else None
    idp = None
    if filas:
        _, r = q("SELECT id FROM barber_conocimiento WHERE pregunta=%s", (filas[0]["pregunta"],))
        idp = r[0][0] if r else None
    ok = (idp == esperado) or (idp in acept)
    if ok:
        aciertos += 1
    else:
        fallos.append((texto, esperado, idp, primero, nota, filas))
    out.append("%s q=%-45r esperado=#%-3d primero=#%-4s %s" % (
        "OK  " if ok else "FALLA", texto, esperado, idp,
        (primero or "(SIN RESULTADO)")[:60]))
    if err:
        out.append("        ERROR: " + err)
    if not ok:
        out.append("        aceptables=%s nota=%s" % (sorted(acept), nota))
        for f in filas[:3]:
            out.append("        >> #%s %s (%s) rank=%.4f" % (
                "", f["pregunta"], f["origen"], f["rank"]))

pct = 100.0 * aciertos / n
out.append("")
out.append("RESULTADO: %d/%d aciertan la FAQ correcta como PRIMER resultado = %.1f%%"
           % (aciertos, n, pct))

out.append("")
out.append("=" * 78)
out.append("CASOS BORDE (deben dar 0 filas SIN error)")
out.append("=" * 78)
borde_ok = 0
for texto, nota in BORDE:
    try:
        filas, err = buscar(texto, 3)
    except Exception as e:
        filas, err = [], "EXCEPCION %s: %s" % (type(e).__name__, e)
    estado = "OK" if (err is None and len(filas) == 0) else "REVISAR"
    if estado == "OK":
        borde_ok += 1
    out.append("%-8s %-42s filas=%d err=%s" % (
        estado, nota, len(filas), err or "ninguno"))
    for f in filas[:3]:
        out.append("         -> %s" % f["pregunta"])
out.append("")
out.append("casos borde sin error y con 0 filas: %d/%d" % (borde_ok, len(BORDE)))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\busqueda.txt", "w", encoding="utf-8").write(txt)
print("consultas=%d aciertos=%d pct=%.1f%%" % (n, aciertos, pct))
print("borde ok=%d/%d" % (borde_ok, len(BORDE)))
print("escrito _aud_con\\busqueda.txt")