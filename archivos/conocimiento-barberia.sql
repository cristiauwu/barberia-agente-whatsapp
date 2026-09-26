-- ============================================================================
--  conocimiento-barberia.sql
--  Base de conocimiento (FAQs) del bot de WhatsApp de Barber Chinos.
--  Motor: BUSQUEDA DE TEXTO COMPLETO nativa de PostgreSQL.
--         Gratis, sin APIs externas, sin dependencias, sin modelos de embedding.
--
--  IDEMPOTENTE: se puede ejecutar tantas veces como haga falta.
--  No borra datos: hace UPSERT por `pregunta`.
--
--  DATOS REALES del sistema en produccion (verificados, no inventados):
--    Negocio  : Barber Chinos - Peluqueria & Barberia
--    Direccion: Calle Pinzon #574
--    Telefono : 452-281-8144
--    Horario  : lunes a sabado 10:00-20:00 / domingo CERRADO
--    Regla    : la ultima cita debe TERMINAR antes de las 20:00
--    Barbero  : UNO SOLO, Esteban Aguilera
--    Zona     : America/Mexico_City, offset fijo -06:00 (sin DST)
--    Servicios: los 8 de la tabla barber_servicios:
--               corte 150/40min  barba 100/20min  ceja 30/10min
--               mascarilla 50/20min  dama 250/50min  planchado 150/30min
--               peinado 300/45min  depilacion (segun zona)/30min
--
--  La columna `origen` distingue el nivel de certeza de cada respuesta:
--    'contexto'  -> derivada de datos REALES ya presentes en el sistema.
--    'propuesta' -> politica plausible que el dueno TODAVIA debe confirmar.
--                   Se marca a proposito: no se presenta como hecho probado.
-- ============================================================================


-- ---------------------------------------------------------------------------
-- 0) Requisitos: extension unaccent + configuracion de texto en espanol
-- ---------------------------------------------------------------------------
-- Sin esto, "depilacion" NO encuentra "depilación" y viceversa.
-- Comprobado en este Postgres:
--     to_tsvector('spanish','depilación') @@ to_tsquery('spanish','depilacion')
--     => false
-- Con la configuracion de abajo => true en ambos sentidos.

CREATE EXTENSION IF NOT EXISTS unaccent;

DO $do$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_ts_config c
    JOIN pg_namespace n ON n.oid = c.cfgnamespace
    WHERE c.cfgname = 'spanish_unaccent' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE TEXT SEARCH CONFIGURATION public.spanish_unaccent (COPY = pg_catalog.spanish)';
    -- unaccent PRIMERO (quita acentos), spanish_stem DESPUES (raiz: cancelar->cancel).
    -- El orden importa: al reves, el stemmer recibe la palabra con acento.
    EXECUTE 'ALTER TEXT SEARCH CONFIGURATION public.spanish_unaccent '
         || 'ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem';
  END IF;
END
$do$;


-- ---------------------------------------------------------------------------
-- 1) Tabla de conocimiento
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.barber_conocimiento (
  id             serial       PRIMARY KEY,
  pregunta       text         NOT NULL,
  respuesta      text         NOT NULL,
  categoria      text         NOT NULL DEFAULT 'general',
  sinonimos      text         NOT NULL DEFAULT '',
  prioridad      integer      NOT NULL DEFAULT 0,
  activo         boolean      NOT NULL DEFAULT true,
  origen         text         NOT NULL DEFAULT 'contexto',
  creado_en      timestamptz  NOT NULL DEFAULT now(),
  actualizado_en timestamptz  NOT NULL DEFAULT now(),

  -- Clave natural: es lo que hace el seed idempotente (ON CONFLICT).
  CONSTRAINT barber_conocimiento_pregunta_uk UNIQUE (pregunta),
  CONSTRAINT barber_conocimiento_origen_ck
    CHECK (origen IN ('contexto', 'propuesta')),

  -- Columna tsvector GENERADA y almacenada: no hay que mantenerla a mano,
  -- PostgreSQL la recalcula sola en cada INSERT/UPDATE.
  -- PESOS (ajustados con pruebas reales, ver RAG-EVALUACION.md):
  --   A = la PREGUNTA y los SINONIMOS (como lo dice el cliente)
  --   B = la CATEGORIA
  --   C = el cuerpo de la RESPUESTA
  --
  -- Se probo tambien pregunta=A, sinonimos=B y Empeoraba: cuando el cliente
  -- usa un alias ("carro" por "estacionamiento", o "abren" por "horario"),
  -- la coincidencia por sinonimo vale menos que una palabra generica de otra
  -- pregunta. Con los sinonimos en A, el alias pesa igual que el titulo y
  -- acierta. Los sinonimos se curan a mano precisamente para eso.
  tsv tsvector GENERATED ALWAYS AS (
      setweight(to_tsvector('public.spanish_unaccent', coalesce(pregunta, '')),   'A')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(sinonimos, '')),  'A')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(categoria, '')),  'B')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(respuesta, '')),  'C')
  ) STORED
);

