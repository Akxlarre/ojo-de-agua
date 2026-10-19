# Plan 0001 — Visor Cartográfico Limpio, Puente Bidireccional y Ficha 360° Reactiva con Prorrateo

> **Spec:** [spec.md](./spec.md) · **Tasks:** [tasks.md](./tasks.md)  
> **Created:** 2026-10-18  

---

## Fases de Implementación

### Fase 1: Limpieza del Mapa e Inyección de Puente en Python (`map_generator.py`)
1. Agregar estilos CSS para `.embed-mode`:
   - `.sidebar { display: none !important; }`
   - `.sidebar-toggle-btn { display: none !important; }`
   - `.legend-card { display: none !important; }`
   - `.search-container { display: none !important; }`
2. En el script del mapa:
   - Detectar `const isEmbed = new URLSearchParams(window.location.search).get('embed') === 'true' || window.self !== window.top;`
   - Si `isEmbed` es verdadero, agregar la clase `embed-mode` a `document.body`.
3. Inyectar `window.parent.postMessage({ type: 'CUENCA_SELECTED', cuencaCodigo: ... }, '*')` dentro del callback de clic de cuencas (`selectBasin`).
4. Inyectar receptor `window.addEventListener('message', (event) => ...)` para manejar `{ type: 'TOGGLE_LAYER', layerId, visible }`.

### Fase 2: Componente Mapa y Puente en Angular
1. En [`water-map.component.ts`](file:///c:/Users/Akxlarre/Desktop/rios/frontend/src/app/features/water-platform/components/water-map/water-map.component.ts):
   - Cargar `mapUrl = '/mapa?embed=true&t=' + Date.now()`.
   - Implementar listener de eventos `window.addEventListener('message', this.handleMapMessage)`.
   - Al recibir `CUENCA_SELECTED`, llamar a `WaterMapFacade.selectCuenca(codigo)` y notificar a la columna de Copiloto/Ficha.
2. Inyectar método para enviar mensajes al iframe cuando se ejecuta `toggleLayer` en el selector de capas.

### Fase 3: Simulador Reactivo de Prorrateo en Angular
1. Crear [`prorrateo-simulator.component.ts`](file:///c:/Users/Akxlarre/Desktop/rios/frontend/src/app/shared/components/water/prorrateo-simulator/prorrateo-simulator.component.ts):
   - Inputs reactivos con `signal`: caudal del río (L/s), caudal ecológico mínimo, demanda APR.
   - Cálculo determinista según Art. 5 bis (prioridad Consumo Humano 100%, remanente repartido entre canales).
   - Barras de distribución visual con porcentajes y colores temáticos.
2. Integrar el simulador dentro de la pestaña `Ficha 360°` en [`water-copilot.component.ts`](file:///c:/Users/Akxlarre/Desktop/rios/frontend/src/app/features/water-platform/components/water-copilot/water-copilot.component.ts).

### Fase 4: Validación y Cierre
1. Verificar que el mapa se vea limpio y sin paneles invasivos.
2. Probar interacción de clic y cambio de pestaña automático.
3. Probar switches del selector de capas y verificar que los elementos del mapa se oculten/muestren.
4. Compilar con `npm run build:raw` para asegurar 0 errores.
