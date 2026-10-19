---
paths:
  - "src/app/core/facades/**/*.ts"
  - "src/app/core/services/**/*.ts"
  - "src/app/features/**/*.ts"
---

# Reglas Arquitectónicas para Facades (`core/facades/`)

Este documento define la ley arquitectónica para la capa de Fachada (Facade) en el proyecto.
El Facade es el corazón del "Flujo de Datos" y la única forma permitida para que la UI obtenga datos.

## 1. Definición y Propósito
Un Facade es un Servicio de Angular (`@Injectable`) que actúa como el **único punto de entrada** para un "Dominio" o "Feature" (Ej: Productos, Usuarios, Dashboard).

Su responsabilidad doble y estricta es:
1. **Orquestar datos:** Inyecta Repositories (`core/repositories/`) para leer y escribir en Supabase. **NUNCA llama `.db.from()` directamente** — eso es responsabilidad exclusiva del Repository.
2. **Gestionar el Estado:** Mantiene en memoria el estado reactivo sincrónico usando `Signals` (a través de `BaseFacade<T>`).

```
UI  →  Facade  →  Repository  →  SupabaseService.client
```

## 2. Nomenclatura y Ubicación

| Tipo | Ruta canónica | Ejemplo |
|---|---|---|
| **Facade de dominio** | `core/facades/{domain}.facade.ts` | `productos.facade.ts` |
| **AuthFacade** (excepción) | `core/services/auth.facade.ts` | Gestiona sesión, no datos de dominio |
| **Service utilitario** | `core/services/{nombre}.service.ts` | `toast.service.ts`, `theme.service.ts` |

- El sufijo `.facade.ts` es obligatorio para todo archivo que extiende `BaseFacade<T>`.
- Los sufijos `.service.ts` se reservan para lógica utilitaria transversal sin estado de dominio.
- `AuthFacade` vive en `core/services/` como excepción documentada: gestiona sesión de usuario con ciclo de vida propio (`whenReady`, `onAuthStateChange`), no extiende `BaseFacade`.

## 3. Prohibiciones Absolutas en Componentes (UI)
Estas reglas definen el por qué existe el Facade:
- **NUNCA** inyectes `SupabaseService` dentro de un componente UI (`*.component.ts`).
- **NUNCA** hagas queries directas (`.from('tabla')`) dentro de un componente.
- **NUNCA** uses variables de estado sueltas ni RxJS puro (`BehaviorSubject`) en las pantallas; todo estado reactivo se expone y se consume mediante Signals (`signal()`, `computed()`) a través del Facade.

## 4. Estructura Interna Obligatoria de un Facade

**Todo Facade de dominio DEBE extender `BaseFacade<T>`** de `@core/facades/base.facade`.
`BaseFacade` provee el estado reactivo (`data`, `isLoading`, `error`, `hasData`), el patrón SWR
y el ciclo de vida (`initialize`, `refreshSilently`, `reset`, `dispose`) de forma consistente.

```typescript
import { Injectable, inject, computed } from '@angular/core';
import { BaseFacade } from '@core/facades/base.facade';
import { SupabaseService } from '@core/services/supabase.service';
import type { Producto } from '@core/models/producto.model';

@Injectable({ providedIn: 'root' })
export class ProductosFacade extends BaseFacade<Producto[]> {
  private supabase = inject(SupabaseService);

  // ── fetchData (contrato obligatorio) ──────────────────────────────────────
  protected override async fetchData(): Promise<Producto[]> {
    const { data, error } = await this.supabase.client
      .from('productos').select('*').order('created_at', { ascending: false });
    if (error) throw error;
    return data ?? [];
  }

  // ── Computed signals de dominio (opcionales) ──────────────────────────────
  readonly activos = computed(() => this.data()?.filter(p => p.activo) ?? []);

  // ── Mutaciones (ver swr-pattern.md para el template completo) ─────────────
  async crear(payload: Omit<Producto, 'id'>): Promise<boolean> { /* ... */ return true; }
  async actualizar(id: string, patch: Partial<Producto>): Promise<boolean> { /* ... */ return true; }
  async eliminar(id: string): Promise<boolean> { /* ... */ return true; }
}
```