-- Indice GIN sobre el tsvector: esto es lo que hace la busqueda instantanea.
-- (Se crea despues de la migracion de pesos de la seccion 1b.)
CREATE INDEX IF NOT EXISTS barber_conocimiento_categoria_ix
  ON public.barber_conocimiento (categoria) WHERE activo;


-- ---------------------------------------------------------------------------
-- 1b) Pesos del tsvector (version definitiva)
-- ---------------------------------------------------------------------------
-- `CREATE TABLE IF NOT EXISTS` NO cambia la definicion de una tabla que ya
-- existe. Si la tabla se creo con una version anterior de los pesos, hay que
-- regenerar la columna generada.
--
-- Como `tsv` es una columna GENERADA, contiene solo informacion derivada de
-- las otras columnas: se puede borrar y volver a crear sin perder ningun dato
-- (PostgreSQL la recalcula). Asi el script siempre deja los pesos correctos y
-- sigue siendo idempotente.
DROP INDEX IF EXISTS public.barber_conocimiento_tsv_gin;
ALTER TABLE public.barber_conocimiento DROP COLUMN IF EXISTS tsv;
ALTER TABLE public.barber_conocimiento ADD COLUMN tsv tsvector
  GENERATED ALWAYS AS (
      setweight(to_tsvector('public.spanish_unaccent', coalesce(pregunta, '')),   'A')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(sinonimos, '')),  'A')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(categoria, '')),  'B')
   || setweight(to_tsvector('public.spanish_unaccent', coalesce(respuesta, '')),  'C')
  ) STORED;

-- Indice GIN sobre el tsvector: esto es lo que hace la busqueda instantanea.
CREATE INDEX IF NOT EXISTS barber_conocimiento_tsv_gin
  ON public.barber_conocimiento USING gin (tsv);


-- ---------------------------------------------------------------------------
-- 2) Funcion de busqueda
-- ---------------------------------------------------------------------------
-- Estrategia:
--   - La frase del cliente se convierte en un tsquery OR (cualquiera de sus
--     palabras significativas). Se usa OR y no AND porque una frase natural
--     lleva relleno ("hola, oye, tienen estacionamiento?") y con AND se
--     perderia la coincidencia.
--   - Se ordena por ts_rank, que respeta los pesos A/B de la columna tsv.
--   - Se descartan los lexemas de menos de 3 caracteres (restos de "a", "e",
--     "o"... que el stemmer espanol deja pasar). Si no quedan palabras utiles,
--     devuelve vacio (nunca error, nunca excepcion).
CREATE OR REPLACE FUNCTION public.barber_buscar_conocimiento(
  p_consulta text,
  p_limite   integer DEFAULT 3
)
RETURNS TABLE (
  id            integer,
  pregunta      text,
  respuesta     text,
  categoria     text,
  origen        text,
  rank          real,
  coincidencias text
)
LANGUAGE plpgsql STABLE
AS $fn$
DECLARE
  v_orq text;
