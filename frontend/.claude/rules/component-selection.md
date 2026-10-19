---
paths:
  - "src/app/shared/**/*.ts"
  - "src/app/features/**/*.ts"
  - "src/app/features/**/*.html"
---

# Estrategia de Selección de Componentes

## Arbol de decision (OBLIGATORIO antes de crear un componente)

```
1. ¿PrimeNG tiene este componente?
   → SI: Usa PrimeNG. Los overrides en _primeng-overrides.scss ya lo estilizan.
   → NO: Paso 2.

2. ¿Ya existe en shared/ (ver indices/COMPONENTS.md)?
   → SI: Usalo. Si necesitas variante, extiende con input() adicional.
   → NO: Paso 3.

3. ¿Se usara en 3+ features diferentes?
   → SI: Crealo en shared/components/. Actualiza indices/COMPONENTS.md.
   → NO: Crealo como componente local en features/X/components/.
```

## Componentes PrimeNG pre-estilizados (NO duplicar)

| Necesidad | PrimeNG | Ya estilizado en |
|-----------|---------|------------------|
| Tablas con sort/filter/paginacion | `p-table` | `_primeng-overrides.scss` |
| Inputs de texto | `p-inputText`, `p-floatLabel` | `_primeng-overrides.scss` |
| Selects/Dropdowns | `p-dropdown`, `p-multiSelect` | `_primeng-overrides.scss` |
| Calendarios/Fechas | `p-calendar`, `p-datePicker` | `_primeng-overrides.scss` |
| Modals/Dialogos | `p-dialog`, `p-confirmDialog` | `_primeng-overrides.scss` |
| Toasts | `p-toast` (via `ToastService`) | `_primeng-overrides.scss` |
| Breadcrumbs | `p-breadcrumb` | `_primeng-overrides.scss` |
| Tabs | `p-tabView` | `_primeng-overrides.scss` |
| Menus | `p-menu`, `p-menubar` | `_primeng-overrides.scss` |
| Badges | `p-badge` | `_primeng-overrides.scss` |
| Botones con loading | `p-button` con `[loading]` | `btn-primary/secondary/ghost` utilities |
| Skeleton loading | `p-skeleton` | `_primeng-overrides.scss` |

## Componentes custom (existen porque PrimeNG NO los tiene)

| Componente | Por que es custom |
|------------|-------------------|
| `app-kpi-card` | KPI con animacion GSAP de contador + trend indicator. No existe en PrimeNG. |
| `app-empty-state` | Estado vacio unificado con icono + accion. PrimeNG no tiene equivalente. |
| `app-alert-card` | Alerta inline con barra de severidad + accion. Diferente de `p-message`. |
| `app-drawer` | Panel lateral animado con GSAP. `p-sidebar` no tiene las animaciones premium. |
| `app-icon` | Wrapper de Lucide. PrimeNG usa PrimeIcons, nosotros Lucide. |
| `skeleton-block` | Atomo basico de loading con variantes (rect/circle/text). |

## Utilidades SCSS (NO crear componentes para esto)

| Necesidad | Clase SCSS | NO crear componente |
|-----------|-----------|---------------------|
| Boton primario | `btn-primary` | No necesitas `<app-button>` |
| Boton secundario | `btn-secondary` | Idem |
| Boton ghost | `btn-ghost` | Idem |
| KPI numero grande | `.kpi-value` | Ya lo usa `app-kpi-card` |
| KPI etiqueta | `.kpi-label` | Idem |
| Banner hero | `.surface-hero` | Clase CSS, no componente |
| Overlay glass | `.surface-glass` | Clase CSS, no componente |

## Prohibiciones

- **NUNCA** crear wrappers de PrimeNG que solo cambien estilos. Para eso estan los overrides SCSS.
- **NUNCA** crear un componente en `shared/` que solo se usa en 1 feature. Va en `features/X/components/`.
- **NUNCA** crear componentes de dominio en `shared/` (ej: `app-user-card`, `app-invoice-card`). Esos son smart o locales.
