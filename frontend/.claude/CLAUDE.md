# frontend — Koa Agent Blueprint v6.5.0

Tu stack: **Angular + Tailwind v4 + PrimeNG + Supabase + GSAP**.

## Estilo de respuesta

**Al escribir código (Edit/Write):** No recapitules lo que acabas de hacer — el diff habla por sí solo.
Si tomaste una decisión no obvia, una línea de justificación basta.

**Al responder preguntas o analizar:** Responde con la profundidad que la pregunta requiere.
Preguntas de diseño, evaluación o discusión merecen respuestas completas.

## Sistema de Hooks Activo

Este proyecto tiene guardrails automáticos que se ejecutan sin intervención humana:

- **Context Guard** — Verifica que exista contexto de negocio. Si `indices/DOMAIN_DICTIONARY.md` o `DATABASE.md` están vacíos/incompletos, te bloqueará para que pidas el brief al humano antes de programar a ciegas.
- **Discovery Gate** — NO puedes escribir código en `src/app/` sin antes leer al menos un archivo de `indices/`. Serás bloqueado automáticamente.
- **Architect Guard** — Cada Edit/Write es validado en tiempo real. Se bloquean: `*ngIf`, `@Input()`, colores hardcodeados, imports de Supabase en UI, `@angular/animations`, `@keyframes`.
- **Spec Gate** — NO puedes escribir código de producción sin un track activo en `specs/.active` con `plan.md` aprobado. Paths exentos: `specs/`, `indices/`, `docs/`, tests, configs.
- **Plan Injector** — Al editar código de producción, inyecta automáticamente el `plan.md` del track activo como contexto.
- **AC Verifier** — Al terminar el turno, verifica que los Acceptance Criteria del track activo hayan sido cumplidos. Bloquea si quedan ACs abiertos.
- **File Protector** — No puedes modificar los archivos del sistema de hooks (`.claude/hooks/`, `settings.json`, `architect.js`).
- **Bash Guard** — No puedes crear archivos `.ts/.html/.scss` via Bash. Usa Edit/Write.
- **Compact Recovery** — Si el contexto se compacta, los índices se re-inyectan automáticamente (PostCompact).
- **Failure Tracker** — Los errores de tools se registran en `.claude/temp/LESSONS_LEARNED.md` con dedup y rotación automática (max 20).
- **Sync Check** — Al terminar de responder, se verifica si los índices necesitan actualización.
- **Prettier** — Cada archivo editado se formatea automáticamente.

Detalle completo: @docs/HOOKS-SYSTEM.md

## Sistema SDD (Spec-Driven Development)

**Todo código de producción requiere un track activo.** El Spec Gate te bloqueará si intentas editar `src/` sin uno.

### Los 3 tracks

| Track | Cuándo | ID format | Contrato |
|-------|--------|-----------|---------|
| **Spec** | Feature nueva | `NNNN-slug` | `specs/<id>/spec.md` con ACs |
| **Fix** | Bug con ACs afectados | `fix-NNN-slug` | `specs/<id>/fix.md` |
| **Hotfix** | Fix urgente simple | `hotfix-NNN-slug` | Auto-cerrado por hook |

### Slash commands globales

- `/spec-new` → crea `specs/<id>/spec.md`
- `/spec-activate <id>` → activa el track (escribe en `specs/.active`)
- `/spec-plan` → genera `specs/<id>/plan.md` desde la spec
- `/spec-tasks` → desglosa el plan en tareas atómicas
- `/spec-verify` → muestra ACs abiertos vs cumplidos
- `/fix-new <desc>` → crea track fix con `fix.md`
- `/fix-close` → cierra el track tras verificar test de regresión

## Comandos del proyecto

- Dev: `ng serve`
- Build: `ng build`
- Lint: `ng lint`
- Lint arquitectónico: `npm run lint:arch`
- Tests: `npm run test:ci` (sin watch, para auto-validación)
- Supabase local: `npx supabase start`

## Flujo obligatorio y Estado Cero (6 pasos)

0. **CONTEXT SEEDING (Día 0)** — Si es un proyecto/módulo nuevo, DEBES establecer el Lenguaje Ubicuo (`indices/DOMAIN_DICTIONARY.md`) y el modelo de datos (`indices/DATABASE.md`) ANTES de codificar. Si te falta contexto, pídeselo al humano (el Context Guard te obligará a hacerlo si lo olvidas).
1. **DESCUBRIR** — Lee los índices de `indices/` (COMPONENTS, SERVICES, FACADES, MODELS, DECISIONS…). Reutiliza antes de crear. **El Discovery Gate te bloqueará si no lo haces.**
2. **PLANIFICAR** — Define qué vas a tocar sin violar las reglas de arquitectura (generando un `plan.md` vía SDD).
3. **EJECUTAR** — Escribe el código. Reutiliza siempre lo existente primero. Los hooks validarán cada escritura en tiempo real. **Si hay lógica nueva, escribe el `.spec.ts` primero (TDD).**
4. **VALIDAR** — Corre `npm run lint:arch` para auditoría arquitectónica y `npm run test:ci` para tests.
5. **SINCRONIZAR** — Actualiza `indices/*.md` con los componentes/servicios creados. **RESEARCH SYNC:** Registra incondicionalmente cualquier error de runtime descubierto (4xx, 5xx) usando el manejador de errores.
6. **COMMITEAR** — Por cada unidad lógica completada, crea un commit Conventional Commits.

## Skills disponibles

| Skill | Cuándo usar |
|---|---|
| `/plan` | SIEMPRE antes de una tarea no trivial (>2 archivos). Genera task-spec con artefactos afectados, reglas que aplican y criterio de done. |
| `/angular-component` | Crear o refactorizar un componente Angular |
| `/angular-signals` | Implementar estado reactivo con Signals |
| `/sync-indices` | Sincronizar índices al cerrar sesión |
| `/commit` | Crear commit Conventional Commits con los cambios actuales |

## Reglas del proyecto (path-scoped — se cargan automáticamente)

Las reglas viven en `.claude/rules/` con frontmatter `paths:`. Claude Code las inyecta
**solo cuando el archivo editado coincide con el path** — no se cargan todas al inicio.

| Archivos editados | Reglas activas |
|---|---|
| `src/app/**/*.ts` + `.html` | `architecture`, `facades`, `swr-pattern`, `testing-tdd`, `state-management` |
| `src/app/core/models/**` + `core/facades/**` | `models`, `facades` |
| `src/app/shared/**` + `features/**` | `component-selection` |
| `src/app/**/*.html` + `shared/**` + `styles/**` | `visual-system`, `ai-readability` |
| `src/app/features/**` + `layout/**` | `notifications`, `layout-blueprints` |
| `supabase/**` + `core/services/**` | `database` |
| `src/**/*.ts` + `src/**/*.html` + `supabase/**/*.sql` | `gitflow` |

## Referencias (leer bajo demanda — no cargadas automáticamente)

- Stack completo: `docs/TECH-STACK-RULES.md`
- Brand & UI: `docs/BRAND_GUIDELINES.md`
- Sistema de Hooks: `docs/HOOKS-SYSTEM.md`
- Visión del producto: `docs/PRODUCT-VISION.md`
