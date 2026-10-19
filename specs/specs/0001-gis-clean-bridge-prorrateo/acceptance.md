# Acceptance 0001 — Visor Cartográfico Limpio, Puente Bidireccional y Ficha 360° Reactiva con Prorrateo

> **Spec:** [spec.md](./spec.md) · **Tasks:** [tasks.md](./tasks.md)  
> **Status:** Verified (Pasa 7/7 Criterios)  
> **Fecha de Validación:** 2026-10-18  

---

## Criterios de Aceptación y Resultados

| ID | Criterio | Verificación | Estado |
|---|---|---|---|
| **AC1** | Modo Limpio en Iframe | Inspección de HTML: `.embed-mode` oculta `.sidebar`, `.sidebar-toggle-btn`, `.legend-card` y `.top-nav` cuando se ejecuta dentro de un iframe o con `?embed=true`. | ✅ PASA |
| **AC2** | Lienzo al 100% | `#map` se expande con `width: 100vw; height: 100vh; position: absolute;` sin márgenes residuales. | ✅ PASA |
| **AC3** | Clic en Cuenca sincroniza Ficha 360° | `selectBasin` emite evento `CUENCA_SELECTED` vía `postMessage` al `window.parent`. `WaterMapComponent` captura el mensaje, selecciona la cuenca en `WaterMapFacade` y conmuta automáticamente a la pestaña `Ficha 360°`. | ✅ PASA |
| **AC4** | Control de Capas desde Angular | Al conmutar una capa en `app-layer-selector`, Angular emite `TOGGLE_LAYER` al iframe, el cual activa o desactiva la capa correspondiente en Leaflet (`layerCuencas`, `layerApr`, `layerRelaves`, etc.). | ✅ PASA |
| **AC5** | Simulador de Prorrateo Integrado | `ProrrateoSimulatorComponent` implementado con sliders reactivos para Caudal Afluente y Demanda APR, integrado dentro de la Ficha 360°. | ✅ PASA |
| **AC6** | Garantía Legal de Consumo Humano | Cálculo reactivo determinista que garantiza al 100% la demanda vital de APR (Art. 5 bis) antes de distribuir el remanente a regadío. | ✅ PASA |
| **AC7** | Cero Errores de Compilación y Consola | `npm run build:raw` compila con 0 errores de TypeScript y plantillas. Servidor Uvicorn y Angular dev server activos y respondiendo 200 OK. | ✅ PASA |
