# Tasks 0001 — Visor Cartográfico Limpio, Puente Bidireccional y Ficha 360° Reactiva con Prorrateo

> **Spec:** [spec.md](./spec.md) · **Plan:** [plan.md](./plan.md)  
> **Created:** 2026-10-18  

---

## Fase 1 — Limpieza del Mapa e Inyección de Puente en Python

- [x] **T1.1** — Agregar soporte CSS para `.embed-mode` en `src/domain/physical/map_generator.py`
  - **AC ref:** AC1, AC2
  - **DoD:**
    - [x] Clases `.sidebar`, `.sidebar-toggle-btn`, `.legend-card`, y buscador ocultos cuando `body.embed-mode` está activo.
    - [x] Detección automática de `embed=true` o `window.self !== window.top`.

- [x] **T1.2** — Inyectar `postMessage` emisor al hacer clic en cuenca en `map_generator.py`
  - **AC ref:** AC3
  - **DoD:**
    - [x] En la función `selectBasin(b)` de Leaflet, se emite `{ type: 'CUENCA_SELECTED', cuencaCodigo: b.codigo_dga, cuencaNombre: b.nombre }` al `window.parent`.

- [x] **T1.3** — Inyectar `postMessage` receptor para alternar capas en `map_generator.py`
  - **AC ref:** AC4
  - **DoD:**
    - [x] Listener de `message` que recibe `{ type: 'TOGGLE_LAYER', layerId, visible }` y alterna capas de Leaflet en tiempo real.

---

## Fase 2 — Puente Bidireccional en Angular

- [x] **T2.1** — Configurar `water-map.component.ts` para solicitar `/mapa?embed=true`
  - **AC ref:** AC1, AC2
  - **DoD:**
    - [x] URL del iframe incluye query param `embed=true`.

- [x] **T2.2** — Implementar listener de eventos `message` en `water-map.component.ts`
  - **AC ref:** AC3
  - **DoD:**
    - [x] Al recibir `CUENCA_SELECTED`, llamar a `WaterMapFacade.selectCuenca()` y emitir evento de selección.
    - [x] Limpiar listener en `ngOnDestroy` para evitar fugas de memoria.

- [x] **T2.3** — Conectar selector de capas flotante de Angular hacia el iframe
  - **AC ref:** AC4
  - **DoD:**
    - [x] Método `onToggleLayer` envía `postMessage` al iframe para encender/apagar capas.

---

## Fase 3 — Simulador Reactivo de Prorrateo en Ficha 360°

- [x] **T3.1** — Crear componente `prorrateo-simulator.component.ts`
  - **AC ref:** AC5, AC6
  - **DoD:**
    - [x] Sliders de Caudal del Río (L/s) y Demanda APR.
    - [x] Respeto de prelación del Art. 5 bis (100% vital antes de otros usos).
    - [x] Visualización con barras de progreso y porcentajes.

- [x] **T3.2** — Integrar simulador en `water-copilot.component.ts` (pestaña Ficha 360°)
  - **AC ref:** AC3, AC5
  - **DoD:**
    - [x] Al seleccionar una cuenca, la pestaña Ficha 360° se activa y muestra el simulador con datos reactivos.

---

## Fase 4 — Validación y Cierre

- [x] **T4.1** — Verificación visual y pruebas de integración
  - **AC ref:** AC1-AC7
  - **DoD:**
    - [x] Mapa sin paneles sobrepuestos ni leyendas gigantes en modo embed.
    - [x] Clic en cuenca abre Ficha 360° y carga datos.
    - [x] Compilación `npm run build:raw` con 0 errores.
