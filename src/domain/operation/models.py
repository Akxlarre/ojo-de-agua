"""
Bounded Context: Operación en Terreno, Celadores, Aforos y Prorrateos.
Represents field operations, physical gate adjustments, and flow allocations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field

from src.core.base import AggregateRoot, Entity, ValueObject


class EstadoOrdenTurno(str, Enum):
    PROGRAMADA = "Programada"
    EJECUTADA = "Ejecutada"
    INCUMPLIDA = "Incumplida"


class Celador(AggregateRoot):
    """
    Operador de terreno encargado de la vigilancia de cauces, compuertas y marcos partidores.
    Es el brazo ejecutor de la distribución de agua de una Asociación o Junta.
    """
    rut: str
    nombre: str
    organizacion_oua_id: str = Field(description="ID de la OUA a la que reporta")
    sector_asignado: str = Field(description="Tramo geográfico de canales o bocatomas a su cargo")
    telefono: Optional[str] = None
    activo: bool = True

    def check_invariants(self) -> List[str]:
        violations = []
        if not self.sector_asignado.strip():
            violations.append("INV-OP-001: Todo celador debe tener un sector geográfico o tramo asignado.")
        return violations


class OrdenTurno(AggregateRoot):
    """
    Instrucción formal emitida por el Repartidor General o Directorio para abrir/cerrar compuertas.
    """
    fecha_emision: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    repartidor_autorizante: str
    celador_id: str
    bocatoma_o_compuerta: str
    caudal_concedido_lps: float = Field(ge=0.0, description="Caudal a entregar en L/s")
    horas_duracion: float = Field(gt=0.0, description="Duración del turno de riego en horas")
    estado: EstadoOrdenTurno = EstadoOrdenTurno.PROGRAMADA

    def check_invariants(self) -> List[str]:
        violations = []
        if self.caudal_concedido_lps <= 0:
            violations.append("INV-OP-002: Una orden de turno debe conferir un caudal mayor a 0 L/s.")
        return violations


class BalanceHidricoSeccion(AggregateRoot):
    """
    Verificación del balance de masa en una sección de río administrada por una Junta de Vigilancia.
    """
    seccion_id: str
    caudal_afluente_m3s: float = Field(ge=0.0, description="Caudal medido al inicio de la sección (m³/s)")
    caudal_ecologico_minimo_m3s: float = Field(
        default=0.0,
        ge=0.0,
        description="Caudal ecológico que por ley debe fluir hacia la sección siguiente"
    )
    extracciones_bocatomas_m3s: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapeo de {bocatoma_nombre: caudal_captado_m3s}"
    )

    def total_extraido_m3s(self) -> float:
        return sum(self.extracciones_bocatomas_m3s.values())

    def caudal_remanente_efectivo_m3s(self) -> float:
        return self.caudal_afluente_m3s - self.total_extraido_m3s()

    def check_invariants(self) -> List[str]:
        violations = []
        total_extraido = self.total_extraido_m3s()
        total_comprometido = total_extraido + self.caudal_ecologico_minimo_m3s

        if total_comprometido > self.caudal_afluente_m3s:
            deficit = total_comprometido - self.caudal_afluente_m3s
            violations.append(
                f"INV-HIDRO-001 (Violación Balance de Masa): La suma de extracciones ({total_extraido:.2f} m³/s) "
                f"+ Caudal Ecológico ({self.caudal_ecologico_minimo_m3s:.2f} m³/s) excede el caudal afluente "
                f"del río ({self.caudal_afluente_m3s:.2f} m³/s) por un déficit de {deficit:.2f} m³/s. "
                f"Se requiere prorrateo inmediato de la Junta de Vigilancia."
            )
        return violations