BEGIN
  -- Normaliza la consulta a un tsquery OR con la config sin acentos,
  -- descartando lexemas de menos de 3 caracteres (ruido: "a", "e", "o"...).
  SELECT array_to_string(
           ARRAY(
             SELECT lex
             FROM unnest(
                    tsvector_to_array(
                      to_tsvector('public.spanish_unaccent', coalesce(p_consulta, ''))
                    )
                  ) AS lex
             WHERE length(lex) >= 3
           ),
           ' | '
         )
    INTO v_orq;

  IF v_orq IS NULL OR v_orq = '' THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT c.id,
         c.pregunta,
         c.respuesta,
         c.categoria,
         c.origen,
         ts_rank(c.tsv, to_tsquery('public.spanish_unaccent', v_orq)) AS rank,
         v_orq AS coincidencias
  FROM public.barber_conocimiento c
  WHERE c.activo
    AND c.tsv @@ to_tsquery('public.spanish_unaccent', v_orq)
  ORDER BY rank DESC, c.prioridad DESC, c.id ASC
  LIMIT greatest(1, least(coalesce(p_limite, 3), 20));
END
$fn$;

COMMENT ON FUNCTION public.barber_buscar_conocimiento(text, integer) IS
  'Busca FAQs por texto libre en espanol. Devuelve las mejores coincidencias ordenadas por relevancia.';


-- ---------------------------------------------------------------------------
-- 3) Semilla de FAQs (UPSERT idempotente: re-ejecutable sin duplicar)
-- ---------------------------------------------------------------------------
INSERT INTO public.barber_conocimiento
  (pregunta, respuesta, categoria, sinonimos, prioridad, origen)
VALUES

-- ---- UBICACION E INSTALACIONES -------------------------------------------
('¿Dónde están ubicados?',
 'Estamos en *Calle Pinzón #574*. Ahí mismo te atendemos. Si tienes duda para llegar, márcanos al *452-281-8144*.',
 'ubicacion', 'direccion domicilio donde queda ubicacion llegar como llego mapa', 10, 'contexto'),

('¿Cuál es el teléfono?',
 'El teléfono del local es *452-281-8144*. También puedes seguir por aquí, que contestamos igual.',
 'ubicacion', 'telefono numero marcar llamar contacto comunicarse', 10, 'contexto'),

('¿Tienen estacionamiento?',
 'No tenemos estacionamiento propio. Hay lugar para dejar el coche sobre la misma calle, junto al local. Si vienes en hora pico, llega con unos minutos de anticipación.',
 'instalaciones', 'estacionamiento parking coche carro auto lugar donde dejo mi carro', 10, 'propuesta'),

('¿Se puede pasar sin cita?',
 'Sí, puedes llegar directo. Pero como atiende *una sola persona*, si vienes sin cita puede que esperes. Lo más seguro es apartar tu lugar por aquí.',
 'citas', 'sin cita walk in directo llegar sin apartar espontaneo turno', 5, 'contexto'),

('¿Aceptan niños?',
 '¡Claro! Puedes traer a tu hijo a cortarse el cabello. Se atiende igual que a cualquier cliente.',
 'instalaciones', 'ninos infantil hijos pequenos edad menor bebe', 0, 'propuesta'),

-- ---- HORARIOS -------------------------------------------------------------
('¿Cuál es el horario?',
 'Abrimos de *lunes a sábado de 10:00 a 20:00*. El domingo estamos cerrados.',
 'horarios', 'horario abren cierran abierto cerrado a que hora atienden', 10, 'contexto'),

('¿Abren el domingo?',
 'No, el domingo estamos cerrados. Atendemos de lunes a sábado de 10:00 a 20:00.',
 'horarios', 'domingo cerrado abierto domingos fin de semana', 10, 'contexto'),

