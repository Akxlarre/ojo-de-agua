# Reglas del Tech Stack (Angular v20+, Supabase, Tailwind v4, GSAP)

> **Importante para Agentes:** NUNCA rompas estas reglas de arquitectura.

## ARCH (Deep links del linter)

<a id="arch-01"></a>
### ARCH-01: No Supabase in UI
- Prohibido importar `@supabase/supabase-js` en `src/app/features/**` y `src/app/shared/**`.
- Solución: mover acceso a datos a un `*FacadeService` (o services core) y exponer estado por Signals.

<a id="arch-02"></a>
### ARCH-02: Facade-only injection (en componentes vista)
- Prohibido inyectar `*Service` directo en `*.component.ts` de `features/` y `shared/` (excepto servicios de infraestructura explícitos).
- Solución: inyecta un `*FacadeService` y deja los services internos en `core/`.

<a id="arch-03"></a>
### ARCH-03: TDD required (core)
- Todo `*.facade.ts` y `*.service.ts` en `src/app/core/**` debe tener su `*.spec.ts`.

<a id="arch-04"></a>
### ARCH-04: OnPush required
- Todo componente debe usar `ChangeDetectionStrategy.OnPush`.

<a id="arch-05"></a>
### ARCH-05: No `@angular/animations`
- Prohibido importar `@angular/animations*`.
- Solución: usar **GSAP** vía `GsapAnimationsService`.

<a id="arch-06"></a>
### ARCH-06: No legacy template directives
- Prohibido `*ngIf`, `*ngFor`, `[ngClass]`, `[ngStyle]`.
- Solución: `@if/@for` y bindings directos `[class.x]`, `[style.prop]`.

<a id="arch-07"></a>
### ARCH-07: No `@keyframes` en estilos de app
- Prohibido `@keyframes` en estilos dentro de `src/app/**`.
- Solución: usar GSAP.

<a id="arch-08"></a>
### ARCH-08: No hardcoded Tailwind colors
- Prohibido `text-red-500`, `bg-blue-200`, etc. en `.ts` y `.html`.
- Solución: tokens semánticos (`text-primary`, `text-muted`, `bg-surface`, `bg-base`, `var(--ds-brand)`).

<a id="arch-09"></a>
### ARCH-09: Complexity warning (shared components)
- Warning si un `shared/**/*.component.ts` tiene una clase muy grande (recomendación: \(\le 200\) líneas de clase).
- Solución: dividir en subcomponentes, extraer helpers y mantener `shared/` como UI presentacional.

<a id="arch-10"></a>
### ARCH-10: Complexity warning (facades)
- Warning si un `*.facade.ts` es demasiado complejo (recomendación: \(\le 5\) `inject()` y métodos \(\le 50\) líneas).
- Solución: extraer lógica a services/helpers y mantener la Facade como orquestador de estado/errores.

## 1. Patrones de Diseño Arquitectónico Obligatorios

### A. Patrón Facade Estricto
- **NUNCA** inyectes `SupabaseService`, `HttpClient`, o referencias directas a bases de datos en los Componentes UI (`*.component.ts`).
- **SIEMPRE** usa un Patrón Facade: La UI llama a un `*FacadeService` y éste delega en la red. El Facade expone el estado global vía Signals.

### B. Smart vs Dumb Components (Atomic Design)
- **Dumb Components (`shared/`):** El 90% de tu UI. Solo reciben data por `input()` y emiten eventos por `output()`. No saben de dónde viene la data. (Ej: `kpi-card`).
- **Smart Components (`features/`):** Tienen inyectado el Facade. Son responsables de coordinar los Dumb Components pasando states/Signals. Son las "Páginas".
- **Skeletons Colocated:** Todo Dumb component que reciba data asíncrona debe tener su `{componente}-skeleton.component.ts` al lado de él que mantenga EXACTAMENTE el mismo layout y proporciones del grid.

### C. Tipados y Manejo de Errores (State & Error Handling)
- **Ubicación de Interfaces:** Los types e interfaces globales deben situarse en `core/models/`. Los modelos específicos de un feature o servicio van junto a su ecosistema (ej. el Facade), **NUNCA** esparcidos o creados al vuelo dentro de los componentes.
- **Gestión de Errores:** Al manejar suscripciones o llamadas a red (Supabase/REST) en el Facade, utiliza `catchError`. Transforma las fallas en un estado seguro para la UI explayando un `Signal` de error (`errorSignal`) o delegando a un servicio centralizado de notificación (Toasts), evitando que los errores rompan la UI silenciosamente.

## 2. Reactividad & Angular v20+ Signals
- **`ChangeDetectionStrategy.OnPush`** es OBLIGATORIO en TODO componente creado.
- **Estado UI (Sincrónico):** Usa `signal()` para contadores, modales abiertos, etc.
- **Flujos Async / Red:** Usa `RxJS` internamente en los servicios. En el nivel de la Facade, usa la función `toSignal()` para exponer los flujos a tu HTML.
- **Templates:** Prohibido usar `*ngIf` o `*ngFor`. Usa obligatoriamente el Control Flow nativo: `@if` y `@for`.
- **Inputs:** Migra `@Input()` y `@Output()` hacia las nuevas APIs de Signals (`input()`, `output()`).
- No uses `ngClass` o `ngStyle`, usa binding directo: `[class.active]="isActive()"` o `[style.width.px]="width()"`.

## 3. Jerarquía Visual (Design System -> PrimeNG -> Custom)
Antes de crear un componente presentacional, consulta en este orden:
1. `indices/COMPONENTS.md`: ¿El Boilerplate (Design System local) tiene algo aplicable? Si la respuesta es sí, úsalo.
2. `PrimeNG`: En inputs de data, dropdowns complejos, calendarios, usa `p-dropdown`, `p-calendar` etc. (Ver [PrimeNG Priority Rule](../skills/primeng-priority.md)).
3. Componente Custom: Solo escríbelo si los pasos 1 y 2 no cubrieron la necesidad.

## 4. Base de Datos & Base de Trabajo (Supabase Migrations)
- Todo esquema DDL va en la carpeta `supabase/migrations/` (Naming convention: `YYYYMMDDHHMMSS_<dominio>_<tipo>_<descripcion>.sql`).
- SIEMPRE documentar en `indices/DATABASE.md` cada nueva tabla y su política de Row Level Security (RLS).
- Si usas Supabase realtime, actualiza tus servicios usando RxJS `Observable` -> `toSignal()`.

## 5. Estilos & Motion (Tailwind v4 + SCSS + View Transitions)
- **Tailwind v4:** Usar de forma predeterminada para el 90% del styling (utilidades como `p-4`, `flex`, `bg-surface`, `text-text-muted`). NUNCA usar colores Tailwind arbitrarios. TODO debe mapear a nuestros tokens de diseño.
- **Vanilla SCSS:** Usar EXCLUSIVAMENTE para layouts complejos estructurales (ej: los mixins abstractos del `_bento-grid.scss`) o donde las utilidades de Tailwind se vuelvan ilegibles.
- **Motion:**
  - Navegación de rutas → **CSS View Transitions API** nativa (`_view-transitions.scss`).
  - Animación de componentes montados → **GSAP** (`GsapAnimationsService`). NO uses `@keyframes` para micro-interacciones complejas.
  - Cambio de Tema (Light/Dark) → **CSS Transitions** puros (manejados globalmente en el `body`).
