import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IconComponent } from '@shared/components/icon/icon.component';

@Component({
  selector: 'app-home',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, IconComponent],
  template: `
    <div class="flex min-h-[100dvh] flex-col items-center justify-center bg-base bg-[image:var(--gradient-subtle)] p-6 text-center">
      <!-- KOA HERO SECTION -->
      <section class="max-w-3xl animate-fade-in-up">
        <div class="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--gradient-primary)] shadow-lg">
          <span class="text-3xl brightness-[10]">🧠</span>
        </div>
        
        <h1 class="m-0 mb-6 font-display text-5xl font-black italic tracking-tighter text-text-primary sm:text-8xl">
          ¡Hola, <span class="text-brand">KOA</span>!
        </h1>
        
        <p class="m-0 text-xl font-medium leading-relaxed text-text-secondary sm:text-2xl">
          Bienvenido al <span class="font-bold text-text-primary">Workflow Agentico</span> de nueva generación.
          <br class="hidden sm:block">
          Diseñado para la automatización inteligente y el desarrollo acelerado.
        </p>

        <div class="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a routerLink="/login" class="btn-primary px-8 py-4 text-lg">
            Empezar ahora
            <app-icon name="arrow-right" [size]="20" />
          </a>
          <p class="text-sm text-text-muted">
            Acceso prioritario al ecosistema agentico.
          </p>
        </div>
      </section>

      <!-- OPTIONAL LOGIN SECTION -->
      <footer class="mt-24 text-text-muted animate-stagger">
        <p class="text-xs uppercase tracking-widest font-semibold opacity-50">Koa Framework v20.0</p>
      </footer>
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class HomeComponent {}
