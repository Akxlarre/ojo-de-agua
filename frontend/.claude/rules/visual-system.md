---
paths:
  - "src/app/**/*.html"
  - "src/app/**/*.scss"
  - "src/app/shared/**/*.ts"
  - "src/styles/**/*.scss"
---

# Sistema Visual

## Prioridad de UI

1. `indices/COMPONENTS.md` — ¿Existe algo reutilizable del Design System local?
2. `PrimeNG` — Para inputs complejos, tablas, calendarios, dropdowns
3. Componente custom — Solo si 1 y 2 no cubren la necesidad

## Tokens de color (PROHIBIDO hardcodear)

- Textos: `text-primary`, `text-secondary`, `text-muted`
- Fondos: `bg-base` (página), `bg-surface` (cards), `bg-surface-elevated`
- Marca: `var(--ds-brand)`, `var(--color-primary)`
- **NUNCA**: `text-red-500`, `bg-[#ff0000]`, u otras utilities de colores arbitrarios de Tailwind. Usa siempre variables abstractas.

## Iconos — Sistema Lucide (OBLIGATORIO)

- **PROHIBIDO** usar emojis como iconos de UI (❌ `✅`, `⚠️`, `🔒`, `📊`)
- **OBLIGATORIO** usar `<app-icon name="..." />` para todo ícono de interfaz
- Selector: `app-icon` | inputs: `name` (requerido), `size` (default 16), `color`, `ariaHidden`
- Nombres en kebab-case igual que en lucide.dev (ej: `"trending-up"`, `"trash-2"`)
- Para agregar un ícono nuevo: importarlo de `'lucide-angular'` y registrarlo en `provideIcons()` en `app.config.ts`
- **NUNCA** insertar `<svg>` inline ad-hoc — siempre pasar por `<app-icon>`

## Regla 3-2-1 de Marca (Brand Color Discipline)

El color de marca `var(--ds-brand)` debe aparecer en **máximo 3 elementos por viewport**:
- **2 interactivos** → CTAs primarios, links de acción, botones `.btn-primary`
- **1 decorativo** → borde de `.card-accent`, indicador de sección activa, o highlight visual

**PROHIBIDO:**
- Usar `var(--ds-brand)` en texto largo o de cuerpo
- Fondos de sección completos con el brand color (usar `.surface-hero` en su lugar)
- Más de 1 elemento puramente decorativo de marca por viewport

## Tipografía de Datos — KPI (OBLIGATORIO)

En componentes con datos numéricos (KPIs, métricas, estadísticas):
- **OBLIGATORIO** `.kpi-value` para el número principal (reemplaza `text-4xl font-bold`)
- **OBLIGATORIO** `.kpi-label` para la etiqueta descriptiva (reemplaza `text-xs uppercase`)
- Combinar con `.card-tinted` para máximo contraste visual

```html
<!-- CORRECTO -->
<div class="card-tinted">
  <span class="kpi-label">Usuarios activos</span>
  <span class="kpi-value">24.8K</span>
</div>

<!-- INCORRECTO -->
<div>
  <p class="text-xs text-gray-500 uppercase">Usuarios activos</p>
  <p class="text-4xl font-bold">24.8K</p>
</div>
```

## Superficies Activas (OBLIGATORIO)

- **`.surface-hero`** → banners, hero sections, headers de alta jerarquía. Aplica `var(--gradient-hero)`. El texto SIEMPRE en `var(--color-primary-text)` (blanco).
- **`.surface-glass`** → modales flotantes, overlays, panels glassmorphism. Usa backdrop-filter blur automático.

```html
<!-- Hero section con superficie de marca -->
<section class="bento-hero surface-hero rounded-xl">
  <h1>Dashboard</h1>
</section>

<!-- Panel flotante con glass -->
<div class="surface-glass rounded-lg p-4">
  <!-- contenido de overlay -->
</div>
```

## Indicadores de Actividad

- **`.indicator-live`** → dot verde pulsante para sistemas activos / conexiones en tiempo real
- **`.badge-pulse`** → pulso de atención en badges de conteo (nuevos items, alertas no leídas)

