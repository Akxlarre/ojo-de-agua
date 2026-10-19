---
paths:
  - "src/app/**/*.html"
  - "src/app/features/**/*.ts"
  - "src/app/shared/**/*.ts"
---

# AI-Readability — Interfaces para Máquinas

El software que construimos no solo debe ser operable por humanos, sino también por
**agentes IA externos** (bots exploradores, asistentes en segundo plano, integraciones agénticas).

Para garantizar esta Interoperabilidad Semántica, aplica etiquetas `data-llm-*` a todo
el DOM interactivo con impacto en el estado de negocio.

---

## Atributos semánticos (Shadow Semantic Overlay)

### `data-llm-action` — Botones de mutación (ENFORCED por Architect Guard)

Todo botón que **altere el estado de negocio** debe tener `data-llm-action`.
El Architect Guard **bloquea** writes en `features/` y `shared/` si detecta:
- Botones `type="submit"` sin `data-llm-action` → **[LLM-01]**
- Botones con `aria-label` de eliminación/borrado sin `data-llm-action` → **[LLM-02]**

```html
<!-- ✅ Correcto -->
<button type="submit" data-llm-action="crear-factura" class="btn-primary">
  Guardar
</button>

<button
  aria-label="Eliminar producto"
  data-llm-action="delete-producto"
  class="btn-ghost"
>
  <app-icon name="trash-2" [size]="16" ariaHidden="true" />
</button>

<!-- ❌ Incorrecto — bloqueado por LLM-01 / LLM-02 -->
<button type="submit" class="btn-primary">Guardar</button>
<button aria-label="Eliminar producto" class="btn-ghost">...</button>
```

**Convención de nombres:**
- Creación: `crear-{dominio}` (ej: `crear-producto`, `crear-factura`)
- Actualización: `actualizar-{dominio}` (ej: `actualizar-perfil`)
- Eliminación: `delete-{dominio}` (ej: `delete-producto`)
- Acciones específicas: `{verbo}-{dominio}` (ej: `aprobar-solicitud`, `archivar-pedido`)

---

### `data-llm-description` — Inputs de formulario críticos (advisory)

Los campos que capturan datos de negocio importantes deben describirse más allá
del `placeholder` o `aria-label`. Permite a los agentes entender el propósito semántico.

```html
<!-- ✅ Correcto — el agente sabe exactamente qué captura este campo -->
<input
  pInputText
  formControlName="email"
  data-llm-description="email principal del usuario para autenticación y comunicaciones"
  placeholder="usuario@empresa.com"
/>

<!-- Mínimo aceptable para campos no críticos -->
<input pInputText formControlName="nombre" placeholder="Nombre completo" />
```

---

### `data-llm-nav` — Navegación principal (advisory)

Los enlaces a áreas principales de la aplicación deben tener `data-llm-nav` para
que los agentes puedan explorar la estructura sin depender de clases CSS.

```html
<a routerLink="/dashboard" data-llm-nav="dashboard">Dashboard</a>
<a routerLink="/productos" data-llm-nav="productos">Productos</a>
```

---

## Regla de aplicación

| Atributo | Dónde | Estado |
|---|---|---|
| `data-llm-action` | Botones submit + destructivos en `features/`, `shared/` | **ENFORCED** — bloqueo en Architect Guard |
| `data-llm-action` | Otros botones de mutación (actualizar, aprobar, etc.) | Advisory — se recomienda, no se bloquea |
| `data-llm-description` | Inputs críticos de formulario | Advisory |
| `data-llm-nav` | Enlaces de navegación principal | Advisory |

---

## Por qué importa

Si un agente evaluador inspecciona tu UI mediante herramientas de browser, o si el usuario
conecta "Agent Desktop" a su PC, estos atributos garantizan un **0% de alucinación visual**.
El agente busca explícitamente `[data-llm-action="delete-producto"]` en vez de inferir
qué botón tiene clase `btn-ghost` con ícono `trash-2`.
