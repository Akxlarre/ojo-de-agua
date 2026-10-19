import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CanalRiego,
  Cuenca,
  DecretoEscasez,
  DemandaCanalInput,
  DepositoRelave,
  DiagnosticoCuenca,
  Glaciar,
  PatenteNoUso,
  ResultadoProrrateo,
  SancionAmbiental,
  SistemaAPR,
} from '@core/models/water-domain.model';

@Injectable({
  providedIn: 'root',
})
export class WaterApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl || 'http://localhost:8000';

  /** 1. Lista las cuencas oficiales DGA con métricas ISH */
  getCuencas(): Observable<Cuenca[]> {
    return this.http.get<Cuenca[]>(`${this.baseUrl}/api/cuencas`);
  }

  /** 2. Lista Sistemas de Agua Potable Rural (APR / SSR) */
  getSistemasAPR(comuna?: string, region?: string): Observable<SistemaAPR[]> {
    let params: Record<string, string> = {};
    if (comuna) params['comuna'] = comuna;
    if (region) params['region'] = region;
    return this.http.get<SistemaAPR[]>(`${this.baseUrl}/api/sistemas-apr`, { params });
  }

  /** 3. Lista glaciares del catastro IPG 2022 */
  getGlaciares(cuencaCodigo?: string): Observable<{ glaciares: Glaciar[]; total_coincidentes: number }> {
    let params: Record<string, string> = {};
    if (cuencaCodigo) params['cuenca'] = cuencaCodigo;
    return this.http.get<{ glaciares: Glaciar[]; total_coincidentes: number }>(
      `${this.baseUrl}/api/glaciares`,
      { params }
    );
  }

  /** 4. Lista canales de riego (CNR / CIREN) */
  getCanalesRiego(cuencaCodigo?: string): Observable<{ canales: CanalRiego[]; total_coincidentes: number }> {
    let params: Record<string, string> = {};
    if (cuencaCodigo) params['cuenca'] = cuencaCodigo;
    return this.http.get<{ canales: CanalRiego[]; total_coincidentes: number }>(
      `${this.baseUrl}/api/canales-riego`,
      { params }
    );
  }

  /** 5. Decretos de Escasez Hídrica MOP vigentes */
  getDecretosEscasez(vigente: boolean = true): Observable<DecretoEscasez[]> {
    return this.http.get<DecretoEscasez[]>(`${this.baseUrl}/api/decretos-escasez`, {
      params: { vigente: String(vigente) },
    });
  }

  /** 6. Patentes por No Uso (TGR) para fiscalización */
  getPatentesNoUso(comuna?: string): Observable<{
    filtro_comuna?: string;
    metricas_comuna?: PatenteNoUso[];
    titulares_en_comuna?: PatenteNoUso[];
  }> {
    let params: Record<string, string> = {};
    if (comuna) params['comuna'] = comuna;
    return this.http.get<any>(`${this.baseUrl}/api/patentes-no-uso`, { params });
  }

  /** 7. Diagnóstico holístico de seguridad hídrica (ISH 0-100) por cuenca */
  getDiagnosticoCuenca(cuencaCodigo: string): Observable<DiagnosticoCuenca> {
    return this.http
      .get<any>(`${this.baseUrl}/api/diagnostico/cuenca/${encodeURIComponent(cuencaCodigo)}`)
      .pipe(
        map((raw: any) => {
          const metricas = raw.metricas_clave || {};
          const alertas = raw.alertas_causales || {};
          const crioclima = raw.crioclima || {};
          const fiscalizacion = raw.fiscalizacion || {};
          const clasificacionStr = (raw.clasificacion || raw.semaforo || 'ESTABLE').toUpperCase();
          let semaforoMapped: 'CRITICO' | 'VULNERABLE' | 'ALERTA' | 'ESTABLE' = 'ESTABLE';
          if (clasificacionStr.includes('CRIT') || clasificacionStr.includes('CRÍT')) {
            semaforoMapped = 'CRITICO';
          } else if (clasificacionStr.includes('VULN')) {
            semaforoMapped = 'VULNERABLE';
          } else if (clasificacionStr.includes('ALER')) {
            semaforoMapped = 'ALERTA';
          }

          return {
            cuenca_codigo: raw.codigo_dga || raw.cuenca_codigo || cuencaCodigo,
            cuenca_nombre: raw.nombre || raw.cuenca_nombre || `Cuenca ${cuencaCodigo}`,
            indice_seguridad_hidrica: Number(raw.indice_seguridad_hidrica ?? 50),
            semaforo: semaforoMapped,
            resumen_ejecutivo:
              Array.isArray(raw.hallazgos_criticos) && raw.hallazgos_criticos.length > 0
                ? raw.hallazgos_criticos.join('. ')
                : raw.resumen_ejecutivo || 'Diagnóstico preliminar en proceso de consolidación.',
            decreto_escasez_activo: Boolean(
              metricas.decreto_escasez_activo ?? raw.decreto_escasez_activo
            ),
            alertas_causales: {
              relaves_cerca_apr:
                metricas.amenazas_relave_apr_aristas ?? alertas.relaves_cerca_apr ?? 0,
              descargas_ptas_humedal:
                metricas.descargas_ptas_humedal_aristas ?? alertas.descargas_ptas_humedal ?? 0,
              hidros_compite_riego:
                metricas.compite_hidro_riego_aristas ?? alertas.hidros_compite_riego ?? 0,
            },
            crioclima: {
              total_glaciares: metricas.glaciares_total ?? crioclima.total_glaciares ?? 0,
              volumen_hielo_km3:
                metricas.glaciares_volumen_km3 ?? crioclima.volumen_hielo_km3 ?? 0,
            },
            fiscalizacion: {
              total_patentes_no_uso:
                metricas.patentes_no_uso_utm ?? fiscalizacion.total_patentes_no_uso ?? 0,
              monto_total_utm:
                metricas.patentes_no_uso_utm ?? fiscalizacion.monto_total_utm ?? 0,
              sanciones_sma_activas:
                metricas.sma_sanciones_total ?? fiscalizacion.sanciones_sma_activas ?? 0,
            },
            recomendaciones_politica_publica:
              raw.recomendaciones_gobernanza || raw.recomendaciones_politica_publica || [],
          };
        })
      );
  }

  /** 8. Simulación de Prorrateo Legal determinista (Art. 5 bis y 18) */
  simularProrrateo(
    caudalAfluenteLps: number,
    caudalEcologicoLps: number,
    demandas: DemandaCanalInput[]
  ): Observable<ResultadoProrrateo> {
    const payload = {
      caudal_afluente_lps: caudalAfluenteLps,
      caudal_ecologico_minimo_lps: caudalEcologicoLps,
      demandas_canales: demandas,
    };
    return this.http.post<ResultadoProrrateo>(`${this.baseUrl}/api/prorrateo`, payload);
  }
}
