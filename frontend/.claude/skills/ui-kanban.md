---
name: ui-kanban
description: >-
  Generación de tableros Kanban con Drag & Drop (Angular CDK), directivas de
  microinteracción del Design System y contratos de accesibilidad.
---

# UI Blueprint: Tablero Kanban (Drag & Drop)

## Principio Fundamental

**NUNCA** mutes arrays manualmente (`splice`, `push`) para mover tarjetas entre columnas.
El proyecto inyecta un `HeadlessKanbanService` que maneja todo el estado interno.
Tu trabajo es SOLO dibujar columnas y tarjetas, y enlazar las directivas CDK.

## Conexión con el Cerebro Headless

```typescript
// En el .ts del componente, inyectas:
readonly kanban = inject(HeadlessKanbanService);
readonly gsap = inject(GsapAnimationsService); // Para animaciones de entrada
// kanban.columns()         → Signal<Column[]> (cada Column tiene .items: Signal<Card[]>)
// kanban.allColumnIds()    → string[] (para cdkDropListConnectedTo)
// kanban.onDrop(event)     → void (procesa el CdkDragDrop internamente)
// kanban.addCard(colId)    → void
// kanban.removeCard(id)    → void
// kanban.moveCard(id, col) → void
```

---

## Reglas Estrictas del Design System

### Tokens de Color — PROHIBICIONES (ARCH-08)
- **PROHIBIDO:** `bg-red-500`, `bg-orange-500`, `bg-blue-500`, `bg-green-500`, o cualquier color Tailwind arbitrario para indicadores de prioridad.
- **OBLIGATORIO:** Usar variables CSS del DS para estados:
  - Crítico: `var(--state-error)`, `var(--state-error-bg)`
  - Alto: `var(--state-warning)`, `var(--state-warning-bg)`
  - Normal: `var(--state-info)`, `var(--state-info-bg)`
  - Bajo: `var(--text-muted)`, `bg-subtle`

### Tarjetas
- **OBLIGATORIO:** Directiva `[appCardHover]` para el efecto hover de tarjetas (elevación GSAP).
- **PROHIBIDO:** CSS `hover:shadow-md` o `transition-shadow` manual. Usar la directiva.
- Fondo: `.card` (que usa `bg-surface`, `border-default`, `var(--radius-lg)`).

### Drag & Drop
- `cdkDrag` + `cdkDropList` del CDK.
- Cursor: `cursor-grab active:cursor-grabbing` (esto es Tailwind de layout, permitido).

### Accesibilidad (A11Y)
- Botones de acción requieren `aria-label` y `data-llm-action`.
- Iconos decorativos: `ariaHidden="true"`.

### Animación de Entrada
- Usar `GsapAnimationsService.animateBentoGrid()` en `ngAfterViewInit` para la entrada escalonada de columnas.

### Empty State
- **OBLIGATORIO:** `<app-empty-state>` en columnas vacías.

---

## Esqueleto Base

