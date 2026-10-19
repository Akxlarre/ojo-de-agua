import {
  Component,
  ChangeDetectionStrategy,
  input,
  output,
} from '@angular/core';
import { AlertCardComponent } from '../alert-card/alert-card.component';

/**
 * ErrorStateComponent — Estado de error unificado para Facades.
 *
 * Úsalo en el bloque `@else if (facade.error())` de cualquier Smart Component.
 * El output `(retry)` debe conectarse a `facade.retryLoad()`.
 *
 * @example
 * ```html
 * @else if (facade.error()) {
 *   <app-error-state
 *     [message]="facade.error()!"
 *     (retry)="facade.retryLoad()"
 *   />
 * }
 * ```
 *
 * @example Con título personalizado
 * ```html
 * <app-error-state
 *   title="No se pudo cargar los productos"
 *   [message]="facade.error()!"
 *   (retry)="facade.retryLoad()"
 * />
 * ```
 */
@Component({
  selector: 'app-error-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AlertCardComponent],
  template: `
    <app-alert-card
      severity="error"
      [title]="title()"
      [actionLabel]="retryLabel()"
      (action)="retry.emit()"
    >
      {{ message() }}
    </app-alert-card>
  `,
})
export class ErrorStateComponent {
  /**
   * Título de la alerta. Debe ser una frase corta que identifique qué falló.
   * Default: 'No se pudo cargar la información'.
   */
  readonly title = input<string>('No se pudo cargar la información');

  /**
   * Mensaje de error. Típicamente `facade.error()!`.
   * Se muestra como cuerpo del alert-card con el detalle técnico.
   */
  readonly message = input.required<string>();

  /**
   * Texto del botón de reintento. Default: 'Reintentar'.
   */
  readonly retryLabel = input<string>('Reintentar');

  /**
   * Emitido al hacer clic en "Reintentar".
   * Conectar a `facade.retryLoad()` en el Smart Component.
   */
  readonly retry = output<void>();
}
