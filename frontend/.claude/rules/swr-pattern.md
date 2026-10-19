---
paths:
  - "src/app/core/facades/**/*.ts"
  - "src/app/features/**/*.ts"
---

# Patrón SWR (Stale-While-Revalidate) + Realtime + Mutaciones

## Principio

**Nunca mostrar skeleton si ya tenemos datos cacheados.** El usuario ve datos inmediatos (posiblemente stale) mientras el Facade refresca silenciosamente en background. El skeleton solo aparece en la primera carga real (sin datos previos).

## BaseFacade — SWR incorporado

**No implementes el patrón SWR manualmente.** Extiende `BaseFacade<T>` de `@core/facades/base.facade`:

```typescript
@Injectable({ providedIn: 'root' })
export class ProductosFacade extends BaseFacade<Producto[]> {
  private supabase = inject(SupabaseService);

  protected override async fetchData(): Promise<Producto[]> {
    const { data, error } = await this.supabase.client
      .from('productos').select('*').order('created_at', { ascending: false });
    if (error) throw error;
    return data ?? [];
  }
}
```

`BaseFacade` expone: `data`, `isLoading`, `error`, `hasData`, `initialize()`, `reset()`, `dispose()`.
El Smart Component solo llama `this.facade.initialize()` en `ngOnInit`.

## Cuando aplicar cada estrategia

| Estrategia | Cuando usar | Ejemplo |
|------------|------------|---------|
| **SWR** | Cualquier Facade con datos que persisten entre navegaciones | Agenda, Dashboard, Alumnos |
| **SWR + Realtime** | Recursos compartidos con alta contención multi-usuario | Agenda (slots), Notificaciones |
| **Solo fetch** | Datos que cambian en cada vista y no se revisitan | Detalle de alumno (por `:id`) |

## Implementación en Facades

### 1. Estado SWR (agregar al estado privado)

```typescript
/** Flag para evitar re-fetch completo con skeleton en re-visitas. */
private _initialized = false;
```

### 2. Initialize con guard SWR

```typescript
async initialize(): Promise<void> {
  if (this._initialized) {
    // SWR: mostrar datos cacheados, refrescar en background
    this.refreshSilently();
    return;
  }
  this._initialized = true;

  // Primera carga: CON skeleton
  this._isLoading.set(true);
  try {
    await this.fetchData();
  } finally {
    this._isLoading.set(false);
  }
}
```

### 3. Refresh silencioso (sin skeleton)

```typescript
/**
 * Refresca datos sin mostrar skeleton.
 * Usado por: SWR re-entry, Realtime events, post-action refresh.
 */
private async refreshSilently(): Promise<void> {
  try {
    await this.fetchData();
  } catch {
    // Fail silencioso — datos stale siguen visibles
  }
}
```

### 4. Método de fetch compartido

Extraer la lógica de fetch a un método reutilizable que solo obtiene y setea datos, sin tocar `_isLoading`:

```typescript
private async fetchData(): Promise<void> {
  const { data, error } = await this.supabase.client
    .from('tabla')
    .select('...');

  if (error) throw error;
  this._data.set(data);
}
```

### 5. Post-action refresh (scheduling, canceling, etc.)

Después de una mutación (INSERT/UPDATE/DELETE), usar refresh silencioso, NO `loadX()` con skeleton:

```typescript
async crearRegistro(payload: Payload): Promise<boolean> {
  // ... insert en BD ...
  await this.refreshSilently(); // <- sin skeleton
  return true;
}
```

## Integración con Realtime

Para recursos compartidos (agenda, notificaciones), combinar SWR con Supabase Realtime:

### Suscripción

```typescript
private realtimeChannel: RealtimeChannel | null = null;

private subscribeRealtime(): void {
  this.disposeRealtime();
  this.realtimeChannel = this.supabase.client
    .channel('nombre-canal')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'tabla_base' },
      () => this.refreshSilently(),
    )
    .subscribe();
}
```

### Dispose

```typescript
dispose(): void {
  this.disposeRealtime();
}

private disposeRealtime(): void {
  if (this.realtimeChannel) {
    this.supabase.client.removeChannel(this.realtimeChannel);
    this.realtimeChannel = null;
  }
}
```

