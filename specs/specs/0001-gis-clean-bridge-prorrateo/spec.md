# Spec 0001 — Visor Cartográfico Limpio, Puente Bidireccional y Ficha 360° Reactiva con Prorrateo

> **Status:** in_progress  
> **Created:** 2026-10-18  
> **Owner:** Antigravity AI  
> **Priority:** P1  
> **Origen:** Asignación `ASG-001`

---

## 1. Contexto de Negocio

**Plataforma:** Ojo de Agua — Atlas & Copiloto de Seguridad Hídrica de Chile.  
**Personas Afectadas:**
- Directores de Juntas de Vigilancia de Ríos (JVR).
- Comités de Agua Potable Rural (APR / SSR).
- Analistas y Fiscalizadores de la DGA / SMA / MOP.

**Problema que Resuelve:**
Actualmente, el mapa satelital se despliega dentro de un `<iframe>` embebiendo un dashboard HTML completo originado en Python (`map_generator.py`). Esto causa una severa "colisión de interfaces":
1. El mapa contiene una barra lateral blanca rígida que tapa el 70% del visor geográfico.
2. Contiene una leyenda hidrológica estática sobredimensionada que colisiona con los widgets de Angular.
3. El mapa y la columna derecha (Ficha 360° y Copiloto AI) están totalmente desconectados; al hacer clic en un río o cuenca en el mapa, Angular no se entera ni actualiza su estado.
4. El simulador de prorrateo legal (Art. 5 bis y 18 del Código de Aguas) está atrapado dentro del iframe en un formulario estático en lugar de ser un componente interactivo de Angular con gráficos en tiempo real.

---

## 2. Alcance y Solución Técnica

1. **Modo Clean Canvas (`embed=true`):**
   - El generador de mapas [`src/domain/physical/map_generator.py`](file:///c:/Users/Akxlarre/Desktop/rios/src/domain/physical/map_generator.py) detecta el parámetro `embed=true` (o vía clase CSS `.embed-mode`).
   - Oculta la barra lateral blanca interna, el botón toggle flotante y la leyenda estática gigante.
   - Deja el mapa a pantalla completa al 100% como un lienzo cartográfico satelital limpio y despejado.
2. **Puente Bidireccional (`window.postMessage`):**
   - **Mapa → Angular:** Al hacer clic en un polígono de cuenca o marcador en Leaflet, el iframe emite:
     `{ type: 'CUENCA_SELECTED', cuencaCodigo: '057', cuencaNombre: 'Río Maipo', region: 'Metropolitana' }`.
   - Angular escucha el mensaje, actualiza `WaterMapFacade.selectCuenca('057')` y cambia la pestaña activa a **"Ficha 360° Cuenca"**.
   - **Angular → Mapa:** Al encender/apagar una capa en el selector flotante de Angular ("Capas de Información"), Angular emite `{ type: 'TOGGLE_LAYER', layerId: 'relaves', visible: boolean }` hacia el iframe, manipulando Leaflet en tiempo real.
3. **Simulador de Prorrateo Legal Reactivo en Ficha 360°:**
   - Componente interactivo [`prorrateo-simulator.component.ts`](file:///c:/Users/Akxlarre/Desktop/rios/frontend/src/app/shared/components/water/prorrateo-simulator/prorrateo-simulator.component.ts) embebido en la Ficha 360°.
   - Sliders táctiles con valores en tiempo real (L/s).
   - Cálculo instantáneo respetando la prelación del Consumo Humano (Art. 5 bis: APR tiene prioridad 100%) y prorrateo proporcional del remanente entre juntas de regantes y canales matrices.

---

## 3. Criterios de Aceptación (AC)

- **AC1 — Modo Limpio en Iframe:** Al cargar `/mapa?embed=true`, el visor Leaflet no muestra la barra lateral blanca, ni el botón hamburguesa, ni la leyenda gigante inferior.
- **AC2 — Lienzo al 100%:** El mapa satelital cubre todo el ancho y alto disponible sin márgenes vacíos ni scrollbars internos innecesarios.
- **AC3 — Clic en Cuenca sincroniza Ficha 360°:** Hacer clic en cualquier cuenca (ej: Maipo 057, Choapa 047) emite `CUENCA_SELECTED` y Angular abre de inmediato la pestaña "Ficha 360° Cuenca" con sus métricas.
- **AC4 — Control de Capas desde Angular:** Conmutar los switches de "839 Relaves Mineros", "2.238 APRs" o "Glaciares" en el widget de Angular activa/desactiva la capa correspondiente dentro de Leaflet.
- **AC5 — Simulador de Prorrateo Integrado:** La Ficha 360° presenta un simulador reactivo con sliders de Caudal Afluente y Demanda Vital APR.
- **AC6 — Garantía Legal de Consumo Humano:** El simulador asegura que la demanda de APR se cubra al 100% antes de distribuir cualquier gota a canales o industria.
- **AC7 — Cero Errores de Consola:** No se generan errores de violación de CSP ni advertencias de script cross-origin no capturadas.
