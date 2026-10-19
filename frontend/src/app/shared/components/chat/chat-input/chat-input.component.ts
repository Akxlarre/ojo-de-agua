import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '@shared/components/icon/icon.component';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  template: `
    <div class="flex flex-col gap-2 w-full">
      <!-- Chips de Sugerencia Rápida -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
        @for (sug of suggestions; track sug) {
          <button
            type="button"
            (click)="onPickSuggestion(sug)"
            [disabled]="disabled()"
            class="shrink-0 rounded-full bg-subtle px-2.5 py-1 text-xs text-text-secondary hover:text-brand hover:bg-elevated transition-colors border-0 cursor-pointer disabled:opacity-50"
          >
            {{ sug }}
          </button>
        }
      </div>

      <!-- Barra de Input -->
      <form
        (ngSubmit)="onSubmit()"
        class="relative flex items-center rounded-2xl border border-border-default bg-surface p-1.5 shadow-sm focus-within:border-brand focus-within:ring-1 focus-within:ring-brand transition-all"
      >
        <textarea
          [(ngModel)]="inputText"
          name="chatQuery"
          [placeholder]="placeholder()"
          [disabled]="disabled()"
          rows="1"
          (keydown.enter)="onEnter($event)"
          class="flex-1 resize-none bg-transparent px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted outline-none border-0 font-sans"
        ></textarea>

        <button
          type="submit"
          [disabled]="disabled() || !inputText().trim()"
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand text-white transition-all hover:bg-brand-hover disabled:opacity-40 disabled:cursor-not-allowed border-0 cursor-pointer"
          aria-label="Enviar mensaje"
        >
          <app-icon name="send" [size]="14" />
        </button>
      </form>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatInputComponent {
  readonly disabled = input<boolean>(false);
  readonly placeholder = input<string>('Pregunta sobre cuencas, APRs, leyes o sequía...');

  readonly send = output<string>();

  readonly inputText = signal<string>('');

  readonly suggestions: string[] = [
    '¿Qué cuencas tienen decreto de sequía activo?',
    '¿Hay relaves cerca del APR Choapa?',
    '¿Cómo aplica el Art. 5 bis en prorrateo?',
    'Ver glaciares del Río Maipo',
  ];

  onSubmit(): void {
    const text = this.inputText().trim();
    if (text && !this.disabled()) {
      this.send.emit(text);
      this.inputText.set('');
    }
  }

  onEnter(event: Event): void {
    const keyEvent = event as KeyboardEvent;
    if (!keyEvent.shiftKey) {
      keyEvent.preventDefault();
      this.onSubmit();
    }
  }

  onPickSuggestion(text: string): void {
    this.inputText.set(text);
    this.onSubmit();
  }
}
