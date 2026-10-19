import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WaterMapFacade } from '@core/facades/water-map.facade';
import { ThemeService } from '@core/services/ui/theme.service';
import { WaterMapComponent } from './components/water-map/water-map.component';
import { WaterCopilotComponent } from './components/water-copilot/water-copilot.component';
import { IconComponent } from '@shared/components/icon/icon.component';

@Component({
  selector: 'app-water-platform',
  standalone: true,
  imports: [
    CommonModule,
    WaterMapComponent,
    WaterCopilotComponent,
    IconComponent,
  ],
  template: `
    <div class="flex h-screen w-screen flex-col bg-base text-text-primary overflow-hidden font-sans">
      <!-- Topbar Institucional y KPIs -->
      <header
        class="flex h-14 shrink-0 items-center justify-between border-b border-border-default bg-surface px-5 shadow-sm z-20"
      >
        <!-- Brand & Misión -->
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white shadow-sm">
            <app-icon name="activity" [size]="18" />
          </div>
          <div>
            <span class="font-display text-base font-bold text-text-primary tracking-tight">
              Ojo de Agua
            </span>
            <span class="hidden sm:inline text-xs text-text-muted ml-2 font-medium">
              Atlas & Copiloto de Seguridad Hídrica de Chile
            </span>
          </div>
        </div>

        <!-- Badges de Estado Nacional -->
        <div class="hidden md:flex items-center gap-2.5 text-xs">
          <div class="flex items-center gap-2 rounded-full bg-subtle border border-border-subtle px-3 py-1 shadow-2xs">
            <span class="indicator-live"></span>
            <span class="font-medium text-text-secondary">90 Cuencas DGA</span>
          </div>

          <div class="flex items-center gap-1.5 rounded-full bg-subtle border border-border-subtle px-3 py-1 shadow-2xs">
            <span class="h-2 w-2 rounded-full bg-sky-500"></span>
            <span class="font-medium text-text-secondary">2.238 APRs Rurales</span>
          </div>

          @if (mapFacade.cuencasEnSequia().length > 0) {
            <div class="badge-pulse flex items-center gap-1.5 rounded-full bg-red-500/10 border border-red-500/30 px-3 py-1 text-red-500">
              <span class="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
              <span class="font-semibold">{{ mapFacade.cuencasEnSequia().length }} Decretos Sequía</span>
            </div>
          }
        </div>

        <!-- Acciones del Topbar -->
        <div class="flex items-center gap-2">
          <!-- Toggle Modo Claro / Oscuro -->
          <button
            type="button"
            (click)="theme.cycleColorMode($event)"
            class="flex h-8 w-8 items-center justify-center rounded-xl bg-subtle text-text-secondary hover:text-text-primary hover:bg-elevated border border-border-subtle cursor-pointer transition-colors shadow-2xs"
            [attr.aria-label]="theme.darkMode() ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
            [title]="theme.darkMode() ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
          >
            <app-icon [name]="theme.darkMode() ? 'sun' : 'moon'" [size]="15" />
          </button>
        </div>
      </header>

      <!-- Main Workspace: Split Layout 60/40 (App-like 100vh) -->
      <main class="flex flex-1 flex-col lg:flex-row gap-4 p-4 overflow-hidden min-h-0">
        <!-- Columna Izquierda: Gemelo Digital Cartográfico (60%) -->
        <section class="h-[50vh] lg:h-full lg:w-[60%] shrink-0 min-h-0 overflow-hidden" aria-label="Visor Cartográfico">
          <app-water-map />
        </section>

        <!-- Columna Derecha: Copiloto AI & Ficha 360° (40%) -->
        <section class="flex-1 h-[50vh] lg:h-full min-w-0 min-h-0 overflow-hidden" aria-label="Copiloto y Diagnóstico">
          <app-water-copilot />
        </section>
      </main>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WaterPlatformComponent {
  readonly mapFacade = inject(WaterMapFacade);
  readonly theme = inject(ThemeService);
}
