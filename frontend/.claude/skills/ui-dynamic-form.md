---
name: ui-dynamic-form
description: >-
  Generación de Formularios Dinámicos complejos con validaciones asíncronas,
  campos condicionales y contratos de accesibilidad del Design System.
---

# UI Blueprint: Formularios Dinámicos Complejos

## Principio Fundamental

**NUNCA** escribas `FormGroup`, `FormControl`, `Validators` ni lógica de validación
en el componente. El proyecto inyecta un `HeadlessFormService` que expone el
formulario reactivo como Signals. Tu trabajo es SOLO dibujar inputs y conectarlos.

## Conexión con el Cerebro Headless

```typescript
// En el .ts del componente, solo inyectas:
readonly form = inject(HeadlessFormService);
// form.fields()          → Signal<FieldConfig[]> (campos visibles según condiciones)
// form.control(key)      → FormControl (para enlazar con [formControl])
// form.errors(field)     → Signal<string[]> (mensajes de error del campo)
// form.hasError(field)   → boolean
// form.isValid()         → Signal<boolean>
// form.isPending(field)  → Signal<boolean> (validación async en curso)
// form.isVisible(field)  → boolean (campo condicional visible o no)
// form.isSubmitting()    → Signal<boolean>
// form.options(field)    → Signal<SelectItem[]> (opciones para selects dinámicos)
// form.submit()          → void
// form.triggerUpload(f)  → void
// form.getPreview(f)     → string | null
```

---

## Reglas Estrictas del Design System

### Layout
- El arquetipo correcto es `form` (de `layout-blueprints.md`).
- **OBLIGATORIO:** `.page-narrow` (centrado, 1 columna, max-width 640px).
- **PROHIBIDO:** `.surface-hero` y `.bento-grid` en formularios.

### Tokens de Color — PROHIBICIONES (ARCH-08)
- **PROHIBIDO:** `text-red-500`, `border-red-500`, `bg-green-100`, o cualquier color arbitrario.
- **OBLIGATORIO:**
  - Error: `var(--state-error)` para texto, `var(--state-error-bg)` para fondo.
  - Éxito: `var(--state-success)` para bordes verdes post-validación.
  - Bordes de input: usar tokens `border-default` (normal), input focus via `--input-shadow-focus-neutral`.

### Accesibilidad (A11Y)
- **OBLIGATORIO:** Labels visibles en cada campo. Si un campo es requerido, marcar con `<span>` en color `var(--state-error)`.
- **OBLIGATORIO:** Mensajes de error solo visibles cuando el campo esté `touched && invalid`.
- **OBLIGATORIO:** Botones submit con `data-llm-action="crear-{dominio}"` o `data-llm-action="actualizar-{dominio}"`.

### Iconos
- **OBLIGATORIO:** `<app-icon>` con `aria-label` si es acción, o `ariaHidden="true"` si es decorativo.

### Loading del Submit
- Usar `<app-icon name="loader-2" [size]="16" class="animate-spin" />` dentro del botón.
- **PROHIBIDO** `pi pi-spinner pi-spin` (no usamos iconos de PrimeNG directamente).

---

## Esqueleto Base

```html
<!-- Layout Archetype: form (.page-narrow) -->
<div class="page-narrow">
  <div class="card">

    <!-- Header del Formulario -->
    <div class="mb-6">
      <h1 class="text-xl font-bold text-primary"><!-- TÍTULO --></h1>
      <p class="text-sm text-muted mt-1">Complete los campos obligatorios marcados con *</p>
    </div>

    <form (ngSubmit)="form.submit()" class="space-y-8">

      <!-- ══════ SECCIÓN (usar <fieldset> para agrupar) ══════ -->
      <fieldset class="space-y-4">
        <legend class="text-lg font-bold text-primary border-b border-default pb-2 w-full">
          <!-- NOMBRE DE SECCIÓN -->
        </legend>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Campo de Texto -->
          <div>
            <label class="block text-sm font-medium text-secondary mb-1">
              Nombre <span [style.color]="'var(--state-error)'">*</span>
            </label>
            <input pInputText [formControl]="form.control('fullName')" class="w-full"
                   [style.border-color]="form.hasError('fullName') ? 'var(--state-error)' : null" />
            @if(form.hasError('fullName')) {
              @for(err of form.errors('fullName')(); track err) {
                <small [style.color]="'var(--state-error)'" class="text-sm mt-1 block">{{ err }}</small>
              }
            }
          </div>

          <!-- Campo con Validación Async -->
          <div>
            <label class="block text-sm font-medium text-secondary mb-1">
              Email <span [style.color]="'var(--state-error)'">*</span>
            </label>
            <div class="relative">
              <input pInputText [formControl]="form.control('email')" class="w-full pr-10"
                     [style.border-color]="form.hasError('email') ? 'var(--state-error)' : null" />
              @if(form.isPending('email')) {
                <app-icon name="loader-2" [size]="16" ariaHidden="true"
                          class="absolute right-3 top-1/2 -translate-y-1/2 text-muted animate-spin" />
              }
              @if(!form.isPending('email') && !form.hasError('email')) {
                <app-icon name="check" [size]="16" ariaHidden="true"
                          class="absolute right-3 top-1/2 -translate-y-1/2"
                          [style.color]="'var(--state-success)'" />
              }
            </div>
          </div>

          <!-- Select (Dropdown) -->
          <div>
            <label class="block text-sm font-medium text-secondary mb-1">País</label>
            <p-select [options]="form.options('country')" [formControl]="form.control('country')"
                      placeholder="Seleccione" class="w-full" />
          </div>

          <!-- Campos Condicionales -->
          @if(form.isVisible('state')) {
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">State</label>
              <p-select [options]="form.options('state')" [formControl]="form.control('state')" class="w-full" />
            </div>
          }

          <!-- Campo Full Width -->
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-secondary mb-1">Dirección</label>
            <textarea pInputTextarea [formControl]="form.control('address')" rows="2" class="w-full" />
          </div>

        </div>
      </fieldset>

      <!-- ══════ FOOTER: Botones ══════ -->
      <div class="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-default">
        <button type="button" class="btn-secondary">Cancelar</button>
        <button type="submit" class="btn-primary" [disabled]="!form.isValid()"
                data-llm-action="crear-{dominio}">
          @if(form.isSubmitting()) {
            <app-icon name="loader-2" [size]="16" ariaHidden="true" class="animate-spin mr-2" />
          }
          Guardar
        </button>
      </div>
    </form>
  </div>
</div>
```