('¿Hasta qué hora puedo agendar?',
 'Puedes agendar hasta que el servicio *termine* antes de las 20:00. Por ejemplo, un corte de 40 minutos a las 19:00 todavía alcanza; a las 19:30 ya no.',
 'horarios', 'ultima cita hora limite hasta que hora tarde ultimo turno cierre', 10, 'contexto'),

('¿Atienden en días festivos?',
 'Los días festivos trabajamos en horario normal si cae de lunes a sábado. Si el encargado cierra ese día, aquí te lo confirmamos al agendar.',
 'horarios', 'festivo feriado puente asueto dia de descanso', 0, 'propuesta'),

-- ---- SERVICIOS ------------------------------------------------------------
('¿Qué servicios tienen?',
 'Corte desvanecido o tijera $150, arreglo de barba $100, ceja $30, mascarilla $50, corte de cabello dama $250, planchado express $150, peinado $300 y depilación. ¿Cuál te aparto?',
 'servicios', 'servicios catalogo que hacen que ofrecen menu carta', 10, 'contexto'),

('¿Hacen corte para dama?',
 'Sí, el corte de cabello dama cuesta *$250* y dura 50 minutos.',
 'servicios', 'dama mujer femenino corte de dama senora', 10, 'contexto'),

('¿Arreglan la barba?',
 'Sí, el arreglo de barba cuesta *$100* y dura 20 minutos.',
 'servicios', 'barba afeitar rasurar bigote perfilado', 10, 'contexto'),

('¿Hacen las cejas?',
 'Sí, la ceja cuesta *$30* y toma unos 10 minutos.',
 'servicios', 'ceja cejas perfilado de ceja', 10, 'contexto'),

('¿Qué es la mascarilla?',
 'Es un tratamiento de *$50* que dura 20 minutos. Va muy bien para la piel después del corte.',
 'servicios', 'mascarilla facial tratamiento cara piel limpieza', 5, 'contexto'),

('¿Hacen planchado?',
 'Sí, el planchado express cuesta *$150* y dura 30 minutos.',
 'servicios', 'planchado plancha alaciado liso alisar', 10, 'contexto'),

('¿Hacen peinado?',
 'Sí, el peinado cuesta *$300* y dura 45 minutos. Es el servicio más completo para una ocasión especial.',
 'servicios', 'peinado peinar evento boda fiesta especial novia', 10, 'contexto'),

('¿Cuánto cuesta la depilación?',
 'La depilación dura 30 minutos y el precio depende de la zona. Dime qué zona quieres y con gusto te lo confirmo.',
 'servicios', 'depilacion cera depilar vello zona', 15, 'contexto'),

('¿Hacen tintes o color?',
 'Ese servicio no lo tenemos en el catálogo. Déjame preguntarle al encargado y te confirmo en un momento.',
 'servicios', 'tinte tintes tenido teñir color pintar pintado canas mechas decoloracion rubio negro cabello', 5, 'contexto'),

('¿Trabajan con máquina o navaja?',
 'Sí, el corte desvanecido o tijera cubre esos estilos y cuesta *$150*. Dime qué estilo buscas y te digo si te lo podemos hacer.',
 'servicios', 'maquina navaja desvanecido fade rasurado', 5, 'contexto'),

('¿Hacen corte para niño?',
 'Sí, se hace con el mismo corte desvanecido o tijera de *$150*. Para los más chicos suele ser más rápido.',
 'servicios', 'nino bebe infantil escolar corte de nino', 5, 'propuesta'),

('¿Tienen un corte llamado "mod cut" o "corte clásico"?',
 'Esos nombres no están en nuestro catálogo. Lo que sí manejamos es el corte desvanecido o tijera de *$150*. Platícame qué estilo quieres y te digo si te lo podemos hacer.',
 'servicios', 'mod cut corte clasico corte laser buzz cut crew cut taper estilos nombres', 10, 'contexto'),

('¿Qué me recomiendan si es mi primera vez?',
 'El más pedido es el *corte desvanecido o tijera*, $150. Queda bien con casi cualquier tipo de cabello y dura 40 minutos.',
 'servicios', 'recomiendas recomiendan mejor corte primera vez cual me queda sugerencia', 10, 'contexto'),

