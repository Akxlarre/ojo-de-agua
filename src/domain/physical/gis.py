"""
GIS and Spatial Topology Models for Chile's Water Infrastructure.
Complies with official DGA (Dirección General de Aguas) geographic boundaries.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import AggregateRoot, ValueObject


class GeoBoundingBox(ValueObject):
    """Límites geográficos de una cuenca o subcuenca (latitud y longitud)."""
    lat_min: float = Field(description="Latitud sur mínima (ej: -34.0)")
    lat_max: float = Field(description="Latitud sur máxima (ej: -33.0)")
    lon_min: float = Field(description="Longitud oeste mínima (ej: -71.8)")
    lon_max: float = Field(description="Longitud oeste máxima (ej: -69.8)")

    def contains(self, lat: float, lon: float) -> bool:
        """Determina si un punto está dentro de los límites del Bounding Box."""
        return (self.lat_min <= lat <= self.lat_max) and (self.lon_min <= lon <= self.lon_max)


class CoordenadaWGS84(ValueObject):
    """Coordenada geográfica estándar WGS84 con elevación sobre el nivel del mar."""
    latitud: float = Field(ge=-56.0, le=-17.0, description="Latitud en territorio chileno")
    longitud: float = Field(ge=-76.0, le=-66.0, description="Longitud en territorio continental")
    elevacion_msnm: Optional[float] = Field(default=None, description="Metros sobre el nivel del mar")


class EstacionFluviometrica(AggregateRoot):
    """
    Estación oficial de medición de caudales de la DGA o de una Junta de Vigilancia.
    Identificada por su código BNA (Banco Nacional de Aguas).
    """
    codigo_bna: str = Field(description="Código oficial BNA DGA (ej: '05701001-8')")
    nombre: str = Field(description="Ej: 'Río Maipo en El Manzano'")
    cuenca_dga_codigo: str = Field(description="Código de la cuenca (ej: '057')")
    rio_nombre: str
    coordenada: CoordenadaWGS84
    tiene_telemetria_tiempo_real: bool = True
    caudal_medio_historico_m3s: Optional[float] = None


class CuencaHidrograficaDGA(AggregateRoot):
    """
    Entidad mayor de división territorial hidrográfica de Chile según la DGA.
    """
    codigo_dga: str = Field(description="Código oficial DGA de 3 dígitos (ej: '057')")
    nombre: str = Field(description="Ej: 'Cuenca del Río Maipo'")
    region: str
    zona_hidrografica: str = Field(description="'Norte Grande', 'Norte Chico', 'Zona Central', 'Zona Sur', 'Zona Austral'")
    superficie_km2: float = Field(ge=0.0)
    rios_principales: List[str] = Field(default_factory=list)
    juntas_vigilancia: List[str] = Field(default_factory=list)
    bbox: GeoBoundingBox

    def contiene_punto(self, coordenada: CoordenadaWGS84) -> bool:
        """Verifica si un punto geográfico cae dentro del bounding box de la cuenca."""
        return self.bbox.contains(coordenada.latitud, coordenada.longitud)

    def check_invariants(self) -> List[str]:
        violations = []
        if len(self.codigo_dga) != 3 or not self.codigo_dga.isdigit():
            violations.append(
                f"INV-GIS-001: El código DGA de la cuenca ('{self.codigo_dga}') debe ser numérico de 3 dígitos."
            )
        if self.superficie_km2 <= 0:
            violations.append("INV-GIS-002: La superficie de la cuenca debe ser estrictamente positiva.")
        return violations
