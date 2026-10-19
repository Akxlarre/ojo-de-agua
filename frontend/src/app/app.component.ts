import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Toast } from 'primeng/toast';

/**
 * AppComponent — raíz de la aplicación.
 *
 * Solo renderiza el router outlet y el toast global de PrimeNG.
 * El layout (sidebar + topbar) vive en AppShellComponent,
 * que se carga únicamente para rutas protegidas (/app/**).
 */
@Component({
  selector: 'app-root',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Toast],
  template: `
    <router-outlet />
    <p-toast
      position="bottom-right"
      [breakpoints]="{ '768px': { width: '100%', right: '0', left: '0' } }"
    />
  `,
})
export class AppComponent {}
