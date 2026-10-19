import { Routes } from '@angular/router';
import { authGuard } from '@core/guards/auth.guard';
import { guestGuard } from '@core/guards/guest.guard';
// import { roleGuard } from '@core/guards/role.guard'; // ← usar para rutas por rol

/**
 * Rutas de la aplicación.
 */
export const routes: Routes = [
  // Ruta principal — Plataforma Ojo de Agua (Atlas y Copiloto)
  {
    path: '',
    loadComponent: () =>
      import('./features/water-platform/water-platform.component').then(
        (m) => m.WaterPlatformComponent
      ),
  },

  // Rutas públicas — autenticación
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },

  // Rutas protegidas — envueltas en el layout AppShell
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./layout/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      // Ruta por defecto → dashboard
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      // TODO: Añade tus feature routes aquí
    ],
  },

  {
    path: '**',
    loadComponent: () =>
      import('./features/not-found/not-found.component').then((m) => m.NotFoundComponent),
  },
];
