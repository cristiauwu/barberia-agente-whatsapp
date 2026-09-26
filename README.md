# Barber Chinos — Agente de citas por WhatsApp

Sistema completo de atención y agenda para una barbería, construido sobre
**n8n + Evolution API + Google Calendar + Google Sheets + Postgres**.

El bot atiende a los clientes por WhatsApp, agenda citas solo, avisa al
barbero y le da un panel con los números del negocio. **Funciona sin
depender de servicios de pago**: el único coste es el modelo de lenguaje.

> **Nota sobre datos:** todo lo que hay aquí es infraestructura y
> documentación. Las credenciales y claves **no** están en el repositorio
> (ver `.gitignore`); se leen de variables de entorno o de archivos locales.

---

## Qué hace

### Para el cliente

- Atiende por WhatsApp en español de México, con tono cercano y breve.
- Muestra el **menú de servicios con precios** en el primer mensaje.
- Verifica disponibilidad real en Google Calendar antes de agendar.
- Agenda, reprograma y cancela citas.
- Envía **recordatorios a las 24 h y a la 1 h** antes de la cita.
- No inventa precios ni servicios: lo que no sabe, lo escala al barbero.

### Para el barbero (Esteban Aguilera)

- **12 comandos por WhatsApp** que no cuestan tokens (no pasan por la IA).
- Avisos automáticos de cita nueva y de casos que el bot no pudo resolver.
- **Panel visual** con ingresos, citas, ticket promedio, horas pico, top
  servicios, no-shows y próximas citas.

### Los 12 comandos del dueño

| Comando | Qué hace |
|---|---|
| `HOY` | Agenda del día |
| `MAÑANA` | Agenda de mañana |
| `SEMANA` | Los próximos 7 días |
| `LIBRE` | Huecos disponibles |
| `CLIENTE 4521206246` | Ficha del cliente |
| `BLOQUEAR 14:00-15:30 comida` | Bloquea un rango |
| `CERRAR 24 dic` | Cierra un día |
| `ABRIR 24 dic` | Lo reabre |
| `PRECIO ceja 40` | Actualiza un precio |
| `PAUSA 4521206246 2h` | El bot deja de responderle |
| `ESTADO` | Salud del sistema |
| `COMANDOS` | Menú de ayuda |

---

## Arquitectura

```
WhatsApp ──► Evolution API ──► n8n (webhook)
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            Router de comandos          AI Agent
            (dueño, 0 tokens)        (cliente, con memoria)
                    │                         │
                    └────────────┬────────────┘
                                 ▼
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
        Google Calendar    Google Sheets      Postgres
        (las citas)        (el registro)    (CRM, FAQs, memoria)
                                 │
                                 ▼
                     Recordatorios 24 h y 1 h
                     + avisos al barbero
```

---

## Componentes

| Pieza | Qué es |
|---|---|
| `BarberiaAgenteFLUJO-1-UNCENSORED.json` | Workflow principal: conversación, comandos del dueño, validaciones |
| `BarberiaAgenteFLUJO-2-RECORDATORIOS.json` | Recordatorios y registro en la hoja |
| `prompt-sistema-agente-barberia.txt` | El prompt del agente (43 KB) |
| `archivos/dashboard/` | El panel visual del barbero |
| `verify.py` | **187 comprobaciones** automáticas del sistema |
| `archivos/*.py` | Scripts de instalación, arreglos y pruebas |
| `docker-compose*.yml` | n8n + Postgres + Evolution API |

---

## Instalación

### 1. Levantar los servicios

```powershell
# n8n + Postgres
docker compose up -d

# Evolution API (WhatsApp)
docker compose -f docker-compose.evolution.yml up -d
```

Detalles en **`COMO-CORRER-N8N.md`**.

### 2. Configurar las credenciales

Hacen falta cuatro:

| Credencial | Para qué |
|---|---|
| Evolution API | Enviar WhatsApp |
| Google Calendar | Leer y crear citas |
| Google Sheets | El registro |
| Uncensored AI | El modelo del agente |

