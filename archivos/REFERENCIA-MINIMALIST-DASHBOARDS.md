# Referencia: `basbruss/Minimalist-Dashboards` — qué adoptar para el dashboard de la barbería

> Estudio hecho leyendo los archivos reales del repo (árbol completo vía GitHub API + cada `.yaml` bajado desde `raw.githubusercontent.com`).
> Fecha del commit estudiado: `f6be0ca851d3bed0b8f361c7ed9702edcb909996` (rama `main`).

---

## 1. Resumen

**Qué es:** un repositorio de *showcase* con los dashboards que el autor usa en **Home Assistant**, construidos sobre el tema [UI-Lovelace-Minimalist](https://github.com/UI-Lovelace-Minimalist/UI). El propio README lo dice: *"It's not advised to directly copy this repo for your own use"*.

**Stack real (verificado):**

| Capa | Qué usa |
|---|---|
| Lenguaje de los dashboards | **YAML**, no HTML/CSS/JS |
| Motor | Home Assistant + integración HACS `ui_lovelace_minimalist` |
| Layout | `custom:layout-card` con `layout_type: custom:grid-layout` |
| Tarjetas | `custom:button-card` (todo el diseño vive en `styles:` de esa tarjeta) |
| Gráficas | `custom:mini-graph-card` y `custom:apexcharts-card` (librerías externas) |
| Modificadores de estilo | `lovelace-card-mod` (bloques `style: \|` con CSS) |
| Carruseles | `custom:swipe-card` (Swiper.js), `horizontal-stack` |
| Popups | `custom:state-switch` |
| Tema | `theme: "minimalist-desktop"` |

**Cuántos dashboards:** 4 vistas en total.
- `dashboard/ui-lovelace.yaml` → vista `prijzen` (precios de luz, con ApexCharts).
- `dashboard/adaptive-dash/views/main.yaml` → vista `home`.
- `dashboard/adaptive-dash/views/livingroom.yaml` → vista `Livingroom` (marcada `# IN PROGRESS`).
- `dashboard/adaptive-dash/views/lights.yaml` → vista `Lights`.

**Estilo:** minimalista de tarjetas sueltas sobre fondo, sin bordes marcados, radios muy grandes, sombras suaves, tipografía de dos niveles (etiqueta diminuta + cifra grande), acento cromático por entidad en lugar de por marca.

### ⚠️ Hallazgo crítico y honesto

**Este repo NO contiene ni un solo archivo `.html`, `.css` o `.js`.** Verificado sobre el árbol recursivo completo: 26 blobs, todos `.yaml` más dos `.png` de mockup y `.gitattributes`/`.gitignore`.

Consecuencias directas para tu proyecto:

1. **No hay CSS puro que copiar.** Todo el estilo se expresa como *valores* dentro de YAML (`styles: card: - border-radius: "12px"`) que luego inyecta `button-card`. Lo que sí es portable son **los números y las decisiones de diseño**, no el archivo.
2. **La sección 4 (kit CSS) es una traducción mía**, construida a partir de los valores reales extraídos del repo, no un copia-pega literal. Lo marco explícitamente para que no te lleves una falsa impresión. Todo valor que cito como "del repo" está respaldado por el fragmento que lo acompaña.
3. **Las gráficas del repo son inservibles aquí**: `mini-graph-card` y `apexcharts-card` son CDNs/librerías. La sección 5 es por tanto **propuesta propia**, no del repo, aunque inspirada en la configuración de las series (barras por hora, agrupación por día).
4. **Soporte claro/oscuro:** no usa `@media (prefers-color-scheme)`. Usa el flag JS `hass.themes.darkMode` y las variables CSS `--color-yellow`, `--color-background-yellow`, `--opacity-bg`, `--border-radius`, `--box-shadow` que aporta el tema de Home Assistant. Es decir: **depende de un design system externo del que aquí no hay ni un hex**.

Lo que sí vale la pena: **los valores numéricos son excelentes y muy coherentes** (radios 30/20/0, padding 12, gaps 6/12, escalas tipográficas 20/14/12). Eso es lo que se rescata.

---

## 2. Patrones a adoptar

### 2.1 Layout: grid declarativo con `grid-template-areas`

**Patrón:** nada de flexbox improvisado. Cada vista declara una rejilla nombrada y cada tarjeta se autoubica con `grid-area`. El número de columnas es literal y explícito.

**Por qué sirve:** tu dashboard tiene 13 bloques heterogéneos (KPI, serie de 30 días, top servicios, agenda…). Con `grid-template-areas` nombras las zonas una vez y reordenas la página **solo reescribiendo las áreas en la media query**, sin tocar el HTML de cada bloque. Es el mecanismo exacto que necesitas para pasar de escritorio a móvil.

**Fragmento real** — `dashboard/adaptive-dash/views/livingroom.yaml`:

```yaml
layout:
  grid-template-rows: "min-content"
  grid-template-columns: "1fr 1fr 1fr"
  grid-template-areas: >
    "title1 title1 title1"
    "card1  card1  card1"
    "card2  card3  card4"
    "card5  card6  ."
    "card7  card8  card9"
mediaquery:
  # Mobile
  "(max-width: 800px)":
    grid-template-columns: "1fr 1fr"
    grid-template-areas: |
      "title1 title1"
      "card1  card1"
      "card2  card3"
      "card4  card5"
```

Traducción directa a CSS puro (lo que adoptarías):

```css
.grid {
  display: grid;
  grid-template-rows: min-content;
  grid-template-columns: repeat(3, 1fr);
  grid-template-areas:
    "title1 title1 title1"
    "hero   hero   hero"
    "k1     k2     k3"
    "chart  chart  top";
  gap: 12px;
}
@media (max-width: 800px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
    grid-template-areas:
      "title1 title1"
      "hero   hero"
      "k1     k2"
      "k3     k4"
      "chart  chart"
      "top    top";
  }
}
.card-hero { grid-area: hero; }
```

**El truco del punto (`.`)**: en `"card5 card6 ."` la celda queda vacía a propósito. Es la forma barata de dejar un hueco de composición sin meter un div fantasma. Útil en tu fila de 5 KPIs cuando la rejilla sea de 3 columnas.

### 2.2 Tres breakpoints concretos, no uno

El repo usa **tres cortes distintos según la vista**, y esa asimetría es intencional:

| Breakpoint | Dónde | Qué hace |
|---|---|---|
| `(max-width: 1100px), (orientation: portrait)` | `dashboard/ui-lovelace.yaml` | Colapsa la columna de popups: `grid-template-columns: "100%"` |
| `(max-width: 800px)` | `views/main.yaml`, `livingroom.yaml`, `lights.yaml` | De 6 ó 3 columnas a **2 columnas** |
| `(min-width: 800px)` / `(min-width: 1100px)` | `views/main.yaml`, `popup.yaml`, `slider.yaml` | *Oculta* bloques con `show: mediaquery:` |

**Fragmento real** — `dashboard/ui-lovelace.yaml` (fíjate en la coma: es un OR de dos condiciones):

```yaml
layout:
  grid-template-columns: "1fr 1fr"
  grid-template-rows: "min-content"
  grid-template-areas: |
    "main popup"
mediaquery: "(max-width: 1100px), (orientation: portrait)":
  grid-template-columns: "100%"
  grid-template-areas: "main"
```

**Por qué sirve:** tu dueño abre el dashboard desde el teléfono **en vertical pero a veces en horizontal**. La condición `(orientation: portrait)` es exactamente el mecanismo para no darle la versión de escritorio cuando gira el móvil. Y el corte en `1100px` (no `768px`) es lo correcto para un dashboard denso: a 900px de ancho la versión de 2 columnas sigue siendo legible, la de 6 no.

**Ocultar en vez de reflowear** — `views/main.yaml`:

```yaml
- view_layout:
    grid-area: "text"
  show:
    mediaquery: "(min-width: 800px)"   # la tarjeta de clima desaparece en móvil
```

Adopción: en tu caso, **Horas pico** y **Top servicios** son buenos candidatos a ocultarse en móvil (o degradarse a top-3), en lugar de apretujarse.

### 2.3 Jerarquía tipográfica: el patrón "caption diminuto + cifra enorme"

Este es el patrón clave que pediste, y el repo lo implementa de forma explícita y repetida. La receta literal es:

> **etiqueta 12px + cifra 20px**, donde la etiqueta va en mayúsculas visuales (peso alto, opacidad reducida) y la cifra en peso `bold`.

**Fragmento real 1** — `custom_cards/weather.yaml`. Observa que la etiqueta pequeña NO baja el peso, sube: `font-weight: "bolder"` con `filter: "opacity(40%)"`.

```yaml
styles:
  name:                 # ← el caption
    - justify-self: "center"
    - align-self: "start"
    - font-weight: "bolder"
    - font-size: "12px"
    - filter: "opacity(40%)"
  label:                # ← la cifra grande
    - margin-top: "10px"
    - justify-self: "center"
    - font-weight: "bold"
    - font-size: "14px"
  grid:
    - grid-template-areas: "'l' 'n'"      # etiqueta arriba, cifra abajo
    - grid-template-columns: "1fr"
    - grid-template-rows: "min-content min-content"
```

**Fragmento real 2** — la variante "cifra dominante" del mismo archivo (`custom_cards/weather.yaml`, tarjeta de temperatura actual), con el salto a **20px bold**:

```yaml
styles:
  name:
    - justify-self: "end"
    - align-self: "end"
    - font-weight: "bold"
    - font-size: "20px"
    - margin-right: "12px"
  label:
    - align-self: "start"
    - justify-self: "center"
    - font-weight: "bold"
    - font-size: "14px"
    - margin-left: "12px"
```

**Fragmento real 3** — el micro-caption dentro de las tarjetas de habitación, a **12px `bolder`** con icono de **20×20** (`custom_cards/room_card/room_card.yaml`):

```yaml
label:
  - justify-self: start
  - align-self: center
  - font-weight: bolder
  - font-size: 12px
  - margin-left: 0px
img_cell:
  - place-self: center
  - width: 20px
  - height: 20px
```

**Escala completa extraída del repo (todos los `font-size` encontrados):**

| Valor | Peso | Rol | Fuente |
|---|---|---|---|
| `20px` | `bold` | Cifra protagonista (temperatura) | `weather.yaml` |
| `14px` | `bold` | Cifra secundaria / valor de lista | `weather.yaml` (×2) |
| `12px` | `bolder` + `opacity(40%)` | Caption/etiqueta de campo | `weather.yaml`, `room_card.yaml` |

**Traducción a CSS puro:**

```css
.kpi-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  opacity: .40;              /* el 40% literal del repo */
  margin-bottom: 10px;       /* el margin-top: 10px del repo */
}
.kpi-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;  /* ver 2.7 */
}
```

**Nota:** el repo no define una escala más allá de 12/14/20 porque cada tarjeta es una isla. Para tu dashboard, donde la cifra de **Ingresos hoy** es el rey, extendé la escala manteniendo la proporción ~1.6× por salto: **12 → 20 → 32 → 52px**. El repo te da 12/20 como base; el resto es extrapolación.

### 2.4 Color: sin paleta propia, todo delega en variables del tema

Este es el punto donde el repo se queda corto para ti y conviene saberlo.

**Lo verificado:** **no hay ni un solo color de marca hardcodeado.** Solo aparecen dos categorías.

**(a) Tokens del tema (sin hex — los resuelve Home Assistant):**

```yaml
# custom_cards/room_card/room_card.yaml
- border-radius: "var(--border-radius)"
- box-shadow:    "var(--box-shadow)"

# custom_cards/energie_graph.yaml
ha-card {
  box-shadow: none;
  border-radius: var(--border-radius);
  padding-bottom: 0 !important
}
```

Tokens usados: `--border-radius`, `--box-shadow`, `--card-background-color`, `--color-theme`, `--color-yellow`, `--color-background-yellow`, `--opacity-bg`, `--google-grey`, `--background-image`.
**Ninguno viene definido en el repo** — todos los aporta el tema `minimalist-desktop`. Si copias esto literal, tu HTML no renderiza nada.

**(b) Colores nombrados en JS de plantilla (únicos literales):**

```yaml
# dashboard/adaptive-dash/assets/domains/rooms.yaml
color: >                       # temperatura
  [[[ if (states['climate.woonkamer'].attributes.hvac_action == 'idle'){ return 'green';}
      if (states['climate.woonkamer'].attributes.hvac_action == 'heating') {return 'rgb(var(--color-yellow))';}
      else return 'grey'; ]]]
color: >                       # humedad
  [[[ return entity.state > 69 ? 'red' : '#3393FF' ]]]
```

Y en `views/main.yaml`, el color de los chips sale del **estado del selector**, no del branding:

```yaml
- background-color: >-
    [[[ return states['input_select.adaptive_slider'].state == variables.option
        ? 'rgba(var(--color-theme),0.2)'
        : 'var(--card-background-color)'; ]]]
```

Y la energía usa nombres de color pelados (`dashboard/adaptive-dash/assets/domains/energy.yaml`):

```yaml
ulm_card_graph_color: orange
ulm_card_graph_color: blue
```

**Hex/valores cromáticos que SÍ aparecen en el repo (lista completa):**

| Valor | Uso | Archivo |
|---|---|---|
| `#3393FF` | Azul de humedad normal | `domains/rooms.yaml` |
| `#1E90FF` | DodgerBlue, umbral de precio barato | `dashboard/ui-lovelace.yaml` |
| `green` | Estado OK / CPU-idle / umbral precio | `rooms.yaml`, `ui-lovelace.yaml` |
| `red` | Alerta (>69% humedad) / precio caro | `rooms.yaml`, `ui-lovelace.yaml` |
| `orange` | Precio medio / serie de consumo | `ui-lovelace.yaml`, `energy.yaml` |
| `blue` | Serie de precio | `energy.yaml` |
| `grey` | Estado inactivo/neutro | `rooms.yaml` |
| `#B3F7CA` | `fillColor` de una anotación de eje | `ui-lovelace.yaml` |
| `dodgerblue` | Serie "Gemiddelde" (comentada) | `dashboard/ui-lovelace.yaml` |
| `purple`, `yellow`, `pink` | Nombres de acento de los chips | `views/main.yaml` |

**El patrón real de "positivo/negativo" es por umbral y por color nombrado, no por una pareja semántica.** En `ui-lovelace.yaml` está lo más cercano a lo que buscas, un `color_threshold`:

```yaml
color_threshold: &color
  - value: -1    color: 1E90FF
  - value: 0.25  color: green
  - value: 0.35  color: orange
  - value: 0.50  color: red
```

**Y el patrón monocromo-con-acento sí existe, en la variante** "tinte translúcido del propio color del dispositivo", que es muy elegante y sí es portable:

```yaml
# custom_cards/room_card/room_card.yaml — fondo de tarjeta
- background-color: >-
    [[[ var color = entity.attributes.rgb_color;
        if(hass.themes.darkMode){
          if (color){ return 'rgba(' + color + ',0.1)' }
          else { return 'rgba(var(--color-yellow),0.1)' }
        }
        return 'rgba(var(--color-background-yellow),var(--opacity-bg)'; ]]]

# custom_cards/room_card/room_card.yaml — icono y su "pastilla"
img_cell:
  - background-color: >    # el mismo color, al 20%
      [[[ ... 'rgba(' + color + ',0.2)' ... ]]]
icon:
  - color: >               # el mismo color, al 100%
      [[[ ... 'rgba(' + color + ',1)' ... ]]]
```

**La regla concreta a adoptar:** *un solo acento, aplicado en tres opacidades.* `0.10` para el fondo de tarjeta, `0.20` para la pastilla del icono, `1.0` para el trazo/icono. Y en modo oscuro los tintes bajan su fuerza (`0.1` sobre negro) mientras en claro se usa el color de fondo del tema con `--opacity-bg`. Esto es directamente aplicable a tu dashboard: **un acento bronce/ámbar para la barbería, en `.10` / `.20` / `1`, y gris neutro para todo lo demás.**

### 2.5 Espaciado y radios: la escala completa y verificada

**Escala de espaciado** (todos los valores que aparecen, ordenados):

| Valor | Dónde se usa |
|---|---|
| `2px` | `padding: "2px"` en `sensor_generic` (`room_card.yaml`) |
| `0px` | `margin-left: 0px`, `padding: 0px`, `border-radius: 0px` |
| `4px` | `margin-bottom: "4px"` — `custom_cards/swiper-margin.yaml` (archivo de 2 líneas, solo para esto) |
| `6px` | `row-gap: "6px"` entre filas de la rejilla interna (`room_card.yaml`); `spaceBetween: 6` en los carruseles |
| `10px` | `margin-top: "10px"` entre caption y cifra (`weather.yaml`) |
| `12px` | **el valor dominante**: `padding: "12px"` en toda tarjeta + `row-gap: "12px"` + `margin-left/right: "12px"` |

**Regla derivada: base 6, y todo múltiplo de 6.** `6 / 12 / 24 = 2× / 4× / 8×`. El `10px` y el `2px` son los dos únicos fuera de escala y ambos son ajustes ópticos finos (separación caption↔cifra, y padding de un micro-widget).

**Fragmento real** — `custom_cards/swiper-margin.yaml`, **el archivo completo**, que es puro espaciado:

```yaml
swiper-margin:
  styles:
    card:
      - margin-bottom: "4px"
```

**Escala de radios** (completa):

| Radio | Uso | Archivo |
|---|---|---|
| `30px` | Tarjeta exterior grande (clima) | `weather.yaml` |
| `20px` | Tarjeta secundaria dentro de la anterior | `weather.yaml` |
| `var(--border-radius)` | Tarjeta estándar (delega al tema) | `room_card.yaml`, `energie_graph.yaml` |
| `0px` | Anulación para tarjetas anidadas | `room_card.yaml` |

**El patrón a copiar es el *anidamiento decreciente*:** la tarjeta contenedor a 30px, la tarjeta hija a 20px, la nieta a 0. Es lo que evita el efecto "cajas dentro de cajas" mal resuelto.

```yaml
# custom_cards/weather.yaml — contenedor
card:
  - border-radius: "30px"
  - box-shadow: "var(--box-shadow)"
  - padding: "12px"
  - height: "160px"
# ...y su hija
card:
  - box-shadow: "none"
  - border-radius: "20px"
  - border: "2px solid var(--google-grey)"
  - height: "70px"
```

**Bordes:** casi nunca. Hay **exactamente un** `border` en todo el repo, y es un truco de espaciado óptico, no un separador:

```yaml
# custom_cards/weather.yaml
- border: "2px solid var(--google-grey)"
```

El resto usa `box-shadow: none` + `background: none` para "disolver" contenedores anidados:

```yaml
# custom_cards/room_card/room_card.yaml
card:
  - box-shadow: none
  - margin-left: 12px
  - border-radius: 0px
  - padding: 0px
  - background-color: "rgba(0,0,0,0)"
  - height: "48px"
  - overflow: "visible"
```

**Adopción recomendada:** alturas fijas para filas de datos (`48px` el micro-item, `70px` la tarjeta media, `160px` la tarjeta grande). Fijar la altura es lo que hace que la rejilla no "baile" cuando cambian los datos — y en tu caso, cuando están todos a cero.

### 2.6 Estados vacíos: `display: none` calculado, no placeholder de texto

**El repo NO tiene estados vacíos con diseño.** No hay "sin datos", ni icono gris, ni mensaje de bienvenida. Lo que hace es **ocultar el hueco**, que es una estrategia distinta y vale la pena evaluar.

**Fragmento real** — `custom_cards/room_card/room_card.yaml`. Un motor JS cuenta cuántas de las 4 entidades están definidas y apaga las celdas sobrantes:

```yaml
variables:
  item_count_engine: >-
    [[[ var pills = []
        const entities = [variables.entity_1.entity_id, variables.entity_2.entity_id,
                          variables.entity_3.entity_id, variables.entity_4.entity_id]
        function entity_check(item) { if (item != "") { pills.push("item" + (pills.length+1)) } }
        entities.forEach(entity_check)
        return pills.length ]]]

styles:
  item1:
    - display: "[[[ return (variables.item_count_engine >= 1) ? 'block' : 'none' ]]]"
  item2:
    - display: "[[[ return (variables.item_count_engine >= 2) ? 'block' : 'none' ]]]"
  item3:
    - display: "[[[ return (variables.item_count_engine >= 3) ? 'block' : 'none' ]]]"
  item4:
    - display: "[[[ return (variables.item_count_engine >= 4) ? 'block' : 'none' ]]]"
```

Y el grid se declara con `grid-template-columns: "1fr 1fr"` fijo, así que al apagar celdas quedan huecos fantasma — imperfecto.

**Veredicto honesto:** aquí **el repo no te sirve**. Para un negocio que arranca de cero necesitas lo contrario: celdas que persistan y muestren `0`, `$0` o `—`. Mi recomendación, **no extraída del repo**:

- **Nunca ocultes un KPI por falta de datos.** Un `$0` es información: dice "hoy no hubo ventas", que es justo lo que el dueño necesita saber.
- Ocultá **solo** los bloques que no tienen representación posible: `Top servicios por ingresos` con 0 filas, o la `Serie de 30 días` con 30 ceros (dibujá la línea base plana, con los ejes, para que se vea *vacía pero no rota*).
- Para esos usá un estado explícito de una línea, no un `display:none`.

```css
.empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
  opacity: .40;
}
```

Lo único rescatable del repo en este punto es el **valor `opacity(40%)`** para todo lo que es "ausencia": es el mismo tratamiento que le da a los captions, así que el vacío se lee como jerarquía y no como error. Esa coherencia sí es un patrón.

### 2.7 Detalles que hacen que se vea bien

**Transiciones de entrada — concretas y con milisegundos.** El repo usa `state-switch` con transición direccional. Fragmento real de `dashboard/adaptive-dash/popup/popup.yaml`:

```yaml
type: "custom:state-switch"
transition: "slide-down"
transition_time: 500
```

Y en los carruseles (`dashboard/adaptive-dash/assets/slider.yaml`):

```yaml
transition: "slide-right"
transition_time: 500
```

**500ms para lo grande, y `spaceBetween: 6` entre tarjetas.** Nótese que **no hay transiciones de `hover`** en todo el repo — coherente con que el target son pantallas táctiles. Para tu dashboard eso es una decisión de diseño heredable: **no gastes en hover, gastá en transición de carga**.

**Alineación de números: el repo NO usa `tabular-nums`.** Verificado, no aparece ninguna ocurrencia de `font-variant-numeric` ni `tabular-nums` en los 26 archivos. Lo que sí hace es **alineación por `justify-self`**, que es más débil pero es lo que hay:

```yaml
# custom_cards/weather.yaml
name:
  - justify-self: "end"      # cifra al borde derecho, en columna
  - align-self: "end"
label:
  - justify-self: "center"   # caption centrado arriba
```

```yaml
# custom_cards/weather.yaml (generic_text)
name:
  - justify-self: "center"
  - align-self: "start"
label:
  - justify-self: "center"
```

```yaml
# custom_cards/room_card/room_card.yaml
label:
  - justify-self: start
  - align-self: center
```

**Regla:** usar `justify-self` explícito en *cada* hijo de la rejilla. Es lo que evita que una tarjeta quede centrada y la vecina alineada a la izquierda.

**Alineación del grid interno:** `align-items: "start"` en la rejilla anidada — evita que las celdas se estiren verticalmente cuando una crece.

```yaml
# custom_cards/room_card/room_card.yaml
grid:
  - grid-template-areas: "'item1 item2' 'item3 item4'"
  - grid-template-rows: min-content
  - grid-template-columns: "1fr 1fr"
  - align-items: "start"
```

**`overflow: visible` explícito** en tarjetas que llevan pastillas/insignias que se salen del borde — dos veces en el repo:

```yaml
# custom_cards/room_card/room_card.yaml  y  custom_cards/weather.yaml
- overflow: "visible"
```

**Esto sí conviene adoptarlo y el repo lo omite:** para un dashboard con ingresos y tickets, **`font-variant-numeric: tabular-nums` es obligatorio**. Sin él, cuando las cifras cambian (`1.240` → `980`), el ancho del texto salta y todo el layout vibra. El repo no lo tiene porque en Home Assistant los valores se actualizan in-place sin reflow visible. Tu Python regenera el HTML entero, pero el dueño compara lecturas y la alineación decimal importa. Añadilo:

```css
.kpi-value, td, .num { font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }
```

### 2.8 Modo claro / oscuro

**Sí lo soporta, pero NO con CSS.** Es lo más flojo del repo para tus fines. El mecanismo real está en el JS de plantilla de `custom_cards/room_card/room_card.yaml`:

```yaml
- background-color: >-
    [[[ var color = entity.attributes.rgb_color;
        if(hass.themes.darkMode){          # ← flag JS, no media query
            if (color){ return 'rgba(' + color + ',0.1)' }
            else { return 'rgba(var(--color-yellow),0.1)' }
        }
        return 'rgba(var(--color-background-yellow),var(--opacity-bg)'; ]]]
```

Es decir: **el tema (`minimalist-desktop`) define dos juegos de variables y Home Assistant le dice al JS cuál está activo.** No hay `@media (prefers-color-scheme: dark)` en ninguna parte, no hay `light-dark()`, no hay un solo valor de color de fondo definido en el repo, y no hay un `<style>` que declare `:root` — todo eso vive en el componente `ui_lovelace_minimalist` que el repo **incluye pero no contiene**:

```yaml
# dashboard/ui-lovelace.yaml
button_card_templates: !include_dir_merge_named
  "../../../custom_components/ui_lovelace_minimalist/__ui_minimalist__/ulm_templates/"
theme: "minimalist-desktop"
background: "var(--background-image)"
```

**Cómo lo adaptas a tu HTML sin dependencias** (propuesta, ya que el repo no lo trae resuelto): dos bloques `:root` con los mismos nombres de token, y el oscuro detrás de la media query. Así conservás la *estructura* que el repo asume (tokens semánticos) sin depender de su design system.

```css
:root {
  --bg: #F7F7F5;      --card: #FFFFFF;
  --fg: #141414;      --fg-muted: #141414;
  --opacity-caption: .40;
  --accent: #B0813F;              /* ámbar/bronce barbería */
  --accent-bg: rgba(176,129,63,.10);
  --accent-pill: rgba(176,129,63,.20);
  --radius-lg: 30px;  --radius-md: 20px;  --radius-sm: 12px;
  --pad: 12px;        --gap: 12px;
  --shadow: 0 1px 2px rgba(0,0,0,.06), 0 8px 24px rgba(0,0,0,.05);
  --positive: #2E7D53;  --negative: #B3261E;  --neutral: #8A8A8A;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0F0F10;    --card: #1A1A1C;
    --fg: #F2F2F0;
    --shadow: none;                 /* el repo apaga sombras en oscuro */
    --accent-bg: rgba(176,129,63,.16);   /* sube de .10 a .16 porque el negro se come el tinte */
    --accent-pill: rgba(176,129,63,.26);
    --positive: #4CAF7D;  --negative: #E5685F;  --neutral: #7A7A7A;
  }
}
```

Dos cosas que el repo sí te enseña aquí:
1. En oscuro **las sombras desaparecen** (`box-shadow: none` aparece repetido por todo el repo cuando quiere "disolver" algo). Sobre negro una sombra no se lee, ensucia.
2. Los tintes translúcidos **deben subir de opacidad** en oscuro, porque un `rgba(x,.10)` sobre `#0F0F10` es casi invisible. El repo lo resuelve cambiando de expresión (`--color-background-yellow` + `--opacity-bg` en claro vs `rgba(color,.1)` en oscuro); con `prefers-color-scheme` lo resolvés redefiniendo la variable.

---

## 3. Lo que NO conviene

| Elemento del repo | Por qué NO sirve aquí |
|---|---|
| **Todo el stack es YAML de Home Assistant** (`custom:button-card`, `custom:layout-card`, `custom:state-switch`) | No son archivos web. Necesitan el runtime de HA, la integración HACS y el componente `ui_lovelace_minimalist`. **Cero aprovechable como código.** |
| **`custom:mini-graph-card`** (`custom_cards/energie_graph.yaml`) | Librería de terceros cargada vía HACS. **Es exactamente el tipo de dependencia que tu restricción prohíbe.** Es la que dibuja las líneas y barras del repo. |
| **`custom:apexcharts-card`** (`dashboard/ui-lovelace.yaml`) | Envuelve **ApexCharts.js**, que trae otro bundle. Toda la vista `prijzen` depende de él. **Descartado.** |
| **`custom:swipe-card`** (Swiper.js) | Carrusel externo. Su `spaceBetween: 6` y `slidesPerView: 3` son buenos números, pero el motor hay que reimplementarlo. |
| **`theme: "minimalist-desktop"` y los `var(--…)`** | **El punto más peligroso.** Si copias `var(--border-radius)` o `var(--box-shadow)` a tu HTML, no renderiza nada: esas variables las inyecta el tema de HA. **Hay que redefinirlas tú** (ver sección 4). |
| **El motor JS del repo (`[[[ … ]]]`)** | Es JavaScript dentro de YAML, evaluado por `button-card` en tiempo real contra el estado de HA. **No es código que puedas ejecutar en un HTML estático.** Tu Python ya precomputa todo en Postgres, así que no lo necesitás — de hecho es una ventaja tuya. |
| **`!include` / YAML-anchors (`&var`, `<<: *var`)** | Mecanismo de reutilización de YAML de HA. Tu reutilización es Python (un `for` que emite tarjetas), que es equivalente y más flexible. |
| **La estrategia de "ocultar el hueco" con `display:none`** | Contradice tu requisito de verse bien con 0 datos. Un dashboard que arranca vacío debe mostrar ceros, no desaparecer bloques. |
| **La ausencia de `tabular-nums`** | En HA no se nota; en un dashboard financiero sí. Omitirlo es un error heredado si copias el estilo tal cual. |
| **Los 6 breakpoints/`show: mediaquery` dispersos** | Bonito en YAML, pero para tu caso un solo `@media (max-width: 800px)` en el CSS propio es más simple y suficiente. No multipliques cortes por imitar. |

**Lo que sí queda en pie y vale el estudio:** los **valores numéricos** (radios 30/20, padding 12, gap 6/12, escala tipográfica 12/20/14, `opacity .40`, `height` fijas 48/70/160), el **patrón grid-template-areas + `.`**, el **patrón de acento en tres opacidades (.10/.20/1)**, y el **anidamiento decreciente de radios**.

---

## 4. Kit de CSS portátil

> **Advertencia de honestidad:** esto **no es un copia-pega del repo** (el repo no tiene CSS). Es la traducción a CSS puro de los valores y patrones verificados arriba, más las decisiones que el repo delega a su tema. Todo valor marcado como "del repo" se puede rastrear al fragmento citado en la sección 2.

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barbería Esteban Aguilera — Dashboard</title>
<style>
/* ───────────────────────── 1. TOKENS ─────────────────────────
   Nombres semánticos (patrón heredado del repo, que trabaja con
   tokens de tema en vez de hex sueltos). El repo NO define estos
   valores: los usa y los delega. Aquí sí se definen.            */
:root{
  /* superficies */
  --bg:#F7F7F5;  --card:#FFFFFF;
  --fg:#141414;  --fg-soft:#5C5C5C;
  /* un solo acento (regla del repo: acento por entidad, no por marca) */
  --accent:#B0813F;
  --accent-bg:rgba(176,129,63,.10);   /* del repo: ,0.1 para fondo de tarjeta */
  --accent-pill:rgba(176,129,63,.20); /* del repo: ,0.2 para pastilla de icono */
  /* semánticos */
  --pos:#2E7D53;  --neg:#B3261E;  --neu:#8A8A8A;
  /* radios — del repo: 30 / 20 / (nieto 0) */
  --r-lg:30px;  --r-md:20px;  --r-sm:12px;
  /* espaciado — base 6, del repo: 6 / 12 */
  --s1:6px;  --s2:12px;  --s3:24px;
  /* sombra — el repo delega en --box-shadow del tema */
  --shadow:0 1px 2px rgba(0,0,0,.06), 0 8px 24px rgba(0,0,0,.05);
  --caption-opacity:.40;  /* del repo: filter: opacity(40%) */
}
/* Modo oscuro: el repo lo resuelve por flag JS, aquí por media query */
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0F0F10;  --card:#1A1A1C;
    --fg:#F2F2F0;  --fg-soft:#9A9A9A;
    --accent-bg:rgba(176,129,63,.16);   /* sube en oscuro (el negro come el tinte) */
    --accent-pill:rgba(176,129,63,.26);
    --pos:#4CAF7D;  --neg:#E5685F;  --neu:#7A7A7A;
    --shadow:none;                      /* del repo: en oscuro las sombras se apagan */
  }
}

