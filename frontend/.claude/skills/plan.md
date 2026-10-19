---
name: plan
description: Generar task-spec antes de implementar. Obliga al agente a declarar intención antes de escribir código. Usar SIEMPRE antes de una tarea no trivial (>2 archivos o >1 dominio).
user-invocable: true
---

Antes de escribir cualquier código, crea un task-spec en `.claude/temp/task-spec-{TIMESTAMP}.md`.

**Pasos:**

1. Lee `indices/COMPONENTS.md`, `indices/SERVICES.md` y `indices/FACADES.md` (Discovery Gate requiere esto).
2. Crea el archivo de spec en `.claude/temp/`:

```markdown
# Task Spec — {TIMESTAMP}

## Objetivo
[Qué problema resuelve esta tarea — en 1-2 frases]

## Contexto de negocio
[Por qué es necesario — referencia a context/brief.md si existe]

## Artefactos afectados
| Archivo | Cambio | Índice a actualizar |
|---------|--------|---------------------|
| `src/app/features/...` | Crear / Modificar / Eliminar | COMPONENTS.md |

## Reglas que aplican
[Lista de reglas relevantes: ARCH-01, A11Y-01, VISUAL-03, etc.]

## Spec de output
[Qué debe existir cuando la tarea esté completa: componentes, tests, índices actualizados]

## Criterio de done
- [ ] ng build sin errores
- [ ] npm run lint:arch sin violaciones
- [ ] indices/ actualizados con nuevos artefactos
- [ ] Tests unitarios escritos (si aplica)
```

3. Muestra el task-spec al usuario y espera aprobación antes de escribir código.

**Por qué:** La intención queda registrada y es trazable. Evita implementaciones sorpresa
y permite al humano redirigir antes de que se escriba código difícil de revertir.
