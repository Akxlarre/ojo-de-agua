import { inject } from "@angular/core";
import { Router, type CanActivateFn } from "@angular/router";
import { AuthFacade } from "@core/facades/auth.facade";

// SEC: Timeout máximo para esperar resolución de sesión inicial.
// Sin esto, si Supabase está caído el guard cuelga indefinidamente (UI congelada).
const READY_TIMEOUT_MS = 10_000;

/**
 * Guard para rutas protegidas. Redirige a /login si no hay sesión activa.
 * Para protección adicional por rol, usar roleGuard() de role.guard.ts.
 */
export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthFacade);
  const router = inject(Router);

  try {
    await Promise.race([
      auth.whenReady,
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("Auth timeout")), READY_TIMEOUT_MS),
      ),
    ]);
  } catch {
    // Timeout o error de red → redirigir al login como fallback seguro
    return router.createUrlTree(["/login"]);
  }

  if (auth.isAuthenticated()) return true;
  return router.createUrlTree(["/login"]);
};
