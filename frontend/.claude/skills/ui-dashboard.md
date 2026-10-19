---
name: ui-dashboard
description: >-
  Generación de Dashboards Analíticos con KPIs, gráficos, Bento Grid,
  animaciones GSAP y componentes obligatorios del Design System.
---

# UI Blueprint: Dashboard Analítico (KPIs + Gráficos)

## Principio Fundamental

**NUNCA** construyas objetos de configuración de Chart.js (`datasets`, `options`, `scales`)
manualmente. **NUNCA** construyas KPIs con divs y texto ad-hoc.
El proyecto inyecta un `HeadlessDashboardService` que transforma datos crudos
en objetos de configuración listos para PrimeNG Charts, y provee componentes
obligatorios del Design System.

## Conexión con el Cerebro Headless

```typescript
// En el .ts del componente, inyectas:
readonly dashboard = inject(HeadlessDashboardService);
readonly gsap = inject(GsapAnimationsService);
// dashboard.kpis()           → Signal<KPI[]> (value, label, trend, icon, color)
// dashboard.barChartData()   → Signal<ChartData> (listo para p-chart)
// dashboard.lineChartData()  → Signal<ChartData>
// dashboard.donutData()      → Signal<ChartData>
// dashboard.segments()       → Signal<Segment[]> (label, color, percentage para leyendas)
// dashboard.topProducts()    → Signal<Product[]>
// dashboard.chartOptions()   → Signal<ChartOptions> (colores del tema, responsivo)
// dashboard.isLoading()      → Signal<boolean>
// dashboard.dateRange         → WritableSignal<{from, to}>
// dashboard.refresh()        → void

// En ngAfterViewInit():
ngAfterViewInit() {
  this.gsap.animateBentoGrid(this.bentoContainer.nativeElement);
}
```

---

## Reglas Estrictas del Design System

### Layout Obligatorio
- El arquetipo correcto es `dashboard` (de `layout-blueprints.md`).
- **OBLIGATORIO:** `.bento-grid` con directiva `[appBentoGridLayout]` como root.
- **OBLIGATORIO:** `.bento-hero.surface-hero` como primer elemento (hero visual).
- Máximo **1** `.card-accent` por sección bento.

### KPIs — COMPONENTE OBLIGATORIO
- **OBLIGATORIO:** Usar `<app-kpi-card>`. **PROHIBIDO** recrear KPIs con divs, `.text-4xl .font-bold` ad-hoc, o clases `.kpi-value` / `.kpi-label` directamente (eso es interno de `app-kpi-card`).
- El pre-write guard emite warning `[M3]` si detecta texto `4xl bold` sin `app-kpi-card`.
- Mínimo 3 `app-kpi-card` en un dashboard.

### Skeleton Loading — COMPONENTE OBLIGATORIO
- **OBLIGATORIO:** Skeleton colocated (`dashboard-skeleton.component.ts`) con `<app-skeleton-block>`.
- **Regla SWR:** NUNCA mostrar skeleton si ya hay datos en caché (`headless.data()` tiene valor).
- Transición skeleton → contenido: directiva `[appAnimateIn]`.

### Empty State
- **OBLIGATORIO:** `<app-empty-state>` en secciones sin datos.

### Gráficos
- **OBLIGATORIO:** `<p-chart [data]="headless.xxxData()" [options]="headless.chartOptions()">`.
- **PROHIBIDO:** Construir el objeto `data` en el HTML o TS.
- Los colores del gráfico se adaptan automáticamente vía `headless.chartOptions()`. **PROHIBIDO** inyectar colores en `[data]`.

### Tokens de Color — PROHIBICIONES (ARCH-08)
- **PROHIBIDO:** `text-green-600`, `text-red-600`, `bg-blue-100`, etc.
- Para tendencias positivas/negativas: `var(--state-success)` / `var(--state-error)`.
- Para fondos de badges: `var(--state-success-bg)` / `var(--state-error-bg)`.

### Iconos
- **OBLIGATORIO:** `<app-icon>` con Lucide en kebab-case. `ariaHidden="true"` si decorativo.
- **PROHIBIDO:** `pi pi-arrow-up` o emojis.

### Animación de Entrada
- **OBLIGATORIO:** `GsapAnimationsService.animateBentoGrid()` en `ngAfterViewInit`.
- **PROHIBIDO:** CSS `transition-*` o `@keyframes` para animaciones de vista.

### Hover de Tarjetas
- **OBLIGATORIO:** Directiva `[appCardHover]` en tarjetas de gráficos y KPIs.
- **PROHIBIDO:** `hover:shadow-md` o `transition-shadow` manual.

---

## Esqueleto Base

