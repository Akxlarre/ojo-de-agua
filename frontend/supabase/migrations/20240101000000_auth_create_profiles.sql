-- spec:
--   tables_added: [profiles]
--   columns_added: [id, household_id, email, role_id, created_at]
--   breaking: false
--   description: "Tabla base de usuarios sincronizada con auth.users. RLS habilitado."
-- /spec

-- Migration: auth_create_profiles
-- Idempotente: usa IF NOT EXISTS para poder re-ejecutar sin errores

CREATE TABLE IF NOT EXISTS public.profiles (
  id          uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  household_id uuid,
  email       text,
  role_id     int         DEFAULT 1,
  created_at  timestamptz DEFAULT now()
);

-- RLS: obligatorio en toda tabla nueva
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Policy: cualquier usuario autenticado puede leer perfiles
CREATE POLICY IF NOT EXISTS "profiles_select_public"
  ON public.profiles FOR SELECT
  USING (auth.role() = 'authenticated');

-- Policy: cada usuario solo puede actualizar su propio perfil
CREATE POLICY IF NOT EXISTS "profiles_update_own"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);
