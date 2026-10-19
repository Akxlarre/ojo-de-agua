"""
DTOs y Esquemas Fuertemente Tipados para Catastros Oficiales de Recursos Hídricos (Pydantic v2).
Garantiza validación estructural, tipos seguros y limpieza previa a la ingestión en el grafo.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class IncendioRawDTO(BaseModel):
    id: str
    nombre: str
    temporada: str = "2023-2024"
    fecha_inicio: str
    comuna: str
    region: str
    cuenca_codigo: str
    cuenca_nombre: Optional[str] = None
    superficie_ha: float = Field(ge=0.0)
    severidad: str = Field(default="MEDIA", description="'EXTREMA', 'MUY ALTA', 'ALTA', 'MEDIA'")
    causa_probable: Optional[str] = None
    tipo_cobertura: Optional[str] = None
    latitud: float = Field(ge=-90.0, le=90.0)
    longitud: float = Field(ge=-180.0, le=180.0)
    impacto_embalse: Optional[str] = None
    amenaza_apr_cercanos: List[str] = Field(default_factory=list)
    riesgo_aluvial_post_incendio: Optional[str] = Field(default="MEDIO")


class DemandaAgricolaRawDTO(BaseModel):
    cuenca_codigo: str
    cuenca_nombre: str
    region: Optional[str] = None
    zona_hidrografica: Optional[str] = None
    superficie_regada_total_ha: float = Field(ge=0.0)
    superficie_riego_tecnificado_ha: float = Field(default=0.0, ge=0.0)
    superficie_riego_gravitacional_ha: float = Field(default=0.0, ge=0.0)
    porcentaje_tecnificacion: float = Field(default=0.0, ge=0.0, le=100.0)
    demanda_hidrica_bruta_m3_ano: float = Field(ge=0.0)
    demanda_media_agricola_lps: float = Field(default=0.0, ge=0.0)
    estres_hidrico_agricola: str = Field(default="BAJO")
    cultivos_principales: List[str] = Field(default_factory=list)
    eficiencia_media_conduccion_pct: Optional[float] = None
    proyectos_ley_18450_activos: Optional[int] = 0
    fuente_oficial: Optional[str] = None


class PredioRiegoRawDTO(BaseModel):
    id: str
    nombre_valle: str
    comuna: str
    region: Optional[str] = None
    cuenca_codigo: str
    cuenca_nombre: Optional[str] = None
    superficie_ha: float = Field(ge=0.0)
    sistema_riego: str = Field(default="Gravitacional")
    porcentaje_tecnificacion: float = Field(default=50.0, ge=0.0, le=100.0)
    canal_matriz_fuente: str = Field(default="Canal local")
    cultivos_principales: List[str] = Field(default_factory=list)
    demanda_estimada_lps: float = Field(default=0.0, ge=0.0)
    latitud: float = Field(ge=-90.0, le=90.0)
    longitud: float = Field(ge=-180.0, le=180.0)


class DesaladoraRawDTO(BaseModel):
    id: str
    nombre: str
    operador: Optional[str] = None
    sector_destino: Optional[str] = "Minería"
    estado_operativo: str = Field(default="Operativo")
    es_operativa: bool = True
    tecnologia: str = Field(default="Osmosis Inversa")
    capacidad_lps: float = Field(ge=0.0)
    capacidad_m3_dia: float = Field(default=0.0, ge=0.0)
    region: Optional[str] = None
    cuenca_codigo: Optional[str] = None
    cuenca_nombre: Optional[str] = None
    coordenadas: Optional[Union[Dict[str, float], List[float]]] = None
    fuente_oficial: Optional[str] = None


class EmbalseOficialRawDTO(BaseModel):
    id: str
    nombre: str
    region: Optional[str] = None
    comuna: Optional[str] = None
    altura_muro_m: Optional[float] = None
    uso: Optional[str] = "RIEGO"
    tamano: Optional[str] = "GRANDE"
    ano_construccion: Optional[str] = None
    monitoreo_dga: bool = False
    coordenadas: Optional[Union[Dict[str, float], List[float]]] = None
    cuenca_codigo: Optional[str] = None


class RelaveRawDTO(BaseModel):
    id: str
    nombre: str
    region: Optional[str] = None
    comuna: Optional[str] = None
    estado_operativo: str
    clasificacion_riesgo: Optional[str] = None
    volumen_total_actual_m3: Optional[float] = 0.0
    cuenca_codigo: Optional[str] = None
    coordenadas: Optional[Union[Dict[str, float], List[float]]] = None


class HumedalProtegidoDTO(BaseModel):
    id: str
    codigo_humedal: Optional[str] = None
    nombre: str
    superficie_ha: float = Field(ge=0.0)
    region: Optional[str] = None
    comuna: Optional[str] = None
    cuenca_codigo: Optional[str] = None
    resolucion_mma: Optional[str] = None
    es_protegido_ley_21202: bool = True
    coordenadas: Optional[Union[Dict[str, float], List[float]]] = None
