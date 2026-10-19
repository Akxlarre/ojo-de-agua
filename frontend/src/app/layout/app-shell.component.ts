import {
  Component,
  ChangeDetectionStrategy,
  inject,
  viewChild,
  ElementRef,
  afterNextRender,
} from "@angular/core";
import { RouterOutlet } from "@angular/router";

import { LayoutService } from "@core/services/ui/layout.service";
import { GsapAnimationsService } from "@core/services/ui/gsap-animations.service";
import { SidebarComponent } from "./sidebar.component";
import { TopbarComponent } from "./topbar.component";

/**
 * AppShellComponent — layout principal de rutas protegidas.
 *
 * Estructura: sidebar fijo + área de contenido (topbar + router-outlet).
 * En mobile el sidebar actúa como drawer animado con GSAP.
 *
 * Uso en app.routes.ts:
 * ```ts
 * { path: 'app', loadComponent: () => import('./layout/app-shell.component')
 *     .then(m => m.AppShellComponent), children: [...] }
 * ```
 */
@Component({
  selector: "app-shell",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, SidebarComponent, TopbarComponent],
  template: `
    <!-- Backdrop mobile drawer -->
    @if (layout.sidebarOpen()) {
      <div
        #backdropEl
        class="fixed inset-0 z-[49] cursor-pointer bg-[var(--overlay-backdrop)] lg:hidden"
        role="presentation"
        aria-hidden="true"
        data-llm-action="close-mobile-sidebar"
        (click)="layout.closeSidebar()"
      ></div>
    }

    <div
      class="grid min-h-[100dvh] grid-cols-1 bg-base lg:grid-cols-[auto_1fr]"
    >
      <!-- Sidebar -->
      <app-sidebar
        #sidebarEl
        class="fixed inset-y-0 start-0 z-50 w-[240px] -translate-x-full transition-transform duration-normal ease-standard lg:static lg:translate-x-0"
        [class.translate-x-0]="layout.sidebarOpen()"
      />

      <!-- Main: topbar + content -->
      <div class="grid min-w-0 grid-rows-[auto_1fr] overflow-hidden">
        <app-topbar />

        <main
          #contentEl
          class="overflow-y-auto p-6 transition-[view-transition-name:main-content]"
          style="view-transition-name: main-content;"
          role="main"
          tabindex="-1"
        >
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  host: { style: "display: contents;" },
})
export class AppShellComponent {
  protected readonly layout = inject(LayoutService);
  private readonly gsap = inject(GsapAnimationsService);

  private readonly contentEl = viewChild<ElementRef<HTMLElement>>("contentEl");

  constructor() {
    afterNextRender(() => {
      const el = this.contentEl()?.nativeElement;
      if (el) this.gsap.animatePageEnter(el);
    });
  }
}