/* ───────────────────────── 2. BASE ───────────────────────── */
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg);  color:var(--fg);
  /* stack del sistema: cero webfonts, cero CDN */
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
              "Helvetica Neue",Arial,sans-serif;
  font-size:16px;  line-height:1.4;
  -webkit-text-size-adjust:100%;
  padding:var(--s2);
}
/* cifras: obligatorio en un dashboard financiero, el repo lo omite */
.num,.kpi-v,td,nav{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

/* ───────────────────────── 3. REJILLA ─────────────────────────
   Patrón del repo: grid-template-areas nombradas + punto = hueco.
   Del repo (livingroom.yaml): 3 columnas en desktop, 2 en móvil. */
.grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  grid-template-areas:
    "head  head  head"
    "hero  hero  hero"
    "k1    k2    k3"
    "k4    k5    ."        /* el "." del repo: celda vacía sin div fantasma */
    "serie serie top"
    "agenda agenda prox";
  gap:var(--s2);           /* del repo: row-gap 12px */
  max-width:1100px;        /* del repo: el corte de popups es a 1100px */
  margin:0 auto;
}
/* Móvil: mismo mecanismo que el repo, solo se reescriben áreas */
@media (max-width:800px){        /* del repo: "(max-width: 800px)" literal */
  .grid{
    grid-template-columns:repeat(2,1fr);
    grid-template-areas:
      "head   head"
      "hero   hero"
      "k1     k2"
      "k3     k4"
      "k5     k5"
      "serie  serie"
      "top    top"
      "agenda agenda"
      "prox   prox";
    gap:var(--s1);              /* del repo: el gap baja de 12 a 6 en móvil */
    padding:0;
  }
  body{padding:var(--s1)}
}
/* La orientación, no solo el ancho: el dueño gira el teléfono */
@media (max-width:1100px),(orientation:portrait){
  .grid{max-width:100%}   /* del repo: "100%" al colapsar */
}

