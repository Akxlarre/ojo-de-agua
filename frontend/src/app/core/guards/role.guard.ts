import { inject } from "@angular/core";
import { Router, type CanActivateFn } from "@angular/router";
import { AuthFacade } from "@core/facades/auth.facade";
import type { UserRole } from "@core/models/user.model";

const READY_TIMEOUT_MS = 10_000;

/**
 * roleGuard — factory de guard de autorización por rol.
 *
 * Verifica que el usuario autenticado tenga el rol requerido.
 * Úsalo después de authGuard, o de forma independiente (incluye check de autenticación).
 *
 * IMPORTANTE: Este guard es una segunda línea de defensa en el cliente.
 * La protección real de datos DEBE implementarse en RLS de Supabase.
 * Un usuario motivado puede eludir guards de frontend — RLS no puede eludirse.
 *
 * @example
 * // Solo administradores
 * { path: 'admin', canActivate: [roleGuard('admin')], loadComponent: ... }
 *
 * @example
 * // Múltiples roles permitidos
 * { path: 'reports', canActivate: [roleGuard(['admin', 'member'])], loadComponent: ... }
 */
export const roleGuard = (
  requiredRole: UserRole | UserRole[],
): CanActivateFn =>
  async () => {
    const auth = inject(AuthFacade);
    const router = inject(Router);

    // Esperar a que la sesión inicial resuelva, con timeout de seguridad
    try {
      await Promise.race([
        auth.whenReady,
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error("Auth timeout")), READY_TIMEOUT_MS),
        ),
      ]);
    } catch {
      return router.createUrlTree(["/login"]);
    }

    const user = auth.currentUser();

    // No autenticado → al login
    if (!user) return router.createUrlTree(["/login"]);

    const allowed = Array.isArray(requiredRole)
      ? requiredRole
      : [requiredRole];

    // Rol insuficiente → redirigir al dashboard (no revelar que la ruta existe)
    if (!allowed.includes(user.role)) return router.createUrlTree(["/app"]);

    return true;
  };
