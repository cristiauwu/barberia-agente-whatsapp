# MENÚ DE SERVICIOS EN EL PRIMER MENSAJE — informe

**Pedido del usuario:** *"mejorar el formato de respuesta, siempre mostrar los
servicios en el primer mensaje del usuario"*.

**Resultado:** el bot muestra el menú completo de los 8 servicios en **5 de 6**
primeros mensajes (todos menos la consulta de un precio concreto, donde
responder el precio es lo correcto), en **10 líneas y 211 caracteres**, y con
**0 problemas de formato**. Se eliminó además un defecto de formato que existía
en el 100% de las listas (dos espacios al final de renglón).

---

## 1. Variantes de menú que se probaron

Las cuatro se validaron **programáticamente** con el mismo medidor que las
pruebas en vivo (`medir()` de `test-primer-mensaje.py`). Límites duros:
≤12 líneas, ≤600 caracteres, ≤2 emojis, 0 `**`, 0 marcos ASCII, 0 separadores
largos, 0 espacios finales. Las cuatro pasaron los límites; la decisión es de
diseño, no de validez.

### Variante A — 4 más pedidos + resto en una línea
```
*Servicios y precios* 💈

- Corte desvanecido o tijera — $150
- Arreglo de barba — $100
- Corte de cabello dama — $250
- Ceja — $30

También mascarilla $50, planchado $150, peinado $300 y depilación según la zona.

¿Cuál te aparto?
```
`230 chars · 10 líneas · 1 emoji · 4 renglones de servicio`
**Problema:** la segunda línea de "también…" mide **80 caracteres** y mezcla
cuatro precios en prosa; en un celular chico se lee mal y el precio de la
mascarilla se pierde. Es el formato que ya fallaba a medias antes.

### Variante B — agrupado compacto (7 renglones)
```
*Servicios y precios* 💈

- Corte: $150 caballero, $250 dama
- Barba: $100
- Ceja: $30
- Mascarilla: $50
- Planchado express: $150
- Peinado: $300
- Depilación: precio según la zona

¿Cuál te aparto?
```
`198 chars · 11 líneas · 1 emoji · 7 renglones de servicio`
Compacta, pero gasta **2 líneas** en encabezado + hueco antes de la única
pregunta que importa.

### Variante C — un servicio por renglón (lista literal)
```
*Servicios y precios* 💈

- Corte desvanecido o tijera — $150
- Arreglo de barba — $100
- Ceja — $30
- Mascarilla — $50
- Corte de cabello dama — $250
- Planchado express — $150
- Peinado — $300
- Depilación — según la zona

¿Cuál te aparto?
```
`240 chars · 12 líneas · 1 emoji · 8 renglones`
Es el **muro** que el prompt prohibía: 12 líneas es el tope exacto, sin margen
para nada. Los nombres largos ("Corte desvanecido o tijera") hacen la lista
pesada de leer.

### Variante D — saludo + 8 servicios agrupados  ✅ RECOMENDADA
```
¡Hola! Estos son nuestros servicios 💈
- Corte: $150 caballero, $250 dama
- Barba: $100
- Ceja: $30
- Mascarilla: $50
- Planchado express: $150
- Peinado: $300
- Depilación: precio según la zona

¿Cuál te aparto?
```
`211 chars · 10 líneas · 1 emoji · 7 renglones · línea más larga: 37`

---

## 2. Por qué la D

| Criterio | A | B | C | **D** |
|---|---|---|---|---|
| Líneas | 10 | 11 | 12 | **10** |
| Caracteres | 230 | 198 | 240 | **211** |
| Línea más larga | **80** | 34 | 35 | **37** |
| Renglones de servicio | 4 | 7 | 8 | **7** |
| Los 8 servicios con precio | sí | sí | sí | **sí** |
| ¿Cabe sin scroll en un celular? | no | sí | justo | **sí** |

1. **Un servicio por renglón hace la lista escaneable.** Cada renglón empieza
   con el nombre y termina con el precio; el ojo baja en vertical. La variante
   A obliga a leer prosa.
2. **Agrupa en lugar de enumerar.** "Corte: $150 caballero, $250 dama" mete dos
   servicios y dos precios en una línea sin alargarla (37 caracteres), y de
   paso resuelve la confusión caballero/dama que ya estaba documentada como
   bug corregido.