**Excepción:** `AuthFacade` NO extiende `BaseFacade` porque gestiona sesión de usuario
(ciclo de vida distinto: `onAuthStateChange`, `whenReady`, etc.), no datos de dominio.

## 5. El Flujo de Trabajo (Mente-Máquina)
1. **Pregunta:** "Necesito traer datos de la Tabla X para mostrarlos o editarlos?"
2. **Acción 1:** Buscar en `indices/FACADES.md` si ya existe un `X.facade.ts`.
3. **Acción 2 (Si no existe):** Crear `<Dominio>Facade`. (Agregar la query y el signal privado/público).
4. **Acción 3:** Inyectar el `<Dominio>Facade` en el Smart Component.
5. **Acción 4:** Disparar un método del Facade (ej: `cargar()`) desde el `ngOnInit` (o constructor) y dejar que la UI se actualice sola por reactividad (vía `OnPush` y señales). Nunca esperar (await) la respuesta en la UI a menos que sea una acción bloqueante específica (ej. login).

## 6. Composición Cross-Domain (Multi-Facade)

Un Smart Component puede — y debe — inyectar **múltiples Facades** cuando necesita datos de varios dominios:

```typescript
// features/dashboard/dashboard.component.ts
@Component({ ... })
export class DashboardComponent {
  private products = inject(ProductsFacade);
  private users = inject(UsersFacade);
  private sales = inject(SalesFacade);

  // Composición local con computed — vive y muere con la página
  topSelling = computed(() =>
    calculateTopSelling(this.products.list(), this.sales.list())
  );
}
```

### Reglas de composición

| Escenario | Solución | Dónde vive |
|---|---|---|
| 1 página combina 2-3 Facades | `computed()` en el Smart Component | `features/` |
| Lógica de combinación se repite en 3+ páginas | Función pura reutilizable | `core/utils/` |
| Transformación DTO → UI de un solo dominio | `computed()` dentro del Facade | `core/facades/` |

### Prohibiciones

- **NUNCA** crear "Orchestrator Facades" ni Facades que inyectan otros Facades — esto introduce dependencias circulares y singletons permanentes innecesarios.
- **NUNCA** duplicar lógica de combinación en múltiples Smart Components. Si se repite, extraer a `core/utils/` como función pura.
- **NUNCA** poner lógica de negocio pesada (rankings, agregaciones, filtros complejos) dentro del `computed()` del Smart Component. Extraer a una función pura en `core/utils/` y llamarla desde el `computed()`.

### Ejemplo con función pura extraída

```typescript
// core/utils/sales.utils.ts
export function calculateTopSelling(
  products: Product[],
  sales: Sale[],
  limit = 10
): Product[] {
  const salesByProduct = new Map<string, number>();
  for (const sale of sales) {
    salesByProduct.set(sale.productId, (salesByProduct.get(sale.productId) ?? 0) + sale.amount);
  }
  return products
    .sort((a, b) => (salesByProduct.get(b.id) ?? 0) - (salesByProduct.get(a.id) ?? 0))
    .slice(0, limit);
}
```

```typescript
// features/dashboard/dashboard.component.ts
import { calculateTopSelling } from '@core/utils/sales.utils';

topSelling = computed(() =>
  calculateTopSelling(this.products.list(), this.sales.list())
);
```

> **Principio:** Los Facades gestionan dominios aislados. Los Smart Components componen. Las funciones puras calculan.

## 7. Transformación de Modelos (DTO -> UI Model)

El Facade es el **único lugar** donde se permite transformar un DTO de base de datos en un modelo de UI.

### Cuando transformar y cuando no

**Crea un UI Model y transforma en el Facade cuando:**
- Necesitas **combinar campos** (ej: `first_names` + `paternal_last_name` -> `name`)
- Necesitas **campos derivados** que no existen en la BD (ej: `initials`, `badgeColor`, `isExpired`)
- Los nombres de BD son confusos para la UI (`snake_case` -> `camelCase` descriptivo)
- Necesitas solo un subconjunto de campos relevantes para la vista

**Expone el DTO directamente cuando:**
- El DTO ya tiene exactamente los campos que la vista necesita
- Los nombres son claros y directamente utilizables en templates
- Crear un UI Model sería duplicar exactamente la misma estructura sin valor agregado

> **Regla de oro:** No crees modelos de UI por burocracia. El objetivo es claridad, no capas artificiales.
