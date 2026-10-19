"""
Illegal Extraction Guardrail & Telemetry Cross-Verification.
Cross-references real-time MEE (Monitoreo de Extracciones Efectivas) sensor data
against active OUA 'OrdenTurno' authorizations to flag illegal water extraction.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import DomainEvent
from src.domain.operation.models import EstadoOrdenTurno, OrdenTurno


class LecturaSensorMEE(BaseModel):
    bocatoma_id: str
    sensor_id: str
    caudal_instantaneo_lps: float = Field(ge=0.0)
    fecha_hora: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertaInfraccionDGA(DomainEvent):
    event_name: str = "AlertaInfraccionDGA"
    bounded_context: str = "Legal"
    bocatoma_id: str
    tipo_infraccion: str = Field(description="'EXTRACCION_CLANDESTINA_SIN_TURNO' o 'SOBREEXTRACCION_EXCESIVA'")
    caudal_medido_lps: float
    caudal_autorizado_lps: float
    exceso_lps: float
    articulo_legal_violado: str = "Art. 173 y Art. 299 bis Código de Aguas (Ley 21.435)"


class IllegalExtractionGuardrail:
    """
    Automated inspector that flags illegal diversions or quota violations.
    """

    TOLERANCIA_SOBREEXTRACCION_PCT = 10.0 # 10% de tolerancia por fluctuaciones hidráulicas

    @classmethod
    def auditar_extraccion(
        cls,
        lectura_mee: LecturaSensorMEE,
        ordenes_activas: List[OrdenTurno]
    ) -> Optional[AlertaInfraccionDGA]:
        """
        Compara el caudal físico medido por el sensor MEE con las órdenes vigentes.
        """
        # Filtrar órdenes activas correspondientes a esta bocatoma
        ordenes_bocatoma = [
            o for o in ordenes_activas
            if o.bocatoma_o_compuerta == lectura_mee.bocatoma_id
            and o.estado == EstadoOrdenTurno.PROGRAMADA
        ]

        caudal_autorizado_total = sum(o.caudal_concedido_lps for o in ordenes_bocatoma)

        # Caso 1: Extracción Clandestina (Flujo sin ninguna orden autorizada)
        if caudal_autorizado_total == 0.0 and lectura_mee.caudal_instantaneo_lps > 20.0: # Umbral de ruido hidráulico (20 L/s)
            return AlertaInfraccionDGA(
                bocatoma_id=lectura_mee.bocatoma_id,
                tipo_infraccion="EXTRACCION_CLANDESTINA_SIN_TURNO",
                caudal_medido_lps=lectura_mee.caudal_instantaneo_lps,
                caudal_autorizado_lps=0.0,
                exceso_lps=lectura_mee.caudal_instantaneo_lps,
                articulo_legal_violado="Art. 173 y 299 bis Código de Aguas (Extracción no autorizada)"
            )

        # Caso 2: Sobre-extracción (Extracción excede la orden más el margen de tolerancia)
        limite_superior = caudal_autorizado_total * (1.0 + cls.TOLERANCIA_SOBREEXTRACCION_PCT / 100.0)
        if lectura_mee.caudal_instantaneo_lps > limite_superior:
            exceso = lectura_mee.caudal_instantaneo_lps - caudal_autorizado_total
            return AlertaInfraccionDGA(
                bocatoma_id=lectura_mee.bocatoma_id,
                tipo_infraccion="SOBREEXTRACCION_EXCESIVA",
                caudal_medido_lps=lectura_mee.caudal_instantaneo_lps,
                caudal_autorizado_lps=caudal_autorizado_total,
                exceso_lps=round(exceso, 2),
                articulo_legal_violado="Art. 282 y 299 bis Código de Aguas (Violación de Turno de Prorrateo)"
            )

        # Extracción conforme a derecho
        return None
