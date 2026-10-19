import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { WaterApiService } from './water-api.service';
import { environment } from '../../../../environments/environment';

describe('WaterApiService', () => {
  let service: WaterApiService;
  let httpMock: HttpTestingController;
  const baseUrl = environment.apiBaseUrl || 'http://localhost:8000';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [WaterApiService],
    });
    service = TestBed.inject(WaterApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('getCuencas should GET /api/cuencas', () => {
    const mockCuencas = [{ codigo_dga: '057', nombre: 'Río Maipo', region: 'RM', zona_hidrografica: 'Zona Central' as const }];
    service.getCuencas().subscribe(data => {
      expect(data.length).toBe(1);
      expect(data[0].codigo_dga).toBe('057');
    });

    const req = httpMock.expectOne(`${baseUrl}/api/cuencas`);
    expect(req.request.method).toBe('GET');
    req.flush(mockCuencas);
  });

  it('getDiagnosticoCuenca should GET /api/diagnostico/cuenca/{id}', () => {
    service.getDiagnosticoCuenca('057').subscribe(diag => {
      expect(diag.cuenca_codigo).toBe('057');
      expect(diag.indice_seguridad_hidrica).toBe(45);
    });

    const req = httpMock.expectOne(`${baseUrl}/api/diagnostico/cuenca/057`);
    expect(req.request.method).toBe('GET');
    req.flush({ cuenca_codigo: '057', cuenca_nombre: 'Río Maipo', indice_seguridad_hidrica: 45 });
  });

  it('simularProrrateo should POST /api/prorrateo with correct body', () => {
    const demandas = [{ canal_id: 'C1', nombre: 'Canal San Carlos', acciones: 100, caudal_solicitado_lps: 500 }];
    service.simularProrrateo(1000, 100, demandas).subscribe(res => {
      expect(res.caudal_afluente_lps).toBe(1000);
    });

    const req = httpMock.expectOne(`${baseUrl}/api/prorrateo`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.caudal_afluente_lps).toBe(1000);
    req.flush({ caudal_afluente_lps: 1000, caudal_repartible_lps: 900, asignaciones: [] });
  });
});
