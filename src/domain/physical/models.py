"""
Bounded Context: Red Física e Hidráulica de Cuencas, Ríos y Canales.
Models the geographic and physical infrastructure of Chile's water networks.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field

from src.core.base import AggregateRoot, Entity, ValueObject
from src.domain.legal.models import CoordenadaUTM


class TipoCanal(str, Enum):
    MATRIZ = "Matriz"          # Nace directamente en la bocatoma del río
    DERIVADO = "Derivado"      # Se desprende del canal matriz
    SUBDERIVADO = "Subderivado"# Ramal menor


class Bocatoma(Entity):
    """
    Obra hidráulica de captación que deriva agua desde el cauce natural hacia un canal.
    """
    nombre: str
    rio_nombre: str
    seccion_rio: int
    capacidad_diseno_m3s: float = Field(ge=0.0, description="Capacidad máxima de captación en m³/s")
    coordenada: Optional[CoordenadaUTM] = None
    sensor_mee_activo: bool = Field(
        default=False,
        description="Cuenta con Monitoreo de Extracciones Efectivas (MEE) homologado por DGA"
    )


class MarcoPartidor(AggregateRoot):
    """
    Dispositivo físico que divide el caudal de un canal proporcionalmente según acciones.
    No posee compuertas móviles; la geometría garantiza la proporción hidráulica.
    """
    nombre: str
    canal_origen_id: str
    distribucion_porcentual: Dict[str, float] = Field(
        description="Mapeo de {nombre_subcanal: porcentaje_del_flujo (0 a 100)}"
    )

    def check_invariants(self) -> List[str]:
        violations = []
        total_pct = sum(self.distribucion_porcentual.values())
        if abs(total_pct - 100.0) > 0.01:
            violations.append(
                f"INV-FIS-001: La suma de repartición del Marco Partidor '{self.nombre}' "
                f"debe ser exactamente 100.0% (actual: {total_pct:.2f}%)."
            )
        return violations


class Canal(AggregateRoot):
    """
    Cauce artificial para conducción de agua.
    """
    nombre: str
    tipo: TipoCanal = TipoCanal.MATRIZ
    bocatoma_origen_id: Optional[str] = None
    canal_padre_id: Optional[str] = None
    longitud_km: Optional[float] = None
    capacidad_maxima_m3s: float = Field(ge=0.0, description="Capacidad máxima de conducción en m³/s")
    marcos_partidores: List[str] = Field(default_factory=list)

    def check_invariants(self) -> List[str]:
        violations = []
        if self.tipo == TipoCanal.MATRIZ and not self.bocatoma_origen_id:
            violations.append(
                f"INV-FIS-002: Todo canal matriz ('{self.nombre}') debe originarse en una bocatoma de río."
            )
        if self.tipo != TipoCanal.MATRIZ and not self.canal_padre_id:
            violations.append(
                f"INV-FIS-003: Un canal derivado ('{self.nombre}') debe indicar su canal matriz o padre."
            )
        return violations


class Cuenca(AggregateRoot):
    """
    Unidad territorial y biogeaográfica delimitada por la DGA (Catastro de Cuencas Hidrográficas).
    """
    codigo_dga: str = Field(description="Ej: '057' para Río Maipo, '054' para Río Aconcagua")
    nombre: str
    region_chile: str
    superficie_km2: float = Field(ge=0.0)
    rios_principales: List[str] = Field(default_factory=list)