-- ---- PRECIOS --------------------------------------------------------------
('¿Cuánto cuesta el corte?',
 'El corte desvanecido o tijera cuesta *$150* y dura 40 minutos.',
 'precios', 'cuanto cuesta el corte precio corte de pelo cuanto sale vale', 15, 'contexto'),

('¿Cuánto cuesta el corte de dama?',
 'El corte de cabello dama cuesta *$250* y dura 50 minutos.',
 'precios', 'precio corte dama mujer cuanto cuesta dama', 15, 'contexto'),

('¿Me dan la lista de precios completa?',
 'Corte desvanecido o tijera $150, barba $100, ceja $30, mascarilla $50, corte de dama $250, planchado express $150, peinado $300. La depilación depende de la zona. ¿Cuál te aparto?',
 'precios', 'lista de precios tarifas cuanto cuestan todos costos precios', 10, 'contexto'),

('¿Cuánto cuesta la barba?',
 'El arreglo de barba cuesta *$100* y dura 20 minutos.',
 'precios', 'precio barba cuanto cuesta barba', 15, 'contexto'),

('¿Cuánto cuesta la ceja?',
 'La ceja cuesta *$30* y dura unos 10 minutos.',
 'precios', 'precio ceja cuanto cuesta ceja', 15, 'contexto'),

-- ---- PAGOS ----------------------------------------------------------------
('¿Hacen descuento?',
 'Déjame preguntarle al encargado y te confirmo en un momento.',
 'pagos', 'descuento rebaja promocion oferta barato mas economico precio especial', 10, 'contexto'),

('¿Cobran menos si me hago varios servicios juntos?',
 'Déjame consultarlo con el encargado y te digo en un momento.',
 'pagos', 'varios servicios juntos combo paquete precio especial descuento', 10, 'contexto'),

('¿Aceptan tarjeta?',
 'El pago se hace directo en el local. Si necesitas confirmar un método de pago en particular, el encargado te lo dice al llegar.',
 'pagos', 'tarjeta credito debito pago efectivo terminal cobrar forma de pago', 10, 'propuesta'),

('¿Puedo pagar con transferencia?',
 'El pago se hace directo en el local. Si necesitas confirmar un método en particular, el encargado te lo dice al llegar.',
 'pagos', 'transferencia deposito spei banco pago electronico', 5, 'propuesta'),

-- ---- CITAS ----------------------------------------------------------------
('¿Cómo agendo una cita?',
 'Dime qué servicio quieres, qué día y a qué hora, y yo te la aparto aquí mismo.',
 'citas', 'agendar apartar reservar cita como hago para una cita', 10, 'contexto'),

('¿Necesito dar mis datos para la cita?',
 'Solo tu *nombre* y el número de WhatsApp desde el que escribes. No necesitas crear cuenta ni nada más.',
 'citas', 'datos datos personales registro cuenta nombre telefono', 5, 'contexto'),

('¿Cuánto tiempo antes debo llegar?',
 'Con llegar unos 5 minutos antes es suficiente. Si vas a llegar tarde, avísanos por aquí.',
 'citas', 'llegar antes anticipacion cuanto tiempo antes puntualidad', 5, 'propuesta'),

('¿Puedo apartar varias citas a la vez?',
 'Sí, dime los servicios y los horarios que quieres y te los aparto. Si son muchos, mejor los vemos uno por uno para no equivocarnos.',
 'citas', 'varias citas dos citas acompanante amigo familia juntos', 0, 'propuesta'),

('¿Con cuánta anticipación puedo agendar?',
 'Puedes agendar para cualquier día a partir de hoy. Si quieres una fecha muy lejana, dime el día exacto y la reviso.',
 'citas', 'anticipacion dias de antelacion hasta cuando puedo agendar futuro', 5, 'contexto'),

