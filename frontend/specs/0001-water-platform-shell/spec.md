# Spec 0001 — Water Platform Shell & Copilot Workspace

**Status:** Approved  
**Created:** 2026-10-18  
**Priority:** High  
**Parent Req:** `context/requirements.md` (REQ-001, REQ-002, REQ-003)

---

## 1. Contexto y Justificación

La plataforma **Ojo de Agua** requiere una interfaz principal empresarial basada en un **Split Workspace (Bento Grid)**:
- **Lado Izquierdo (60%):** Visor GIS interactivo para renderizar cuencas, APRs, relaves y glaciares.
- **Lado Derecho (40%):** Panel dinámico conmutador entre el **Copiloto AI (Chat)** y la **Ficha 360° Territorial**.

Este layout permite que la cartografía y el copiloto dialoguen bidireccionalmente mediante eventos reactivos (Signals).

---

## 2. Historias de Usuario

* **US-1:** Como usuario quiero ver una barra superior (Topbar) con buscador híbrido, selector de cuenca rápida y conmutador de tema visual.
* **US-2:** Como usuario quiero explorar el mapa de Chile con capas activables para identificar cuencas con decreto de sequía y APRs en riesgo.
* **US-3:** Como usuario quiero abrir el panel del Copiloto AI para hacer preguntas territoriales y recibir streaming con widgets interactivos de dominio.
* **US-4:** Como usuario quiero hacer clic en cualquier cuenca del mapa para que el panel derecho cargue su Ficha Radiográfica 360° de seguridad hídrica.

---

## 3. Criterios de Aceptación (Acceptance Criteria)

- [x] **AC-01 (Layout Shell):** Implementar `AppShellComponent` en layout dividido con `Topbar`, contenedor de mapa `WaterMapComponent` (60%) y contenedor de panel lateral `WaterCopilotDrawerComponent` (40%).
- [x] **AC-02 (Signals & Facades):** Crear `WaterMapFacadeService` y `WaterChatFacadeService` en `core/facades/`, exponiendo el estado mediante Signals (`signal()`, `computed()`) y respetando `ARCH-01` a `ARCH-10`.
- [x] **AC-03 (Design System Semántico):** Aplicar tokens semánticos de Tailwind v4 (`bg-base`, `bg-surface`, `bg-elevated`, `text-primary`, `text-muted`, `brand`) sin colores hardcodeados ni `@keyframes` arbitrarios.
- [x] **AC-04 (Animaciones GSAP):** Conectar transiciones de apertura/cierre del panel y animación de entrada de mensajes mediante `GsapAnimationsService`.
- [x] **AC-05 (Skeletons Colocados):** Todo Dumb Component que cargue datos asíncronos (ej. Ficha 360° o mensaje del chat) debe tener su archivo `*-skeleton.component.ts` con idéntico layout.
- [x] **AC-06 (TDD Core):** Toda Facade y Servicio Core debe contar con su suite de pruebas unitarias `.spec.ts`.
