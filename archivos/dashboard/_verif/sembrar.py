#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Siembra un mes realista de barberia en barber_citas / barber_clientes.

TODO lo que inserta lleva prefijo `verif-` en el id (citas) o en el jid
(clientes), para poder borrarlo con precision.

Casos extremos incluidos a proposito:
  - un sabado con 20 citas
  - un cliente con gasto altisimo (muchos peinados $300)
  - citas de servicio "Depilacion" SIN precio (precio NULL)
  - nombres de cliente muy largos
"""
from __future__ import annotations

import datetime as dt
import random
import sys

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar, ejecutar

random.seed(20260925)

# --- catalogo real de barber_servicios ---
SERVICIOS = [
    ("Corte desvanecido o tijera", 150, 40),
    ("Arreglo de barba", 100, 20),
    ("Ceja", 30, 10),
    ("Mascarilla", 50, 20),
    ("Corte de cabello dama", 250, 50),
    ("Planchado express", 150, 30),
    ("Peinado", 300, 45),
    ("Depilación", None, 30),   # segun zona -> sin precio
]

PESOS = [40, 22, 12, 6, 8, 5, 4, 3]   # frecuencia relativa

NOMBRES = [
    "Luis Ángel Ramírez", "Jorge Antonio Mendoza", "Miguel Ángel Torres",
    "Francisco Javier Salinas", "Roberto Carlos Núñez", "Alejandro Vidal",
    "Juan Pablo Escobar", "Diego Armando Reyna", "Ricardo Alberto Peña",
    "Fernando Iván Castillo", "Óscar Eduardo Zamora", "Héctor Manuel Rivas",
    "Gerardo Adrián Lozano", "Sergio Andrés Villalobos", "Raúl Alejandro Bustos",
    "María Fernanda Quintero", "Ana Sofía Delgadillo", "Guadalupe Yolanda Rangel",
    "Verónica Alejandra Ibarra", "Claudia Beatriz Maldonado",
    "María de los Ángeles Guzmán Barrera", "Ana Patricia Villaseñor y Robles",
    "Juan Carlos Domínguez Arellano III", "José María Fernández de Córdova y Alcántara",
    "Brenda Jazmín Huerta", "Pedro Iván Macías", "Tomás Emilio Barragán",
    "Emiliano Zapata Ríos", "Nicolás Alejandro Buenrostro", "Adrián Felipe Quiroz",
    "Cristian Eduardo Nápoles", "Daniel Alberto Sepúlveda", "Iván de Jesús Carrillo",
    "Marco Tulio Esparza", "Rodrigo Alonso Betancourt", "Israel de la Cruz Márquez",
    "Enrique Yamil Ponce", "Gustavo Adolfo Lemus", "Octavio Ramiro Fuentes",
    "Bernardo Javier Delgado", "César Augusto Lomelí", "Ángel Gabriel Paredes",
    "Salvador Uriel Ocampo", "Ramón Alberto Tiscareño", "Efraín Napoleón Guajardo",
    "Martín Ricardo Covarrubias", "Israel Alejandro Villanueva", "Uriel Sebastián Anaya",
    "Brayan Alexis Moreno", "Kevin Yair Estrada", "Jonathan Emmanuel Salcedo",
    "Julio César Villalobos", "Aldo Fabián Zamudio", "Cristóbal Andrés Mejía",
    "Rubén Darío Escalante",
]

ETIQUETAS = ["nuevo", "frecuente", "frecuente", "frecuente", "vip", "en_riesgo",
             "problematico", "consulta", "inactivo"]


def esc(s: str) -> str:
    return s.replace("'", "''")


def traer_hoy():
    s = consultar("SET TIME ZONE 'America/Mexico_City';\n\\echo ===@@h@@===\n"
                  "SELECT to_char(current_date,'YYYY-MM-DD') AS hoy;")
    return dt.date.fromisoformat(s["h"][0]["hoy"])


HOY = traer_hoy()
print("hoy (Mexico):", HOY, HOY.strftime("%A"))

# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
N_CLIENTES = 55
clientes = []
for i, nombre in enumerate(NOMBRES[:N_CLIENTES]):
    jid = f"verif-cli{i:02d}@s.whatsapp.net"
    tel = f"4{random.randint(10000000, 99999999)}"
    visitas = random.randint(1, 28)
    no_shows = random.randint(0, 3) if random.random() < 0.3 else 0
    canc = random.randint(0, 2) if random.random() < 0.2 else 0
    ticket = round(random.uniform(80, 320), 2)
    etq = random.choice(ETIQUETAS)
    clientes.append(dict(jid=jid, nombre=nombre, telefono=tel, visitas=visitas,
                         no_shows=no_shows, cancelaciones=canc, ticket=ticket,
                         etiqueta=etq))

# cliente de gasto altisimo
clientes.append(dict(jid="verif-vip@s.whatsapp.net",
                     nombre="Cliente de Gasto Altísimo (VIP histórico)",
                     telefono="4521234567", visitas=64, no_shows=0,
                     cancelaciones=0, ticket=1180.50, etiqueta="vip"))

citas = []


def agrega(dia: dt.date, hora: int, minuto: int, cli: dict, srv, estado: str,
           n: int):
    nombre_srv, precio_base, dur = srv
    ini = dt.datetime(dia.year, dia.month, dia.day, hora, minuto)
    fin = ini + dt.timedelta(minutes=dur)
    if fin.hour > 20 or (fin.hour == 20 and fin.minute > 0):
        return None
    precio = precio_base
    # Depilacion: a veces sin precio (segun zona), a veces con precio
    if precio_base is None:
        precio = None if random.random() < 0.6 else random.choice([120, 180, 250])
    citas.append(dict(
        id=f"verif-c{n:04d}", jid=cli["jid"], nombre=cli["nombre"],
        servicio=nombre_srv, precio=precio,
        inicio=ini.strftime("%Y-%m-%d %H:%M:%S"),
        fin=fin.strftime("%Y-%m-%d %H:%M:%S"),
        estado=estado))
    return True


n = 0
# ---- 30 dias hacia atras (y algo mas: cubre agosto para recurrentes) ----
dias = []
d = HOY - dt.timedelta(days=38)
while d < HOY:
    dias.append(d)
    d += dt.timedelta(days=1)

for dia in dias:
    # domingo cerrado (weekday 6)
    if dia.weekday() == 6:
        continue
    es_sabado = (dia.weekday() == 5)
    cuantas = random.randint(4, 6) if es_sabado else random.randint(3, 6)
    disponibles = list(range(10, 20))
    random.shuffle(disponibles)
    slots = sorted(disponibles[:cuantas])
    for h in slots:
        cli = random.choice(clientes)
        srv = random.choices(SERVICIOS, weights=PESOS, k=1)[0]
        r = random.random()
        if dia < HOY:
            estado = "atendido" if r < 0.80 else ("no_show" if r < 0.90 else "cancelado")
        else:
            estado = "atendido"
        if agrega(dia, h, random.choice([0, 0, 10, 20, 30]), cli, srv, estado, n):
            n += 1

# ---- SABADO EXTREMO: 20 citas ----
sab = HOY - dt.timedelta(days=6)
while sab.weekday() != 5:
    sab -= dt.timedelta(days=1)
print("sabado extremo:", sab)
horas20 = [10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17,
           18, 18, 19, 19]
for k, h in enumerate(horas20):
    cli = random.choice(clientes)
    srv = SERVICIOS[k % len(SERVICIOS)]
    agrega(sab, h, 0 if k % 2 == 0 else 30, cli, srv, "atendido", n)
    n += 1

# ---- Cliente de gasto altisimo: 6 peinados $300 el mismo dia ----
dia_vip = HOY - dt.timedelta(days=3)
if dia_vip.weekday() == 6:
    dia_vip -= dt.timedelta(days=1)
vip = clientes[-1]
for h in [10, 11, 12, 15, 16, 17]:
    agrega(dia_vip, h, 0, vip, SERVICIOS[6], "atendido", n)
    n += 1

# ---- HOY ----
hoy_horas = [10, 11, 12, 13, 16, 17, 18]
for k, h in enumerate(hoy_horas):
    cli = random.choice(clientes)
    srv = SERVICIOS[k % len(SERVICIOS)]
    est = "atendido" if h < 17 else ("agendado" if h >= 18 else "confirmado")
    agrega(HOY, h, 0, cli, srv, est, n)
    n += 1

# ---- FUTURO (proximas citas) ----
for delta in range(1, 11):
    dia = HOY + dt.timedelta(days=delta)
    if dia.weekday() == 6:
        continue
    cuantas = random.randint(2, 4)
    for h in sorted(random.sample(range(10, 19), cuantas)):
        cli = random.choice(clientes)
        srv = random.choices(SERVICIOS, weights=PESOS, k=1)[0]
        agrega(dia, h, 0, cli, srv,
               "confirmado" if random.random() < 0.4 else "agendado", n)
        n += 1

print("clientes:", len(clientes), "citas:", len(citas))

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------
partes = ["SET TIME ZONE 'America/Mexico_City';",
          "BEGIN;",
          "DELETE FROM barber_citas WHERE id LIKE 'verif-%';",
          "DELETE FROM barber_clientes WHERE jid LIKE 'verif-%';"]

vals = []
for c in clientes:
    vals.append("('%s','%s','%s',%d,%d,%d,%.2f,'%s')" % (
        esc(c["jid"]), esc(c["nombre"]), esc(c["telefono"]),
        c["visitas"], c["no_shows"], c["cancelaciones"], c["ticket"],
        esc(c["etiqueta"])))
partes.append("INSERT INTO barber_clientes (jid,nombre,telefono,visitas,"
              "no_shows,cancelaciones_tardias,ticket_promedio,etiqueta) VALUES "
              + ",".join(vals) + ";")

vals = []
for c in citas:
    p = "NULL" if c["precio"] is None else str(c["precio"])
    vals.append("('%s','%s','%s','%s',%s,'%s','%s','%s')" % (
        esc(c["id"]), esc(c["jid"]), esc(c["nombre"]), esc(c["servicio"]),
        p, c["inicio"], c["fin"], c["estado"]))
partes.append("INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,"
              "fin,estado) VALUES " + ",".join(vals) + ";")
partes.append("COMMIT;")

sql = "\n".join(partes)
rc, out, err = ejecutar(sql)
print("RC:", rc)
print(out[-2000:] if out else "")
print("ERR:", err[:3000] if err else "")

# resumen
s = consultar("""SET TIME ZONE 'America/Mexico_City';
\\echo ===@@r@@===
SELECT (SELECT count(*) FROM barber_citas WHERE id LIKE 'verif-%') AS citas_verif,
       (SELECT count(*) FROM barber_clientes WHERE jid LIKE 'verif-%') AS cli_verif,
       (SELECT count(*) FROM barber_citas) AS citas_total,
       (SELECT count(*) FROM barber_citas WHERE precio IS NULL) AS sin_precio,
       (SELECT count(*) FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL
         AND inicio::date = current_date) AS atendidas_hoy;
""")
print(s["r"])