### Lifecycle en Smart Components

El Smart component controla el ciclo de vida del Realtime:

```typescript
export class MiPageComponent implements OnInit {
  private readonly facade = inject(MiFacade);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.facade.initialize();
    this.destroyRef.onDestroy(() => this.facade.dispose());
  }
}
```

## Limitaciones Supabase Realtime

- **Solo tablas base** — las VIEWs (`v_*`) NO disparan eventos Realtime.
- **Filtros limitados** — solo `eq`, no rangos (`gte`, `lt`). Para filtrar por rango de fechas, escuchar todos los eventos y refrescar incondicionalmente.
- **Idempotencia** — `subscribeRealtime()` siempre llama `disposeRealtime()` primero para evitar canales duplicados.

## Patrón de Mutaciones (Optimistic-First)

**Una sola estrategia para todos los writes.** La UI responde inmediato; si el servidor falla, se hace rollback y se muestra toast de error.

### CREATE — Insertar un ítem

```typescript
async crearProducto(payload: NuevoProducto): Promise<boolean> {
  // 1. Optimistic: añadir al inicio de la lista antes de ir al servidor
  const optimisticItem = { id: crypto.randomUUID(), ...payload };
  const prev = this._data();
  this._data.update(items => [optimisticItem, ...(items ?? [])]);

  try {
    const { data, error } = await this.supabase.client
      .from('productos').insert(payload).select().single();
    if (error) throw error;
    // Reemplazar el ítem optimístico con el real (id correcto del servidor)
    this._data.update(items => items?.map(i => i.id === optimisticItem.id ? data : i) ?? []);
    return true;
  } catch {
    this._data.set(prev); // Rollback
    inject(ToastService).error('No se pudo crear el producto');
    return false;
  }
}
```

### UPDATE — Actualizar un ítem

```typescript
async actualizarProducto(id: string, patch: Partial<Producto>): Promise<boolean> {
  // 1. Optimistic: mutar en la lista inmediatamente
  const prev = this._data();
  this._data.update(items => items?.map(i => i.id === id ? { ...i, ...patch } : i) ?? []);

  try {
    const { error } = await this.supabase.client
      .from('productos').update(patch).eq('id', id);
    if (error) throw error;
    await this.refreshSilently(); // sync final con BD
    return true;
  } catch {
    this._data.set(prev); // Rollback
    inject(ToastService).error('No se pudo actualizar el producto');
    return false;
  }
}
```

### DELETE — Eliminar un ítem

```typescript
async eliminarProducto(id: string): Promise<boolean> {
  // 1. Optimistic: eliminar de la lista inmediatamente
  const prev = this._data();
  this._data.update(items => items?.filter(i => i.id !== id) ?? []);

  try {
    const { error } = await this.supabase.client
      .from('productos').delete().eq('id', id);
    if (error) throw error;
    return true;
  } catch {
    this._data.set(prev); // Rollback
    inject(ToastService).error('No se pudo eliminar el producto');
    return false;
  }
}
```

### Reglas del patrón de mutaciones

| Regla | Razón |
|---|---|
| Siempre guardar `prev` antes del optimistic update | Permite rollback exacto |
| `refreshSilently()` solo en UPDATE (no en delete/create) | Evita parpadeos innecesarios |
| `inject(ToastService).error()` en el catch | Feedback siempre visible al usuario |
| Retornar `boolean` (true=éxito, false=error) | El Smart Component puede reaccionar si necesita |
| **NUNCA** llamar `initialize()` post-mutación | Mostraría skeleton; usar `refreshSilently()` |

## Prohibiciones

- **NUNCA** mostrar skeleton si `_data()` ya tiene valor (SWR activo).
- **NUNCA** usar `setInterval`/polling — Supabase Realtime existe para esto.
- **NUNCA** suscribir Realtime sin su correspondiente `dispose()` en el ciclo de vida.
- **NUNCA** suscribir Realtime a VIEWs de Supabase — usar la tabla base subyacente.
- **NUNCA** implementar SWR manualmente — extender `BaseFacade<T>` de `@core/facades/base.facade`.
