"""
Hydraulic and Physical Consistency Guardrails.
Enforces conservation of mass, statutory consistency, and regulatory invariants.
"""

from typing import Dict, List
from pydantic import BaseModel


class GuardrailResult(BaseModel):
    is_valid: bool
    violations: List[str]


class HydraulicGuardrail:
    """
    Deterministic invariant evaluator for water balance and hydraulic distribution.
    """

    @staticmethod
    def validate_mass_balance(
        caudal_afluente_m3s: float,
        caudal_ecologico_m3s: float,
        extracciones_m3s: Dict[str, float]
    ) -> GuardrailResult:
        """
        Validates conservation of mass:
        sum(extracciones) + caudal_ecologico <= caudal_afluente
        """
        violations = []
        total_extraido = sum(extracciones_m3s.values())
        total_requerido = total_extraido + caudal_ecologico_m3s

        if total_requerido > (caudal_afluente_m3s + 0.001): # Tolerance for float precision
            deficit = total_requerido - caudal_afluente_m3s
            violations.append(
                f"GUARD-HIDRO-001: Violación del principio de conservación de masa. "
                f"Caudal total comprometido ({total_requerido:.3f} m³/s) excede el caudal afluente "
                f"disponible en la estación ({caudal_afluente_m3s:.3f} m³/s). Déficit: {deficit:.3f} m³/s."
            )

        return GuardrailResult(
            is_valid=len(violations) == 0,
            violations=violations
        )

    @staticmethod
    def validate_marco_partidor(distribucion_porcentual: Dict[str, float]) -> GuardrailResult:
        """
        Validates that a marco partidor distributes exactly 100% of the diverted water.
        """
        violations = []
        total = sum(distribucion_porcentual.values())
        if abs(total - 100.0) > 0.01:
            violations.append(
                f"GUARD-HIDRO-002: El marco partidor reparte {total:.2f}%. Debe sumar exactamente 100.00%."
            )
        for ramal, pct in distribucion_porcentual.items():
            if pct <= 0:
                violations.append(f"GUARD-HIDRO-003: El ramal '{ramal}' tiene un porcentaje no positivo ({pct}%).")

        return GuardrailResult(
            is_valid=len(violations) == 0,
            violations=violations
        )
