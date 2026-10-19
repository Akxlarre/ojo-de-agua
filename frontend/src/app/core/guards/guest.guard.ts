import { inject } from "@angular/core";
import { Router, type CanActivateFn } from "@angular/router";
import { AuthFacade } from "@core/facades/auth.facade";

/**
 * Guard para rutas públicas (login, register).
 * Si el usuario ya está autenticado, redirige a /app.
 */
const READY_TIMEOUT_MS = 10_000;

export const guestGuard: CanActivateFn = async () => {
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
    return true; // Timeout → dejar pasar al login, es la ruta más segura
  }

  if (auth.isAuthenticated()) return router.createUrlTree(["/app"]);
  return true;
};
