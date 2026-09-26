# Rediseño del panel — de tablero genérico a Mr.BLACK

## Qué se hizo

Se reemplazó **todo el CSS** del panel del barbero por el lenguaje visual de
`https://mrblack-case.dolganev.com/`, copiado **token por token** desde su
CSS real (no de memoria, no "parecido a").

El rediseño lo empecé yo después de que el subagente que lo tenía asignado
se quedara sin contexto: solo alcanzó a capturar el "antes" (sus dos
capturas siguen en `capturas/antes-*.png`).

---

## Tokens adoptados (extraídos de su CSS)

### Colores — su paleta completa, sin inventar ninguno

| Token | Valor | Uso en el panel |
|---|---|---|
| `--black` | `#262626` | base del mundo oscuro |
| `--orange` | `#df6341` | **el acento único**: cifras clave, barras, foco |
| `--ivory` | `#f3f1e9` | texto principal |
| `--green` | `#afab8e` | barras neutras, estados "todavía no pasó" |
| `--salmon` | `#de7e64` | no-shows |
| `--brown` | `#a59171` | cancelaciones |

Antes el panel usaba colores **heredados de GitHub** (`#58a6ff` azul,
`#3fb950` verde fosforito, `#f4614f` rojo, `#e5b34a` ámbar). Chocaban con
el naranja. **Los eliminé todos**; ahora hay cero colores fuera de paleta
(verificado por script).

### Tipografías — las 3 suyas, **embebidas en base64**

| Familia | Rol | Peso |
|---|---|---|
| **Inter Tight** | cuerpo | 400 |
| **Courier Prime** | **etiquetas** (la firma del sitio) | 400 |
| **Unbounded** | títulos y cifras | 800 |

Se descargaron sus `.woff2` reales y se embebieron dentro del `<style>`
como `data:font/woff2;base64`. **126 KB de fuentes dentro del HTML.**

Por qué embebidas: el panel funciona **sin internet**. Si el dueño abre el
archivo sin conexión, o el Wi-Fi del local falla, las fuentes siguen ahí.
Si algún archivo faltara, el CSS tiene pilas de respaldo y degrada sin
romperse.

### Detalles de firma que hacen que se reconozca

1. **TODO en mayúsculas con `letter-spacing: -.03em`.** Es la seña del sitio.
2. **Bordes discontinuos** (`1px dashed`) en vez de sólidos: secciones,
   tarjetas, campos, barras, píldoras. **16 usos.**
3. **Etiqueta diminuta + cifra enorme.** El patrón clave de los dashboards
   minimalistas: `INGRESOS HOY` en mono de 15 px arriba, `$100` en Unbounded
   de hasta 2,5 rem debajo.
4. **El icono de 6 puntos** de su marca, en la cabecera y en los chips.
5. **Foco visible** `2px dashed` (accesible, como el sitio).
6. **`font-variant-numeric: tabular-nums`** en todas las cifras, para que no
   bailen al cambiar de valor.
7. Prefijo `///` naranja en los títulos de sección, guiño a su lenguaje.
8. `prefers-reduced-motion` respetado.

### Patrones de `Minimalist-Dashboards` que se aplicaron

El repo que pasaste es **YAML de Home Assistant**, no CSS (ver
`REFERENCIA-MINIMALIST-DASHBOARDS.md`). Pero cinco ideas suyas sí eran
portables y están dentro:

- **Rejilla 4 → 2 → 1** columnas con transición limpia.
- **Radios decrecientes** (2 px exterior, 1 px interior) en vez de uno solo.
- **Acento en varias opacidades**: el naranja aparece al 10 %, 20 %, 45 %
  y 100 % según el peso de cada elemento.
- **Breakpoint con `orientation`**: `@media (max-width:1100px),
  (orientation:portrait)` — importante porque el barbero **gira el
  teléfono**.
- **Estado vacío con ceros visibles**, nunca oculto.

---

## Los 2 defectos que encontré mirando las capturas

Rediseñé, capturé, y **miré el resultado**. Salieron dos cosas:

### 1. La leyenda se troceaba en el móvil

`bloque_salud` genera `<span>Base del mes: <b>0</b> cita(s) programadas…</span>`
y el CSS lo ponía en `display:flex`. En flex, **el `<b>` del medio se
convierte en un ítem aparte**, así que la frase se partía en tres columnas
estrechas y apretadas. Se veía claramente en la captura móvil.

