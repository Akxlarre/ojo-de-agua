import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { WaterMapFacade } from './water-map.facade';
import { WaterApiService } from '@core/services/water/water-api.service';
import { Cuenca, DiagnosticoCuenca } from '@core/models/water-domain.model';

describe('WaterMapFacade', () => {
  let facade: WaterMapFacade;
  let apiServiceMock: jasmine.SpyObj<WaterApiService>;

  const mockCuencas: Cuenca[] = [
    { codigo_dga: '057', nombre: 'Río Maipo', region: 'RM', zona_hidrografica: 'Zona Central', decreto_escasez_activo: true },
    { codigo_dga: '073', nombre: 'Río Maule', region: 'Maule', zona_hidrografica: 'Zona Central', decreto_escasez_activo: false },
  ];

  const mockDiagnostico: DiagnosticoCuenca = {
    cuenca_codigo: '057',
    cuenca_nombre: 'Río Maipo',
    indice_seguridad_hidrica: 42,
    semaforo: 'CRITICO',
    resumen_ejecutivo: 'Cuenca bajo estrés hídrico severo.',
    decreto_escasez_activo: true,
    alertas_causales: { relaves_cerca_apr: 4, descargas_ptas_humedal: 2, hidros_compite_riego: 3 },
    crioclima: { total_glaciares: 250, volumen_hielo_km3: 12.5 },
    fiscalizacion: { total_patentes_no_uso: 120, monto_total_utm: 5400, sanciones_sma_activas: 8 },
    recomendaciones_politica_publica: ['Priorizar consumo humano en APRs.'],
  };

  beforeEach(() => {
    apiServiceMock = jasmine.createSpyObj<WaterApiService>('WaterApiService', [
      'getCuencas',
      'getDiagnosticoCuenca',
      'getSistemasAPR',
    ]);
    apiServiceMock.getCuencas.and.returnValue(of(mockCuencas));
    apiServiceMock.getDiagnosticoCuenca.and.returnValue(of(mockDiagnostico));
    apiServiceMock.getSistemasAPR.and.returnValue(of([]));

    TestBed.configureTestingModule({
      providers: [
        WaterMapFacade,
        { provide: WaterApiService, useValue: apiServiceMock },
      ],
    });

    facade = TestBed.inject(WaterMapFacade);
  });

  it('should be created and have initial state', () => {
    expect(facade).toBeTruthy();
    expect(facade.cuencas().length).toBe(0);
    expect(facade.selectedCuenca()).toBeNull();
    expect(facade.loading()).toBeFalse();
  });

  it('loadCuencas should populate cuencas and update cuencasEnSequia computed', () => {
    facade.loadCuencas();
    expect(facade.loading()).toBeFalse();
    expect(facade.cuencas().length).toBe(2);
    expect(facade.cuencasEnSequia().length).toBe(1);
    expect(facade.cuencasEnSequia()[0].codigo_dga).toBe('057');
  });

  it('selectCuenca should set selectedCuenca and trigger loadDiagnostico', () => {
    facade.loadCuencas();
    facade.selectCuenca('057');

    expect(facade.selectedCuenca()?.codigo_dga).toBe('057');
    expect(facade.diagnostico()?.indice_seguridad_hidrica).toBe(42);
    expect(apiServiceMock.getDiagnosticoCuenca).toHaveBeenCalledWith('057');
  });

  it('toggleLayer should add and remove layers from activeLayers set', () => {
    expect(facade.isLayerActive('glaciares')).toBeFalse();
    facade.toggleLayer('glaciares');
    expect(facade.isLayerActive('glaciares')).toBeTrue();
    facade.toggleLayer('glaciares');
    expect(facade.isLayerActive('glaciares')).toBeFalse();
  });

  it('handles error gracefully when loadCuencas fails', () => {
    apiServiceMock.getCuencas.and.returnValue(throwError(() => new Error('Network error')));
    facade.loadCuencas();
    expect(facade.error()).toBe('Network error');
    expect(facade.loading()).toBeFalse();
  });
});
