# Tendencias tecnológicas 2026 — evaluación para Barber Chinos

**Fecha del análisis:** 25 de septiembre de 2026
**Autor:** agente de investigación (subagente)
**Naturaleza:** investigación. **No se modificó nada del sistema.**

> Este documento distingue en todo momento entre **lo confirmado** (con fuente
> verificable) y **la opinión razonada** del autor. Cuando algo no se pudo
> verificar, se dice explícitamente.

---

## 1. Resumen ejecutivo

1. De las tres noticias, **ninguna es implementable hoy** en este producto, y por
   razones distintas.
2. **WhatsApp + agentes de IA de terceros**: es real, pero es una función del
   **usuario** en su WhatsApp personal (beta iOS/TestFlight, "muy pocos usuarios
   en países selectos"), no un canal para negocios. **No aplica.** Además va
   **sin cifrado de extremo a extremo**.
3. **Meta Muse**: real, lanzada el 8-sep-2026, arrasó (2,5 M descargas), pero es
   **solo EE. UU.**, es un producto de **consumidor** sin API para que el negocio
   se integre, y tiene plan de pago de $20/$100 al mes. **No aplica hoy.**
4. **Cohere + Aleph Alpha**: real (acuerdo definitivo firmado el 16-sep-2026,
   pendiente de aprobación regulatoria), pero es **IA empresarial y soberana para
   gobiernos**, sin producto para pymes. **No aplica en absoluto.**
5. Ninguna de las tres mejora la atención al cliente de una barbería de un solo
   barbero en México. Perseguirlas es una **solución buscando problema**.
6. El hallazgo más importante del análisis **no está en las tres noticias**:
   el servicio de WhatsApp local corre **Evolution API v2.3.7**, que es
   **exactamente la versión con el bug documentado de botones y listas
   interactivas** (issue abierto desde feb-2026). Es decir: **los botones
   interactivos hoy no funcionan aquí**, aunque se los recomiende por doquier.
7. Hay mejoras de **altísimo valor y coste casi nulo** que ya están a medio
   construir en el propio sistema: la tabla `barber_lista_espera` está **vacía**
   (0 filas) y los recordatorios piden "SI/NO" **sin que ese "SI" cambie nada**.
8. La palanca real de dinero no son los agentes de IA de las noticias: es
   **cerrar el bucle de confirmación** para bajar los no-shows. Un solo barbero
   pierde el 100% del ingreso de cada hueco que queda vacío.
9. La única vía técnica para tener botones interactivos *nativos*, insignia
   verificada y **cero riesgo de ban** es migrar a la **API oficial de Meta**, que
   es **de pago y exige tarjeta** → choca de frente con las restricciones del
   dueño. Es una decisión de negocio, no una mejora que se pueda "colar" gratis.
10. Recomendación de venta: **no** justificar la propuesta al cliente con estas
    tres noticias. Justificarla con las mejoras concretas de la sección 4, que sí
    se notan y sí son gratis.

---

## 2. Ficha por noticia

### 2.1 Noticia 1 — WhatsApp prueba agentes de IA de terceros en los chats

**Enlace de partida:**
https://gadgets.beebom.com/news/whatsapp-testing-feature-to-add-third-party-ai-agents-to-chats

**Qué es (confirmado):**
- WhatsApp permite a **usuarios** crear hasta **5 chats con agentes de terceros**
  dentro de la app, dando al agente un nombre y una foto, y generando una
  **clave API** que el usuario pega en el servicio donde está alojado su agente.
  Lo detectó **WABetaInfo** en la **beta de iOS 26.37.10.70** (TestFlight) y ya
  existía en la **beta de Android 2.26.35.3**.
  https://wabetainfo.com/whatsapp-is-rolling-out-chats-with-third-party-agents-on-ios/
  https://9to5mac.com/2026/09/07/whatsapp-will-soon-let-users-chat-with-up-to-five-third-party-ai-agents/
- **Disponibilidad real:** *"esta función está disponible para un número muy
  limitado de usuarios en países selectos"*. **No se enumeran los países.** No hay
  fecha de lanzamiento general anunciada.
  https://wabetainfo.com/whatsapp-is-rolling-out-chats-with-third-party-agents-on-ios/
- **Coste:** no se describe cobro por esta función.
- **Limitación grave (confirmada):** *"los chats con agentes **no** están cifrados
  de extremo a extremo, ya que los gestiona un servicio seguro de Meta en nombre
  del desarrollador del agente"*, y **el desarrollador del agente puede acceder a
  esos mensajes**. Tampoco se admiten **mensajes efímeros**.
  https://wabetainfo.com/whatsapp-is-rolling-out-chats-with-third-party-agents-on-ios/
- **Privacidad:** el agente **solo** puede leer lo que el usuario comparte en esa
  conversación; no ve otros chats, ni la agenda de contactos, ni la media del
  dispositivo. (Esto es un alivio de alcance, **no** de cifrado.)

**¿Exagera el titular?** Sí, en un punto clave: los titulares lo presentan como
"agentes de IA en WhatsApp", cuando en realidad es **el usuario conectando su
propio bot externo**. WABetaInfo precisa además que *"un agente no es
necesariamente IA: también puede ser un bot"*.

**¿Aplica a Barber Chinos? — NO.**

- Es una función del **lado usuario** de WhatsApp (cuenta personal), no del **lado
  negocio**. No existe forma de que la barbería se "instale" como agente en el
  WhatsApp de sus clientes; el cliente tendría que agregar el agente a *su* cuenta.
  Eso no es un canal de atención al cliente, es lo contrario.
- Está en beta cerrada, en "países selectos" **sin especificar si México está
  incluido** — **no pude confirmarlo**.
- Nuestro stack entra por **Evolution API / Baileys**, que es **WhatsApp Web
  enlazado**, no la plataforma de agentes de Meta. Son caminos distintos.
- **El problema de cifrado es serio y va en contra del negocio:** hoy las
  conversaciones de los clientes están cifradas de extremo a extremo (es WhatsApp
  normal). Meter esas conversaciones en un chat **sin E2E** significa que
  **nombres, teléfonos y detalles de citas de clientes** pasarían por servidores
  de un tercero y serían **legibles por el desarrollador de ese agente**. Para un
  negocio mexicano esto es un riesgo de privacidad y un problema frente a la
  **LFPDPPP** (Ley Federal de Protección de Datos Personales en Posesión de los
  Particulares), no una mejora.

**Veredicto:** Real pero **irrelevante para este producto**. Y si algún día fuese
técnicamente posible, **el coste de privacidad es inaceptable**: degradaría una
garantía que el cliente ya tiene hoy.

---

### 2.2 Noticia 2 — Meta Muse

**Enlace de partida:** https://www.cnn.com/2026/09/23/tech/meta-muse-ai-agent

**Qué es (confirmado):**
- Meta lanzó **Muse** el **8 de septiembre de 2026**: un **agente personal de IA**
  que ejecuta tareas (envía correos, reserva viajes, rellena formularios, negocia
  facturas, compra). Funciona sobre **Muse Spark** y corre en una **VM dedicada
  ("Muse Secure VM")**.
  https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/
  https://www.cnbc.com/2026/09/08/meta-personal-ai-agents-public-reckoning-privacy-safety.html
- **Tracción (confirmada):** más de **2,5 millones de descargas** desde el
  lanzamiento y **número 1 de apps gratuitas en el App Store de EE. UU.**, según
  **Sensor Tower**. En el mismo periodo, ChatGPT tuvo 3,1 M de descargas globales
  y Claude 200.000.
  https://www.cbsnews.com/news/meta-ai-agent-muse-shopping/
- **Dónde está disponible (confirmado):** **solo Estados Unidos**. La lista de
  iOS devuelve resultados en la tienda de EE. UU. y **nada en otras quince
  tiendas**; el bloqueo está en la capa de cuenta (*"Muse is not available in your
  country"*). Meta **no publicó** lista de países, ni lista de espera, ni fecha
  para el resto del mundo. México **no está incluido**.
  https://moclaw.ai/blog/meta-muse-not-available-in-your-country
  *(fuente de terceros; el dato duro es el propio anuncio de Meta, que dice "the US")*
- **¿Requiere pago? Parcialmente sí:** Meta describió un **nivel gratuito** y
  **planes de suscripción de $20 o $100 al mes según uso** (declaración de Alexandr
  Wang, jefe de IA de Meta, a CNBC).
  https://www.cnbc.com/2026/09/08/meta-personal-ai-agents-public-reckoning-privacy-safety.html
- Muse se usa *"en la app de Muse o directamente en WhatsApp"* (anuncio de Meta).
- Dato revelador de fricción: **Amazon bloqueó a Muse** para comprar en su
  plataforma, por seguridad y experiencia de usuario. Expedia y PayPal sí se
  aliaron.
  https://www.cbsnews.com/news/meta-ai-agent-muse-shopping/
- **Escepticismo sano:** el propio análisis de CBS cita a un analista: *"la gente
  todavía está un poco nerviosa sobre dejar que los agentes de IA hagan las
  compras por ellos"*. Las descargas masivas **no** equivalen a uso fiable.

**¿Exagera el titular?** El titular de CNN ("puede hacer cosas por ti") es
optimista, pero el artículo es honesto: detalla limitaciones y dudas de privacidad.
Precisión importante: CNN dice *"en dos semanas fue la app gratuita más
descargada"*; el dato verificable de Sensor Tower son **2,5 M de descargas**, y ser
#1 en la categoría gratuita **de EE. UU.** **no** es lo mismo que ser #1 global.

**¿Aplica a Barber Chinos? — NO.**

- **No está en México.** Ni hoy, ni con fecha anunciada.
- Es un producto de **consumidor**: es el agente *del cliente*, no una herramienta
  del negocio. **No existe API ni integración** por la que la barbería pueda
  exponer su agenda a Muse. **No pude encontrar ninguna** — y la ausencia es
  coherente con el diseño del producto.
- Aun si estuviera en México, el caso de uso sería "un cliente le pide a su agente
  que le reserve un corte" — y eso **requiere que el negocio esté detrás de una
  plataforma a la que Muse pueda llamar** (tipo OpenTable/Expedia). Nuestra agenda
  es **Google Calendar** sobre una instancia de Evolution API **en localhost**:
  literalmente **no es alcanzable desde internet**, así que ningún agente externo
  podría reservar ni aunque existiera la integración.
- **El riesgo estratégico que sí conviene mirar:** en un mundo donde los agentes
  del cliente reservan solos, un negocio que **no** es alcanzable por agentes
  pierde esos clientes. Es un argumento a favor de, algún día, tener una **API
  pública mínima** de disponibilidad. **Hoy no hay que hacer nada al respecto**,
  pero es la única lectura útil de esta noticia. *(Opinión razonada.)*

**Veredicto:** Real y con tracción enorme, pero **geográfica y
arquitectónicamente fuera de alcance**. Ninguna acción hoy.

---

### 2.3 Noticia 3 — Cohere y Aleph Alpha se fusionan

**Enlace de partida:**
https://siliconangle.com/2026/09/16/cohere-and-aleph-alpha-agree-to-merge-in-reported-20b-deal/

**Qué es (confirmado):**
- **Firmaron un acuerdo definitivo de fusión el 16-sep-2026**. La empresa
  combinada operará como **Cohere**, con **doble sede en Toronto y Berlín**, y la
  oficina de Heidelberg (Aleph Alpha) como centro de investigación. Ilhan Scheer
  (Co-CEO de Aleph Alpha) será COO de Cohere.
  https://www.reuters.com/legal/transactional/cohere-aleph-alpha-combine-target-enterprise-ai-market-2026-09-16/
  https://www.prnewswire.com/news-releases/cohere-and-aleph-alpha-sign-agreement-to-become-the-first-transatlantic-sovereign-ai-solution-302880758.html
- El plan **se anunció en abril de 2026**; el 16 de septiembre se firmó. No es un
  rumor de última hora.
  https://www.reuters.com/legal/transactional/canadas-cohere-germanys-aleph-alpha-announce-merger-handelsblatt-reports-2026-04-24/
- **Pendiente de aprobación (confirmado):** el comunicado oficial dice que la
  transacción *"sigue sujeta a las aprobaciones regulatorias finales"*. Es decir:
  **firmada, pero no cerrada.**
- **El "cierre a fin de año" NO lo pude confirmar.** El comunicado oficial **no
  fija fecha**. Es un dato que aparece en la prensa; **no lo pude verificar desde
  fuente primaria.**
- **Sobre los "20.000 millones":** el propio titular de SiliconANGLE dice
  *"reported"* (reportado). El comunicado oficial **no menciona la cifra**. Es el
  valor **reportado** de la empresa resultante, no una cifra confirmada por las
  partes. Cohere recaudó en sept-2025 a una valoración de **$7.000 M**, lo que
  hace plausible el salto a $20.000 M, pero sigue siendo dato de prensa.
- **Financiación (confirmada):** **Schwarz Group** invertirá **500 M €** en la
  compañía e invertirá **hasta 13.000 M €** en cómputo vía **StackIT**.
  https://www.reuters.com/legal/transactional/cohere-aleph-alpha-combine-target-enterprise-ai-market-2026-09-16/
- **A qué se dedica el resultado:** "soluciones de IA **segura y soberana** para
  **gobiernos e industrias altamente reguladas**", con despliegue **en la propia
  infraestructura del cliente**. Cohere vendía acceso a modelos por API y un
  servicio de productividad llamado **North**; su ingreso llegó a **$240 M**.
  https://siliconangle.com/2026/09/16/cohere-and-aleph-alpha-agree-to-merge-in-reported-20b-deal/

**¿Exagera el titular?** Sí, en dos cosas: (a) **el precio no está confirmado**
—es "reportado"— y (b) el cierre no está cerrado. Llamarlo ya "la primera IA
soberana transatlántica" es el lenguaje del comunicado de prensa, no un hecho
consumado.

**¿Aplica a Barber Chinos? — NO. En absoluto.**

- El producto resultante se dirige a **gobiernos y empresas reguladas** que
  despliegan IA **en su propia infraestructura**. Una barbería de un barbero en
  México **no es el cliente objetivo** de ninguna manera.
- Lo único que *podría* interesar es cambiar el modelo de lenguaje: hoy usamos
  **GPT-4o vía Uncensored AI (compatible con OpenAI)**. Cohere tiene modelos
  **Command** y endpoint compatible; migrar sería técnicamente posible.
  **Pero no aporta nada que el cliente note**: las respuestas del bot no mejorarían
  de forma perceptible, y a cambio habría que reescribir la integración del modelo,
  volver a validar el prompt de ~44.506 caracteres y asumir el coste del nuevo
  proveedor. **Es trabajo sin beneficio visible.** *(Opinión razonada.)*
- **Nota de arquitectura:** el proyecto ya documentó que **Uncensored AI no tiene
  endpoint de embeddings** (`/embeddings` → 404), lo que bloqueó el RAG. Un
  proveedor de embeddings es el *único* hueco real que Cohere podría llenar… pero
  para eso no hace falta esperar una fusión, y el proyecto ya decidió usar
  búsqueda de texto completo de Postgres (gratis, nativa, suficiente a esta
  escala).

**Veredicto:** Real, pero **completamente ajeno al producto**. Cero acciones.

---

## 3. Lo que encontré en NUESTRO sistema (el hallazgo que importa)

Esto no viene de las noticias. Se verificó en vivo contra el sistema.

### 3.1 Confirmado: Evolution API v2.3.7 — la versión con el bug de botones

```
GET http://localhost:8080
{"status":200,"message":"Welcome to the Evolution API, it is working!",
 "version":"2.3.7","clientName":"evolution_barberia",
 "whatsappWebVersion":"2.3000.1048518751"}
```

Y la instancia responde:

```
GET /instance/connectionState/hector
{"instance":{"instanceName":"hector","state":"open"}}
```

**El problema, confirmado con fuentes:**

- El issue **#2390** se titula literalmente *"[BUG] Interactive Buttons and Lists
  fail in Evolution API **v2.3.7**"*: *"los mensajes interactivos de WhatsApp
  (botones y listas) no funcionan correctamente… Requests que antes funcionaban
  (p. ej. 2.3.6) ahora fallan"*. Error reportado:
  `"TypeError: this.isZero is not a function"` → HTTP 400.
  https://github.com/EvolutionAPI/evolution-api/issues/2390
- El issue **#2404** —al que #2390 fue consolidado por un maintainer— describe el
  peor caso: *"los mensajes con botones (`sendButtons`) **devuelven HTTP 201 pero
  nunca se entregan**… no hay errores y el estado queda PENDING"*.
  **Estado: ABIERTO** desde el 3-feb-2026.
  https://github.com/EvolutionAPI/evolution-api/issues/2404
- El **PR #2651** que arregla la causa raíz (se envolvía el contenido en
  `viewOnceMessage`, que no soporta botones) **sigue ABIERTO y sin mergear**.
  https://github.com/evolution-foundation/evolution-api/pull/2651
- El **release oficial v2.4.0** sí documenta la corrección: *"Button rendering
  fixed on WhatsApp Web/Desktop/iOS/Android — removed the `viewOnceMessage`
  wrapper… List messages fixed…"*, y avisa: *"Buttons/list not rendering on
  WhatsApp Web — make sure you are on **v2.4.0+**"*.
  https://github.com/evolution-foundation/evolution-api/releases/tag/2.4.0-rc1

**Conclusión (confirmada):** en **v2.3.7** los botones y listas **no se entregan**.
El arreglo existe, pero **solo desde v2.4.0**.

**Y aquí está la trampa:** **v2.4.0 introduce un cambio de ruptura** — a partir de
esa versión cada instancia **debe activarse contra el servidor de licencias de
Evolution Foundation** antes de servir tráfico. Sin activar, **todos los endpoints
de negocio devuelven `HTTP 503 LICENSE_REQUIRED`**.
https://github.com/evolution-foundation/evolution-api/releases/tag/2.4.0-rc1

**Matiz honesto:** la licencia **community es gratuita**, sin límite de instancias
ni de mensajes, y el proyecto **sigue siendo Apache 2.0**. Pero la activación
**exige un correo y un teléfono** y la instancia manda **latidos periódicos** con
versión, contadores agregados de uso, features habilitadas e **IP del servidor**.
No se envían mensajes ni contactos.
https://docs.evolutionfoundation.com.br/licensing

*(Ojo: esto lo verifica la documentación del proveedor. Es una afirmación suya
sobre su propio comportamiento; no la audité en el código.)*

**Lo que NO pude verificar:** no ejecuté un `sendButtons` real contra la instancia
`hector`, porque eso enviaría un mensaje a un número real y la misión prohíbe
modificar el sistema. Lo confirmado es **(a) la versión que corre** y **(b) el bug
documentado en esa versión exacta**. La combinación es concluyente, pero no es una
observación directa del fallo en esta máquina.

### 3.2 Confirmado: el bucle de confirmación no cierra

- Los dos recordatorios son **`sendText` en texto plano** (nodos HTTP POST a
  `/message/sendText/hector`). La frase del recordatorio de 24 h es:
  *"Responde **SI** para confirmar o **NO** si necesitas cambiarla."*
- El workflow del agente **no tiene ninguna rama que consuma esa respuesta**. El
  `Switch` de entrada solo reconoce **texto**:
  ```
  message_content_type = {{ extendedTextMessage ? 'text':'' }}{{ conversation ? 'text':'' }}
  ```
- Buscando en el JSON del workflow: **`buttonsResponseMessage` → 0**,
  **`listResponseMessage` → 0**, **`interactiveResponseMessage` → 0**,
  **`templateButtonReplyMessage` → 0**, y **`sendButtons`/`sendList` → 0** en los
  dos workflows.
- Las **7 herramientas** del agente son: `Consultar agenda`, `Agendar cita`,
  `Cancelar cita`, `Reagendar`, `Registrar en hoja de citas`,
  `Notificar al encargado`, `Que dia es`. **No hay ninguna herramienta de
  "Confirmar cita".**
- Existe el estado `confirmado` en `barber_citas`, pero **ningún camino real lo
  escribe por una respuesta del cliente**.

**Traducción a negocio:** el recordatorio *pide* confirmación y **no la registra**.
El "SI" del cliente cae en el modelo de lenguaje, que puede contestar amablemente
pero **no cambia nada en la agenda ni en el panel**. El barbero **no sabe quién
confirmó**. Es una función que *parece* existir y no existe. *(Opinión razonada,
apoyada en los conteos de arriba.)*

**Coste oculto añadido:** cada "SI" o "NO" de cada recordatorio **pasa por el
modelo** (≈$0,026 por turno según `ARQUITECTURA.md`), gastando tokens para no hacer
nada útil.

### 3.3 Confirmado: la lista de espera existe y está vacía

```
tabla barber_lista_espera → columnas: id, jid, servicio, duracion_min,
                                     ventana_deseada, creado_en, atendido
filas: 0
```

También están vacías `barber_escalaciones` (0) y `barber_consentimiento` (0). El
CRM tiene 2 clientes reales y 55 de pruebas (`verif-*`), y `barber_citas` tiene
2 filas reales y 209 de verificación. Es decir: **hay esquema construido y sin
usar**. Es la oportunidad más barata del sistema.

### 3.4 Sobre la insignia verificada de WhatsApp

**Confirmado, y es una mala noticia:** la ruta **gratuita** a la insignia es
**Official Business Account**, y exige, entre otros requisitos, estar
**registrado en la WhatsApp Business Platform durante al menos 30 días**.
Fuente de Meta:
https://www.facebook.com/business/help/604726921052590

Lo crítico, según un análisis que revisó la documentación de Meta el 3-ago-2026:
*"Tres categorías quedan explícitamente excluidas: los números personales de los
empleados, las cuentas de prueba y **los números de la app WhatsApp Business**.
Esa última exclusión es la que detiene a la mayoría de los negocios pequeños: la
app verde que descargas en el teléfono **no califica**."*
https://redclawey.com/en/blog/whatsapp-business-verification-guide/

La ruta de **pago** es **Meta Verified for Business**, desde **$14,99/mes**.
https://redclawey.com/en/blog/whatsapp-business-verification-guide/

**Traducción:** la insignia **no es alcanzable gratis** con nuestro stack actual
(Baileys + número normal en la app). Exigiría migrar a la **API oficial de Meta**
—que además cobra por mensaje desde el 1-oct-2026— y, en la ruta gratuita, cumplir
30 días de plataforma + verificación de negocio. **No es una mejora de una tarde.**

### 3.5 Contexto de coste de la API oficial (para la decisión)

**Confirmado:** desde el **1 de octubre de 2026**, Meta **deja de regalar las
respuestas dentro de la ventana de 24 h**: *"los mensajes de servicio y los
mensajes de utilidad dentro de la ventana serán cobrados por mensaje"*. Hasta ahora
eran gratis.
https://blog.peppercloud.com/whatsapp-api-pricing-everything-you-need-to-know/

Esto **refuerza** la elección actual (Baileys/Evolution) para un negocio que no
quiere pagar, pero también significa que **el camino de pago se encarece, no se
abarata**. *(Nota: esta cifra proviene de un blog de un proveedor, no de la página
de precios de Meta, que no pude leer directamente. Tómese como indicio.)*

---

## 4. Recomendaciones priorizadas (más valor por menos esfuerzo)

### 🥇 1. Cerrar el bucle de confirmación — **la mejora más valiosa**

**Problema que resuelve:** hoy el recordatorio pide confirmar y nadie registra la
respuesta. El barbero no sabe quién viene.

**Cómo se haría (sin botones, porque v3.7 no los entrega):**
- **No** cambiar el motor de mensajes. Seguir con **texto plano**, que sí funciona.
- Añadir en el workflow del agente una **rama temprana** —antes del modelo, como el
  router del dueño— que detecte un mensaje de **una o dos palabras** (`SI`, `SÍ`,
  `NO`, `CONFIRMO`, `CONFIRMAR`, `CANCELAR`, `REPROGRAMAR`, `1`, `2`) **y** que ese
  `jid` tenga una cita en las próximas 48 horas.
- Esa rama debe consultar la cita y **actualizar el estado** (`confirmado` /
  `cancelado`) en `barber_citas`, y avisar al dueño.
- **Beneficio:** respuestas de confirmación **cuestan 0 tokens** (igual que `HOY`),
  el panel muestra la verdad y el barbero ve de un vistazo quién confirmó.
- **Esfuerzo:** bajo-medio. Es copiar el patrón del router existente. Tocar
  `Switch`/`IF` + un nodo Postgres + `verify.py`.
- **Coste:** **$0**. De hecho **ahorra** tokens.
- **Riesgo:** hay que **desambiguar** un "SÍ" que venga de una conversación normal,
  no de un recordatorio. La condición de "tiene cita en las próximas 48 h" lo
  resuelve casi siempre.

### 🥈 2. Usar la lista de espera que ya está construida y vacía

**Problema que resuelve:** una cancelación deja un hueco muerto que un barbero
solo **no puede rellenar**.

**Cómo se haría:** la tabla `barber_lista_espera` **ya existe con esquema
adecuado** (`jid`, `servicio`, `duracion_min`, `ventana_deseada`, `atendido`).
- Cuando el agente no tenga hueco, **ofrecer apuntarse** (INSERT).
- Cuando se cancele una cita, recorrer la lista en orden de antigüedad y **ofrecer
  el hueco al primero**.
- **Beneficio real y directo en dinero:** recuperar aunque sea 1 cita de $150–$300
  al mes ya paga el esfuerzo con holgura.
- **Esfuerzo:** medio. Es el flujo más "nuevo" de la lista.
- **Coste:** **$0**.
- **Cuidado:** el **primer cliente que responda** se queda el hueco; hay que evitar
  ofrecer el mismo hueco a varios a la vez sin control (la constraint anti-solape de
  `barber_citas` ayuda, pero el flujo debe manejarla).

### 🥉 3. Conectar las 58 FAQs de `barber_conocimiento` al agente

**Problema que resuelve:** el agente responde políticas "de memoria" (y puede
alucinar) cuando ya existe una tabla curada.

**Cómo se haría:** `ARQUITECTURA.md` documenta que la tabla y `barber_buscar`
existen y que **el agente todavía no las consulta**. Añadir esa consulta es una
herramienta más (`ai_tool`), y la búsqueda usa `spanish_unaccent` —gratis y nativa—
así que **no hace falta RAG ni embeddings** (que, recordemos, **no están
disponibles** en el proveedor actual).

**Beneficio:** respuestas consistentes sobre precios, políticas y horarios.
**Esfuerzo:** bajo. **Coste:** $0. *(Nota: 13 FAQs están marcadas como `propuesta`
y conviene que el dueño las confirme antes.)*

### 4. Aviso automático al dueño de huecos libres del día

**Problema que resuelve:** un barbero solo no ve los huecos del día sin mirar el
calendario. Un resumen a las 09:00 con "hoy tienes 2 huecos: 15:00 y 18:20" es
accionable.

**Cómo se haría:** un **Schedule Trigger** (gratis, nodo nativo) → leer Google
Calendar del día → formatear huecos → `sendText` al dueño.
Se parece mucho al workflow de vigilancia que ya existe (5 nodos).
**Esfuerzo:** bajo. **Coste:** $0.

### 5. Aviso de "cliente en riesgo" a T-1 h si no confirmó

Cuando el recordatorio de 1 h no obtuvo confirmación, avisar al barbero. Le permite
sobrevender el hueco. Es **consecuencia natural** del punto 1, no trabajo nuevo.

### 6. Reseñas post-servicio (más adelante)

- **Cómo:** cron T+2 h → `sendText` con el enlace de reseña de Google.
- **El enlace es gratis:** Google ofrece crear un enlace o QR de reseñas.
  https://support.google.com/business/answer/16816815?hl=en
- **Coste:** $0. **Esfuerzo:** bajo.
- **Por qué va más abajo:** es crecimiento a medio plazo, no arregla una fuga de
  dinero actual. Y dado que **el agente no detecta el fin del servicio** (no hay
  evento de "atendido"), hay que decidir de dónde sale el disparo.

### Sobre los botones interactivos: **el orden correcto es arreglar primero la base**

Tengo que ser explícito porque es contraintuitivo: **los botones interactivos
—botón "Confirmo"/"No puedo", listas, mensajes de plantilla— son una gran mejora de
UX, pero en este sistema NO se pueden entregar hoy.** El motivo está **confirmado**
en la sección 3.1: corre **v2.3.7** y en esa versión `sendButtons`/`sendList`
**devuelven 201 y no llegan nunca**.

La única vía de arreglarlo es **subir a v2.4.0+**, que a cambio **exige activación
de licencia** (gratuita, pero con registro de correo/teléfono y telemetría).
Y como el `Switch` de entrada **no reconoce** `buttonsResponseMessage` ni
`listResponseMessage` (conteo = 0), meter botones **sin** añadir esa rama haría que
**pulsar un botón no hiciera absolutamente nada** — peor que el texto plano actual.

**Orden recomendado:** (1) cerrar el bucle **en texto plano** — funciona hoy,
cuesta $0 y resuelve el negocio; (2) *después*, si se aprueba la subida a v2.4.0,
migrar a botones **y** añadir el manejo de `buttonsResponseMessage` en el mismo
trabajo. **Los botones son una optimización de UX, no el arreglo.**

---

## 5. Lo que NO hay que hacer

1. **No integrar los "agentes de IA de terceros" de WhatsApp.** Es una función del
   lado usuario, en beta cerrada por países, y **sin cifrado de extremo a extremo**.
   Expondría datos de clientes por un beneficio nulo. (Sección 2.1.)
2. **No intentar integrar Meta Muse.** No está en México, no tiene API para
   negocios y nuestra agenda vive en **localhost**. Perseguirlo es perder el tiempo.
3. **No cambiar el modelo a Cohere/Aleph Alpha.** Funciona técnicamente, no mejora
   nada perceptible y obliga a revalidar 44.506 caracteres de prompt.
4. **No adoptar RAG con embeddings.** Ya se descartó por imposible (el proveedor
   **no tiene endpoint de embeddings**, `/embeddings` → 404) y el Postgres local no
   tiene `pgvector`. La búsqueda de texto completo ya resuelve esto y es gratis.
5. **No poner botones interactivos antes de arreglar la base.** En v2.3.7 no se
   entregan; y sin manejar `buttonsResponseMessage`, pulsarlos no haría nada.
6. **No prometer la insignia verificada de WhatsApp.** Exige estar en la
   **WhatsApp Business Platform ≥30 días** y los números de la app WhatsApp
   Business **están excluidos**. La vía rápida es **Meta Verified, $14,99/mes**, que
   **viola la restricción de "solo gratis"**.
7. **No migrar a la API oficial de Meta sin consultar al dueño.** Es la **única**
   forma de tener botones nativos, cero riesgo de ban e insignia — pero es **de
   pago, exige tarjeta y desde el 1-oct-2026 cobra por mensaje**. Choca con tres
   restricciones a la vez. Es una **decisión del dueño**, no una mejora técnica.
8. **No añadir cobros por adelantado con pasarela** (Mercado Pago/Stripe).
   Requiere tarjeta y comisiones; el negocio cobra en efectivo o transferencia. Un
   depósito por **transferencia/SPEI sí es gratis**, pero exige verificación manual
   del pago por el barbero; para un ticket de $150–$300 **la fricción supera el
   beneficio**. *(Opinión razonada.)*
9. **No añadir tablas ni métricas "por barbero".** Restricción explícita del
   dueño: **un solo barbero**. Cualquier "ranking por barbero" sería la misma fila.
10. **No procesar audio ni imagen**, aunque un cliente mande una nota de voz.
    Restricción del dueño, ya implementada, y ahorra tokens.
11. **No creer que el titular equivale al hecho.** "20.000 millones" es
    **reportado**; el cierre **no está confirmado**; la fusión **está pendiente de
    aprobación regulatoria**. Este es exactamente el hábito que hay que mantener al
    vender.

---

## 6. Riesgo serio que debe conocerse antes de la venta

**El riesgo #1 de este sistema no es ninguna de las tres noticias: es el riesgo de
ban del número de WhatsApp.**

- **Confirmado:** la propia documentación del proyecto registra que *"un webhook
  n8n + Evolution API que se auto-disparó envió cientos de requests por segundo y
  terminó en **ban del número de WhatsApp**"* (`features-roadmap-research.md`).
- **Confirmado (fuente de terceros, con interés comercial):** un análisis de 600+
  cuentas de pymes afirma que **el 68% de los negocios que usan herramientas no
  oficiales reportan al menos un ban en 12 meses**, y que **Evolution API** —por ser
  un envoltorio REST sobre Baileys/whatsmeow— va marcado como riesgo **alto-crítico**.
  Es una fuente interesada (vende la alternativa oficial), así que **el 68% hay que
  tomarlo con pinzas**; lo que **no** es opinión es que Baileys **reingeniería** el
  protocolo de WhatsApp Web, lo cual **viola los términos de servicio** y es
  detección automatizada.
  https://blog.kraya-ai.com/whatsapp-automation-ban-risk
- **Implicación honesta para el cliente:** el canal por el que entra **todo** el
  negocio es un número de WhatsApp sobre una integración no oficial. **Si ese número
  cae, el negocio pierde su recepcionista.** Eso hay que decirlo en la venta, con la
  mitigación incluida (rate limiting por `jid`, debounce, y un plan B con el número
  personal). **No es un motivo para no vender; es un motivo para no**
  **prometer disponibilidad absoluta.**

Esto también explica por qué **no** conviene hacer experimentos con botones en el
número de producción: añadir superficie de riesgo sin beneficio probado.

---

## 7. Fuentes

### Noticia 1 — WhatsApp y agentes de terceros
- Beebom (artículo de partida): https://gadgets.beebom.com/news/whatsapp-testing-feature-to-add-third-party-ai-agents-to-chats
- WABetaInfo (fuente original, iOS): https://wabetainfo.com/whatsapp-is-rolling-out-chats-with-third-party-agents-on-ios/
- WABetaInfo (Android): https://wabetainfo.com/whatsapp-is-rolling-out-chats-with-third-party-agents/
- 9to5Mac: https://9to5mac.com/2026/09/07/whatsapp-will-soon-let-users-chat-with-up-to-five-third-party-ai-agents/

### Noticia 2 — Meta Muse
- CNN (artículo de partida): https://www.cnn.com/2026/09/23/tech/meta-muse-ai-agent
- Meta (anuncio oficial): https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/
- CBS News (descargas / Sensor Tower / Amazon bloquea): https://www.cbsnews.com/news/meta-ai-agent-muse-shopping/
- CNBC (precios $20/$100, contexto): https://www.cnbc.com/2026/09/08/meta-personal-ai-agents-public-reckoning-privacy-safety.html
- Disponibilidad solo EE. UU. (terceros): https://moclaw.ai/blog/meta-muse-not-available-in-your-country
- Reuters (lanzamiento): https://www.reuters.com/business/meta-launches-ai-agent-that-can-access-other-apps-send-emails-make-payments-2026-09-08/

### Noticia 3 — Cohere + Aleph Alpha
- SiliconANGLE (artículo de partida): https://siliconangle.com/2026/09/16/cohere-and-aleph-alpha-agree-to-merge-in-reported-20b-deal/
- Comunicado oficial (PR Newswire): https://www.prnewswire.com/news-releases/cohere-and-aleph-alpha-sign-agreement-to-become-the-first-transatlantic-sovereign-ai-solution-302880758.html
- Reuters (fusión, Schwarz, StackIT): https://www.reuters.com/legal/transactional/cohere-aleph-alpha-combine-target-enterprise-ai-market-2026-09-16/
- Reuters (anuncio de abril): https://www.reuters.com/legal/transactional/canadas-cohere-germanys-aleph-alpha-announce-merger-handelsblatt-reports-2026-04-24/

### Verificación técnica del sistema
- Evolution API v2.3.7 — versión detectada en vivo: `GET http://localhost:8080` (25-sep-2026)
- Instancia `hector` en estado `open`: `GET /instance/connectionState/hector`
- Issue del bug de botones/lists en v2.3.7: https://github.com/EvolutionAPI/evolution-api/issues/2390
- Issue ABIERTO "201 pero nunca se entrega": https://github.com/EvolutionAPI/evolution-api/issues/2404
- PR #2651 (arreglo) sin mergear: https://github.com/evolution-foundation/evolution-api/pull/2651
- Release v2.4.0 (arreglo + licencia obligatoria): https://github.com/evolution-foundation/evolution-api/releases/tag/2.4.0-rc1
- Documentación de licencia (gratuita, con telemetría): https://docs.evolutionfoundation.com.br/licensing
- Insignia verificada — requisitos de Meta: https://www.facebook.com/business/help/604726921052590
- Insignia — rutas gratuita y de pago: https://redclawey.com/en/blog/whatsapp-business-verification-guide/
- Cambio de precios de la API oficial (1-oct-2026): https://blog.peppercloud.com/whatsapp-api-pricing-everything-you-need-to-know/
- Riesgo de ban con herramientas no oficiales: https://blog.kraya-ai.com/whatsapp-automation-ban-risk
- Enlace de reseñas de Google: https://support.google.com/business/answer/16816815?hl=en

### Documentación interna del proyecto consultada
- `CONTEXTO-SUBAGENTES.md`, `ARQUITECTURA.md`, `features-roadmap-research.md`
- `BarberiaAgenteFLUJO-1-UNCENSORED.json`, `BarberiaAgenteFLUJO-2-RECORDATORIOS.json`
- `prompt-sistema-agente-barberia.txt` (44.506 caracteres)
- Postgres `barberia` (esquema y conteos de `barber_lista_espera`, `barber_citas`, etc.)

---

## 8. Qué NO pude confirmar (honestidad)

- **Si México está incluido** en los "países selectos" de la beta de agentes de
  terceros de WhatsApp. La fuente dice "países selectos" **sin listarlos**.
- **La fecha de cierre** de la fusión Cohere/Aleph Alpha. El comunicado oficial
  **no la fija**; el "fin de año" es prensa.
- **La cifra de $20.000 M** como hecho. El comunicado oficial **no la menciona**;
  el propio titular que la usa dice "reportado".
- **El fallo de botones observado en esta máquina.** No ejecuté un `sendButtons`
  real (habría enviado un mensaje a un número real, y la misión lo prohíbe).
  Lo confirmado es la **versión** y el **bug documentado en esa versión exacta**.
- **La página de precios oficial de Meta** no se pudo leer directamente; el cobro
  por mensaje desde el 1-oct-2026 viene de un blog de un proveedor.
- **El 68% de bans** proviene de una fuente con interés comercial en vender la
  alternativa oficial. No lo traté como dato duro.

---

## 9. Limpieza

**No se modificó nada.** No se crearon workflows, ni citas, ni filas en ninguna
tabla. **Los scripts de consulta fueron de solo lectura.** Únicamente se ejecutaron
`SELECT` e `information_schema` contra Postgres y `GET` contra Evolution API y n8n,
más lecturas de los JSON locales. El único archivo escrito es **este documento**.

> Nota de integridad: `barber_citas` contiene 209 filas con prefijo `verif-*` y
> `barber_clientes` 55 con prefijo `verif-*` que **ya existían** antes de este
> análisis (son datos de las suites de verificación, no míos). No las toqué.