('¿Atienden a domicilio?',
 'No, la atención es solamente en el local, en Calle Pinzón #574.',
 'citas', 'domicilio a domicilio ir a mi casa servicio a domicilio movil', 5, 'contexto'),

-- ---- POLITICAS ------------------------------------------------------------
('¿Puedo cancelar mi cita?',
 'Sí. Avísame aquí y la cancelo. Lo único que pedimos es que nos avises con la mayor anticipación posible, para que ese lugar lo aproveche alguien más.',
 'politicas', 'cancelar cancelacion anular quitar cita ya no puedo ir', 15, 'contexto'),

('¿Puedo cambiar mi cita de día u hora?',
 'Sí, sin problema. Dime para qué día y hora la quieres mover y yo la reprogramo. Te confirmo si el nuevo horario está libre.',
 'politicas', 'reprogramar cambiar mover reagendar otra fecha posponer', 15, 'contexto'),

('¿Qué pasa si llego tarde?',
 'Te esperamos. Si te retrasas más de 15 minutos puede que se atienda a alguien más primero, así que avísanos por aquí si vas a llegar tarde.',
 'politicas', 'tarde llegar tarde retraso demora minutos', 5, 'propuesta'),

('¿Cobran si no llego a mi cita?',
 'No cobramos por no llegar. Solo te pedimos que nos avises para liberar el lugar.',
 'politicas', 'no show no llegue cobran penalizacion falta castigo', 5, 'propuesta'),

('¿Cuál es la política de cancelación?',
 'Puedes cancelar o mover tu cita cuando quieras, avisándonos por aquí. No hay penalización; solo te pedimos avisar con anticipación.',
 'politicas', 'politica de cancelacion reglas cancelar condiciones', 10, 'propuesta'),

('¿Hay garantía si no me gusta el corte?',
 'Déjame preguntarle al encargado y te confirmo en un momento.',
 'politicas', 'garantia no me gusto quedo mal reclamacion devolucion arreglo', 5, 'contexto'),

('¿Necesito cita para la ceja o la barba?',
 'No es obligatorio, pero son servicios cortos de 10 y 20 minutos. Si vienes sin cita puede que te toque esperar. Apartar tu lugar por aquí te asegura la hora.',
 'citas', 'ceja barba cita necesito cita servicio corto rapido', 5, 'contexto'),

-- ---- BARBERO --------------------------------------------------------------
('¿Quién me va a atender?',
 'Te atiende *Esteban Aguilera*. Es quien lleva la barbería.',
 'barbero', 'quien atiende barbero estilista peluquero nombre del barbero', 10, 'contexto'),

('¿Puedo elegir a otro barbero?',
 'No, en la barbería atiende *una sola persona*, Esteban Aguilera. No hay otros barberos.',
 'barbero', 'otro barbero elegir barbero diferentes barberos equipo', 10, 'contexto'),

('¿Tienen experiencia cortando este tipo de cabello?',
 'Sí, Esteban tiene experiencia con distintos tipos de cabello. Platícame qué buscas y te dice si te lo puede hacer.',
 'barbero', 'experiencia sabe cortar especialidad capacitado tipo de cabello', 0, 'propuesta'),

-- ---- GENERAL / FUERA DE ALCANCE ------------------------------------------
('¿Dan factura?',
 'Déjame preguntarle al encargado y te confirmo en un momento.',
 'general', 'factura comprobante fiscal rfc recibo', 5, 'contexto'),

('¿Venden productos para el cabello?',
 'Por ahora lo que ofrecemos son los servicios de la barbería. Si te interesa algún producto en específico, pregúntale al encargado al llegar.',
 'general', 'productos venden shampoo cera pomada gel venta', 0, 'contexto'),

('¿Puedo dejar una propuesta o una queja?',
 'Claro, cuéntame y se lo paso al encargado ahora mismo. Él te escribe en un momento.',
 'general', 'queja reclamo sugerencia propuesta comentario opinion', 5, 'contexto'),

