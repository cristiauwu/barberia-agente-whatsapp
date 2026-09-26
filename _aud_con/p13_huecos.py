import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, buscar

out = []

def bloque(titulo, consultas):
    out.append("== %s ==" % titulo)
    for t in consultas:
        filas, err = buscar(t, 3)
        out.append("  q=%-46r -> %s" % (
            t, ("SIN RESULTADO (0 filas)" if not filas else
                " / ".join(f["pregunta"] for f in filas[:2]))))

bloque("SINONIMOS pedidos en la auditoria", [
    "checar mi cita", "consultar mi cita", "como checo si tengo cita",
    "cortarme el pelo", "quiero cortarme", "corte de pelo", "cortada",
    "como hago el pago", "el cobro", "cuanto me cobran", "cuanto es el cobro",
    "apartar", "reservar", "turno", "hueco", "cita",
    "cuanto vale", "cuanto sale", "cuanto es", "precio", "tarifa", "costo",
])

bloque("HUECOS: cosas que un cliente real preguntaria", [
    "hay estacionamiento cerca",
    "como llego en camion",
    "tienen uber",
    "aceptan deposito",
    "puedo pagar con qr",
    "puedo pagar con mercado pago",
    "hay cajero cerca",
    "cortan el cabello a bebes",
    "mi hijo tiene 3 anos",
    "hacen cortes para bebe",
    "tienen servicio de dama para novia",
    "me hacen corte de novio",
    "hay promocion",
    "hay paquete de corte y barba",
    "hacen corte y barba juntos",
    "cuanto tiempo tengo que esperar si llego sin cita",
    "hay mucha fila",
    "que pasa si llueve",
    "que pasa si no puedo llegar",
    "que pasa si me cancelan",
    "tengo que llegar antes",
    "puedo llegar 10 minutos tarde",
    "puedo llevar a mi esposa",
    "atienden a mi abuelo en silla de ruedas",
    "tienen baño",
    "puedo pagar en dolares",
    "me dan ticket o recibo",
    "me dan comprobante",
    "tienen tarjeta de lealtad",
    "me guardan mi lugar si llego tarde",
    "hay que hacer cita para el corte",
    "el barbero habla ingles",
    "puedo ir con mi novio",
    "que ciudad es",
    "en que colonia estan",
    "tienen pagina web",
    "tengo que descargar una app",
    "hacen uñas",
    "hacen tatuajes",
    "tienen regalo o tarjeta de regalo",
    "hay algo para la caida del cabello",
    "hacen tratamiento capilar",
    "trabajan los lunes",
    "estan abiertos ahora",
    "a que hora cierran hoy",
    "cuanto cuesta el planchado",
    "hay anticipo para apartar",
    "debo dar deposito para reservar",
])

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\huecos.txt", "w", encoding="utf-8").write(txt)
print(txt)