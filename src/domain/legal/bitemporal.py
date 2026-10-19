"""
Bitemporal Modeling for Water Rights (DAA) and Registry History.
Separates Valid Time (tiempo en que el hecho rige en el río) from
Transaction/System Time (tiempo en que la DGA o el CBR registraron la escritura).
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import Entity, ValueObject
from src.domain.legal.models import ClaseDerecho, TipoAprovechamiento


class IntervaloBitemporal(ValueObject):
    """
    Representa las dos dimensiones temporales de un hecho de dominio:
    1. Tiempo Válido (Mundo Físico / Hecho real)
    2. Tiempo de Transacción (Registro en Base de Datos / CBR)
    """
    valido_desde: date = Field(description="Fecha en que el derecho o extracción rige en la realidad")
    valido_hasta: Optional[date] = Field(default=None, description="Fecha de extinción o caducidad física (None si vigente)")
    registrado_el: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Momento exacto en que el sistema o el CBR tomó conocimiento y asentó el registro"
    )
    reemplazado_el: Optional[datetime] = Field(
        default=None,
        description="Momento en que este registro fue enmendado o corregido por una resolución posterior"
    )

    def contiene_tiempo_valido(self, fecha_consulta: date) -> bool:
        if fecha_consulta < self.valido_desde:
            return False
        if self.valido_hasta is not None and fecha_consulta > self.valido_hasta:
            return False
        return True

    def contiene_tiempo_transaccion(self, tiempo_sistema: datetime) -> bool:
        if tiempo_sistema < self.registrado_el:
            return False
        if self.reemplazado_el is not None and tiempo_sistema >= self.reemplazado_el:
            return False
        return True


class RegistroBitemporalDAA(Entity):
    """
    Registro bitemporal de un Derecho de Aprovechamiento de Aguas.
    Permite responder consultas 'As-Of' (¿Cuál era el derecho legal en fecha X según sabíamos en fecha Y?).
    """
    codigo_dga: str
    titular: str
    caudal_lps: float
    tipo: TipoAprovechamiento = TipoAprovechamiento.CONSUNTIVO
    clase: ClaseDerecho = ClaseDerecho.PERMANENTE
    temporalidad: IntervaloBitemporal

    def es_valido_en(self, fecha_mundo_real: date, as_of_tiempo_sistema: datetime) -> bool:
        """
        Consulta bitemporal exacta.
        """
        es_valido_mundo = self.temporalidad.contiene_tiempo_valido(fecha_mundo_real)
        era_conocido_en_sistema = self.temporalidad.contiene_tiempo_transaccion(as_of_tiempo_sistema)
        return es_valido_mundo and era_conocido_en_sistema
