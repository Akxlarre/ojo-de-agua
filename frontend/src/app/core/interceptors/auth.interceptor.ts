import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpErrorResponse,
  HttpContextToken,
} from '@angular/common/http';
import { from, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { SupabaseService } from '@core/services/infrastructure/supabase.service';

/**
 * Interceptor funcional de autenticación (Angular v15+).
 * - Añade Authorization: Bearer <token> a las peticiones HTTP.
 * - En 401: intenta refreshSession UNA SOLA VEZ y reintenta con el nuevo token.
 *   SEC-T06: el flag IS_RETRY previene loops infinitos si el token refreshado también es inválido.
 *
 * Registrar en app.config.ts vía provideCoreAuth().
 */

/** Context token — previene retry loop: marca la segunda llamada como "ya fue reintento". */
const IS_RETRY = new HttpContextToken<boolean>(() => false);

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const supabase = inject(SupabaseService);

  const addToken = (request: typeof req, token: string) =>
    request.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

  return from(supabase.getSession()).pipe(
    switchMap(({ data: { session } }) =>
      session?.access_token
        ? next(addToken(req, session.access_token))
        : next(req)
    ),
    catchError((err: unknown) => {
      // SEC-T06: Only retry once — skip if this request is already a retry.
      if (err instanceof HttpErrorResponse && err.status === 401 && !req.context.get(IS_RETRY)) {
        return from(supabase.refreshSession()).pipe(
          switchMap(({ data: { session } }) => {
            if (!session?.access_token) return throwError(() => err);
            // Mark the retry request so the interceptor won't recurse on another 401.
            const retryReq = addToken(req, session.access_token).clone({
              context: req.context.set(IS_RETRY, true),
            });
            return next(retryReq);
          }),
          catchError(() => throwError(() => err))
        );
      }
      return throwError(() => err);
    })
  );
};