('¿Tienen redes sociales?',
 'Déjame preguntarle al encargado y te confirmo en un momento.',
 'general', 'instagram facebook redes sociales tiktok pagina', 0, 'contexto'),

('¿Puedo dejar reservado para una boda o un evento?',
 'Déjame consultarlo con el encargado, porque depende del día y de cuántas personas sean. Te confirmo en un momento.',
 'general', 'boda evento grupo xv anos graduacion muchos invitados', 5, 'contexto')

-- Si la pregunta ya existia, solo se actualiza la respuesta.
ON CONFLICT (pregunta) DO UPDATE
  SET respuesta      = EXCLUDED.respuesta,
      categoria      = EXCLUDED.categoria,
      sinonimos      = EXCLUDED.sinonimos,
      prioridad      = EXCLUDED.prioridad,
      origen         = EXCLUDED.origen,
      activo         = true,
      actualizado_en = now();


-- ---------------------------------------------------------------------------
-- 4) Comprobacion rapida (opcional)
-- ---------------------------------------------------------------------------
-- SELECT categoria, count(*) FROM public.barber_conocimiento
--  GROUP BY 1 ORDER BY 2 DESC;
--
-- SELECT id, categoria, rank::numeric(6,4), pregunta
--   FROM public.barber_buscar_conocimiento('tienen estacionamiento?', 3);


-- ============================================================================
--  INSTRUCCIONES PARA REPLICARLO EN SUPABASE
-- ============================================================================
--
--  IMPORTANTE: con las `publishable` keys NO se puede hacer DDL ni escribir.
--  Son claves de cliente. El DDL va en el SQL Editor del dashboard.
--
--  1) Entra a https://supabase.com/dashboard  y abre el proyecto
--     `zucgrcyzofelmiorvxhb`.
--  2) Menu lateral -> *SQL Editor* -> *New query*.
--  3) Pega el bloque de abajo (es el mismo esquema de arriba, ya adaptado:
--     Supabase ya trae `unaccent` y no hace falta tocar permisos).
--  4) Pulsa *Run*. Debe terminar sin errores.
--  5) Verifica con:
--         SELECT count(*) FROM public.barber_conocimiento;
--         SELECT * FROM public.barber_buscar_conocimiento('tienen estacionamiento?');
--
--  ---------- BLOQUE PARA PEGAR EN SUPABASE ----------
--
--  CREATE EXTENSION IF NOT EXISTS unaccent;
--
--  DO $do$
--  BEGIN
--    IF NOT EXISTS (SELECT 1 FROM pg_ts_config c
--                   JOIN pg_namespace n ON n.oid = c.cfgnamespace
--                   WHERE c.cfgname = 'spanish_unaccent' AND n.nspname = 'public') THEN
--      EXECUTE 'CREATE TEXT SEARCH CONFIGURATION public.spanish_unaccent (COPY = pg_catalog.spanish)';
--      EXECUTE 'ALTER TEXT SEARCH CONFIGURATION public.spanish_unaccent '
--           || 'ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem';
--    END IF;
--  END
--  $do$;
--
--  (y a continuacion, tal cual, la seccion 1) CREATE TABLE, la seccion 2)
--   CREATE FUNCTION y la seccion 3) INSERT ... ON CONFLICT de este archivo)
--
--  ---------- CONSULTAR DESDE n8n ----------
--    Nodo  : Postgres / Execute Query   (credencial `NUrqrDWN8OsBFmgV`,
--            la misma que ya usa el workflow)
--    Query : SELECT * FROM public.barber_buscar_conocimiento($1, 3)
--    Param : la pregunta del cliente
--
--  ---------- EXPONER POR REST (PostgREST) ----------
--    GRANT EXECUTE ON FUNCTION public.barber_buscar_conocimiento(text, integer)
--      TO anon, authenticated;
--    -- luego: POST /rest/v1/rpc/barber_buscar_conocimiento
--    --        {"p_consulta": "tienen estacionamiento?", "p_limite": 3}
-- ============================================================================