/* ───────────────────────── 4. TARJETA ─────────────────────────
   Del repo (room_card.yaml + weather.yaml): padding 12px,
   border-radius, box-shadow, hijos "disueltos" con none/transparent. */
.card{
  background:var(--card);
  border-radius:var(--r-md);
  box-shadow:var(--shadow);
  padding:var(--s2);                 /* del repo: padding: "12px" */
  min-width:0;                       /* evita que el grid reviente en móvil */
  display:flex; flex-direction:column;
}
/* Anidamiento decreciente de radios (patrón del repo 30 → 20 → 0) */
.card--lg{border-radius:var(--r-lg);min-height:160px}  /* del repo: height 160px */
.card--flat{border-radius:0;box-shadow:none;background:transparent;padding:0}

/* Zonas de la rejilla */
.z-head{grid-area:head}    .z-hero{grid-area:hero}
.z-k1{grid-area:k1}        .z-k2{grid-area:k2}   .z-k3{grid-area:k3}
.z-k4{grid-area:k4}        .z-k5{grid-area:k5}
.z-serie{grid-area:serie}  .z-top{grid-area:top}
.z-agenda{grid-area:agenda}.z-prox{grid-area:prox}

/* ───────────────────────── 5. TIPOGRAFÍA ─────────────────────────
   El patrón clave: caption diminuto + cifra enorme.
   Escala del repo: 12 / 20 (→20 bold, caption 12 bolder + 40%).
   Extensión proporcional (~1.6×) para cifras protagonistas. */
