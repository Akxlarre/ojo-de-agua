import { signal, computed } from '@angular/core';

/**
 * BaseFacade<T> — Clase base para todos los Facades de dominio.
 *
 * Encapsula el patrón SWR (Stale-While-Revalidate) de forma consistente:
 * - Primera carga: muestra skeleton (isLoading = true)
 * - Re-visitas: datos cacheados inmediatos + refresco silencioso en background
 *
 * Uso:
 * ```ts
 * @Injectable({ providedIn: 'root' })
 * export class ProductosFacade extends BaseFacade<Producto[]> {
 *   private repo = inject(SupabaseService);
 *
 *   protected override async fetchData(): Promise<Producto[]> {
 *     const { data, error } = await this.repo.findAll();
 *     if (error) throw error;
 *     return data ?? [];
 *   }
 * }
 * ```
 *
 * El Smart Component solo necesita llamar `facade.initialize()` en `ngOnInit`.
 * El patrón SWR se encarga del resto automáticamente.
 */
export abstract class BaseFacade<T> {
  // ── Estado privado ────────────────────────────────────────────────────────

  private _initialized = false;

  protected readonly _data = signal<T | null>(null);
  protected readonly _isLoading = signal(false);
  protected readonly _error = signal<string | null>(null);

  // ── Estado público (solo lectura) ─────────────────────────────────────────

  readonly data = this._data.asReadonly();
  readonly isLoading = this._isLoading.asReadonly();
  readonly error = this._error.asReadonly();

  /** true cuando ya hay datos cacheados (evita mostrar skeleton en re-visitas). */
  readonly hasData = computed(() => this._data() !== null);

  // ── Contrato abstracto ────────────────────────────────────────────────────

  /**
   * Implementado por cada subclase. Debe obtener y retornar los datos del
   * dominio. NO debe tocar _isLoading ni _data directamente — BaseFacade lo hace.
   * Lanzar un Error para indicar fallo; BaseFacade lo capturará y seteará _error.
   */
  protected abstract fetchData(): Promise<T>;

  // ── API pública ───────────────────────────────────────────────────────────

  /**
   * Inicializa el Facade desde un Smart Component (ngOnInit / constructor).
   *
   * - Primera llamada: carga completa con skeleton (isLoading = true).
   * - Llamadas posteriores: devuelve datos cacheados + refresca en background.
   */
  async initialize(): Promise<void> {
    if (this._initialized) {
      this.refreshSilently();
      return;
    }
    this._initialized = true;
    this._isLoading.set(true);
    this._error.set(null);
    try {
      this._data.set(await this.fetchData());
    } catch (e) {
      // SEC: nunca exponer mensajes internos del servidor (nombres de tabla,
      // detalles de query, stack traces de Supabase). Usar sanitizeError().
      this._error.set(BaseFacade.sanitizeError(e));
    } finally {
      this._isLoading.set(false);
    }
  }

  /**
   * Convierte un error desconocido en un mensaje seguro para la UI.
   * Subclases pueden sobreescribir para mensajes específicos del dominio.
   */
  protected static sanitizeError(e: unknown): string {
    if (!(e instanceof Error)) return 'Error inesperado. Intenta de nuevo.';
    const msg = e.message.toLowerCase();
    if (msg.includes('network') || msg.includes('fetch') || msg.includes('failed to fetch'))
      return 'Error de conexión. Verifica tu internet e intenta de nuevo.';
    if (msg.includes('permission') || msg.includes('policy') || msg.includes('rls') || msg.includes('403'))
      return 'No tienes permisos para realizar esta acción.';
    return 'Error al cargar los datos. Intenta de nuevo.';
  }

  /**
   * Refresca los datos sin mostrar skeleton.
   * Usar después de mutaciones (INSERT/UPDATE/DELETE) o desde Realtime handlers.
   * Los datos stale permanecen visibles si el fetch falla.
   */
  protected async refreshSilently(): Promise<void> {
    try {
      this._data.set(await this.fetchData());
    } catch {
      // Fail silencioso — datos stale siguen visibles
    }
  }

  /**
   * Resetea el Facade a su estado inicial (útil en tests y en logout).
   * Fuerza una carga completa con skeleton en el próximo initialize().
   */
  reset(): void {
    this._initialized = false;
    this._data.set(null);
    this._isLoading.set(false);
    this._error.set(null);
  }

  /**
   * Reintenta la carga desde cero tras un error.
   * Equivale a reset() + initialize() — úsalo como handler de (retry) en
   * el componente app-error-state:
   * ```html
   * <app-error-state [message]="facade.error()!" (retry)="facade.retryLoad()" />
   * ```
   */
  async retryLoad(): Promise<void> {
    this.reset();
    await this.initialize();
  }

  /**
   * Sobreescribir en subclases que usen Supabase Realtime.
   * Llamar desde el DestroyRef del Smart Component:
   * ```ts
   * this.destroyRef.onDestroy(() => this.facade.dispose());
   * ```
   */
  dispose(): void {}
}