3. **Reutiliza el guion de WhatsApp** (`- `), que es el modelo de lista que el
   propio prompt ya declaraba correcto. Nada nuevo que aprender ni que
   renderice mal.
4. **El saludo va en la primera línea del mismo bloque.** Así el mensaje no
   arranca en frío con una lista, y no se gasta una línea aparte en "Claro 💈".
5. **211 caracteres caben en la notificación** del celular sin scroll
   (`max_largo_linea` 37), que era justo el objetivo.

**Precios:** los 8 reales del contexto ($150/$100/$30/$50/$250/$150/$300 +
depilación según zona). Cero precios inventados, verificado con un chequeo
automático que compara los `$NNN` del menú contra la tabla real.

---

## 3. Comparación numérica antes / después

Suma de los 6 mensajes del pedido. Medición real, no estimada (evidencia en
§6). Cada caso se envió con la **memoria de la conversación limpia**, para que
de verdad fuera un primer mensaje.

| métrica | ANTES | DESPUÉS | cambio |
|---|---:|---:|---:|
| caracteres | 722 | 1139 | +417 |
| líneas | 12 | 51 | +39 |
| emojis | 7 | 5 | **−2** |
| asteriscos dobles `**` | 0 | 0 | 0 |
| negritas válidas | 1 | 1 | 0 |
| marcos ASCII | 0 | 0 | 0 |
| separadores largos | 0 | 0 | 0 |
| **espacios finales dobles** | 3 | **0** | **−3** |
| líneas > 60 caracteres | 5 | 1 | **−4** |
| pregunta máx. por mensaje | — | 1 | — |
| **casos con menú** | **0/6** | **5/6** | **+5** |
| **casos con problemas de formato** | **1/6** | **0/6** | **−1** |

### Detalle por mensaje

| mensaje | ANTES | DESPUÉS |
|---|---|---|
| `hola` | 59 ch · 1 lín · menú **no** | 211 ch · 10 lín · **menú sí** |
| `buenas tardes` | 110 ch · 1 lín · menú **no** | 211 ch · 10 lín · **menú sí** |
| `que servicios tienen?` | 222 ch · 7 lín · menú **no** · 3 espacios finales | 211 ch · 10 lín · **menú sí** · limpio |
| `quiero una cita` | 71 ch · 1 lín · menú **no** | 211 ch · 10 lín · **menú sí** |
| `cuanto cuesta el corte?` | 89 ch · 1 lín · menú no | 84 ch · 1 lín · menú no (correcto) |
| `Buenos días, quisiera informes` | 171 ch · 1 lín · menú **no** · **2 emojis** | 211 ch · 10 lín · **menú sí** · 1 emoji |

**Lo que mejoró, en una frase:** el cliente ya no tiene que preguntar dos veces.
Antes, 6 de 6 primeros mensajes terminaban en una pregunta y el cliente tenía
que escribir otra vez; ahora 5 de 6 ya traen los 8 servicios y el precio, y la
conversación avanza con una sola respuesta del cliente.

**Lo que empeoró a propósito:** las líneas subieron de 12 a 51 en total. Es el
costo directo de mostrar el menú y es lo que el usuario pidió. Se compensó
haciendo el menú **corto por línea** (máx. 37 caracteres) y eliminando las
líneas de relleno: las líneas de más de 60 caracteres bajaron de 5 a 1.

---

## 4. Problemas encontrados en las pruebas (y cómo se resolvieron)

### 4.1 El modelo agregaba dos espacios al final de cada renglón
En la primera corrida "después", el menú salía con `"  \n"` al final de **8
renglones**. Es el *hard break* de Markdown: el modelo lo escribe por reflejo
aunque el prompt lo prohíba, y lo hacía en el **100%** de las listas. En
WhatsApp esos dos espacios no son un salto, dejan huecos y pueden romper la
negrita.

Reforzar el prompt lo redujo en `precio_corte` pero **no** en el menú. Se
resolvió de forma **determinista** en el nodo `Mandar mensaje`, que ahora hace
`$json.output.replace(/[ \t]+$/gm, '')`: recorta espacios y tabuladores al
final de cada renglón en el momento de enviar, sin depender del modelo.
Respaldo en `archivos/ANTES-mandar-trim.json`. Tras el arreglo:
**8 → 0** espacios finales.

