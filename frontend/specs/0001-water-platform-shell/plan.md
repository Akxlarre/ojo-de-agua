# Plan 0001 — Implementación Técnica del Shell y Copiloto Workspace

**Track:** `0001-water-platform-shell`  
**Spec:** `specs/0001-water-platform-shell/spec.md`  
**Architect:** Koa Agent Blueprint  

---

## 1. Arquitectura de Componentes

```
src/app/
├── core/
│   ├── facades/
│   │   ├── water-map.facade.ts           # Estado cartográfico (cuencas, capas, selección)
│   │   ├── water-map.facade.spec.ts      # Tests unitarios TDD
│   │   ├── water-chat.facade.ts          # Estado del chat (mensajes, streaming SSE, pensamiento)
│   │   └── water-chat.facade.spec.ts     # Tests unitarios TDD
│   └── models/
│       ├── water-domain.model.ts         # Tipos: Cuenca, APR, Glaciar, Relave, ISH
│       └── water-chat.model.ts           # Tipos: ChatMessage, ThoughtStep, DomainArtifact
│
├── features/
│   ├── water-platform/                   # Smart Feature Page
│   │   ├── water-platform.component.ts   # OnPush, coordina el Split Workspace
│   │   ├── water-platform.component.html # Layout 60/40 con @if/@for
│   │   └── water-platform.component.scss # Bento grid mixins
│   ├── water-map/                        # Smart Sub-Feature (Visor GIS)
│   │   ├── water-map.component.ts        # Renderiza Leaflet / MapLibre
│   │   └── water-map-skeleton.component.ts # Skeleton colocado
│   └── water-copilot/                    # Smart Sub-Feature (Chat + Ficha 360°)
│       ├── water-copilot.component.ts    # Conmutador de pestañas Chat vs Ficha 360°
│       └── water-copilot-skeleton.component.ts
│
└── shared/components/
    ├── chat/
    │   ├── chat-bubble.component.ts      # Dumb message bubble + markdown
    │   ├── chat-thought.component.ts     # Acordeón colapsable GSAP de pensamiento
    │   └── chat-input.component.ts       # Input elástico con PrimeNG
    └── water/
        ├── cuenca-card.component.ts      # Card de resumen ISH
        ├── layer-selector.component.ts   # Switches de capas del mapa
        └── cuenca-card-skeleton.component.ts
```

---

## 2. Reglas del Blueprint que Aplican

* **`ARCH-01` & `ARCH-02`:** Prohibido inyectar `HttpClient` o `SupabaseClient` en componentes. Todo pasa por `WaterMapFacadeService` y `WaterChatFacadeService`.
* **`ARCH-03`:** TDD obligatorio para `water-map.facade.spec.ts` y `water-chat.facade.spec.ts`.
* **`ARCH-04`:** `ChangeDetectionStrategy.OnPush` en el 100% de los componentes.
* **`ARCH-05` & `ARCH-07`:** GSAP exclusivo vía `GsapAnimationsService` para transiciones del panel y cards. Cero `@keyframes` en SCSS de app.
* **`ARCH-06`:** Prohibido `*ngIf` / `*ngFor`; uso estricto de `@if` y `@for`.
* **`ARCH-08`:** Prohibido colores Tailwind hardcodeados; usar tokens semánticos (`bg-base`, `bg-surface`, `bg-elevated`, `text-primary`, `brand`).

---

## 3. Plan de Verificación y Criterios de Done

1. `npm run test:ci` pasa sin fallas en todas las facades core.
2. `npm run build` compila con 0 errores y warnings bajo presupuesto.
3. Validación de AST con `npm run lint:arch`.
4. Sincronización de índices con `npm run claude:sync`.
