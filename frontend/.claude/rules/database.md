---
paths:
  - "supabase/**"
  - "src/app/core/services/supabase*"
  - "src/app/core/services/*facade*"
  - "src/app/core/services/*service*"
---

# Reglas de Base de Datos (Supabase)

## Migraciones

- Todo DDL en `supabase/migrations/`
- Naming: `YYYYMMDDHHMMSS_<dominio>_<tipo>_<descripcion>.sql`
- **NUNCA** alterar la BD desde el Dashboard de Supabase manualmente
- Los scripts deben ser idempotentes (`CREATE TABLE IF NOT EXISTS`, etc.)

## Documentación obligatoria

- Toda tabla nueva → agregar en `indices/DATABASE.md`
- Incluir columnas clave y políticas RLS en la documentación

## RLS (Row Level Security)

- **SIEMPRE** activar RLS en tablas nuevas: `ALTER TABLE x ENABLE ROW LEVEL SECURITY;`
- Documentar cada policy: quién puede SELECT, INSERT, UPDATE, DELETE
- Usar funciones helper si hay lógica de ownership compleja

## Realtime

- Servicios con Supabase Realtime → usar RxJS `Observable`
- En la Facade → `toSignal()` para exponer al template
- Cancelar subscripciones en `ngOnDestroy`

## Tipos TypeScript desde Supabase (fuente de verdad)

- Ejecuta `npm run supabase:types` después de cada migración (requiere `supabase start`)
- El archivo `src/app/core/models/supabase.types.ts` es **AUTO-GENERADO** — no editar manualmente
- Las interfaces en `core/models/dto/` deben **extender** de `supabase.types.ts`, no redefinir campos
- El Architect Guard bloqueará ediciones manuales a `supabase.types.ts` (`ARCH-11`)

```typescript
// CORRECTO: extender desde tipos generados
import type { Database } from './supabase.types';
type ProfileRow = Database['public']['Tables']['profiles']['Row'];

export interface ProfileDto extends ProfileRow {
  // campos derivados adicionales aquí
}
```

## Spec Header obligatorio en migraciones

Toda migración nueva debe incluir un bloque spec al inicio del archivo:

```sql
-- spec:
--   tables_added: [nombre_tabla]
--   columns_added: [col1, col2, ...]
--   breaking: false
--   description: "Descripción breve"
-- /spec
```

## Patrón de query

```typescript
// CORRECTO: en un FacadeService o CoreService
const { data, error } = await this.supabase.client
  .from('tabla')
  .select('*')
  .order('created_at', { ascending: false });
```
