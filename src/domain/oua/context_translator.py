"""
Context Mapping Translator: DGA Flow Rates (L/s) <--> OUA Fractional Actions (Acciones).
Provides an automated Anti-Corruption Layer (ACL) between Legal-DGA and OUA Operations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import ValueObject


class ConversionResultado(BaseModel):
    bocatoma_id: str
    nombre_titular: str
    numero_acciones: float
    valor_lps_por_accion: float
    caudal_calculado_lps: float
    caudal_tope_legal_daa_lps: Optional[float] = None
    caudal_final_concedido_lps: float
    fue_topado_por_daa: bool = False


class AccionesFlowTranslator:
    """
    Translates relative OUA alícuotas (acciones) into absolute physical flows (L/s)
    conditioned on total circulating river discharge and legal DAA caps.
    """

    @staticmethod
    def calcular_lps_por_accion(caudal_disponible_reparto_lps: float, total_acciones_estatuto: float) -> float:
        """
        Calcula el valor hidráulico instantáneo de una acción de agua:
        L/s por acción = Q_disponible / Total_Acciones
        """
        if total_acciones_estatuto <= 0:
            raise ValueError("El total estatutario de acciones debe ser mayor a 0.")
        return caudal_disponible_reparto_lps / total_acciones_estatuto

    @classmethod
    def traducir_acciones_a_flujo(
        cls,
        caudal_disponible_reparto_lps: float,
        total_acciones_estatuto: float,
        usuarios_acciones: List[Dict[str, Any]]
    ) -> List[ConversionResultado]:
        """
        Traduce el padrón de accionistas a caudal físico, aplicando la invariante
        de tope máximo autorizado en su DAA.
        """
        valor_accion = cls.calcular_lps_por_accion(caudal_disponible_reparto_lps, total_acciones_estatuto)
        resultados = []

        for u in usuarios_acciones:
            bocatoma = u["bocatoma_id"]
            titular = u["nombre"]
            acciones = float(u["acciones"])
            tope_daa = u.get("caudal_maximo_daa_lps")

            caudal_calculado = acciones * valor_accion
            fue_topado = False
            caudal_final = caudal_calculado

            if tope_daa is not None and caudal_calculado > tope_daa:
                caudal_final = tope_daa
                fue_topado = True

            resultados.append(
                ConversionResultado(
                    bocatoma_id=bocatoma,
                    nombre_titular=titular,
                    numero_acciones=acciones,
                    valor_lps_por_accion=round(valor_accion, 3),
                    caudal_calculado_lps=round(caudal_calculado, 2),
                    caudal_tope_legal_daa_lps=tope_daa,
                    caudal_final_concedido_lps=round(caudal_final, 2),
                    fue_topado_por_daa=fue_topado
                )
            )

        return resultados