**Arreglo:** la leyenda deja de ser flex (`display:block`) y el punto de
color se pone `inline-block`. Ahora el texto fluye normal.

### 2. El gráfico vacío parecía un hueco roto

Con 0 datos las 30 barras se dibujan a ~3 px, pegadas al borde inferior:
quedaba **un rectángulo grande y vacío** que se lee como error, no como
gráfico sin datos.

**Arreglo:** líneas guía horizontales sutiles dentro del área (cada 38 px) y
barras vacías con un mínimo visible. Ahora se lee como "gráfico en cero".

**No seguí puliendo**: construí, miré una vez (escritorio y móvil juntos),
arreglé los dos defectos en un lote, confirmé con una ronda más y paré.

---

## Verificación con evidencia

### Los números cuadran (probado con datos reales)

Inserté 4 citas con valores conocidos, regeneré, y comprobé el HTML:

| KPI | Esperado | En el HTML |
|---|---|---|
| Ingresos del mes | `$280` (150+100+30) | ✅ |
| Ingresos de hoy | `$100` | ✅ |
| Ingresos de la semana | `$130` (el de hace 8 días queda fuera) | ✅ |
| Ticket promedio de hoy | `$100` | ✅ |
| No-shows | `1` | ✅ |

**0 fallos.** Después borré los datos de prueba: `barber_citas` volvió a 0.

### Sin dependencias externas

```
refs externas http:// o https://    → 0
<script src> o <link>                → 0
@font-face embebidas                 → 3
colores fuera de la paleta           → 0
```

### El panel

| | |
|---|---|
| Tamaño | **140 KB** (126 KB son las fuentes embebidas) |
| Fuentes sin conexión | ✅ |
| Se ve con **0 datos** | ✅ |
| Se ve en **390 px reales** | ✅ |
| Se ve **con datos** | ✅ |
| Servidor `--una-vez` | ✅ exit 0 |

---

## Capturas

En `G:\Barberia\archivos\dashboard\capturas\`:

| Archivo | Qué muestra |
|---|---|
| `antes-escritorio.png` | cómo se veía antes (lo capturó el subagente) |
| `antes-movil.png` | antes, en móvil |
| `con-datos-escritorio.png` | **después**, con citas ($280, gráfico lleno) |
| `con-datos-movil.png` | **después**, en móvil de 390 px |
| `despues-escritorio.png` | después, con 0 datos |
| `despues-movil.png` | después, en móvil con 0 datos |

---

## Archivos

| Archivo | Qué es |
|---|---|
| `generar-dashboard.py` | el generador, con el CSS nuevo |
| `rediseno-css.py` | el script que aplicó el rediseño (idempotente) |
| `fix-defectos-visuales.py` | arregla los 2 defectos de las capturas |
| `fix-paleta-estados.py` | alinea los colores de estado a la paleta |
| `capturar-rediseno.py` | captura escritorio y móvil con Chrome headless |
| `probar-con-datos.py` | prueba que los KPIs cuadran |
| `ANTES-generar-dashboard.py` | respaldo del original |
| `tipografias/` | los 3 `.woff2` descargados |

---

## Cómo abrirlo

```powershell
# Ver desde el celular (recomendado)
uv run python G:\Barberia\archivos\dashboard\servidor-dashboard.py
# → imprime http://192.168.x.x:8099

# O el archivo directo, sin servidor y sin internet
start G:\Barberia\archivos\dashboard\dashboard.html
```

---

## Pendiente (no lo hice a propósito)

1. **Permitir el puerto 8099 en el Firewall** para verlo desde el celular.
   Requiere Administrador:
   ```powershell
   New-NetFirewallRule -DisplayName "Dashboard Barberia" -Direction Inbound -LocalPort 8099 -Protocol TCP -Action Allow
   ```
2. **Regeneración automática**: el panel es una foto. El servidor ya lo
   refresca cada 2 minutos mientras corre, pero si lo cierras no se
   actualiza. Una tarea programada de Windows cada 30 min lo resolvería.
3. **Comparativa contra el periodo anterior**: no está porque al no haber
   histórico todavía daría siempre cero.