```html
<span class="indicator-live text-sm text-secondary">Sistema activo</span>
<span class="badge-pulse">
  <p-badge value="3" severity="danger" />
</span>
```

## Bento Grid

- **Todo Smart Component (feature) DEBE usar `.bento-grid` como root. Queda prohibido el uso de `.page-wide` en la capa de features.**
- Contenedor: `.bento-grid` + directiva `[appBentoGridLayout]`
- Hijos: `.bento-square`, `.bento-wide`, `.bento-tall`, `.bento-feature`, `.bento-hero`
- Solo **UN** `.card-accent` por sección bento
- SCSS canónico: `src/styles/layout/_bento-grid.scss`

## Cards

- `.card` — base con borde y padding estándar
- `.card-accent` — borde superior con `var(--ds-brand)` (1 por sección)
- `.card-tinted` — fondo primario diluido (para KPIs y highlights)

## Modo claro/oscuro

- Controlado por `ThemeService` con `[data-mode='dark']` en el documentElement
- `this.themeService.setColorMode('dark' | 'light' | 'system')`
- PrimeNG: usar `darkModeSelector: '.fake-dark-mode'` para evitar conflictos

## Personalización de marca por cliente (Multi-Brand)

Cuando un cliente requiere colores corporativos distintos al default, **no crees un tema paralelo ni dupliques tokens**. El sistema de 4 capas ya lo soporta:

### Cómo aplicar

Sobreescribir **solo Layer 3 (Brand)** en `_variables.scss`:

```scss
// Antes (default del Blueprint)
:root {
  --ds-brand: #0ea5e9;
  --color-primary-hover: #0284c7;
  --gradient-hero: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
}
[data-mode="dark"] {
  --ds-brand: #38bdf8;
  --color-primary-hover: #7dd3fc;
}

// Después (cliente "Acme Corp" con verde corporativo)
:root {
  --ds-brand: #16a34a;
  --color-primary-hover: #15803d;
  --gradient-hero: linear-gradient(135deg, #16a34a 0%, #059669 100%);
}
[data-mode="dark"] {
  --ds-brand: #4ade80;
  --color-primary-hover: #86efac;
}
```

### Reglas

- **SOLO** tocar Layer 3 (brand, gradientes, estados). Layers 1, 2 y 4 no cambian.
- El dark mode del brand **debe cumplir WCAG AA** (contraste ≥ 4.5:1 sobre `--bg-surface`). Verificar en [webaim.org/resources/contrastchecker](https://webaim.org/resources/contrastchecker/).
- Los component tokens (Layer 4) como `--btn-primary-bg: var(--ds-brand)` heredan automáticamente — no necesitan cambios.
- **NUNCA** crear selectores `[data-brand="x"]` ni CSS condicional por cliente. Un proyecto = una marca. Si necesitas multi-tenant runtime, eso es una feature distinta que requiere `ThemeService` extendido.

## Animaciones

- **PROHIBIDO** `@angular/animations` (redundante con CSS nativo y GSAP)
- **SIEMPRE** respetar `prefers-reduced-motion` en cualquier animación

### Sin GSAP (default — `blueprint.gsap: false`)
- Entradas de vistas: clases CSS `.animate-fade-in-up`, `.animate-fade-in`, `.animate-stagger` de `src/styles/_animations.scss`
- Navegación entre rutas: `withViewTransitions()` en `app.config.ts` + estilos en `src/styles/_view-transitions.scss`
- `@keyframes` permitido en cualquier archivo SCSS

### Con GSAP (`blueprint.gsap: true`, flag `--with-gsap`)
- **OBLIGATORIO** `GsapAnimationsService` en `ngAfterViewInit`
- Métodos clave: `animateBentoGrid()`, `animateHero()`, `animateCounter()`, `addCardHover()`
- Siempre `clearProps: 'transform'` tras animaciones de movimiento
- **PROHIBIDO** `@keyframes` en estilos de componente (`src/app/`). Solo en design system global (`src/styles/`)
- **PROHIBIDO** inventar `durations` o `eases` arbitrarios. Usa variables CSS (`--duration-*`, `--ease-*`)
