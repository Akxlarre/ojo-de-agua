---
name: ui-table
description: >-
  Generación de DataTables complejas usando PrimeNG (preset Aura), tokens
  semánticos del Design System, lógica Headless y contratos de accesibilidad.
---

# UI Blueprint: Tablas de Datos (DataTables)

## Principio Fundamental

**NUNCA** escribas lógica de ordenación, paginación o filtrado en el componente.
El proyecto inyecta un `HeadlessTableService` (o directiva `[koaHeadlessTable]`)
que expone el estado como Signals. Tu trabajo es SOLO dibujar la tabla y enlazar los datos.

## Conexión con el Cerebro Headless

```typescript
// En el .ts del componente, inyectas:
readonly headless = inject(HeadlessTableService);
// headless.data()        → Signal<T[]>
// headless.total()       → Signal<number>
// headless.loading()     → Signal<boolean>
// headless.sort(field)   → void
// headless.load(event)   → void (LazyLoadEvent de PrimeNG)
// headless.setFilter(ev) → void
// headless.refresh()     → void
```

---

## Reglas Estrictas del Design System

### Tokens de Color — PROHIBICIONES (ARCH-08)
- **PROHIBIDO:** `text-red-500`, `bg-green-100`, `bg-blue-200`, `bg-surface-50`, o cualquier color Tailwind arbitrario.
- **OBLIGATORIO:** Tokens semánticos del DS:
  - Fondos: `bg-base`, `bg-surface`, `bg-elevated`, `bg-subtle`
  - Texto: `text-primary`, `text-secondary`, `text-muted`, `text-disabled`
  - Bordes: `border-subtle`, `border-default`, `border-strong`
  - Estados: `var(--state-success)`, `var(--state-error)`, `var(--state-warning)`, `var(--state-info)`
  - Fondos de estado: `var(--state-success-bg)`, `var(--state-error-bg)`, etc.

### Accesibilidad (A11Y-02)
- **OBLIGATORIO:** `<p-table>` requiere `aria-label` o `<ng-template pTemplate="caption">`.

### AI-Readability (LLM-01, LLM-02)
- **OBLIGATORIO:** Todo botón de acción destructiva o de submit requiere `data-llm-action`.
  - Formato: `data-llm-action="delete-{dominio}"`, `data-llm-action="actualizar-{dominio}"`

### Estados Vacíos
- **OBLIGATORIO:** Usar `<app-empty-state>`. PROHIBIDO `<p>No hay datos</p>` suelto.

### Skeletons
- **OBLIGATORIO:** Skeleton colocated (`tabla-skeleton.component.ts`) con `<app-skeleton-block>`.
- **Regla SWR:** NUNCA mostrar skeleton si ya hay datos en caché. Solo en la primera carga real.

### Layout
- El arquetipo correcto para vistas de tabla es `list` (de `layout-blueprints.md`).
- Usar `.page-header` plano. **PROHIBIDO** `.surface-hero` y **PROHIBIDO** `.bento-grid` en vistas de lista.

### Hover de Filas
- Usar tokens: `hover:bg-elevated` (no `hover:bg-surface-50`).

### Iconos
- **PROHIBIDO** emojis o SVG inline. Usar `<app-icon name="kebab-case" [size]="16" />` con `aria-label`.

---

## Esqueleto Base

```html
<!-- Layout Archetype: list -->
<div class="space-y-4">

  <!-- Page Header (plano, sin hero) -->
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
    <div>
      <h1 class="text-2xl font-bold text-primary"><!-- TÍTULO --></h1>
      <p class="text-sm text-muted mt-1"><!-- SUBTÍTULO --></p>
    </div>
    <button class="btn-primary" data-llm-action="crear-{dominio}">
      <app-icon name="plus" [size]="16" aria-label="Agregar" /> Nuevo
    </button>
  </div>

  <!-- Barra de Filtros -->
  <div class="flex flex-col md:flex-row gap-3">
    <div class="relative w-full md:w-64">
      <app-icon name="search" [size]="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" ariaHidden="true" />
      <input pInputText placeholder="Buscar..." (input)="headless.setFilter($event)" class="pl-10 w-full" />
    </div>
  </div>

  <!-- Tabla -->
  @if(headless.loading() && !headless.data().length) {
    <!-- Skeleton Colocated (primera carga) -->
    <app-tabla-skeleton />
  } @else {
    <div class="card p-0 overflow-hidden" [appAnimateIn]>
      <p-table
        [value]="headless.data()"
        [lazy]="true"
        [paginator]="true"
        [rows]="10"
        [totalRecords]="headless.total()"
        [loading]="headless.loading()"
        (onLazyLoad)="headless.load($event)"
        aria-label="<!-- NOMBRE DE LA TABLA -->"
      >
        <ng-template pTemplate="header">
          <tr>
            <th pSortableColumn="nombre">Nombre <p-sortIcon field="nombre" /></th>
            <!-- INYECTA TUS COLUMNAS -->
            <th>Acciones</th>
          </tr>
        </ng-template>

        <ng-template pTemplate="body" let-item>
          <tr>
            <td class="font-medium text-primary">{{ item.nombre }}</td>
            <!-- INYECTA TUS CELDAS -->
            <td>
              <button class="btn-ghost" aria-label="Ver detalle"
                      data-llm-action="ver-{dominio}">
                <app-icon name="eye" [size]="16" ariaHidden="true" />
              </button>
              <button class="btn-ghost" aria-label="Eliminar"
                      data-llm-action="delete-{dominio}">
                <app-icon name="trash-2" [size]="16" ariaHidden="true" />
              </button>
            </td>
          </tr>
        </ng-template>

        <ng-template pTemplate="emptymessage">
          <tr>
            <td [attr.colspan]="999">
              <app-empty-state
                icon="inbox"
                title="Sin registros"
                description="No se encontraron resultados." />
            </td>
          </tr>
        </ng-template>
      </p-table>
    </div>
  }
</div>
```

## Estados Condicionales de Celdas (Usando Tokens Semánticos)

Para representar estados (ej. Urgente, Estable, Pendiente), usa las variables CSS del DS:

```html
<span class="px-2 py-1 rounded-full text-xs font-bold"
      [style.background-color]="item.status === 'urgente' ? 'var(--state-error-bg)' : 'var(--state-success-bg)'"
      [style.color]="item.status === 'urgente' ? 'var(--state-error)' : 'var(--state-success)'"
      [style.border-color]="item.status === 'urgente' ? 'var(--state-error-border)' : 'var(--state-success-border)'"
      class="border">
  {{ item.status }}
</span>
```

**NUNCA** uses `bg-red-100 text-red-700` o `bg-green-100 text-green-700`.
