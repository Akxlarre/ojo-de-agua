"""
Spatial and Topological Guardrails for Water Infrastructure.
Enforces physical invariants: spatial containment, gravity flow direction, and DGA hierarchy.
"""

from typing import List, Optional
from pydantic import BaseModel

from src.domain.physical.gis import CoordenadaWGS84, CuencaHidrograficaDGA


class SpatialGuardrailResult(BaseModel):
    is_valid: bool
    violations: List[str]


class TopologicalGuardrail:
    """
    Guarantees spatial and physical coherence of water infrastructure elements.
    """

    @staticmethod
    def validate_spatial_containment(
        coordenada: CoordenadaWGS84,
        cuenca: CuencaHidrograficaDGA,
        nombre_elemento: str = "Infraestructura"
    ) -> SpatialGuardrailResult:
        """
        Ensures that an extraction intake, canal, or monitoring station
        physically resides within its claimed hydrographic basin.
        """
        violations = []
        if not cuenca.contiene_punto(coordenada):
            violations.append(
                f"GUARD-TOPOLOGY-001: La coordenada ({coordenada.latitud}, {coordenada.longitud}) "
                f"del elemento '{nombre_elemento}' se encuentra fuera del polígono/bounding box "
                f"de la {cuenca.nombre} (DGA {cuenca.codigo_dga})."
            )
        return SpatialGuardrailResult(
            is_valid=len(violations) == 0,
            violations=violations
        )

    @staticmethod
    def validate_gravity_flow(
        cota_captacion_msnm: float,
        cota_entrega_msnm: float,
        tiene_estacion_bombeo: bool = False,
        nombre_canal: str = "Canal"
    ) -> SpatialGuardrailResult:
        """
        Physics Invariant: Open-channel water flows strictly by gravity.
        Point of intake must be higher in elevation than the point of delivery
        unless mechanical pumping is explicitly registered.
        """
        violations = []
        if (cota_entrega_msnm >= cota_captacion_msnm) and not tiene_estacion_bombeo:
            desnivel = cota_entrega_msnm - cota_captacion_msnm
            violations.append(
                f"GUARD-PHYSICS-002: Violación de flujo gravitacional en '{nombre_canal}'. "
                f"La cota de entrega ({cota_entrega_msnm} msnm) es superior o igual a la cota "
                f"de captación ({cota_captacion_msnm} msnm) por {desnivel:.1f} m, y no existe "
                f"estación de elevación mecánica o bombeo registrada."
            )
        return SpatialGuardrailResult(
            is_valid=len(violations) == 0,
            violations=violations
        )
