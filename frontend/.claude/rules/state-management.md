---
paths:
  - "src/app/core/**/*.ts"
  - "src/app/features/**/*.ts"
---

# State Management — Cuándo usar qué

## Facade + BaseFacade (default — siempre disponible)

Usar cuando:
- El estado pertenece a **un solo dominio**
- CRUD estándar: lista, detalle, crear, actualizar, eliminar
- No hay estado compartido entre múltiples features

```typescript
// core/facades/productos.facade.ts
@Injectable({ providedIn: 'root' })
export class ProductosFacade extends BaseFacade<Producto[]> {
  private repo = inject(ProductosRepository);
  private toast = inject(ToastService);

  protected override async fetchData(): Promise<Producto[]> {
    return this.repo.findAll();
  }

  // computed() para derivados — viven en el Facade, no en el componente
  readonly activos = computed(() => this.data()?.filter(p => p.activo) ?? []);
}
```

El Smart Component solo llama `this.facade.initialize()` en `ngOnInit`.
`BaseFacade` provee: `data`, `isLoading`, `error`, `hasData`, `initialize()`, `reset()`, `dispose()`.

## Signal Store (requiere `blueprint.ngrxSignals: true`)

Usar cuando:
- Estado compartido entre **2+ features simultáneamente**
- Más de 5 signals con derived state complejo
- Necesitas `patchState()` para updates parciales atómicos
- El dominio tiene más de 5 acciones/métodos

```typescript
// core/state/{domain}.store.ts
export const ProductosStore = signalStore(
  { providedIn: 'root' },
  withState({ items: [] as Producto[], isLoading: false }),
  withComputed(store => ({
    activos: computed(() => store.items().filter(p => p.activo)),
  })),
  withMethods((store, repo = inject(ProductosRepository)) => ({
    async load(): Promise<void> {
      patchState(store, { isLoading: true });
      const items = await repo.findAll();
      patchState(store, { items, isLoading: false });
    },
  }))
);
```

## Regla de escalamiento

1. Empieza siempre con **Facade + BaseFacade**
2. Si el Facade crece a `>5 inject()` o `>8 signals` → migra a **Signal Store**
3. **NUNCA** mezclar Facade + Signal Store para el MISMO dominio
4. Signal Stores viven en `core/state/` — nunca en `features/` ni `shared/`

## Ubicación canónica

| Patrón | Ruta | Extiende |
|--------|------|---------|
| Facade de dominio | `core/facades/{domain}.facade.ts` | `BaseFacade<T>` |
| AuthFacade (excepción) | `core/services/auth.facade.ts` | — (gestiona sesión) |
| Signal Store | `core/state/{domain}.store.ts` | `signalStore()` |
| Repository | `core/repositories/{domain}.repository.ts` | — |
| Service utilitario | `core/services/{nombre}.service.ts` | — |

## Inyección en componentes

- Smart Components (`features/`) inyectan Facades o Signal Stores
- **NUNCA** exponer `patchState` al template — solo métodos del store
- Dumb Components (`shared/`) nunca inyectan — solo `input()` / `output()`
- **NUNCA** inyectar `SupabaseService` ni Repositories en componentes
