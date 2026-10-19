import {
  Component,
  ChangeDetectionStrategy,
  inject,
  input,
  output,
  viewChild,
  ElementRef,
  effect,
  AfterViewInit,
  HostListener,
} from '@angular/core';
import { IconComponent } from '@shared/components/icon/icon.component';
import { PressFeedbackDirective } from '@core/directives/press-feedback.directive';
import { GsapAnimationsService } from '@core/services/ui/gsap-animations.service';

/**
 * Modal centrado con backdrop, animaciones GSAP y accesibilidad.
 * Usa GsapAnimationsService.animatePanelIn/Out para entrada/salida.
 *
 * Uso básico:
 * <app-modal [isOpen]="open()" title="Confirmar" (closed)="open.set(false)">
 *   <p>Contenido</p>
 *   <ng-container appModalFooter>
 *     <button class="btn-ghost" (click)="open.set(false)">Cancelar</button>
 *   </ng-container>
 * </app-modal>
 */
@Component({
  selector: 'app-modal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconComponent, PressFeedbackDirective],
  template: `
    @if (isOpen()) {
      <div class="modal__backdrop" (click)="dismissible() && close()" aria-hidden="true"></div>

      <div
        #dialog
        class="modal__dialog"
        role="dialog"
        [attr.aria-modal]="true"
        [attr.aria-labelledby]="titleId"
        (keydown)="onDialogKeydown($event)"
      >
        @if (title() || showCloseButton()) {
          <header class="modal__header">
            @if (title()) {
              <h2 [id]="titleId" class="modal__title">{{ title() }}</h2>
            }
            @if (showCloseButton()) {
              <button
                type="button"
                class="modal__close"
                appPressFeedback
                aria-label="Cerrar"
                (click)="close()"
              >
                <app-icon name="x" [size]="16" [ariaHidden]="true" />
              </button>
            }
          </header>
        }

        <div class="modal__body">
          <ng-content />
        </div>

        <div class="modal__footer">
          <ng-content select="[appModalFooter]" />
        </div>
      </div>
    }
  `,
  styles: [
    `
      .modal__backdrop {
        position: fixed;
        inset: 0;
        z-index: 1199;
        background: var(--overlay-backdrop);
        backdrop-filter: blur(2px);
      }

      .modal__dialog {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 1200;
        width: calc(100% - 2rem);
        max-width: 480px;
        max-height: calc(100dvh - 2rem);
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg, 0.75rem);
        box-shadow: var(--shadow-lg);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        opacity: 0;
      }

      .modal__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--border-subtle);
        background: var(--bg-base);
        flex-shrink: 0;
      }

      .modal__title {
        margin: 0;
        font-size: var(--text-lg, 1.125rem);
        font-weight: 600;
        color: var(--text-primary);
      }

      .modal__close {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        padding: 0;
        border: none;
        border-radius: 9999px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition:
          color 0.15s ease,
          background 0.15s ease;
      }

      .modal__close:hover {
        background: var(--bg-elevated, var(--bg-base));
        color: var(--text-primary);
      }

      .modal__body {
        padding: 1.25rem;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
      }

      .modal__footer {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--border-subtle);
        background: var(--bg-base);
        flex-shrink: 0;
      }

      .modal__footer:empty {
        display: none;
      }
    `,
  ],
})
export class ModalComponent implements AfterViewInit {
  private readonly gsap = inject(GsapAnimationsService);

  readonly isOpen = input<boolean>(false);
  readonly title = input<string | undefined>(undefined);
  readonly dismissible = input<boolean>(true);
  readonly showCloseButton = input<boolean>(true);

  readonly closed = output<void>();

  readonly titleId = `modal-title-${Math.random().toString(36).slice(2, 9)}`;

  private readonly dialogRef = viewChild<ElementRef<HTMLElement>>('dialog');

  constructor() {
    effect(() => {
      if (this.isOpen()) {
        document.body.style.overflow = 'hidden';
        setTimeout(() => this.animateIn(), 10);
      } else {
        document.body.style.overflow = '';
      }
    });
  }

  ngAfterViewInit(): void {
    if (this.isOpen()) setTimeout(() => this.animateIn(), 10);
  }

  close(): void {
    if (!this.dismissible()) return;
    const el = this.dialogRef()?.nativeElement;
    if (el) {
      this.gsap.animatePanelOut(el, () => this.closed.emit());
    } else {
      this.closed.emit();
    }
  }

  onDialogKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape' && this.dismissible()) {
      event.preventDefault();
      this.close();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen() && this.dismissible()) this.close();
  }

  private animateIn(): void {
    const el = this.dialogRef()?.nativeElement;
    if (el) {
      this.gsap.animatePanelIn(el);
      const focusable = el.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      focusable?.focus();
    }
  }
}
