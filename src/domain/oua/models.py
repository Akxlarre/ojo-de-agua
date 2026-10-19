"""
Bounded Context: Organizaciones de Usuarios de Agua (OUAs) de Chile.
Models Juntas de Vigilancia, Asociaciones de Canalistas, Comunidades de Aguas y sus padrones de accionistas.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field

from src.core.base import AggregateRoot, ValueObject


class TipoOUA(str, Enum):
    JUNTA_VIGILANCIA = "Junta de Vigilancia"         # Cauces naturales (ríos, esteros)
    ASOCIACION_CANALISTAS = "Asociacion de Canalistas" # Canales artificiales matrices
    COMUNIDAD_AGUAS = "Comunidad de Aguas"           # Canales secundarios o pozos


class AccionistaOUA(ValueObject):
    """
    Miembro del padrón de regantes de una OUA.
    La posesión de 'acciones' define su cuota de participación y su voto.
    """
    rut: str
    nombre: str
    numero_acciones: float = Field(ge=0.0, description="Cantidad de alícuotas o acciones que posee")
    cuotas_al_dia: bool = Field(default=True, description="Si adeuda cuotas sociales no tiene derecho a voto")


class JuntaVigilancia(AggregateRoot):
    """
    Organización máxima de una cuenca o sección de río.
    Distribuye el agua del cauce natural entre los canales matrices según sus títulos.
    """
    nombre: str = Field(description="Ej: 'Junta de Vigilancia del Río Maipo Primera Sección'")
    rio_nombre: str
    seccion_rio: int = Field(ge=1, description="Sección del río (1ra, 2da, 3ra sección, etc.)")
    rut: Optional[str] = None
    total_acciones: float = Field(ge=0.0, description="Total estatutario de acciones en que se divide el río")
    asociaciones_canalistas_adheridas: List[str] = Field(
        default_factory=list,
        description="IDs o nombres de Asociaciones de Canalistas matrices conectadas"
    )
    decreto_escasez_activo: bool = Field(
        default=False,
        description="Indica si rige un Decreto de Escasez Hídrica DGA en su jurisdicción"
    )

    def check_invariants(self) -> List[str]:
        violations = []
        if self.total_acciones <= 0:
            violations.append("INV-OUA-001: La Junta de Vigilancia debe tener un total de acciones estatutarias mayor a 0.")
        return violations


class AsociacionCanalistas(AggregateRoot):
    """
    Organización que administra un canal matriz artificial derivado de una bocatoma de río.
    """
    nombre: str = Field(description="Ej: 'Asociación de Canalistas del Canal San Carlos'")
    canal_matriz: str
    bocatoma_nombre: str
    junta_vigilancia_id: Optional[str] = None
    total_acciones: float = Field(ge=0.0, description="Total de acciones estatutarias del canal")
    padron_accionistas: List[AccionistaOUA] = Field(default_factory=list)

    def suma_acciones_padron(self) -> float:
        return sum(a.numero_acciones for a in self.padron_accionistas)

    def check_invariants(self) -> List[str]:
        violations = []
        if self.total_acciones <= 0:
            violations.append("INV-OUA-002: La Asociación de Canalistas debe definir un total de acciones positivo.")
        
        # Validar consistencia del padrón con el total de acciones
        if self.padron_accionistas:
            suma = self.suma_acciones_padron()
            if abs(suma - self.total_acciones) > 0.001:
                violations.append(
                    f"INV-OUA-003: La suma de acciones de los accionistas ({suma:.2f}) "
                    f"no coincide con el total estatutario ({self.total_acciones:.2f})."
                )
        return violations
