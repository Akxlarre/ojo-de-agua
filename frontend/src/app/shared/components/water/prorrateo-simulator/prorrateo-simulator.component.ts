import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '@shared/components/icon/icon.component';
import { CardHoverDirective } from '@core/directives/card-hover.directive';
import { WaterApiService } from '@core/services/water/water-api.service';
import { DemandaCanalInput, ResultadoProrrateo } from '@core/models/water-domain.model';

interface CanalSimulado {
  id: string;
  nombre: string;
  acciones: number;
  demandaLps: number;
  esConsumoHumano: boolean;
}

@Component({
  selector: 'app-prorrateo-simulator',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, CardHoverDirective],
  template: `
    <div
      appCardHover
      class="flex flex-col gap-3 rounded-2xl border border-border-default bg-surface p-4 shadow-sm"
    >
      <!-- Encabezado del Simulador -->
      <div class="flex items-center justify-between pb-2 border-b border-border-subtle">
        <div class="flex items-center gap-2">
          <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
            <app-icon name="sliders" [size]="15" />
          </div>
          <div>
            <span class="micro-label font-bold text-text-primary block">
              Simulador de Prorrateo Legal
            </span>
            <span class="text-[10px] text-text-muted">
              Art. 5 bis (Consumo Humano) & Art. 18 (Alícuotas) Código de Aguas
            </span>
          </div>
        </div>
        <span
          class="rounded-full px-2 py-0.5 text-[10px] font-bold"
          [class.bg-emerald-500/10]="factorProrrateo() >= 1"
          [class.text-emerald-500]="factorProrrateo() >= 1"
          [class.bg-amber-500/10]="factorProrrateo() < 1 && factorProrrateo() >= 0.5"
          [class.text-amber-500]="factorProrrateo() < 1 && factorProrrateo() >= 0.5"
          [class.bg-red-500/10]="factorProrrateo() < 0.5"
          [class.text-red-400]="factorProrrateo() < 0.5"
        >
          {{ (factorProrrateo() * 100) | number: '1.0-1' }}% Prorrateo
        </span>
      </div>

      <!-- Sliders Interactivos -->
      <div class="flex flex-col gap-3 pt-1">
        <!-- Control 1: Caudal del Río -->
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between text-xs">
            <span class="text-text-secondary font-medium">Caudal Afluente Río en Estación:</span>
            <span class="font-bold text-brand font-mono">{{ caudalRio() | number }} L/s</span>
          </div>
          <input
            type="range"
            [min]="500"
            [max]="15000"
            [step]="250"
            [ngModel]="caudalRio()"
            (ngModelChange)="caudalRio.set($event)"
            class="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-subtle accent-brand"
          />
          <div class="flex justify-between text-[10px] text-text-muted">
            <span>500 L/s (Estiaje Crítico)</span>
            <span>15.000 L/s (Régimen Pleno)</span>
          </div>
        </div>

        <!-- Control 2: Demanda Vital APR -->
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between text-xs">
            <span class="text-text-secondary font-medium">
              Demanda Vital Consumo Humano (APR):
            </span>
            <span class="font-bold text-emerald-500 font-mono">{{ demandaApr() | number }} L/s</span>
          </div>
          <input
            type="range"
            [min]="200"
            [max]="3000"
            [step]="100"
            [ngModel]="demandaApr()"
            (ngModelChange)="demandaApr.set($event)"
            class="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-subtle accent-emerald-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted">
            <span>200 L/s</span>
            <span>Prioridad Absoluta Art. 5 bis</span>
            <span>3.000 L/s</span>
          </div>
        </div>
      </div>

      <!-- Resumen de Balance Hídrico -->
      <div class="grid grid-cols-3 gap-2 rounded-xl bg-base/80 p-2.5 text-center text-xs">
        <div class="flex flex-col">
          <span class="text-[10px] text-text-muted">Caudal Ecológico</span>
          <span class="font-bold text-text-secondary font-mono">{{ caudalEcologico() | number }} L/s</span>
        </div>
        <div class="flex flex-col border-x border-border-subtle">
          <span class="text-[10px] text-text-muted">Consumo Humano</span>
          <span class="font-bold text-emerald-400 font-mono">100% Protegido</span>
        </div>
        <div class="flex flex-col">
          <span class="text-[10px] text-text-muted">Remanente Regadío</span>
          <span class="font-bold font-mono" [class.text-amber-400]="caudalRemanente() < 3000" [class.text-text-primary]="caudalRemanente() >= 3000">
            {{ caudalRemanente() | number }} L/s
          </span>
        </div>
      </div>

      <!-- Tabla / Barras de Distribución por Canal -->
      <div class="flex flex-col gap-2 pt-1">
        <span class="micro-label text-text-muted">
          Asignación Legal en Bocatomas de Derivación:
        </span>

        <div class="flex flex-col gap-2">
          @for (c of asignaciones(); track c.id) {
            <div class="flex flex-col gap-1 rounded-xl bg-subtle/50 p-2 text-xs">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  @if (c.esConsumoHumano) {
                    <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                    <span class="font-semibold text-emerald-400">{{ c.nombre }}</span>
                    <span class="rounded bg-emerald-500/10 px-1 py-0.2 text-[9px] font-bold text-emerald-400">
                      Art. 5 bis
                    </span>
                  } @else {
                    <span class="h-1.5 w-1.5 rounded-full bg-sky-400"></span>
                    <span class="font-medium text-text-primary">{{ c.nombre }}</span>
                    <span class="text-[10px] text-text-muted">({{ c.acciones }} acc.)</span>
                  }
                </div>

                <div class="flex items-center gap-2 font-mono">
                  <span class="font-bold text-text-primary">
                    {{ c.caudalEntregado | number: '1.0-0' }} L/s
                  </span>
                  <span
                    class="text-[10px]"
                    [class.text-emerald-400]="c.porcentajeSatisfecho >= 99"
                    [class.text-amber-400]="c.porcentajeSatisfecho < 99 && c.porcentajeSatisfecho >= 60"
                    [class.text-red-400]="c.porcentajeSatisfecho < 60"
                  >
                    ({{ c.porcentajeSatisfecho | number: '1.0-0' }}%)
                  </span>
                </div>
              </div>

              <!-- Barra de Progreso de Asignación -->
              <div class="h-1.5 w-full overflow-hidden rounded-full bg-base">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  [style.width.%]="c.porcentajeSatisfecho > 100 ? 100 : c.porcentajeSatisfecho"
                  [class.bg-emerald-500]="c.esConsumoHumano"
                  [class.bg-brand]="!c.esConsumoHumano && c.porcentajeSatisfecho >= 80"
                  [class.bg-amber-500]="!c.esConsumoHumano && c.porcentajeSatisfecho < 80 && c.porcentajeSatisfecho >= 50"
                  [class.bg-red-500]="!c.esConsumoHumano && c.porcentajeSatisfecho < 50"
                ></div>
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProrrateoSimulatorComponent {
  readonly cuencaCodigo = input<string>('057');

  readonly caudalRio = signal<number>(5000);
  readonly demandaApr = signal<number>(1000);
  readonly caudalEcologico = signal<number>(300);

  readonly canales = signal<CanalSimulado[]>([
    {
      id: 'apr-01',
      nombre: 'Red APR Consumo Humano',
      acciones: 0,
      demandaLps: 1000,
      esConsumoHumano: true,
    },
    {
      id: 'canal-01',
      nombre: 'Canal San Carlos (JVR 1ª)',
      acciones: 1200,
      demandaLps: 2200,
      esConsumoHumano: false,
    },
    {
      id: 'canal-02',
      nombre: 'Canal Pirque (Asoc. Canalistas)',
      acciones: 800,
      demandaLps: 1500,
      esConsumoHumano: false,
    },
    {
      id: 'canal-03',
      nombre: 'Canal Eyzaguirre',
      acciones: 600,
      demandaLps: 1100,
      esConsumoHumano: false,
    },
  ]);

  /** Caudal disponible después del caudal ecológico */
  readonly caudalNeto = computed(() => {
    return Math.max(0, this.caudalRio() - this.caudalEcologico());
  });

  /** Reserva prioritaria para consumo humano (Art. 5 bis: 100% satisfecho antes de otros usos) */
  readonly asignacionApr = computed(() => {
    return Math.min(this.caudalNeto(), this.demandaApr());
  });

  /** Caudal remanente a prorratear entre regadío e industria */
  readonly caudalRemanente = computed(() => {
    return Math.max(0, this.caudalNeto() - this.asignacionApr());
  });

  /** Demanda total de canales de regadío */
  readonly demandaTotalRegantes = computed(() => {
    return this.canales()
      .filter((c) => !c.esConsumoHumano)
      .reduce((acc, c) => acc + c.demandaLps, 0);
  });

  /** Total de acciones de regadío */
  readonly totalAcciones = computed(() => {
    return this.canales()
      .filter((c) => !c.esConsumoHumano)
      .reduce((acc, c) => acc + c.acciones, 0);
  });

  /** Factor de prorrateo legal (0.0 a 1.0) para regantes */
  readonly factorProrrateo = computed(() => {
    const dem = this.demandaTotalRegantes();
    if (dem === 0) return 1.0;
    return Math.min(1.0, this.caudalRemanente() / dem);
  });

  /** Asignaciones finales en tiempo real */
  readonly asignaciones = computed(() => {
    const factor = this.factorProrrateo();
    const aprEntrega = this.asignacionApr();
    const aprDemanda = this.demandaApr();

    return this.canales().map((c) => {
      if (c.esConsumoHumano) {
        return {
          id: c.id,
          nombre: c.nombre,
          acciones: 0,
          caudalEntregado: aprEntrega,
          porcentajeSatisfecho: aprDemanda > 0 ? (aprEntrega / aprDemanda) * 100 : 100,
          esConsumoHumano: true,
        };
      } else {
        const entregado = c.demandaLps * factor;
        return {
          id: c.id,
          nombre: c.nombre,
          acciones: c.acciones,
          caudalEntregado: entregado,
          porcentajeSatisfecho: factor * 100,
          esConsumoHumano: false,
        };
      }
    });
  });
}
