import { Injectable, computed, inject, signal } from '@angular/core';
import { WaterApiService } from '@core/services/water/water-api.service';
import { Cuenca, DiagnosticoCuenca, SistemaAPR } from '@core/models/water-domain.model';

@Injectable({
  providedIn: 'root',
})
export class WaterMapFacade {
  private readonly api = inject(WaterApiService);

  // --- Signals de Estado Central ---
  private readonly _cuencas = signal<Cuenca[]>([]);
  private readonly _selectedCuenca = signal<Cuenca | null>(null);
  private readonly _diagnostico = signal<DiagnosticoCuenca | null>(null);
  private readonly _aprs = signal<SistemaAPR[]>([]);
  private readonly _activeLayers = signal<Set<string>>(new Set(['cuencas', 'aprs', 'relaves']));
  private readonly _loading = signal<boolean>(false);
  private readonly _error = signal<string | null>(null);

  // --- Exposición Pública Readonly ---
  readonly cuencas = this._cuencas.asReadonly();
  readonly selectedCuenca = this._selectedCuenca.asReadonly();
  readonly diagnostico = this._diagnostico.asReadonly();
  readonly aprs = this._aprs.asReadonly();
  readonly activeLayers = this._activeLayers.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();

  // --- Computed Signals ---
  readonly totalCuencas = computed(() => this._cuencas().length);

  readonly cuencasEnSequia = computed(() =>
    this._cuencas().filter((c) => Boolean(c.decreto_escasez_activo))
  );

  readonly hasSelectedCuenca = computed(() => this._selectedCuenca() !== null);

  // --- Acciones de Dominio ---

  /** Carga la lista nacional de cuencas */
  loadCuencas(): void {
    this._loading.set(true);
    this._error.set(null);

    this.api.getCuencas().subscribe({
      next: (data) => {
        this._cuencas.set(data || []);
        this._loading.set(false);
      },
      error: (err) => {
        this._error.set(err.message || 'Error al cargar cuencas');
        this._loading.set(false);
      },
    });
  }

  /** Selecciona una cuenca por entidad o código DGA y carga su diagnóstico */
  selectCuenca(target: Cuenca | string): void {
    const cuenca =
      typeof target === 'string'
        ? this._cuencas().find((c) => c.codigo_dga === target) || {
            codigo_dga: target,
            nombre: `Cuenca ${target}`,
            region: 'Chile',
            zona_hidrografica: 'Zona Central',
          }
        : target;

    this._selectedCuenca.set(cuenca);
    this.loadDiagnostico(cuenca.codigo_dga);
  }

  /** Carga el diagnóstico holístico (ISH 0-100) de la cuenca activa */
  loadDiagnostico(cuencaCodigo: string): void {
    this._loading.set(true);
    this.api.getDiagnosticoCuenca(cuencaCodigo).subscribe({
      next: (diag) => {
        this._diagnostico.set(diag);
        this._loading.set(false);
      },
      error: (err) => {
        this._error.set(err.message || 'Error al cargar diagnóstico');
        this._loading.set(false);
      },
    });
  }

  /** Activa o desactiva una capa cartográfica */
  toggleLayer(layerId: string): void {
    this._activeLayers.update((layers) => {
      const next = new Set(layers);
      if (next.has(layerId)) {
        next.delete(layerId);
      } else {
        next.add(layerId);
      }
      return next;
    });
  }

  /** Verifica si una capa está activa */
  isLayerActive(layerId: string): boolean {
    return this._activeLayers().has(layerId);
  }

  /** Deselecciona la cuenca actual */
  clearSelection(): void {
    this._selectedCuenca.set(null);
    this._diagnostico.set(null);
  }
}
