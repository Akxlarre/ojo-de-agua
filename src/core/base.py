"""
DDD Core Primitives (Agnostic).
Provides the fundamental building blocks for Domain-Driven Design architectures:
Entities, Value Objects, Aggregates, Domain Events, and Invariants.
"""

from abc import ABC
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ValueObject(BaseModel):
    """
    Inmutable, without identity. Defined exclusively by its attributes.
    Equality is structural.
    """
    model_config = ConfigDict(frozen=True)


class DomainEvent(BaseModel):
    """
    Immutable representation of a significant domain occurrence in the past.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_name: str
    occurred_on: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bounded_context: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=True)


class Invariant(BaseModel):
    """
    Formal representation of an invariant or hard business rule.
    Must always hold true for the aggregate to remain valid.
    """
    code: str = Field(description="Unique code, e.g., 'INV-HIDRO-001'")
    name: str = Field(description="Human readable rule name")
    description: str = Field(description="Detailed business rationale")
    bounded_context: str = Field(description="Bounded context where this rule applies")
    source_legal_ref: Optional[str] = Field(default=None, description="Legal/Official reference e.g., 'Art. 268 Codigo de Aguas'")
    severity: str = Field(default="CRITICAL", description="CRITICAL, WARNING, or ADVISORY")


class Entity(BaseModel):
    """
    Domain object defined by a continuous identity over time, rather than its attributes.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Entity):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity, ABC):
    """
    Boundary for data consistency and invariant enforcement.
    External objects can only reference the AggregateRoot.
    """
    _domain_events: List[DomainEvent] = []

    def record_event(self, event: DomainEvent) -> None:
        """Register an event that occurred inside the aggregate."""
        if not hasattr(self, "_domain_events") or self._domain_events is None:
            self._domain_events = []
        self._domain_events.append(event)

    def pull_domain_events(self) -> List[DomainEvent]:
        """Retrieve and clear registered domain events (e.g. for publishing)."""
        if not hasattr(self, "_domain_events") or self._domain_events is None:
            return []
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def check_invariants(self) -> List[str]:
        """
        Validate all invariants of the aggregate.
        Returns a list of violation messages. Empty list if all valid.
        """
        return []
