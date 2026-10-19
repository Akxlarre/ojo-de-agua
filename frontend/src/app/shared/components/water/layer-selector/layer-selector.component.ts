import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IconComponent } from '@shared/components/icon/icon.component';
import { CardHoverDirective } from '@core/directives/card-hover.directive';

export interface LayerItem {
  id: string;
  label: string;
  icon: string;
  badgeCount?: number;
  colorDot?: string;
}

@Component({
  selector: 'app-layer-selector',
  standalone: true,
  imports: [CommonModule, IconComponent, CardHoverDirective],
  template: `
    <div
      appCardHover
      class="flex flex-col gap-1.5 rounded-2xl border border-border-default bg-surface/90 p-3.5 shadow-md backdrop-blur-md transition-all hover:border-brand"
      role="region"
      aria-label="Selector de capas cartográficas"
    >
      <div class="flex items-center gap-2 pb-2 border-b border-border-subtle">
        <app-icon name="layers" [size]="15" class="text-brand" />
        <span class="micro-label text-text-primary font-bold">
          Capas de Información
        </span>
      </div>

      <div class="flex flex-col gap-1">
        @for (layer of availableLayers; track layer.id) {
          <button
            type="button"
            (click)="onToggle(layer.id)"
            class="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors border-0 cursor-pointer"
            [class.bg-brand-muted]="isActive(layer.id)"
            [class.text-brand]="isActive(layer.id)"
            [class.bg-transparent]="!isActive(layer.id)"
            [class.text-text-secondary]="!isActive(layer.id)"
            [class.hover:bg-elevated]="!isActive(layer.id)"
          >
            <div class="flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full"
                [style.backgroundColor]="layer.colorDot || 'var(--color-brand)'"
              ></span>
              <app-icon [name]="layer.icon" [size]="14" />
              <span>{{ layer.label }}</span>
            </div>

            <div class="flex items-center gap-1.5">
              @if (layer.badgeCount) {
                <span class="rounded bg-base px-1.5 py-0.5 text-[10px] text-text-muted">
                  {{ layer.badgeCount }}
                </span>
              }
              <span
                class="h-4 w-7 rounded-full p-0.5 transition-colors inline-flex items-center"
                [class.bg-brand]="isActive(layer.id)"
                [class.bg-subtle]="!isActive(layer.id)"
              >
                <span
                  class="h-3 w-3 rounded-full bg-white transition-transform transform"
                  [class.translate-x-3]="isActive(layer.id)"
                  [class.translate-x-0]="!isActive(layer.id)"
                ></span>
              </span>
            </div>
          </button>
        }
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LayerSelectorComponent {
  readonly activeLayers = input.required<Set<string>>();
  readonly toggle = output<string>();

  readonly availableLayers: LayerItem[] = [
    { id: 'cuencas', label: '90 Cuencas DGA', icon: 'map', colorDot: '#3b82f6' },
    { id: 'aprs', label: '2.238 APRs (Consumo Humano)', icon: 'home', colorDot: '#10b981' },
    { id: 'relaves', label: '839 Relaves Mineros', icon: 'alert-triangle', colorDot: '#ef4444' },
    { id: 'glaciares', label: '2.094 Glaciares (IPG)', icon: 'cloud-snow', colorDot: '#06b6d4' },
    { id: 'canales', label: 'Canales de Riego', icon: 'git-branch', colorDot: '#f59e0b' },
  ];

  isActive(id: string): boolean {
    return this.activeLayers().has(id);
  }

  onToggle(id: string): void {
    this.toggle.emit(id);
  }
}
