import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThoughtStep } from '@core/models/water-chat.model';
import { IconComponent } from '@shared/components/icon/icon.component';

@Component({
  selector: 'app-chat-thought',
  standalone: true,
  imports: [CommonModule, IconComponent],
  template: `
    <div
      class="w-full max-w-[88%] rounded-xl border border-border-subtle bg-base/60 overflow-hidden text-xs"
    >
      <button
        type="button"
        (click)="toggleOpen()"
        class="flex w-full items-center justify-between px-3 py-2 text-text-muted hover:text-text-primary bg-transparent border-0 cursor-pointer"
        [attr.aria-expanded]="isOpen()"
      >
        <div class="flex items-center gap-1.5 font-medium">
          <app-icon name="activity" [size]="13" class="text-brand" />
          <span>Razonamiento del Agente ({{ thoughts().length }} pasos)</span>
        </div>
        <app-icon [name]="isOpen() ? 'chevron-up' : 'chevron-down'" [size]="13" />
      </button>

      @if (isOpen()) {
        <div class="flex flex-col gap-1.5 px-3 pb-3 pt-1 border-t border-border-subtle/50">
          @for (step of thoughts(); track step.id) {
            <div class="flex items-start gap-2 text-text-secondary leading-snug">
              <span class="rounded bg-subtle px-1.5 py-0.2 text-[10px] font-mono text-text-muted shrink-0 mt-0.5">
                #{{ step.pasoNumero }}
              </span>
              <div class="flex-1">
                <span class="font-medium text-text-primary">{{ step.titulo }}</span>
                @if (step.detalle) {
                  <p class="text-[11px] text-text-muted mt-0.5 m-0 font-mono">
                    {{ step.detalle }}
                  </p>
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatThoughtComponent {
  readonly thoughts = input.required<ThoughtStep[]>();
  readonly isOpen = signal<boolean>(false);

  toggleOpen(): void {
    this.isOpen.update((v) => !v);
  }
}