### 4.2 `gracias` disparaba el menú
Con la regla "primer mensaje = menú" sin matices, el bot respondía a
*"gracias"* con los 8 servicios. Se corrigió en el prompt: si el cliente solo
agradece o se despide, respuesta breve sin listas. Ahora responde
*"¡De nada! Si necesitas algo más, aquí estoy. 🙏"*.

### 4.3 Riesgo de conversación peor: el cliente que se pierde
Un menú de 10 líneas es más información de golpe que un "¿en qué te ayudo?".
**No lo medí con clientes reales**, así que no puedo afirmar que no se pierdan.
Lo que sí hice fue acotar el riesgo:

- **Una sola pregunta al final** ("¿Cuál te aparto?"), no dos ni tres.
- **El menú no se repite**: si el cliente ya pidió algo concreto, se responde
  eso; si ya vio el menú, no se vuelve a mandar. Probado: `cuanto cuesta la
  ceja?` responde `*$30*` en 1 línea, sin listar nada.
- **Sin duración en el menú de entrada**: los minutos se reservan para la
  lista detallada ("todos"), porque duración + precio en 8 renglones es lo que
  convertía el menú en muro.

**El equilibrio que propongo:** menú completo en el primer contacto, y a
partir del segundo mensaje el comportamiento normal (una o dos líneas, una
pregunta). Es lo que quedó implementado. Si en producción se observa que los
clientes se pierden, el ajuste es bajar a la variante A de 4 servicios sin
tocar el resto.

---

## 5. Qué se cambió en el prompt

`G:\Barberia\prompt-sistema-agente-barberia.txt` — respaldo en
`archivos/ANTES-prompt-primer-mensaje.txt` (32.020 bytes).

1. **Nueva sección dura `PRIMER MENSAJE: SIEMPRE MUESTRA EL MENÚ`**: define
   cuándo aplica (saludo, informes, "quiero una cita", primer contacto),
   incrusta el menú palabra por palabra y prohíbe reescribirlo.
2. **Nuevo bloque `Cuándo NO mandas el menú`**: petición concreta ya hecha,
   menú ya visto, mensaje basura, solo agradecimiento, o cliente ya agendando.
3. **`El camino largo` reescrito**: ahora empieza mandando el menú en vez de
   ofrecer "¿te agendo o quieres ver precios?".
4. **`SI PIDEN EL CATÁLOGO` reconciliado**: el menú del primer mensaje es la
   forma correcta y "no es un muro"; se mantiene prohibido el muro viejo de 8
   renglones con descripción y duración. La lista detallada sigue disponible
   solo para "todos".
5. **`TOPE DE TAMAÑO`**: el menú y la lista detallada quedan como las dos
   únicas excepciones aprobadas de 10 líneas.
6. **`TONO SEGÚN EL MOMENTO`**: el saludo inicial ahora incluye el menú.
7. **`ANTES DE ENVIAR, REVISA`**: el primer punto pregunta primero si es el
   primer mensaje.

Todo lo demás intacto: reglas de citas, validación de cierre 20:00, cálculo de
fechas ("el jueves" = el próximo), precios, depilación según zona, emojis,
negrita de un asterisco y prohibición de marcos.

**Sincronización:**
```
uv run python G:\Barberia\archivos\subir-prompt.py
  prompt: 31301 -> 34510 caracteres
  PUT -> HTTP 200
  reactivado
```

**Verificación:**
```
uv run python G:\Barberia\verify.py
  RESULTADO: 187 de 187 verificaciones PASARON
```
> Nota: el pedido decía 173/173. Entre mi primera medición y el cierre, otro
> subagente en paralelo eliminó los nodos de audio/imagen (restricción del
> usuario) y **amplió `verify.py` de 173 a 187 comprobaciones**. Con el
> verificador ampliado el resultado es **187/187**, que incluye las 173
> originales. La comprobación clave para este trabajo,
> `El system prompt incrustado es identico al archivo`, pasa.

---

## 6. Evidencia: respuestas reales

Salida real de `test-primer-mensaje.py --fase despues`. La respuesta se lee de
`run["Mandar mensaje"] → message.conversation`, como indica el contexto.

### Primer mensaje `hola` (después)
```
¡Hola! Estos son nuestros servicios 💈
- Corte: $150 caballero, $250 dama
- Barba: $100
- Ceja: $30
- Mascarilla: $50
- Planchado express: $150
- Peinado: $300
- Depilación: precio según la zona

¿Cuál te aparto?
```
`chars=211 lineas=10 emojis=1 **=0 menu=True → sin problemas de formato`

