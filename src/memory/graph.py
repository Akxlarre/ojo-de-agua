import logging
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DomainNode(BaseModel):
    id: str
    label: str = Field(description="e.g., 'Cuenca', 'Rio', 'JuntaVigilancia', 'Bocatoma', 'Canal', 'Celador'")
    bounded_context: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class DomainEdge(BaseModel):
    source_id: str
    target_id: str
    relation_type: str = Field(description="e.g., 'ADMINISTRA', 'ALIMENTA_A', 'OPERA_EN', 'PERTENECE_A'")
    bounded_context: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class DomainKnowledgeGraph:
    """
    In-memory semantic graph supporting Bounded Context queries,
    topological upstream/downstream traversals, and persistence.
    """

    def __init__(self):
        self.nodes: Dict[str, DomainNode] = {}
        self.edges: List[DomainEdge] = []
        self._adj_out: Dict[str, List[DomainEdge]] = {}
        self._adj_in: Dict[str, List[DomainEdge]] = {}

    def add_node(self, node: DomainNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self._adj_out:
            self._adj_out[node.id] = []
        if node.id not in self._adj_in:
            self._adj_in[node.id] = []

    def add_edge(self, edge: DomainEdge) -> None:
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError(f"Both source '{edge.source_id}' and target '{edge.target_id}' must exist.")
        self.edges.append(edge)
        self._adj_out[edge.source_id].append(edge)
        self._adj_in[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> Optional[DomainNode]:
        return self.nodes.get(node_id)

    def find_nodes_by_label(self, label: str, bounded_context: Optional[str] = None) -> List[DomainNode]:
        results = [n for n in self.nodes.values() if n.label.lower() == label.lower()]
        if bounded_context:
            results = [n for n in results if n.bounded_context == bounded_context]
        return results

    def get_connected_nodes(self, node_id: str, direction: str = "out") -> List[DomainNode]:
        """Traverse one hop out or in."""
        neighbors = []
        if direction in ("out", "both"):
            for e in self._adj_out.get(node_id, []):
                if e.target_id in self.nodes:
                    neighbors.append(self.nodes[e.target_id])
        if direction in ("in", "both"):
            for e in self._adj_in.get(node_id, []):
                if e.source_id in self.nodes:
                    neighbors.append(self.nodes[e.source_id])
        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "edges": [e.model_dump() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], ignore_missing_nodes: bool = True) -> "DomainKnowledgeGraph":
        """
        Reconstruye el grafo desde un diccionario.
        FAL-07: Tolera aristas con extremos no existentes sin abortar la carga.
        """
        graph = cls()
        for nd in data.get("nodes", []):
            graph.add_node(DomainNode(**nd))
        for ed in data.get("edges", []):
            source_id = ed.get("source_id")
            target_id = ed.get("target_id")
            if source_id in graph.nodes and target_id in graph.nodes:
                graph.add_edge(DomainEdge(**ed))
            elif not ignore_missing_nodes:
                graph.add_edge(DomainEdge(**ed))
            else:
                logger.debug("Omitiendo arista huérfana: %s -> %s", source_id, target_id)
        return graph

