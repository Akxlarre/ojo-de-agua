# frontend — AI Agent Guidelines

> **Universal entry point** for all AI coding assistants (OpenCode, Cursor, Windsurf, Copilot, Codex, etc.).
> If you are Claude Code: `.claude/CLAUDE.md` extends this file with hooks, skills, and memory — use that instead.

## Tech Stack

- Angular 20+ — standalone components, signal-based reactivity, `@if`/`@for` control flow
- Tailwind CSS v4 — semantic tokens only (never arbitrary colors)
- PrimeNG — complex UI components (tables, dropdowns, calendars)
- Supabase — PostgreSQL + Auth + Realtime (optional via `--with-supabase`)
- GSAP — animations via `GsapAnimationsService` (optional via `--with-gsap`)

---

## Mandatory Session Workflow

**Follow these 5 steps every session. Do not skip or reorder them.**

### 1. DISCOVER — Read before you write

Before touching any file in `src/app/`, read:

- `indices/COMPONENTS.md` — what UI components already exist
- `indices/SERVICES.md` — what services and facades already exist
- `indices/FACADES.md` — facade inventory
- `indices/MODELS.md` — TypeScript interfaces and models
- `indices/DATABASE.md` — Supabase tables and RLS policies (if applicable)
- `indices/ANTI-PATTERNS.md` — known pitfalls
- `indices/DIRECTIVES.md` — custom directives
- `indices/STYLES.md` — shared styles and tokens
- `indices/PIPES.md` — custom pipes
- `indices/STORES.md` — state stores (if applicable)

Then read context files if they exist:
- `context/domain.md` — business domain, entities, terminology
- `context/brief.md` — what is being built **today** (session objective)
- `context/learnings.md` — validated insights from past sessions

**Rule: never create something that already exists. Reuse first, create second.**

### 2. PLAN — Define scope before coding

Before writing a single line of code:
- Identify which files you will touch
- Confirm you are not violating architecture rules (see below)
- If the task touches more than 2 files, state your plan explicitly

### 3. EXECUTE — Write code following all rules

- Reuse existing components, facades, and models
- Every new component goes in the correct folder (see Folder Structure)
- Hooks validate writes automatically in Claude Code — in other tools, self-enforce

### 4. VALIDATE — Verify architecture compliance

After writing code:
- Run `npm run lint:arch` for a full architectural audit
- Confirm no anti-patterns were introduced (see Anti-Patterns section)

### 5. SYNC — Update indices

At the end of every session, update the relevant `indices/*.md` files with new components, services, facades, models, or database changes you created.

---

## Folder Structure (canonical — never deviate)

```
src/
├── app/
│   ├── core/       # Facades, Services, Guards, Models, Utils (infrastructure)
│   ├── features/   # Smart Components (pages — inject Facades, coordinate Dumb)
│   ├── shared/     # Dumb Components (presentational — input()/output() only)
│   └── layout/     # App shell, sidebar, topbar
├── styles/
│   ├── tokens/     # SCSS variables — NEVER hardcode in components
│   └── vendors/    # PrimeNG overrides
supabase/
└── migrations/     # Idempotent SQL — NEVER alter DB manually
```

**Never invent folders outside this structure.**

---

## Architecture Rules

### Facade Pattern (mandatory)

- UI components **NEVER** inject `SupabaseService`, `HttpClient`, or any data client directly
- **ALWAYS** use a `*FacadeService` in `core/` that centralizes state via Signals
- Facades expose data to templates with `toSignal()`
- Facades capture errors with `catchError` and expose an `error` signal

```typescript
@Injectable({ providedIn: 'root' })
export class ExampleFacade {
  private svc = inject(ExampleService);
  readonly items = toSignal(this.svc.items$, { initialValue: [] });
  readonly error = signal<string | null>(null);

  async create(data: CreateDto): Promise<void> {
    const result = await this.svc.create(data);
    if (result.error) this.error.set(result.error.message);
  }
}
```

### Change Detection

- `changeDetection: ChangeDetectionStrategy.OnPush` on **every** component — no exceptions

### Signals & RxJS

| Use | For |
|---|---|
| `signal()` | Synchronous UI state (counters, modals, toggles) |
| `computed()` | Derived state |
| `RxJS` | Async flows in Services |
| `toSignal()` | Expose RxJS streams to templates (in Facades) |

