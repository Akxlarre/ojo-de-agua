"""
Event Sourcing & CQRS Engine for Water Operations (Compuertas, Aforos y Celadores).
Maintains an immutable append-only event stream for forensic auditing and rehydration.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from src.core.base import DomainEvent, Entity


class CompuertaAjustadaEvent(DomainEvent):
    event_name: str = "CompuertaAjustada"
    bounded_context: str = "Operacion"
    bocatoma_id: str
    celador_id: str
    orden_turno_id: str
    apertura_porcentaje: float = Field(ge=0.0, le=100.0)
    caudal_resultante_lps: float = Field(ge=0.0)


class AforoRealizadoEvent(DomainEvent):
    event_name: str = "AforoRealizado"
    bounded_context: str = "Operacion"
    estacion_bna_id: str
    caudal_medido_m3s: float = Field(ge=0.0)
    nivel_rio_metros: Optional[float] = None
    metodo_aforo: str = Field(default="Sensor Telemétrico MEE", description="Moliente, MEE, Escala visual")


class EventStore:
    """
    Append-only repository that persists and replays domain events.
    Guarantees immutability and complete historical traceability.
    """

    def __init__(self):
        self._events: List[DomainEvent] = []

    def append(self, event: DomainEvent) -> None:
        self._events.append(event)

    def get_events_for_aggregate(self, aggregate_id: str) -> List[DomainEvent]:
        matching = []
        for e in self._events:
            # Check payload or direct event attributes
            if getattr(e, "bocatoma_id", None) == aggregate_id:
                matching.append(e)
            elif e.payload.get("aggregate_id") == aggregate_id:
                matching.append(e)
        return matching

    def get_all_events(self) -> List[DomainEvent]:
        return list(self._events)


class CompuertaAggregate(Entity):
    """
    Event-Sourced Aggregate Root representing an adjustable water diversion gate.
    State is reconstructed exclusively by replaying its domain events.
    """
    bocatoma_id: str
    nombre: str
    apertura_actual_porcentaje: float = 0.0
    caudal_actual_lps: float = 0.0
    ultimo_celador_operador: Optional[str] = None
    ultima_orden_id: Optional[str] = None
    ultima_modificacion: Optional[datetime] = None

    def apply(self, event: DomainEvent) -> None:
        """State mutation happens strictly inside apply handler."""
        if isinstance(event, CompuertaAjustadaEvent):
            self.apertura_actual_porcentaje = event.apertura_porcentaje
            self.caudal_actual_lps = event.caudal_resultante_lps
            self.ultimo_celador_operador = event.celador_id
            self.ultima_orden_id = event.orden_turno_id
            self.ultima_modificacion = event.occurred_on

    def ajustar(
        self,
        celador_id: str,
        orden_turno_id: str,
        apertura_porcentaje: float,
        caudal_resultante_lps: float
    ) -> CompuertaAjustadaEvent:
        """
        Command method: validates business invariants and raises an event.
        """
        if apertura_porcentaje < 0.0 or apertura_porcentaje > 100.0:
            raise ValueError("La apertura de compuerta debe estar entre 0.0% y 100.0%.")
        if caudal_resultante_lps < 0.0:
            raise ValueError("El caudal resultante no puede ser negativo.")

        event = CompuertaAjustadaEvent(
            bocatoma_id=self.bocatoma_id,
            celador_id=celador_id,
            orden_turno_id=orden_turno_id,
            apertura_porcentaje=apertura_porcentaje,
            caudal_resultante_lps=caudal_resultante_lps
        )
        self.apply(event)
        return event

    @classmethod
    def rehydrate(cls, bocatoma_id: str, nombre: str, events: List[DomainEvent]) -> "CompuertaAggregate":
        """Reconstructs the aggregate from the beginning of time."""
        aggregate = cls(id=bocatoma_id, bocatoma_id=bocatoma_id, nombre=nombre)
        for event in events:
            aggregate.apply(event)
        return aggregate


# --- CQRS Read Projections ---

class BitacoraCeladorProjection:
    """
    Read Model Projection: summarizes physical field maneuvers performed by celadores.
    """

    @staticmethod
    def generar_reporte(event_store: EventStore, celador_id: str) -> List[Dict[str, Any]]:
        maniobras = []
        for ev in event_store.get_all_events():
            if isinstance(ev, CompuertaAjustadaEvent) and ev.celador_id == celador_id:
                maniobras.append({
                    "fecha_hora": ev.occurred_on.isoformat(),
                    "bocatoma": ev.bocatoma_id,
                    "orden": ev.orden_turno_id,
                    "apertura_pct": ev.apertura_porcentaje,
                    "caudal_lps": ev.caudal_resultante_lps
                })
        return maniobras
