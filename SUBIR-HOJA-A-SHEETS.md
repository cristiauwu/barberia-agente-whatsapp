# Cómo subir la hoja "Citas barbería" a Google Sheets

## Archivos generados en `G:\Barberia`

| Archivo | Para qué |
| --- | --- |
| **`Citas barberia.xlsx`** | **Recomendado.** Sube este. |
| `Citas barberia.csv` | Alternativa si el xlsx te da problemas |

Ambos tienen exactamente las **8 columnas** que el flujo espera, ni una más
ni una menos, y la pestaña se llama **`Hoja 1`**.

## Paso a paso

1. Entra a **https://sheets.google.com** con la cuenta **`crir627@gmail.com`**
2. Arriba a la izquierda: **+ En blanco** (crea una hoja vacía)
3. Menú **Archivo → Importar**
4. Pestaña **Subir** → arrastra `Citas barberia.xlsx`
5. En "Acción de importación" elige: **Reemplazar hoja de cálculo**
6. **Importar datos**
7. Renombra el archivo (arriba a la izquierda) a: **`Citas barbería`**
8. Asegúrate de que la pestaña de abajo diga **`Hoja 1`**

## Las columnas que quedaron (no las cambies)

```
ID | Estatus | Nombre | Servicio | Precio del servicio | Día  | Hora | Numero celular
```

### ⚠️ Tres columnas que parecen raras y son correctas

**1. `Día ` lleva un ESPACIO al final.**
No es un error de tecleo. Lo verifiqué byte a byte:
```
bytes = b'D\xc3\xada '   <- termina en espacio (0x20)
```
Si le quitas el espacio, **el registro de citas deja de funcionar**. Si le
cambias el acento, lo mismo.

**2. Están `ID` y `Estatus`** aunque tu otra hoja no los tenía.
Son necesarios:
- **`ID`** → identifica la cita para poder **cancelarla o reprogramarla**
- **`Estatus`** → el flujo lo lee para decidir si programa el recordatorio
  (`agendado`) o lo cancela (`cancelado`)

Sin esas dos columnas, el agente puede agendar pero **no puede cancelar ni
reagendar**, y los recordatorios no se disparan.

**3. `Precio del servicio`** es informativo. Podrías borrarla, pero entonces
tendrías que avisarme para ajustar el nodo.

## Después de subirla: falta un paso

**La hoja nueva tendrá un ID distinto.** El flujo apunta hoy al ID de la hoja
del vendedor, que ya no existe en tu cuenta:

```
Actual:  17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY   (no es tuya)
```

Cuando la subas, **cópiame la URL** de tu hoja nueva. Se ve así:

```
https://docs.google.com/spreadsheets/d/[ESTE_ES_EL_ID]/edit
```

Con ese ID yo reapunto los nodos (son 4 en los dos flujos). Sin eso, el agente
dirá "cita agendada" pero **no escribirá nada** — es justo el error
*"The caller does not have permission"* que ya vimos.

## Verificación que ya hice

```
PASS  CSV: encabezados identicos al workflow
PASS  CSV: lleva BOM UTF-8 (acentos correctos)
PASS  XLSX: la pestaña se llama 'Hoja 1'
PASS  XLSX: encabezados identicos al workflow
PASS  XLSX: solo el encabezado (1 fila)
PASS  La columna es 'D' + i-acentuada + 'a' + ESPACIO
PASS  La columna termina en espacio (importa)
RESULTADO: 7 de 7 PASARON
```

Los encabezados los extraje **directamente del workflow**, no los escribí a
mano: por eso no hay errores de tecleo.