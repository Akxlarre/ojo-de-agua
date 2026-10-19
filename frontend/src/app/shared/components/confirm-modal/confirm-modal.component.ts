import { Component, ChangeDetectionStrategy, inject, computed } from '@angular/core';
import { Button } from 'primeng/button';
import { ModalComponent } from '@shared/components/modal/modal.component';
import { ModalFooterDirective } from '@shared/components/modal/modal-footer.directive';
import { ConfirmModalService } from '@core/services/ui/confirm-modal.service';

@Component({
  selector: 'app-confirm-modal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ModalComponent, ModalFooterDirective, Button],
  template: `
    <app-modal [isOpen]="svc.isOpen()" [title]="svc.config()?.title ?? ''" (closed)="svc.cancel()">
      @if (svc.config(); as cfg) {
        <p class="text-secondary m-0">{{ cfg.message }}</p>
      }

      @if (svc.config(); as cfg) {
        <ng-container appModalFooter>
          <p-button
            [label]="cfg.cancelLabel ?? 'Cancelar'"
            severity="secondary"
            [text]="true"
            data-llm-action="confirm-modal-cancel"
            (onClick)="svc.cancel()"
          />
          <p-button
            [label]="cfg.confirmLabel ?? 'Aceptar'"
            [severity]="btnSeverity()"
            data-llm-action="confirm-modal-accept"
            (onClick)="svc.accept()"
          />
        </ng-container>
      }
    </app-modal>
  `,
})
export class ConfirmModalComponent {
  protected readonly svc = inject(ConfirmModalService);

  protected readonly btnSeverity = computed(() => {
    const s = this.svc.config()?.severity ?? 'secondary';
    return s as 'danger' | 'warn' | 'success' | 'info' | 'secondary';
  });
}
