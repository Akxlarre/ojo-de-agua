"""
Bounded Context: Legal & Regulatorio (Código de Aguas de Chile - DFL 1.122 / Ley 21.435).
Defines DAA (Derechos de Aprovechamiento de Aguas), inscripciones y estado registral.
"""

from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import Field

from src.core.base import AggregateRoot, ValueObject


class TipoAprovechamiento(str, Enum):
    CONSUNTIVO = "Consuntivo"        # El agua no se restituye al cauce
    NO_CONSUNTIVO = "No Consuntivo"  # El agua debe restituirse (ej: hidroeléctricas)


class ClaseDerecho(str, Enum):
    PERMANENTE = "Permanente"  # Se satisfacen con prioridad en cauces naturales
    EVENTUAL = "Eventual"      # Solo se satisfacen en épocas de sobrante


class ModalidadEjercicio(str, Enum):
    CONTINUO = "Continuo"
    DISCONTINUO = "Discontinuo"
    ALTERNADO = "Alternado"


class FuenteAgua(str, Enum):
    SUPERFICIAL = "Superficial"
    SUBTERRANEA = "Subterranea"


class InscripcionCBR(ValueObject):
    """
    Registro en el Conservador de Bienes Raíces (Registro de Propiedad de Aguas).
    Requisito de validez y tradición del dominio en Chile.
    """
    foja: str
    numero: str
    ano: int
    comuna_cbr: str
    fecha_inscripcion: Optional[date] = None


class CoordenadaUTM(ValueObject):
    """Coordenada oficial georreferenciada del punto de captación."""
    norte: float
    este: float
    huso: int = 19
    datum: str = "WGS84"


class DAA(AggregateRoot):
    """
    Derecho de Aprovechamiento de Aguas.
    Concesión de uso otorgada por el Estado (DGA) o reconocida por la ley.
    """
    codigo_dga: str = Field(description="Código de expediente o resolución DGA")
    titular_nombre: str
    titular_rut: str
    tipo: TipoAprovechamiento
    clase: ClaseDerecho
    modalidad: ModalidadEjercicio = ModalidadEjercicio.CONTINUO
    fuente: FuenteAgua = FuenteAgua.SUPERFICIAL
    caudal_lps: float = Field(description="Caudal autorizado en litros por segundo (L/s)")
    coordenada_captacion: Optional[CoordenadaUTM] = None
    inscripcion_cbr: Optional[InscripcionCBR] = None
    inscrito_cpa: bool = Field(
        default=False,
        description="Inscrito en el Catastro Público de Aguas (CPA) de la DGA (obligatorio por Ley 21.435)"
    )
    vigente: bool = True

    def check_invariants(self) -> List[str]:
        violations = []
        if self.caudal_lps <= 0:
            violations.append("INV-LEGAL-003: El caudal de un DAA debe ser estrictamente mayor a 0 L/s.")
        if self.vigente and not self.inscrito_cpa:
            violations.append("INV-LEGAL-001 (Alerta Ley 21.435): El DAA no cuenta con registro en el Catastro Público de Aguas (CPA).")
        if self.vigente and not self.inscripcion_cbr:
            violations.append("INV-LEGAL-002: El DAA carece de inscripción en el Registro de Propiedad de Aguas del CBR competente.")
        return violations