.kpi{
  display:flex; flex-direction:column;
  justify-content:space-between;
  min-height:96px;
}
.kpi-l{                             /* el caption */
  font-size:12px;                   /* del repo: font-size: "12px" */
  font-weight:700;                  /* del repo: font-weight: "bolder" */
  text-transform:uppercase;
  letter-spacing:.04em;
  color:var(--fg);
  opacity:var(--caption-opacity);    /* del repo: filter: opacity(40%) */
  margin:0 0 10px 0;                 /* del repo: margin-top: "10px" (invertido) */
}
.kpi-v{                             /* la cifra */
  font-size:32px;                   /* extrapolado desde el 20px del repo */
  font-weight:700;                  /* del repo: font-weight: "bold" */
  line-height:1.05;
  letter-spacing:-.02em;
  margin:0;
  align-self:flex-end;              /* del repo: justify-self: "end" */
}
.kpi-v--xl{font-size:52px}          /* solo "Ingresos hoy" */
.kpi-v--sm{font-size:20px}          /* del repo: font-size: "20px" */
.kpi-u{font-size:14px;font-weight:700;
       color:var(--fg-soft);margin-left:.25em}  /* del repo: 14px bold */

/* valor por fila de tabla / lista */
.row{display:flex;justify-content:space-between;align-items:baseline;
     gap:var(--s2);height:48px}     /* del repo: height: "48px" */
