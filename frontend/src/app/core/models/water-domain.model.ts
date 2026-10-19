/**
 * Entidades y DTOs del dominio hídrico chileno (Código de Aguas DFL 1.122 / Ley 21.435).
 * Conecta con los endpoints del backend FastAPI y el Grafo de Conocimiento Nacional.
 */

export type ZonaHidrografica =
  | 'Norte Grande'
  | 'Norte Chico'
  | 'Zona Central'
  | 'Zona Sur'
  | 'Zona Austral';

export type EstadoSemaforoISH = 'CRITICO' | 'VULNERABLE' | 'ALERTA' | 'ESTABLE';

export type EstadoRelave = 'ACTIVO' | 'INACTIVO' | 'ABANDONADO';

export interface GeoPunto {
  latitud: number;
  longitud: number;
}

export interface BoundingBox {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}

/** 1. Macrocuenca hidrográfica oficial de Chile (DGA) */
export interface Cuenca {
  codigo_dga: string;
  nombre: string;
  region: string;
  zona_hidrografica: ZonaHidrografica;
  area_km2?: number;
  bbox?: BoundingBox;
  ish_score?: number;
  semaforo?: EstadoSemaforoISH;
  decreto_escasez_activo?: boolean;
}

/** 2. Sistema Sanitario Rural (Comité / Cooperativa APR) para consumo humano */
export interface SistemaAPR {
  id: string;
  nombre: string;
  comuna: string;
  region: string;
  cuenca_codigo?: string;
  coordenadas?: GeoPunto;
  familias_beneficiadas?: number;
  caudal_diseno_lps?: number;
  amenazas_aguas_arriba_count?: number;
}

/** 3. Depósito de Relave Minero (Sernageomin) */
export interface DepositoRelave {
  id: string;
  nombre: string;
  empresa: string;
  comuna: string;
  region: string;
  cuenca_codigo?: string;
  estado: EstadoRelave;
  coordenadas: GeoPunto;
  distancia_apr_cercano_km?: number;
  apr_amenazado_id?: string;
}

/** 4. Glaciar catastrado en el Inventario Público de Glaciares (IPG 2022) */
export interface Glaciar {
  id: string;
  nombre: string;
  cuenca_codigo: string;
  clasificacion: string;
  area_km2: number;
  volumen_estimado_km3: number;
  agua_dulce_equivalente_km3?: number;
}

/** 5. Canal matriz de la red de riego (CNR / CIREN) */
export interface CanalRiego {
  id: string;
  nombre: string;
  cuenca_codigo: string;
  fuente_hidrica: string;
  junta_vigilancia?: string;
  longitud_km?: number;
}

/** 6. Decreto de Escasez Hídrica dictado por el MOP (Art. 314) */
export interface DecretoEscasez {
  id: string;
  numero_decreto: string;
  cuenca_codigo: string;
  region: string;
  fecha_promulgacion: string;
  fecha_vencimiento: string;
  es_vigente: boolean;
}

/** 7. Patente por No Uso de derechos de aprovechamiento de aguas (TGR Art. 129 bis) */
export interface PatenteNoUso {
  id: string;
  titular_rut: string;
  titular_nombre: string;
  comuna: string;
  cuenca_codigo: string;
  caudal_lps: number;
  monto_utm: number;
  es_moroso: boolean;
}

/** 8. Proceso sancionatorio ambiental vinculado al agua (SMA) */
export interface SancionAmbiental {
  id: string;
  expediente: string;
  titular: string;
  comuna: string;
  estado_sancion: string;
  infraccion_gravedad: string;
  multa_uta?: number;
}

/** 9. Diagnóstico Holístico de Seguridad Hídrica por Cuenca (ISH 0-100) */
export interface DiagnosticoCuenca {
  cuenca_codigo: string;
  cuenca_nombre: string;
  indice_seguridad_hidrica: number;
  semaforo: EstadoSemaforoISH;
  resumen_ejecutivo: string;
  decreto_escasez_activo: boolean;
  alertas_causales: {
    relaves_cerca_apr: number;
    descargas_ptas_humedal: number;
    hidros_compite_riego: number;
  };
  crioclima: {
    total_glaciares: number;
    volumen_hielo_km3: number;
  };
  fiscalizacion: {
    total_patentes_no_uso: number;
    monto_total_utm: number;
    sanciones_sma_activas: number;
  };
  recomendaciones_politica_publica: string[];
}

/** 10. Demanda y simulación de prorrateo legal (Art. 5 bis y 18) */
export interface DemandaCanalInput {
  canal_id: string;
  nombre: string;
  acciones: number;
  caudal_solicitado_lps: number;
  es_consumo_humano?: boolean;
}

export interface ResultadoAsignacionCanal {
  canal_id: string;
  nombre: string;
  acciones: number;
  caudal_entregado_lps: number;
  porcentaje_satisfecho: number;
  es_prioridad_humana: boolean;
}

export interface ResultadoProrrateo {
  caudal_afluente_lps: number;
  caudal_ecologico_lps: number;
  caudal_repartible_lps: number;
  reserva_humana_total_lps: number;
  deficit_total_lps: number;
  factor_prorrateo: number;
  asignaciones: ResultadoAsignacionCanal[];
}
