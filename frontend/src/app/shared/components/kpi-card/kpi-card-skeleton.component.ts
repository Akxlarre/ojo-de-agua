import { Component, ChangeDetectionStrategy } from '@angular/core';
import { SkeletonBlockComponent } from '../skeleton-block/skeleton-block.component';

/**
 * KpiCardSkeletonComponent — Skeleton colocated de KpiCardComponent.
 *
 * Refleja la estructura del KPI card para evitar layout shift durante la carga.
 * Úsalo en la misma celda bento mientras esperas los datos del Facade.
 *
 * @example
 * @if (facade.loading()) {
 *   <app-kpi-card-skeleton />
 * } @else {
 *   <app-kpi-card [value]="facade.totalUsers()" label="Usuarios activos" [appAnimateIn] />
 * }
 */
@Component({
  selector: 'app-kpi-card-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SkeletonBlockComponent],
  template: `
    <div class="card card-tinted flex flex-col gap-2 h-full" aria-busy="true" aria-label="Cargando métrica">
      <!-- kpi-label placeholder -->
      <app-skeleton-block variant="text" width="55%" height="12px" />

      <!-- kpi-value placeholder -->
      <app-skeleton-block width="70%" height="44px" />

      <!-- trend placeholder -->
      <app-skeleton-block variant="text" width="40%" height="14px" />
    </div>
  `,
})
export class KpiCardSkeletonComponent {}
