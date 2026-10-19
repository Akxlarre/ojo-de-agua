# GitHub Copilot Instructions — frontend

Read `AGENTS.md` in the project root before starting any task. It contains the mandatory session workflow, full architecture rules, and anti-patterns for this project.

## Critical Rules (Never Violate)

- **Facade Pattern**: NEVER inject `SupabaseService` or `HttpClient` in `features/` or `shared/` — always use a `*FacadeService` from `core/`
- **Template syntax**: NEVER use `*ngIf`, `*ngFor`, `@Input()`, `@Output()` — use `@if`, `@for`, `input()`, `output()`
- **Color tokens**: NEVER hardcode colors (`text-red-500`, `#hex`) — use `text-primary`, `bg-surface`, `var(--ds-brand)`
- **Animations**: NEVER use `@angular/animations` — use `GsapAnimationsService`
- **Change detection**: ALL components must declare `changeDetection: ChangeDetectionStrategy.OnPush`
- **Reuse first**: Check `indices/` before creating any new component, service, facade, or model
