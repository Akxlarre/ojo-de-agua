"""
Agentic Knowledge Harness Runner.
Orchestrates the ingestion, validation, guardrailing, and query lifecycle
for Domain-Driven Knowledge bases.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from src.core.hooks import HookContext, HookManager, HookStage
from src.core.ubiquitous import LintViolation
from src.guardrails.hydraulic_guard import HydraulicGuardrail
from src.guardrails.ubiquitous_linter import WaterUbiquitousGuard
from src.memory.graph import DomainEdge, DomainKnowledgeGraph, DomainNode


class IngestionReport(BaseModel):
    success: bool
    nodes_added: int = 0
    edges_added: int = 0
    lint_violations: List[LintViolation] = Field(default_factory=list)
    guardrail_errors: List[str] = Field(default_factory=list)
    aborted_by_hook: bool = False
    abort_reason: Optional[str] = None


class KnowledgeHarness:
    """
    The central runtime harness.
    Guarantees that no knowledge enters or exits without passing through
    domain hooks and guardrails.
    """

    def __init__(self, ubiquitous_dataset_path: Optional[str] = None):
        self._graph = DomainKnowledgeGraph()
        self._token_index: Dict[str, Set[str]] = {}
        self.hook_manager = HookManager()
        self.ubiquitous_guard = WaterUbiquitousGuard(ubiquitous_dataset_path)
        self.hydraulic_guard = HydraulicGuardrail()
        self._setup_default_hooks()

    @property
    def graph(self) -> DomainKnowledgeGraph:
        return self._graph

    @graph.setter
    def graph(self, value: DomainKnowledgeGraph) -> None:
        self._graph = value
        self._build_index()

    def _build_index(self) -> None:
        """Construye el índice invertido de tokens para búsquedas sub-milisegundo."""
        self._token_index = {}
        for node in self._graph.nodes.values():
            self._index_node(node)

    def _index_node(self, node: DomainNode) -> None:
        """Indexa los tokens del nombre e identificador de un nodo."""
        tokens = set(w.strip("¿?.,;:!\"'()[]{}").lower() for w in node.name.lower().split() if len(w) > 2)
        tokens.add(node.id.lower())
        for token in tokens:
            if token not in self._token_index:
                self._token_index[token] = set()
            self._token_index[token].add(node.id)


    def _setup_default_hooks(self) -> None:
        """Installs baseline ACL and reflection hooks."""
        # Pre-query hook: Automatically sanitize and normalize queries
        def acl_pre_query_hook(ctx: HookContext) -> HookContext:
            if isinstance(ctx.input_data, str):
                normalized = self.ubiquitous_guard.sanitize_query(ctx.input_data, ctx.bounded_context)
                ctx.metadata["original_query"] = ctx.input_data
                ctx.input_data = normalized
            return ctx

        self.hook_manager.register(HookStage.PRE_QUERY, acl_pre_query_hook)

    def ingest_candidate_elements(
        self,
        nodes: List[DomainNode],
        edges: List[DomainEdge],
        source_doc: Optional[str] = None
    ) -> IngestionReport:
        """
        Processes candidate domain elements through hooks and guardrails
        before incorporating them into the persistent graph.
        """
        report = IngestionReport(success=False)

        # 1. Trigger PRE_INGESTION Hook
        pre_ctx = HookContext(
            stage=HookStage.PRE_INGESTION,
            input_data={"nodes": nodes, "edges": edges, "source": source_doc}
        )
        pre_ctx = self.hook_manager.trigger(HookStage.PRE_INGESTION, pre_ctx)
        if pre_ctx.aborted:
            report.aborted_by_hook = True
            report.abort_reason = pre_ctx.abort_reason
            return report

        # 2. Run Guardrail: Ubiquitous Language Linter on all names and descriptions
        all_violations = []
        for n in nodes:
            violations = self.ubiquitous_guard.validate(n.name, n.bounded_context)
            all_violations.extend(violations)
            for prop_val in n.properties.values():
                if isinstance(prop_val, str):
                    all_violations.extend(self.ubiquitous_guard.validate(prop_val, n.bounded_context))

        if all_violations:
            report.lint_violations = all_violations
            # Log warning or block if critical
            # Here we record violations; if severe, we can halt
            has_critical = any("Lenguaje Ubicuo" in v.reason for v in all_violations)
            if has_critical:
                report.guardrail_errors.append(
                    f"Se detectaron {len(all_violations)} violaciones del Lenguaje Ubicuo."
                )

        # 3. Incorporate Nodes and Edges into Knowledge Graph
        try:
            for node in nodes:
                self.graph.add_node(node)
                self._index_node(node)
                report.nodes_added += 1

            for edge in edges:
                self.graph.add_edge(edge)
                report.edges_added += 1

            report.success = True
        except Exception as e:
            report.success = False
            report.guardrail_errors.append(f"Error de consistencia topológica: {str(e)}")

        # 4. Trigger POST_EXTRACTION Hook
        post_ctx = HookContext(
            stage=HookStage.POST_EXTRACTION,
            input_data=report.model_dump()
        )
        self.hook_manager.trigger(HookStage.POST_EXTRACTION, post_ctx)

        return report

    def prepare_agent_context(self, user_query: str, active_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Applies Pre-Execution hooks, sanitizes the user query via the Anti-Corruption Layer (ACL),
        and retrieves relevant graph nodes for the downstream agent.
        """
        ctx = HookContext(
            stage=HookStage.PRE_QUERY,
            bounded_context=active_context,
            input_data=user_query
        )
        ctx = self.hook_manager.trigger(HookStage.PRE_QUERY, ctx)

        sanitized_query = ctx.input_data
        relevant_nodes = []

        # Find matching nodes in graph ranked by specificity
        stop_words = {
            "de", "la", "el", "en", "que", "los", "las", "un", "una", "del", "al", "hace", "¿", "?",
            "rio", "río", "cuenca", "junta", "vigilancia", "asociacion", "asociación", "canal", "para", "por"
        }
        
        # Specific distinct tokens
        query_distinct_tokens = set(
            w.strip("¿?.,;:!\"'")
            for w in sanitized_query.lower().split()
            if len(w) > 2 and w.lower() not in stop_words
        )
        
        # All query words
        all_query_words = set(w.strip("¿?.,;:!\"'") for w in sanitized_query.lower().split() if len(w) > 2)

        scored_nodes = []
        sanitized_lower = sanitized_query.lower()

        # FAL-04: Búsqueda O(1) de candidatos usando índice invertido de tokens
        search_tokens = query_distinct_tokens.union(all_query_words)
        candidate_ids: Set[str] = set()
        for token in search_tokens:
            matched = self._token_index.get(token)
            if matched:
                candidate_ids.update(matched)

        # Si hay candidatos indexados se evalúan únicamente ellos; fallback a todos si la consulta no arrojó tokens
        if candidate_ids:
            nodes_to_evaluate = [self.graph.nodes[nid] for nid in candidate_ids if nid in self.graph.nodes]
        else:
            nodes_to_evaluate = list(self.graph.nodes.values())

        for node in nodes_to_evaluate:
            if active_context and node.bounded_context != active_context:
                continue

            node_name_lower = node.name.lower()
            score = 0.0

            # Exact full name match in query
            if node_name_lower in sanitized_lower:
                score += 100.0
            
            # Distinct specific token match (e.g. 'tinguiririca', 'serrano', 'maipo')
            for token in query_distinct_tokens:
                if token in node_name_lower:
                    score += 50.0

            # General word match
            for word in all_query_words:
                if word in node_name_lower.split():
                    score += 5.0

            if score > 0.0:
                scored_nodes.append((score, node))


        # Sort by score descending
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        relevant_nodes = [node for _, node in scored_nodes]

        return {
            "original_query": ctx.metadata.get("original_query", user_query),
            "sanitized_query": sanitized_query,
            "bounded_context": active_context,
            "relevant_graph_nodes": [n.model_dump() for n in relevant_nodes],
        }
