import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

out = []
out.append("== limite fuera de rango (count de filas reales) ==")
for lim in [0, -5, 1, 3, 21, 1000, 20]:
    try:
        r = q("SELECT count(*) FROM public.barber_buscar_conocimiento('corte', %s)", (lim,))[1][0][0]
        out.append("limite=%-5s -> %d filas" % (lim, r))
    except Exception as e:
        out.append("limite=%-5s -> ERROR %s" % (lim, e))
out.append("")
out.append("== limite NULL ==")
try:
    r = q("SELECT count(*) FROM public.barber_buscar_conocimiento('corte', NULL)")[1][0][0]
    out.append("limite=NULL -> %d filas" % r)
except Exception as e:
    out.append("limite=NULL -> ERROR %s" % e)
out.append("")
out.append("== consulta NULL ==")
try:
    r = q("SELECT count(*) FROM public.barber_buscar_conocimiento(NULL)")[1][0][0]
    out.append("consulta=NULL -> %d filas" % r)
except Exception as e:
    out.append("consulta=NULL -> ERROR %s" % e)
out.append("")
out.append("== la funcion FUNCIONA con la funcion VIEJA barber_buscar? ==")
for t in ["cuanto cuesta el corte", "tienen wifi", "dan factura"]:
    try:
        r = q("SELECT pregunta, rank FROM barber_buscar(%s, 1)", (t,))[1]
        out.append("barber_buscar(%r) -> %s" % (t, r))
    except Exception as e:
        out.append("barber_buscar(%r) -> ERROR %s" % (t, e))
out.append("")
out.append("== 'depilasion' / 'estoacionamiento': por que fallan ==")
for t in ["depilasion", "depilacion", "estoacionamiento", "estacionamiento",
          "orario", "horario", "kual", "cual"]:
    lex = q("SELECT tsvector_to_array(to_tsvector('public.spanish_unaccent', %s))", (t,))[1][0][0]
    out.append("%-20r -> lexemas %s" % (t, lex))
out.append("")
out.append("== lexemas que la BD guarda para las palabras clave ==")
for t in ["depilación", "estacionamiento", "horario", "ubicación", "barba"]:
    lex = q("SELECT tsvector_to_array(to_tsvector('public.spanish_unaccent', %s))", (t,))[1][0][0]
    out.append("%-20r -> lexemas %s" % (t, lex))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\limites.txt", "w", encoding="utf-8").write(txt)
print(txt)