.row-l{font-size:12px;font-weight:700;letter-spacing:.03em;
       text-transform:uppercase;opacity:var(--caption-opacity);
       white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row-v{font-size:20px;font-weight:700;margin-left:auto}  /* del repo: 20px bold */

h1.sec{                             /* título de sección */
  font-size:12px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;opacity:var(--caption-opacity);
  margin:var(--s3) 0 var(--s1);
}

/* ───────────────────────── 6. COLOR SEMÁNTICO ─────────────────────────
   El repo marca por umbral y color nombrado (green/red/orange).
   Aquí se fija la pareja positivo/negativo que el repo no tiene. */
.pos{color:var(--pos)}   .neg{color:var(--neg)}   .neu{color:var(--neu)}
/* Acento en tres opacidades — el patrón más portable del repo */
.acento-bg{background:var(--accent-bg)}
.acento-pill{background:var(--accent-pill);color:var(--accent);
             border-radius:var(--r-sm);padding:2px var(--s1);
             font-size:12px;font-weight:700}

/* ───────────────────────── 7. ESTADO VACÍO ─────────────────────────
   El repo NO tiene esto (oculta con display:none). Aquí se define:
   misma opacity de caption → el vacío se lee como jerarquía, no error. */
.empty{
  padding:var(--s3) var(--s2);
  text-align:center;font-size:12px;font-weight:700;
  text-transform:uppercase;letter-spacing:.04em;
  opacity:var(--caption-opacity);
}
/* barra de proporción reutilizable (para estados del mes, horas pico, etc.) */
.bar{display:flex;align-items:center;gap:var(--s1);height:24px}
.bar-t{flex:1;height:6px;border-radius:3px;background:var(--accent-bg);
       overflow:hidden}      /* pista */
.bar-f{display:block;height:100%;background:var(--accent);border-radius:3px}
.bar-v{font-size:12px;font-weight:700;min-width:3.5em;text-align:right}
</style>
</head>
<body>
  <div class="grid">
    <section class="card card--lg z-hero">
      <p class="kpi-l">Ingresos hoy</p>
      <p class="kpi-v kpi-v--xl">—</p>
    </section>
    <!-- … -->
  </div>
</body>
</html>
```

**Decisiones de la sección 4 y su origen:**

| Decisión | Origen |
|---|---|
| `grid-template-areas` + `.` para hueco | `livingroom.yaml` |
| 3 col → 2 col en `max-width:800px` | `livingroom.yaml`, `main.yaml`, `lights.yaml` |
| OR con `orientation:portrait` | `ui-lovelace.yaml` |
| `max-width:1100px` como techo | `ui-lovelace.yaml` |
| `padding:12px` / `gap:12px` | `room_card.yaml`, `weather.yaml` |
| Radios 30/20/0 anidados | `weather.yaml`, `room_card.yaml` |
| Caption `12px` `bold` `opacity .40` | `weather.yaml`, `room_card.yaml` |
| Cifra `20px` `bold` | `weather.yaml` |
| `margin 10px` caption↔cifra | `weather.yaml` |
| `height:48px` / `160px` | `room_card.yaml`, `weather.yaml` |
| `justify-self:end` en cifras | `weather.yaml` |
| Acento `.10 / .20 / 1` | `room_card.yaml` |
| `box-shadow:none` en oscuro | `room_card.yaml`, `weather.yaml`, `energie_graph.yaml` |
| **`tabular-nums`, escala 32/52, `.empty`, modo oscuro por media query** | **Extrapolación propia** — el repo no los tiene |

---

## 5. Cómo hacer las gráficas sin librería

> Esto es **propuesta propia**. El repo usa `mini-graph-card` y `apexcharts-card` (ambas descartadas). Lo único que se conserva es su *configuración de datos*, que revela el enfoque correcto para tu caso.

**Lo que el repo sí dice de las series** (`dashboard/adaptive-dash/assets/domains/energy.yaml` + `custom_cards/energie_graph.yaml`):

```yaml
variables:
  ulm_card_graph_type: bar        # barras, no línea
  ulm_card_graph_group_by: hour   # agrupado por HORA
  ulm_card_graph_points: 1
  ulm_card_graph_func: max
  ulm_card_graph_color: orange
  ulm_card_graph_hours: 168       # 168h = 7 días, agrupado por 'date'
```

Lección: **la serie de 30 días y las horas pico son el mismo dato con distinto `group_by`** (`date` vs `hour`) y distinto `func` (`max`/`sum`). En Python eso es una sola función de agregación con dos parámetros. El repo grafica `bar` para el consumo por hora y `line`/`fill` para el histórico de 7 días.

### 5.1 Barras: divs con altura en %, sin SVG ni canvas

Para **30 días**, **horas pico** y **reparto de estados del mes** el enfoque más barato y robusto es alto porcentual sobre el valor máximo. Es puro CSS, escala solo, y no tiene problemas de nitidez en móvil.

```html
<div class="chart-cols" style="--max:1240">
  <!-- Python emite un .col por día; la altura es valor/max -->
  <div class="col">
    <span class="col-f" style="height:82%"></span>   <!-- ya calculado en Python -->
    <span class="col-x">L</span>
  </div>
  <div class="col">
    <span class="col-f" style="height:0%"></span>    <!-- día sin ventas: barra invisible -->
    <span class="col-x">M</span>
  </div>
  <!-- … 30 veces -->
</div>
```

```css
.chart-cols{
  display:flex; align-items:flex-end;   /* las barras crecen desde abajo */
  gap:2px;                               /* del repo: spaceBetween pequeño */
  height:120px; margin-top:var(--s2);
}
.col{
  flex:1 1 0; min-width:0;
  display:flex; flex-direction:column; justify-content:flex-end;
  height:100%; position:relative;
}
.col-f{
  display:block; width:100%;
  background:var(--accent);              /* un solo acento, como el repo */
  border-radius:3px 3px 0 0;
  min-height:2px;                        /* evita que un 0 desaparezca del todo */
  transition:height .4s ease;            /* del repo: transition_time: 500 */
}
.col-x{
  position:absolute; bottom:-16px; left:0; right:0;
  text-align:center;
  font-size:10px; font-weight:700;
  opacity:var(--caption-opacity);
}
```

**Clave del diseño en Python:** no emitas `height: 0%`. Emití `height: 1%` o dejá que `min-height:2px` actúe, para que el día sin ventas siga ocupando su columna y el eje X conserve las 30 posiciones. Una serie con huecos se ve rota; una serie con bases visibles se ve *vacía*, que es lo correcto con 0 datos.

### 5.2 Serie de tendencia: SVG inline con `polyline`

Para la serie de 30 días como **línea** (tendencia, no magnitud diaria) y para el **relleno de área**, SVG inline es superior a los divs: se dibuja con una sola ruta, se estira con `preserveAspectRatio="none"` y el trazo se mantiene nítido con `vector-effect="non-scaling-stroke"`.

```html
<svg class="spark" viewBox="0 0 300 60" preserveAspectRatio="none"
     role="img" aria-label="Ingresos últimos 30 días">
  <!-- Python calcula los puntos: x = i/(n-1)*300, y = 60 - v/max*56 -->
  <polyline class="spark-area"
            points="0,60 10.3,42 20.7,48 … 300,18 300,60"
            fill="var(--accent-bg)" stroke="none"/>
  <polyline class="spark-line"
            points="0,60 10.3,42 20.7,48 … 300,18"
            fill="none" stroke="var(--accent)" stroke-width="2"
            stroke-linejoin="round" stroke-linecap="round"
            vector-effect="non-scaling-stroke"/>
</svg>
```

```css
.spark{display:block; width:100%; height:60px; overflow:visible}
.spark-line{stroke:var(--accent)}
.spark-area{fill:var(--accent-bg)}
```

**Estado vacío de la gráfica (30 días a cero):** no ocultes el gráfico. Dibujá la línea base plana al fondo del `viewBox` (`y = 59`, un punto por día) y superponé el `.empty`. Así el dueño ve el eje y entiende "aún no hay datos", en vez de un hueco.

### 5.3 Barras horizontales: para Top servicios y Horas pico

Cuando las etiquetas son texto largo ("Corte + barba"), barras verticales no sirven. Barras horizontales con `flex` y ancho en %, sin necesitar librería:

```html
<ul class="hbars">
  <li class="hbar">
    <span class="hbar-l">Corte + barba</span>
    <span class="bar"><span class="bar-f" style="width:100%"></span></span>
    <span class="bar-v">$0</span>
  </li>
  <li class="hbar">
    <span class="hbar-l">Corte simple</span>
    <span class="bar"><span class="bar-f" style="width:43%"></span></span>
    <span class="bar-v">$0</span>
  </li>
</ul>
```

```css
.hbars{list-style:none;margin:0;padding:0}
.hbar{display:grid;grid-template-columns:minmax(0,1fr) 40% 3.5em;
      align-items:center;gap:var(--s1);height:32px}
.hbar-l{font-size:12px;font-weight:700;text-transform:uppercase;
        letter-spacing:.03em;opacity:var(--caption-opacity);
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* .bar / .bar-f / .bar-v reutilizados de la sección 4 (kit) */
```

Nótese la reutilización: `.bar`, `.bar-f` y `.bar-v` se definen **una sola vez** en el kit y sirven para Top servicios, Horas pico y Reparto de estados del mes. El repo hace lo mismo con `swiper-margin` (un archivo de 2 líneas reutilizado en todas las tarjetas de todos los carruseles): **extraer el detalle repetido a una clase de una sola responsabilidad**.

### 5.4 Por qué NO usar SVG con JS en este proyecto

Tu HTML lo genera Python y se abre desde el teléfono como archivo local. El enfoque de **precomputar todo en Python** (alturas en %, puntos del `polyline`, anchos) es el correcto:

- **Cero JS para las gráficas** → cero superficie de fallo. Si el CSS no carga, los números siguen ahí.
- **Los valores ya están en el HTML** (accesibles, seleccionables, imprimibles), no detrás de un render en canvas.
- **Escala solo**: `%` y `viewBox` se adaptan sin recalcular en resize.
- Coincide con la filosofía del repo: allí el dato también se precomputa (vía `group_by`/`func`) y la tarjeta solo pinta.

---

## Resumen ejecutivo

El repo es **YAML de Home Assistant sobre UI-Lovelace-Minimalist**, con 4 vistas, y **no contiene CSS ni HTML**: un tercio de lo que pediste no existe y hay que decirlo. Lo aprovechable son **valores y patrones**, no código:

1. **Rejilla nombrada** con `grid-template-areas`, el punto `.` como hueco, y el mismo mecanismo reescrito en `@media (max-width:800px)` de 3 → 2 columnas.
2. **Caption 12px bold al 40% de opacidad + cifra 20px bold**, con 10px entre ambos.
3. **Acento único en tres opacidades** `.10` / `.20` / `1`, y `box-shadow:none` en oscuro.
4. **Radios anidados decrecientes** 30 → 20 → 0, con `padding` 12 y `gap` 6/12 (base 6).
5. **Alturas fijas** (48 / 70 / 160px) para que el layout no baile.

Y hay que **aportar de fuera** cuatro cosas que el repo no resuelve: `tabular-nums`, el estado vacío con ceros visibles, el modo oscuro por `prefers-color-scheme` (el repo lo hace por flag JS del runtime de HA), y el dibujo de gráficas (el repo usa dos librerías, ambas prohibidas aquí).