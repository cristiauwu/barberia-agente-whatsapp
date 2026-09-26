-- Run manually as a trusted migration owner on the SAME Postgres used by W1.
-- This script never connects to a database; back up and inspect existing data first.
-- Requires existing barber_servicios with precio numeric and actualizado_en.
BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'barber_admin_price') THEN
    CREATE ROLE barber_admin_price LOGIN NOINHERIT;
  END IF;
END $$;
-- Set password out of band with psql \password barber_admin_price (never commit it).
ALTER ROLE barber_admin_price NOBYPASSRLS;
DO $$ BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO barber_admin_price', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO barber_admin_price;

ALTER TABLE public.barber_servicios
  ADD COLUMN IF NOT EXISTS precio_version bigint NOT NULL DEFAULT 1;

-- Preserve 0 as "ask for zone", never a free depilation quote, including W1 owner writes.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'barber_admin_depilacion_sentinel'
    AND conrelid = 'public.barber_servicios'::regclass) THEN
    ALTER TABLE public.barber_servicios ADD CONSTRAINT barber_admin_depilacion_sentinel
      CHECK (clave <> 'depilacion' OR precio = 0);
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.admin_precio_version_guard()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
  IF NEW.clave = 'depilacion' AND NEW.precio <> 0 THEN
    RAISE EXCEPTION 'Depilación requiere precio por zona';
  END IF;
  IF NEW.precio IS DISTINCT FROM OLD.precio THEN
    NEW.precio_version := OLD.precio_version + 1;
  ELSE
    NEW.precio_version := OLD.precio_version;
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS barber_admin_precio_version ON public.barber_servicios;
CREATE TRIGGER barber_admin_precio_version BEFORE UPDATE ON public.barber_servicios
FOR EACH ROW EXECUTE FUNCTION public.admin_precio_version_guard();

CREATE TABLE IF NOT EXISTS public.barber_admin_precio_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  request_id uuid NOT NULL UNIQUE,
  clave text NOT NULL,
  anterior numeric NOT NULL,
  nuevo numeric NOT NULL,
  version_anterior bigint NOT NULL,
  version_nueva bigint NOT NULL,
  actor text NOT NULL DEFAULT 'admin_web',
  cambiado_en timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON public.barber_admin_precio_audit FROM PUBLIC;
REVOKE ALL ON public.barber_servicios FROM barber_admin_price;

-- The function owner must own barber_servicios and audit, or have table permissions.
-- Lock down default PUBLIC EXECUTE atomically before COMMIT.
CREATE OR REPLACE FUNCTION public.admin_cambiar_precio(
  p_clave text, p_precio numeric, p_version bigint, p_request_id uuid
) RETURNS TABLE(precio numeric, version bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE old_price numeric; old_version bigint; new_version bigint;
BEGIN
  IF p_clave IS NULL OR p_clave = 'depilacion' OR p_precio IS NULL
     OR p_precio <= 0 OR p_precio > 999999.99
     OR scale(p_precio) > 2 OR p_version IS NULL OR p_version < 1
     OR p_request_id IS NULL THEN
    RAISE EXCEPTION 'Precio o servicio inválido';
  END IF;
  -- Row lock serializes concurrent updates, including W1 owner price commands.
  SELECT s.precio, s.precio_version INTO old_price, old_version
    FROM public.barber_servicios s WHERE s.clave = p_clave AND s.activo FOR UPDATE;
  IF NOT FOUND OR old_version <> p_version OR old_price = p_precio THEN
    RETURN;
  END IF;
  UPDATE public.barber_servicios s
    SET precio = p_precio, actualizado_en = now()
    WHERE s.clave = p_clave AND s.precio_version = p_version
    RETURNING s.precio_version INTO new_version;
  IF NOT FOUND THEN RETURN; END IF;
  INSERT INTO public.barber_admin_precio_audit
    (request_id, clave, anterior, nuevo, version_anterior, version_nueva)
    VALUES (p_request_id, p_clave, old_price, p_precio, old_version, new_version);
  precio := p_precio; version := new_version;
  RETURN NEXT;
END $$;
REVOKE ALL ON FUNCTION public.admin_cambiar_precio(text,numeric,bigint,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_cambiar_precio(text,numeric,bigint,uuid) TO barber_admin_price;
-- Abort instead of leaving an over-privileged role (e.g. via pre-existing PUBLIC grants).
DO $$ BEGIN
  IF has_table_privilege('barber_admin_price', 'public.barber_servicios', 'UPDATE')
     OR has_table_privilege('barber_admin_price', 'public.barber_servicios', 'INSERT')
     OR has_table_privilege('barber_admin_price', 'public.barber_servicios', 'DELETE')
     OR has_table_privilege('barber_admin_price', 'public.barber_clientes', 'SELECT')
     OR has_table_privilege('barber_admin_price', 'public.barber_citas', 'SELECT')
     OR has_table_privilege('barber_admin_price', 'public.barber_admin_precio_audit', 'SELECT') THEN
    RAISE EXCEPTION 'barber_admin_price has direct table access; remove PUBLIC/inherited grants first';
  END IF;
END $$;
COMMIT;
-- Operator: confirm price role cannot UPDATE tables or SELECT CRM; create separate
-- ADMIN_PRICE_DB_DSN for barber_admin_price and protect it outside the repository.