### Template Syntax

| NEVER use | ALWAYS use instead |
|---|---|
| `*ngIf` | `@if` |
| `*ngFor` | `@for` |
| `ngSwitch` | `@switch` |
| `@Input()` | `input()` |
| `@Output()` | `output()` |
| `[ngClass]` | `[class.name]="expr()"` |
| `[ngStyle]` | `[style.prop]="expr()"` |

### Smart vs Dumb Components

- **Dumb (`shared/`)**: Only `input()` and `output()`. No service/facade injection.
- **Smart (`features/`)**: Inject Facades. Coordinate Dumb components.
- **Skeleton**: Every async Dumb component has a colocated `{name}-skeleton.component.ts`

---

## Visual System

### Color Tokens (NEVER hardcode)

| NEVER | ALWAYS |
|---|---|
| `text-red-500`, `text-blue-200` | `text-primary`, `text-secondary`, `text-muted` |
| `bg-[#hex]`, arbitrary hex | `bg-base` (page), `bg-surface` (cards/modals) |
| any Tailwind color utility | `var(--ds-brand)`, `var(--color-primary)` |

### Component Priority

1. Check `indices/COMPONENTS.md` — does it already exist?
2. Use **PrimeNG** — for complex inputs, tables, calendars, dropdowns
3. Build custom — only if 1 and 2 don't cover the need

### Layout

- Container: `.bento-grid` + directive `[appBentoGridLayout]`
- Children: `.bento-square`, `.bento-wide`, `.bento-tall`, `.bento-feature`, `.bento-hero`
- Only **ONE** `.card-accent` per bento section
- Cards: `.card` (base), `.card-accent` (branded top border), `.card-tinted` (KPI highlight)

### Icons

- NEVER use emojis as UI icons
- ALWAYS use `<app-icon name="kebab-case" [size]="16" />`
- Names match lucide.dev kebab-case (`"trending-up"`, `"trash-2"`)

### Animations

- Without GSAP: CSS `.animate-fade-in-up`, `.animate-stagger` + `withViewTransitions()` in router
- With GSAP: `GsapAnimationsService` in `ngAfterViewInit` — methods: `animateBentoGrid()`, `animateHero()`, `animateCounter()`, `addCardHover()`
- **NEVER** use `@angular/animations` or `@keyframes` for view entry animations
- Always `clearProps: 'transform'` after movement animations
- Always respect `prefers-reduced-motion`

---

## Database (Supabase)

- Migrations in `supabase/migrations/` — idempotent SQL files
- Naming: `YYYYMMDDHHMMSS_domain_action_description.sql`
- RLS (Row Level Security) **required** on every table
- **NEVER** modify the database manually — always via migrations
- Document every new table in `indices/DATABASE.md`

---

## Testing (Vitest)

- Co-located `.spec.ts` files next to source
- Facades and Services: mandatory unit tests
- Utils and pure functions: mandatory tests
- Dumb components with `computed()`: mandatory tests
- Use `vi.fn()` for mocks — not `jasmine.createSpy`
- Use `LucideAngularModule.pick({...})` in TestBed imports

---

## Anti-Patterns (stop and fix if you see these)

| # | Never do | Do instead |
|---|---|---|
| AP-001 | `[ngClass]="{'active': x}"` | `[class.active]="x()"` |
| AP-002 | `@Input() value` / `@Output() change` | `input()` / `output()` |
| AP-003 | `inject(SupabaseService)` in `features/` or `shared/` | Use a `*FacadeService` |
| AP-004 | `text-red-500`, `bg-blue-200`, `#hex` in templates | Semantic tokens only |
| AP-005 | `import { animations } from '@angular/animations'` | `GsapAnimationsService` |

---

## Note for Claude Code users

When running Claude Code, `.claude/CLAUDE.md` extends this file with:
- **Hooks** that automatically enforce rules (Discovery Gate, Architect Guard, File Protector, etc.)
- **Skills** (`/angular-component`, `/angular-signals`, `/sync-indices`, `/plan`)
- **Automatic index sync** reminders on session end
- **Context Guardian** that monitors staleness of `context/` files

If you are not using Claude Code, enforce these rules manually — no automation backs you up.
