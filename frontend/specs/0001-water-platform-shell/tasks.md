# Tareas de Implementación — Track 0001 (Water Platform Shell)

**Track:** `0001-water-platform-shell`  
**Estado:** In Progress  

---

## Fase 1 — Modelos y Tipos de Dominio (Core)
- [x] **Task 1.1:** Crear `src/app/core/models/water-domain.model.ts` con interfaces tipadas para `Cuenca`, `SistemaAPR`, `Glaciar`, `DepositoRelave`, `DecretoEscasez` e `IndiceSeguridadHidrica`.
- [x] **Task 1.2:** Crear `src/app/core/models/water-chat.model.ts` con interfaces para `ChatMessage`, `ThoughtStep`, `DomainArtifact` y `ChatThread`.

## Fase 2 — Servicios e Infraestructura HTTP
- [x] **Task 2.1:** Crear `src/app/core/services/water/water-api.service.ts` para conectar con los endpoints de FastAPI (`/api/cuencas`, `/api/sistemas-apr`, `/api/glaciares`, `/api/diagnostico/cuenca/{id}`).
- [x] **Task 2.2:** Crear `src/app/core/services/ai/water-ai-stream.service.ts` con soporte para streaming Server-Sent Events (SSE).

## Fase 3 — Facades con Signals y TDD (Core)
- [x] **Task 3.1:** Escribir suite de pruebas unitarias `src/app/core/facades/water-map.facade.spec.ts`.
- [x] **Task 3.2:** Implementar `src/app/core/facades/water-map.facade.ts` con Signals para capas activas, cuenca seleccionada y estado de carga.
- [x] **Task 3.3:** Escribir suite de pruebas unitarias `src/app/core/facades/water-chat.facade.spec.ts`.
- [x] **Task 3.4:** Implementar `src/app/core/facades/water-chat.facade.ts` con streaming reactivo, estado de pensamiento del agente e inyección de artefactos de UI.

## Fase 4 — Componentes Presentacionales (Shared Dumb Components)
- [x] **Task 4.1:** Implementar `chat-bubble.component.ts` y su skeleton colocated.
- [x] **Task 4.2:** Implementar `chat-thought.component.ts` con acordeón animado por GSAP.
- [x] **Task 4.3:** Implementar `cuenca-card.component.ts` (semáforo ISH y alertas de sequía) y su skeleton.
- [x] **Task 4.4:** Implementar `layer-selector.component.ts` con switches semánticos de PrimeNG.

## Fase 5 — Smart Features y Layout Shell
- [x] **Task 5.1:** Implementar `water-map.component.ts` con integración de mapas y renderizado condicional por zoom.
- [x] **Task 5.2:** Implementar `water-copilot.component.ts` coordinando la pestaña del chat y la ficha 360°.
- [x] **Task 5.3:** Ensamblar `water-platform.component.ts` en la ruta `/` o `/app` con Bento Grid 60/40.
- [x] **Task 5.4:** Validar build final (`npm run build`), auditoría arquitectónica (`npm run lint:arch`) y tests (`npm run test:ci`).