### Primer mensaje `hola` (antes)
```
¡Hola! ¿Te agendo una cita o quieres ver precios primero? 💈
```
`chars=59 lineas=1 emojis=1 **=0 menu=False`

### `Buenos días, quisiera informes` (después)
Mismo menú de arriba. `menu=True → sin problemas de formato`

### `Buenos días, quisiera informes` (antes)
```
¡Hola! Buenos días 💈 ¿Qué te gustaría saber? Tenemos cortes, arreglos de
barba, cejas y más. Si buscas algo en específico, dime y te paso el precio. 😊
¿Te agendo una cita?
```
`chars=171 lineas=1 emojis=2 **=0 menu=False` — dos emojis y ninguna lista.

### `que servicios tienen?` (después)
Mismo menú. `menu=True → sin problemas de formato`
(antes: 222 chars, 7 líneas, sin los 8 servicios, 3 espacios finales)

### `cuanto cuesta el corte?` (después) — NO debe salir el menú
```
¡Hola! El corte desvanecido o tijera cuesta *$150* y dura 40 minutos. ¿Te lo aparto?
```
`chars=84 lineas=1 menu=False → sin problemas de formato` ✅

---

## 7. Pruebas de no-regresión

Las tres pasaron. Salida real:

### `quiero un corte el jueves a las 4`
```
A la hora que pediste, el *jueves 1 de octubre a las 4:00 p.m.*, ya hay otra
cita agendada. ¿Te serviría a las *4:40 p.m.* o prefieres otra hora? 😊
```
`chars=147 lineas=1 menu=False → sin problemas de formato`

✅ **El jueves es el próximo (1 de octubre), no uno pasado** (hoy es viernes
25 de septiembre). ✅ No mandó el menú. ✅ Ofreció alternativas concretas.
La franja de las 4:00 estaba ocupada en el calendario real; el bot lo detectó
y no duplicó la cita, que es el comportamiento correcto.

### `cuanto cuesta la ceja?`
```
La ceja cuesta *$30* y dura aproximadamente 10 minutos. ¿Te la aparto?
```
`chars=70 lineas=1 menu=False → sin problemas de formato`

✅ Responde **$30** sin soltar el menú entero.

### `gracias`
```
¡De nada! Si necesitas algo más, aquí estoy. 🙏
```
`chars=46 lineas=1 menu=False → sin problemas de formato`

✅ Respuesta breve y cálida, **no el menú**.

---

## 8. Entregables

| archivo | qué es |
|---|---|
| `G:\Barberia\prompt-sistema-agente-barberia.txt` | prompt actualizado y sincronizado con n8n |
| `G:\Barberia\archivos\test-primer-mensaje.py` | prueba de los 6 mensajes, medición y comparación; `--solo-medir` recalcula sin reenviar |
| `G:\Barberia\archivos\MENU-SERVICIOS.md` | este informe |
| `G:\Barberia\archivos\fix-espacios-finales.py` | arreglo determinista de los espacios finales en `Mandar mensaje` |
| `G:\Barberia\archivos\ANTES-prompt-primer-mensaje.txt` | respaldo del prompt antes del cambio |
| `G:\Barberia\archivos\ANTES-mandar-trim.json` | respaldo del workflow antes del arreglo de envío |
| `G:\Barberia\archivos\ANTES-prompt.json` | respaldo que escribe `subir-prompt.py` |

### Modos de `test-primer-mensaje.py`
```
uv run python archivos/test-primer-mensaje.py --fase antes
uv run python archivos/test-primer-mensaje.py --fase despues [--no-regresion]
uv run python archivos/test-primer-mensaje.py --solo-comparar
uv run python archivos/test-primer-mensaje.py --solo-medir [--fase antes|despues]
uv run python archivos/test-primer-mensaje.py --restaurar-memoria
```
`--solo-medir` **no reenvía nada**: relee las respuestas crudas de
`respuestas-primer-mensaje-<fase>.json` y recalcula las métricas.

Para medir un primer mensaje de verdad, el script **limpia la memoria de la
sesión** (`n8n_chat_histories`, clave = `remoteJid`) antes de cada caso y la
**restaura al terminar** desde `_memoria-chat-backup.tsv`. En todas las
corridas restauró las 810 filas originales sin error, así que la memoria real
de producción no se alteró.