```html
<div class="min-h-[70vh] p-4 lg:p-6">

  <!-- Header del Tablero -->
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
    <div>
      <h1 class="text-2xl font-bold text-primary"><!-- TÍTULO DEL TABLERO --></h1>
      <p class="text-sm text-muted mt-1"><!-- SUBTÍTULO --></p>
    </div>
    <button class="btn-primary" data-llm-action="crear-tarea">
      <app-icon name="plus" [size]="16" ariaHidden="true" /> Nueva Tarea
    </button>
  </div>

  <!-- Tablero Kanban -->
  <div class="flex gap-4 overflow-x-auto pb-4" cdkDropListGroup #kanbanContainer>
    @for(col of kanban.columns(); track col.id) {
      <div class="min-w-72 w-80 flex-shrink-0 flex flex-col">

        <!-- Header de Columna -->
        <div class="flex justify-between items-center mb-3 px-1">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full"
                 [style.background-color]="col.color"></div>
            <h3 class="font-bold text-secondary text-sm uppercase tracking-wide">
              {{ col.title }}
            </h3>
          </div>
          <span class="text-xs font-medium bg-subtle text-muted px-2 py-0.5 rounded-full">
            {{ col.items().length }}
          </span>
        </div>

        <!-- Drop Zone -->
        <div cdkDropList
             [cdkDropListData]="col.items()"
             [id]="col.id"
             [cdkDropListConnectedTo]="kanban.allColumnIds()"
             (cdkDropListDropped)="kanban.onDrop($event)"
             class="flex-1 space-y-2 min-h-32 bg-elevated/50 rounded-xl p-2">

          @for(card of col.items(); track card.id) {
            <div cdkDrag [cdkDragData]="card" appCardHover
                 class="card p-0 cursor-grab active:cursor-grabbing group">

              <!-- Indicador de Prioridad -->
              <div class="h-1 rounded-t-lg"
                   [style.background-color]="card.priorityColor"></div>

              <div class="p-3 space-y-3">
                <!-- Título + Menú -->
                <div class="flex justify-between items-start">
                  <h4 class="font-medium text-primary text-sm leading-snug">
                    {{ card.title }}
                  </h4>
                  <button class="opacity-0 group-hover:opacity-100 transition-opacity p-1
                                 hover:bg-subtle rounded btn-ghost"
                          aria-label="Opciones de tarea"
                          data-llm-action="opciones-tarea">
                    <app-icon name="ellipsis" [size]="14" ariaHidden="true" />
                  </button>
                </div>

                <!-- Etiquetas -->
                @if(card.labels.length > 0) {
                  <div class="flex flex-wrap gap-1">
                    @for(label of card.labels; track label.name) {
                      <span class="px-2 py-0.5 rounded text-xs font-medium"
                            [style.background-color]="label.color + '20'"
                            [style.color]="label.color">
                        {{ label.name }}
                      </span>
                    }
                  </div>
                }

                <!-- Footer: Deadline + Asignado -->
                <div class="flex justify-between items-center pt-1">
                  <div class="flex items-center gap-3 text-xs text-muted">
                    @if(card.deadline) {
                      <span class="flex items-center gap-1"
                            [style.color]="card.isOverdue ? 'var(--state-error)' : null"
                            [class.font-bold]="card.isOverdue">
                        <app-icon name="calendar" [size]="12" ariaHidden="true" />
                        {{ card.deadline | date:'dd MMM' }}
                      </span>
                    }
                    @if(card.commentCount > 0) {
                      <span class="flex items-center gap-1">
                        <app-icon name="message-square" [size]="12" ariaHidden="true" />
                        {{ card.commentCount }}
                      </span>
                    }
                  </div>
                  @if(card.assignee) {
                    <img [src]="card.assignee.avatar" [alt]="card.assignee.name"
                         class="w-6 h-6 rounded-full border border-default" />
                  }
                </div>
              </div>

              <!-- Drag Placeholder -->
              <div *cdkDragPlaceholder
                   class="border-2 border-dashed rounded-lg h-20"
                   [style.border-color]="'var(--ds-brand)'"
                   [style.background-color]="'var(--color-primary-muted)'">
              </div>
            </div>
          }

          <!-- Empty State de Columna -->
          @if(col.items().length === 0) {
            <app-empty-state
              icon="inbox"
              title="Sin tareas"
              size="sm" />
          }
        </div>

        <!-- Botón Agregar -->
        <button (click)="kanban.addCard(col.id)"
                class="btn-ghost mt-2 w-full py-2 text-sm flex items-center justify-center gap-1"
                data-llm-action="crear-tarea">
          <app-icon name="plus" [size]="14" ariaHidden="true" /> Añadir tarea
        </button>
      </div>
    }
  </div>
</div>
```

## Nota sobre `*cdkDragPlaceholder`
La directiva `*cdkDragPlaceholder` es una directiva estructural del CDK de Angular (no de la API legacy).
El Architect Guard tiene una whitelist para directivas CDK — no confundir con `*ngIf`.
