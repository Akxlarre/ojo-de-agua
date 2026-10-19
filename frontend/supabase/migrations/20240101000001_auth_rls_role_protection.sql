-- spec:
--   tables_modified: [profiles]
--   columns_added: [display_name, avatar_url, role]
--   breaking: false
--   description: "Añade columnas requeridas por AuthFacade y bloquea auto-elevación de rol vía RLS."
-- /spec

-- Migration: auth_rls_role_protection
-- Idempotente: usa IF NOT EXISTS / IF EXISTS donde aplica.

-- 1. Añadir columnas que requiere AuthFacade / ProfilesRepository
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS display_name text,
  ADD COLUMN IF NOT EXISTS avatar_url   text,
  ADD COLUMN IF NOT EXISTS role         text NOT NULL DEFAULT 'member'
                             CHECK (role IN ('admin', 'member'));

-- 2. Eliminar la policy de UPDATE genérica (permite editar CUALQUIER columna incluyendo role)
--    SEC: sin esta restricción cualquier usuario autenticado puede auto-elevarse a 'admin'
--    enviando una petición PATCH directa al API de Supabase.
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;

-- 3. Policy de UPDATE segura: cada usuario puede editar su propio perfil
--    pero NUNCA la columna `role` (protegida solo para admin o service_role).
CREATE POLICY IF NOT EXISTS "profiles_update_own_safe"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (
    auth.uid() = id
    -- Previene auto-elevación: el role no puede cambiar a menos que sea el mismo valor
    AND role = (SELECT role FROM public.profiles WHERE id = auth.uid())
  );

-- 4. Policy: solo admins (vía service_role o función RPC) pueden cambiar roles
--    Los cambios de role de usuarios deben hacerse desde el backend con service_role key,
--    nunca desde el cliente con anon/user key.
CREATE POLICY IF NOT EXISTS "profiles_admin_update_role"
  ON public.profiles FOR UPDATE
  USING (
    -- Solo si la sesión tiene claim 'admin' (requiere custom JWT o trigger de Supabase)
    (auth.jwt() ->> 'user_role') = 'admin'
  )
  WITH CHECK (
    (auth.jwt() ->> 'user_role') = 'admin'
  );

-- 5. Policy de INSERT: trigger handle_new_user lo hace automáticamente.
--    Bloquear INSERT manual desde el cliente para evitar perfiles huérfanos.
CREATE POLICY IF NOT EXISTS "profiles_insert_via_trigger_only"
  ON public.profiles FOR INSERT
  WITH CHECK (false);  -- nunca desde el cliente; solo el trigger puede insertar

-- 6. Trigger: crear perfil automáticamente al registrar un nuevo usuario
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, display_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
    'member'   -- SIEMPRE 'member' al crear — nunca confiar en el cliente para el rol inicial
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
