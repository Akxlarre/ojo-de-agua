---
paths:
  - "src/app/**/*.html"
---

# Regla: A11y Spec (Accesibilidad)

Los templates Angular deben cumplir contratos mínimos de accesibilidad.
El Architect Guard valida estos contratos automáticamente en cada escritura.

## Contratos obligatorios

### A11Y-01 — `<app-icon>` requiere aria-label si es acción
- **PROHIBIDO**: `<app-icon name="trash" />`  
- **OBLIGATORIO**: `<app-icon name="trash" [attr.aria-label]="'Eliminar registro'" />`
- **Excepción**: si hay texto hermano visible (`<button><app-icon name="plus" /> Agregar</button>`), el aria-label es opcional en el icono

### A11Y-02 — `<p-table>` requiere caption o aria-label
- **PROHIBIDO**: `<p-table [value]="datos()">`  
- **OBLIGATORIO**: `<p-table [value]="datos()" [attr.aria-label]="'Tabla de usuarios'">` o con `<ng-template pTemplate="caption">`

### A11Y-03 — botones de solo icono requieren aria-label
- **PROHIBIDO**: `<button (click)="borrar()"><app-icon name="trash" /></button>`  
- **OBLIGATORIO**: `<button (click)="borrar()" aria-label="Eliminar registro"><app-icon name="trash" /></button>`

### A11Y-04 — `data-llm-action` en botones de mutación (ya cubierto por ai-readability.md)
- Refuerzo: toda acción que modifica datos (`save`, `delete`, `submit`) debe tener `data-llm-action`.

## Por qué importa
Los guardrails agénticos (y los tests de accesibilidad automatizados) dependen de atributos
semánticos correctos. Un icono sin `aria-label` no es un error visual — es un contrato roto
para usuarios de lectores de pantalla y para otros agentes AI que navegan la UI.
