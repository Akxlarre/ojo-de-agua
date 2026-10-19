---
paths:
  - "src/app/features/**/*.ts"
  - "src/app/features/**/*.html"
---

# Layout Blueprints — Arquetipos de Página

Antes de estructurar cualquier feature page, **identifica su arquetipo**.
El arquetipo determina el hero, la grilla y los componentes obligatorios.

> Skeletons HTML completos: `indices/LAYOUTS.md`

## Árbol de selección (OBLIGATORIO)

```
¿Qué propósito tiene la página?
│
├── Resumen / inicio / overview          → dashboard
├── Índice de entidades (tabla)          → list
├── Ficha detalle de 1 entidad           → detail
├── Formulario crear / editar            → form
├── Login / registro / auth              → auth
├── Gráficos / reportes / métricas       → analytics
├── Configuración / ajustes / perfil     → settings
└── Primer uso / wizard / setup          → onboarding
```

**PROHIBIDO** inventar un layout si algún arquetipo aplica.

---

## Tabla de restricciones por arquetipo

| Arquetipo | `.surface-hero` | Hero / Header | Grid | Componentes obligatorios | Prohibiciones |
|-----------|:-:|---|---|---|---|
| `dashboard` | ✅ | `.bento-hero.surface-hero` | `.bento-grid [appBentoGridLayout]` | `app-kpi-card` (≥3), `app-empty-state` en actividad | No más de 1 `.card-accent` |
| `list` | ❌ | `.page-header` plano (título + CTA) | Columna simple | `p-table` con `emptymessage`, `app-empty-state` | No `.surface-hero`, no bento-grid |
| `detail` | ❌ | `.card.card-accent` (nombre + acciones) | `grid grid-cols-3 gap-6` (main 2 + aside 1) | `app-drawer` para edición, `app-alert-card` si hay warning | No `.surface-hero` |
| `form` | ❌ | Breadcrumb + título plano | `.page-narrow` (centrado, 1 col) | PrimeNG inputs, `app-alert-card` para errores server | No hero visual, no bento-grid |
| `auth` | ✅ | Split 50/50: hero izquierdo + form derecho | `grid grid-cols-2 min-h-screen` | `app-alert-card` para errores de auth | No sidebar, no tablas |
| `analytics` | ❌ | Strip de KPIs (bento-grid sin hero-section) | `.bento-grid` + `grid grid-cols-2` charts | `app-kpi-card` (3-4), `p-table` drill-down | No `.surface-hero` |
| `settings` | ❌ | Título plano (sin visual) | `grid grid-cols-4` (nav 1 + content 3) | `p-menu` nav lateral, panels `.card` por sección | No hero, no bento-grid |
| `onboarding` | ✅ | `.surface-hero` fullwidth (logo + tagline) | `.page-narrow` centrado | `p-stepper` para pasos | No sidebar, no tablas |

---

## Reglas transversales (aplican a todos los arquetipos)

- **`.card-accent`**: máximo 1 por vista. En `dashboard` lo cumple el `.bento-hero`. En `detail` es el header de entidad.
- **`app-empty-state`**: SIEMPRE presente en estados vacíos. En tablas, dentro de `ng-template pTemplate="emptymessage"`.
- **`app-kpi-card`**: obligatorio en `dashboard` y `analytics`. Siempre con `app-kpi-card-skeleton` mientras carga.
- **`app-drawer`**: preferido para edición inline en `detail`. Evitar navegar a `/edit` salvo formularios complejos.
- **`.surface-hero`**: solo en `dashboard`, `auth`, `onboarding`. El texto SIEMPRE en `var(--color-primary-text)`.
- **Iconos**: `<app-icon name="..." />` en todos. PROHIBIDO emojis o SVG inline.