Guía paso a paso en **`GUIA-CREDENCIALES.md`** y **`TUTORIAL-WHATSAPP-Y-GOOGLE.md`**.

### 3. Importar los workflows

Importa los dos JSON en n8n y actívalos.

### 4. Preparar la base de datos

```powershell
uv run python archivos/aplicar-esquema.py       # tablas del CRM
uv run python archivos/probar-consultas.py      # verifica
```

### 5. Verificar que todo funciona

```powershell
uv run python verify.py
```

Debe terminar con **`RESULTADO: 187 de 187 verificaciones PASARON`**.

---

## El panel del barbero

Se genera desde Postgres y **funciona sin internet** (las tipografías van
embebidas). Se abre desde el celular en la misma Wi-Fi.

```powershell
uv run python archivos/dashboard/servidor-dashboard.py
# imprime http://192.168.x.x:8099
```

Diseño basado en la identidad visual de
[Mr.BLACK](https://mrblack-case.dolganev.com/): fondo oscuro, un solo
acento naranja, etiquetas monoespaciadas en mayúsculas y bordes
discontinuos. Detalles en `archivos/dashboard/REDISENO.md`.

---

## Decisiones de diseño

Estas son las que más importan si vas a tocar el sistema:

**Un solo barbero.** No hay tablas ni campos por barbero (`barbers`,
`barber_id`, `commission_pct`). Cualquier "ranking por barbero" sería una
fila repetida.

**Los comandos del dueño no usan la IA.** El router va *antes* del agente,
así que consultar la agenda cuesta 0 tokens.

**La base impide las dobles reservas.** Hay una restricción
`EXCLUDE USING gist` en `barber_citas`: dos citas a la misma hora son
**imposibles** a nivel de base de datos, aunque el código falle.

**La ventana de memoria está acotada.** Sin eso, cada mensaje reenviaba
todo el historial y el coste crecía de forma cuadrática (se detectó una
conversación con 642 mensajes).

**Se ve bien con 0 datos.** El panel no oculta las secciones vacías: las
muestra con ceros y un mensaje claro.

**Nada de audio ni imágenes.** El sistema no procesa notas de voz ni fotos;
responde pidiendo que le escriban. Esto es deliberado.

**Sin pagos con tarjeta.** Está fuera por decisión del negocio.

---

## Verificación

El proyecto usa verificación automatizada, no suposiciones:

| Suite | Comprobaciones |
|---|---|
| `verify.py` | 187 |
| `archivos/test-estados.py` | 52 (máquina de estados) |
| `archivos/test-comandos.py` | 49 (router del dueño) |
| `archivos/dashboard/probar-con-datos.py` | KPIs cuadran con datos reales |
| `archivos/verificar-calendario.py` | El calendario está limpio |

Los fallos que se fueron encontrando están documentados con su causa en
`archivos/` — casi todos se detectaron **probando**, no leyendo código.

---

## Documentación

| Archivo | Contenido |
|---|---|
| `README-AGENTE-BARBERIA.md` | Visión general y arquitectura |
| `COMO-CORRER-N8N.md` | Levantar los servicios |
| `GUIA-CREDENCIALES.md` | Las cuatro credenciales |
| `TUTORIAL-WHATSAPP-Y-GOOGLE.md` | Conectar WhatsApp y Google |
| `archivos/MANUAL-DUENO.md` | **Manual para el barbero** (no técnico) |
| `archivos/dashboard/REDISENO.md` | El rediseño del panel |
| `archivos/AUDITORIA-N8N.md` | Auditoría contra buenas prácticas |
| `archivos/SEGURIDAD-OBSERVABILIDAD.md` | Seguridad y observabilidad |

---

## Estado

| | |
|---|---|
| Workflows activos | 3 (agente, recordatorios, vigilancia) |
| Comprobaciones | 187/187 |
| Coste del prompt | ~10.400 tokens por mensaje |
| Dependencias externas del panel | 0 |
| Secretos en el repo | 0 |

### Pendiente

- Conectar n8n a Supabase para replicar los datos fuera del equipo.
- Confirmar las 13 FAQs de políticas del negocio que están como propuesta.
- Programar la regeneración automática del panel.