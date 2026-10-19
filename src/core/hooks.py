"""
Agentic Lifecycle Hooks Engine.
Provides pluggable interceptors for the knowledge harness:
Pre-Ingestion, Post-Extraction, Pre-Query (ACL/Enrichment), Post-Execution, and Invariant Violation.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class HookStage(str, Enum):
    PRE_INGESTION = "pre_ingestion"
    POST_EXTRACTION = "post_extraction"
    PRE_QUERY = "pre_query"
    POST_EXECUTION = "post_execution"
    ON_INVARIANT_VIOLATION = "on_invariant_violation"


class HookContext(BaseModel):
    """
    Contextual payload passed to every hook during execution.
    """
    stage: HookStage
    bounded_context: Optional[str] = None
    input_data: Any = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    aborted: bool = False
    abort_reason: Optional[str] = None


HookCallable = Callable[[HookContext], HookContext]


class HookManager:
    """
    Registry and runner for lifecycle hooks.
    """

    def __init__(self):
        self._hooks: Dict[HookStage, List[HookCallable]] = {stage: [] for stage in HookStage}

    def register(self, stage: HookStage, hook: HookCallable) -> None:
        self._hooks[stage].append(hook)

    def trigger(self, stage: HookStage, context: HookContext) -> HookContext:
        """
        Executes all hooks registered for a given stage in sequence.
        Halts if a hook marks context.aborted = True.
        """
        context.stage = stage
        for hook in self._hooks[stage]:
            try:
                context = hook(context)
                if context.aborted:
                    break
            except Exception as e:
                context.metadata["hook_error"] = str(e)
                # Fail-safe: don't let hook crash unhandled
                break
        return context
