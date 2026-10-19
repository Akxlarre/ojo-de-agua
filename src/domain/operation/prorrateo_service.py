"""
Domain Service: Motor de Prorrateo Legal y Distribución Jerárquica de Aguas.
Implements Art. 5 bis (Prioridad de Consumo Humano) and Art. 18 (Permanentes vs Eventuales)
of the Chilean Water Code (Ley 21.435).
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import ValueObject


class EstadoEscasez(str, Enum):
    ABUNDANCIA = "Abundancia (Satisface Permanentes y Eventuales)"
    NORMAL = "Normal (Satisface 100% Permanentes)"
    PRORRATEO_MODERADO = "Prorrateo Moderado (Factor Permanente > 0.70)"
    PRORRATEO_SEVERO = "Prorrateo Severo (Factor Permanente <= 0.70)"
    EMERGENCIA_CONSUMO_HUMANO = "Emergencia Crítica (Déficit en Consumo Humano)"


class DemandaCanal(ValueObject):
    """Demanda hídrica solicitada por una bocatoma o canal matriz."""
    bocatoma_id: str
    nombre_canal: str
    caudal_consumo_humano_lps: float = Field(default=0.0, ge=0.0, description="Destinado a APR o agua potable")
    caudal_permanente_autorizado_lps: float = Field(ge=0.0, description="Derechos permanentes (riego/industria)")
    caudal_eventual_autorizado_lps: float = Field(default=0.0, ge=0.0, description="Derechos eventuales")


class AsignacionCanal(ValueObject):
    """Resultado del cálculo de entrega física para una bocatoma."""
    bocatoma_id: str
    nombre_canal: str
    caudal_consumo_humano_entregado_lps: float
    caudal_permanente_entregado_lps: float
    caudal_eventual_entregado_lps: float
    caudal_total_entregado_lps: float
    porcentaje_satisfaccion_total: float


class ResultadoProrrateo(BaseModel):
    """Veredicto determinista de distribución hídrica en una sección de río."""
    caudal_afluente_disponible_lps: float
    caudal_humano_total_reservado_lps: float
    caudal_ecologico_reservado_lps: float
    factor_prorrateo_permanente: float = Field(ge=0.0, le=1.0, description="Factor alpha de prorrateo permanente")
    factor_prorrateo_eventual: float = Field(ge=0.0, le=1.0, description="Factor beta de sobrante para eventuales")
    estado_cuenca: EstadoEscasez
    asignaciones_por_canal: List[AsignacionCanal]
    invariantes_violadas: List[str] = Field(default_factory=list)


class ProrrateoLegalService:
    """
    Domain Service que ejecuta el algoritmo legal de distribución hídrica en Chile.
    """

    @classmethod
    def calcular_distribucion(
        cls,
        caudal_afluente_lps: float,
        caudal_ecologico_minimo_lps: float,
        demandas_canales: List[DemandaCanal]
    ) -> ResultadoProrrateo:
        """
        Calcula la asignación estricta de caudales respetando la jerarquía de la Ley 21.435.
        """
        # FAL-09: Guardrails de consistencia física y regulatoria
        if caudal_afluente_lps < 0:
            raise ValueError(f"El caudal afluente no puede ser negativo ({caudal_afluente_lps} L/s).")
        if caudal_ecologico_minimo_lps < 0:
            raise ValueError(f"El caudal ecológico mínimo no puede ser negativo ({caudal_ecologico_minimo_lps} L/s).")

        invariantes = []
        
        # 1. Sumar demandas agregadas

        demanda_humana_total = sum(d.caudal_consumo_humano_lps for d in demandas_canales)
        demanda_permanente_total = sum(d.caudal_permanente_autorizado_lps for d in demandas_canales)
        demanda_eventual_total = sum(d.caudal_eventual_autorizado_lps for d in demandas_canales)

        # 2. Paso 1: Reserva de Consumo Humano (Prioridad Absoluta Art. 5 bis)
        if caudal_afluente_lps < demanda_humana_total:
            # Caso de crisis extrema: ni siquiera el agua del río alcanza para beber
            factor_humano = caudal_afluente_lps / demanda_humana_total if demanda_humana_total > 0 else 0.0
            invariantes.append(
                f"INV-LEGAL-CRISIS: El caudal del río ({caudal_afluente_lps:.1f} L/s) es inferior "
                f"a la demanda vital de consumo humano ({demanda_humana_total:.1f} L/s). Alerta sanitaria máxima."
            )
            asignaciones = [
                AsignacionCanal(
                    bocatoma_id=d.bocatoma_id,
                    nombre_canal=d.nombre_canal,
                    caudal_consumo_humano_entregado_lps=d.caudal_consumo_humano_lps * factor_humano,
                    caudal_permanente_entregado_lps=0.0,
                    caudal_eventual_entregado_lps=0.0,
                    caudal_total_entregado_lps=d.caudal_consumo_humano_lps * factor_humano,
                    porcentaje_satisfaccion_total=(factor_humano * 100.0) if d.caudal_consumo_humano_lps > 0 else 0.0
                )
                for d in demandas_canales
            ]
            return ResultadoProrrateo(
                caudal_afluente_disponible_lps=caudal_afluente_lps,
                caudal_humano_total_reservado_lps=caudal_afluente_lps,
                caudal_ecologico_reservado_lps=0.0,
                factor_prorrateo_permanente=0.0,
                factor_prorrateo_eventual=0.0,
                estado_cuenca=EstadoEscasez.EMERGENCIA_CONSUMO_HUMANO,
                asignaciones_por_canal=asignaciones,
                invariantes_violadas=invariantes
            )

        caudal_post_humano = caudal_afluente_lps - demanda_humana_total

        # 3. Paso 2: Reserva de Caudal Ecológico Mínimo (Art. 129 bis 1)
        caudal_ecologico_efectivo = min(caudal_post_humano, caudal_ecologico_minimo_lps)
        caudal_remanente_productivo = caudal_post_humano - caudal_ecologico_efectivo

        # 4. Paso 3: Asignación a Derechos Permanentes (Art. 18 CdA)
        factor_permanente = 1.0
        factor_eventual = 0.0

        if demanda_permanente_total > 0:
            if caudal_remanente_productivo >= demanda_permanente_total:
                # Los permanentes se satisfacen al 100%
                factor_permanente = 1.0
                sobrante_para_eventuales = caudal_remanente_productivo - demanda_permanente_total
                
                # 5. Paso 4: Asignación a Derechos Eventuales (Sólo si sobra)
                if demanda_eventual_total > 0:
                    factor_eventual = min(1.0, sobrante_para_eventuales / demanda_eventual_total)
            else:
                # No alcanza para los permanentes -> PRORRATEO OBLIGATORIO
                factor_permanente = caudal_remanente_productivo / demanda_permanente_total
                factor_eventual = 0.0 # Prohibido por ley entregar a eventuales si permanentes sufren prorrateo
        else:
            factor_permanente = 1.0
            if demanda_eventual_total > 0:
                factor_eventual = min(1.0, caudal_remanente_productivo / demanda_eventual_total)

        # 6. Determinar Estado de la Cuenca
        if factor_permanente == 1.0 and factor_eventual > 0:
            estado = EstadoEscasez.ABUNDANCIA
        elif factor_permanente == 1.0:
            estado = EstadoEscasez.NORMAL
        elif factor_permanente > 0.70:
            estado = EstadoEscasez.PRORRATEO_MODERADO
        else:
            estado = EstadoEscasez.PRORRATEO_SEVERO

        # 7. Construir asignaciones individuales por canal
        asignaciones = []
        for d in demandas_canales:
            humano = d.caudal_consumo_humano_lps
            perm = d.caudal_permanente_autorizado_lps * factor_permanente
            event = d.caudal_eventual_autorizado_lps * factor_eventual
            total_entregado = humano + perm + event
            total_solicitado = d.caudal_consumo_humano_lps + d.caudal_permanente_autorizado_lps + d.caudal_eventual_autorizado_lps
            pct = (total_entregado / total_solicitado * 100.0) if total_solicitado > 0 else 100.0

            asignaciones.append(
                AsignacionCanal(
                    bocatoma_id=d.bocatoma_id,
                    nombre_canal=d.nombre_canal,
                    caudal_consumo_humano_entregado_lps=round(humano, 2),
                    caudal_permanente_entregado_lps=round(perm, 2),
                    caudal_eventual_entregado_lps=round(event, 2),
                    caudal_total_entregado_lps=round(total_entregado, 2),
                    porcentaje_satisfaccion_total=round(pct, 2)
                )
            )

        # 8. Validar balance de masa estricto
        total_asignado = sum(a.caudal_total_entregado_lps for a in asignaciones)
        balance_total = total_asignado + caudal_ecologico_efectivo
        if balance_total > (caudal_afluente_lps + 0.1): # Margen de redondeo float
            invariantes.append(
                f"INV-BALANCE-MASA: Asignación total ({balance_total:.2f} L/s) excede el caudal del río ({caudal_afluente_lps:.2f} L/s)."
            )

        return ResultadoProrrateo(
            caudal_afluente_disponible_lps=caudal_afluente_lps,
            caudal_humano_total_reservado_lps=round(demanda_humana_total, 2),
            caudal_ecologico_reservado_lps=round(caudal_ecologico_efectivo, 2),
            factor_prorrateo_permanente=round(factor_permanente, 4),
            factor_prorrateo_eventual=round(factor_eventual, 4),
            estado_cuenca=estado,
            asignaciones_por_canal=asignaciones,
            invariantes_violadas=invariantes
        )