```html
<!-- Layout Archetype: dashboard -->
@if(dashboard.isLoading() && !dashboard.kpis().length) {
  <app-dashboard-skeleton />
} @else {
  <div class="bento-grid" [appBentoGridLayout] #bentoContainer [appAnimateIn]>

    <!-- ══════ HERO (bento-hero + surface-hero) ══════ -->
    <div class="bento-hero surface-hero">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold"><!-- TÍTULO --></h1>
          <p class="text-sm opacity-80 mt-1"><!-- SUBTÍTULO --></p>
        </div>
        <div class="flex items-center gap-3">
          <p-datePicker [(ngModel)]="dashboard.dateRange" selectionMode="range"
                        dateFormat="dd/mm/yy" placeholder="Rango de fechas"
                        [showIcon]="true" class="w-64" />
          <button (click)="dashboard.refresh()" class="btn-secondary"
                  aria-label="Actualizar datos" data-llm-action="refresh-dashboard">
            <app-icon name="refresh-cw" [size]="16" ariaHidden="true" />
          </button>
        </div>
      </div>
    </div>

    <!-- ══════ KPIs (bento-square × N, mínimo 3) ══════ -->
    @for(kpi of dashboard.kpis(); track kpi.label) {
      <div class="bento-square">
        <app-kpi-card
          [value]="kpi.value"
          [label]="kpi.label"
          [trend]="kpi.trend"
          [icon]="kpi.icon"
          [suffix]="kpi.suffix"
          appCardHover />
      </div>
    }

    <!-- ══════ GRÁFICO DE BARRAS (bento-wide) ══════ -->
    <div class="bento-wide">
      <div class="card h-full" appCardHover>
        <div class="flex justify-between items-center mb-4">
          <div>
            <h3 class="font-bold text-primary"><!-- TÍTULO GRÁFICO --></h3>
            <p class="text-xs text-muted mt-0.5"><!-- SUBTÍTULO --></p>
          </div>
        </div>
        <p-chart type="bar" [data]="dashboard.barChartData()"
                 [options]="dashboard.chartOptions()" height="260px" />
      </div>
    </div>

    <!-- ══════ GRÁFICO DE LÍNEAS (bento-wide) ══════ -->
    <div class="bento-wide">
      <div class="card h-full" appCardHover>
        <h3 class="font-bold text-primary mb-4"><!-- TÍTULO --></h3>
        <p-chart type="line" [data]="dashboard.lineChartData()"
                 [options]="dashboard.chartOptions()" height="260px" />
      </div>
    </div>

    <!-- ══════ DONUT (bento-square) ══════ -->
    <div class="bento-square">
      <div class="card h-full flex flex-col" appCardHover>
        <h3 class="font-bold text-primary mb-4">Segmentación</h3>
        <div class="flex-1 flex items-center justify-center">
          <p-chart type="doughnut" [data]="dashboard.donutData()"
                   [options]="dashboard.chartOptions()" width="200px" height="200px" />
        </div>
        <!-- Leyenda Custom -->
        <div class="mt-4 space-y-2">
          @for(seg of dashboard.segments(); track seg.label) {
            <div class="flex justify-between items-center text-sm">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full" [style.background-color]="seg.color"></div>
                <span class="text-secondary">{{ seg.label }}</span>
              </div>
              <span class="font-medium text-primary">{{ seg.percentage }}%</span>
            </div>
          }
        </div>
      </div>
    </div>

    <!-- ══════ TABLA RESUMEN (bento-feature) ══════ -->
    <div class="bento-feature">
      <div class="card h-full p-0 overflow-hidden" appCardHover>
        <div class="p-4 border-b border-default flex justify-between items-center">
          <h3 class="font-bold text-primary">Top Productos</h3>
          <a class="text-sm font-medium cursor-pointer"
             [style.color]="'var(--ds-brand)'">Ver todos →</a>
        </div>
        <!-- Para tablas simples (<10 filas, sin paginación), usar HTML nativo -->
        <table class="w-full" aria-label="Top productos por ventas">
          <thead>
            <tr class="border-b border-default text-left">
              <th class="p-4 text-xs font-semibold text-muted uppercase tracking-wider">Producto</th>
              <th class="p-4 text-xs font-semibold text-muted uppercase tracking-wider">Ventas</th>
              <th class="p-4 text-xs font-semibold text-muted uppercase tracking-wider">Progreso</th>
            </tr>
          </thead>
          <tbody>
            @for(product of dashboard.topProducts(); track product.id) {
              <tr class="border-b border-subtle hover:bg-elevated transition-colors">
                <td class="p-4 font-medium text-primary text-sm">{{ product.name }}</td>
                <td class="p-4 text-sm text-secondary">{{ product.sales | number }}</td>
                <td class="p-4">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-subtle rounded-full overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-500"
                           [style.width.%]="product.progress"
                           [style.background-color]="'var(--ds-brand)'">
                      </div>
                    </div>
                    <span class="text-xs text-muted w-8 text-right">{{ product.progress }}%</span>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>

  </div>
}
```

## Regla de Umbral: Tablas Simples vs PrimeNG
- **< 10 filas, sin paginación ni filtros:** Usar `<table>` HTML nativo con clases del DS.
- **≥ 10 filas, con paginación/filtros:** Usar `<p-table>` con el Blueprint de `ui-table.md`.
