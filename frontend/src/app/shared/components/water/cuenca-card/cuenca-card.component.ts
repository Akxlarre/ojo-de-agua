import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Cuenca, DiagnosticoCuenca } from '@core/models/water-domain.model';
import { IconComponent } from '@shared/components/icon/icon.component';
import { CardHoverDirective } from '@core/directives/card-hover.directive';

@Component({
  selector: 'app-cuenca-card',
  standalone: true,
  imports: [CommonModule, IconComponent, CardHoverDirective],
  template: `
    <div
      appCardHover
      class="group relative flex flex-col gap-3 rounded-2xl border border-border-default bg-surface p-4 shadow-sm transition-all hover:border-brand cursor-default"
      role="article"
      [attr.aria-label]="cuenca().nombre"
    >
      <!-- Header: Código y Estado de Sequía -->
      <div class="flex items-center justify-between">
        <span class="micro-label rounded-lg bg-subtle px-2.5 py-1 text-text-secondary border border-border-subtle">
          DGA {{ cuenca().codigo_dga }}
        </span>
        @if (cuenca().decreto_escasez_activo || diagnostico()?.decreto_escasez_activo) {
          <span
            class="badge-pulse flex items-center gap-1.5 rounded-full bg-red-950/30 px-2.5 py-0.5 text-xs font-semibold text-red-400 border border-red-800/40"
            role="status"
          >
            <span class="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse"></span>
            Sequía Activa MOP
          </span>
        } @else {
          <span class="micro-label text-emerald-500 font-medium flex items-center gap-1">
            <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            Vigente
          </span>
        }
      </div>

      <!-- Título de Cuenca -->
      <div>
        <h3 class="item-title text-base font-bold text-text-primary group-hover:text-brand transition-colors m-0">
          {{ diagnostico()?.cuenca_nombre || cuenca().nombre }}
        </h3>
        <p class="section-eyebrow text-xs text-text-secondary mt-0.5 m-0">
          {{ cuenca().region }} • {{ cuenca().zona_hidrografica }}
        </p>
      </div>

      <!-- Métricas / Diagnóstico (si está disponible) -->
      @if (diagnostico(); as diag) {
        <div class="grid grid-cols-2 gap-2 rounded-xl bg-base/80 border border-border-subtle p-3 text-xs">
          <div class="flex flex-col gap-0.5">
            <span class="micro-label text-text-muted">Seguridad Hídrica</span>
            <div class="flex items-baseline gap-1">
              <span
                class="font-display font-bold text-lg leading-tight"
                [class.text-red-400]="diag.semaforo === 'CRITICO'"
                [class.text-amber-400]="diag.semaforo === 'VULNERABLE'"
                [class.text-yellow-400]="diag.semaforo === 'ALERTA'"
                [class.text-emerald-400]="diag.semaforo === 'ESTABLE'"
              >
                {{ diag.indice_seguridad_hidrica }}
              </span>
              <span class="text-[10px] text-text-muted font-medium">/ 100</span>
            </div>
            <span
              class="text-[10px] font-semibold uppercase tracking-wider"
              [class.text-red-400]="diag.semaforo === 'CRITICO'"
              [class.text-amber-400]="diag.semaforo === 'VULNERABLE'"
              [class.text-yellow-400]="diag.semaforo === 'ALERTA'"
              [class.text-emerald-400]="diag.semaforo === 'ESTABLE'"
            >
              {{ diag.semaforo }}
            </span>
          </div>

          <div class="flex flex-col gap-0.5">
            <span class="micro-label text-text-muted">Amenaza Relaves</span>
            <div class="flex items-baseline gap-1">
              <span class="font-display font-bold text-lg text-text-primary leading-tight">
                {{ diag.alertas_causales.relaves_cerca_apr }}
              </span>
              <span class="text-[10px] text-text-muted font-medium">depósitos</span>
            </div>
            <span class="text-[10px] text-text-secondary">
              a &lt;20km de APR
            </span>
          </div>
        </div>
      }

      <!-- Acciones de Tarjeta -->
      <div class="flex items-center justify-between pt-2 border-t border-border-subtle mt-1">
        <button
          type="button"
          (click)="onSelect()"
          class="text-xs font-semibold text-brand hover:text-brand-hover flex items-center gap-1 bg-transparent border-0 cursor-pointer p-0"
        >
          <span>Enfocar en Mapa</span>
          <app-icon name="chevron-right" [size]="14" />
        </button>

        <button
          type="button"
          (click)="onSimular()"
          class="text-xs font-semibold text-text-secondary hover:text-text-primary flex items-center gap-1 bg-transparent border-0 cursor-pointer p-0"
        >
          <app-icon name="activity" [size]="14" />
          <span>Simular Prorrateo</span>
        </button>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CuencaCardComponent {
  readonly cuenca = input.required<Cuenca>();
  readonly diagnostico = input<DiagnosticoCuenca | null>(null);

  readonly select = output<Cuenca>();
  readonly simular = output<Cuenca>();

  onSelect(): void {
    this.select.emit(this.cuenca());
  }

  onSimular(): void {
    this.simular.emit(this.cuenca());
  }
}
