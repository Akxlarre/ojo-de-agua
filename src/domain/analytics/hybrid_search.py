"""
Motor de Búsqueda Híbrida: Lexical Exact ($O(1)$), Full-Text BM25 (FTS5) y Fuzzy Matching.
Tolerante a faltas de ortografía, abreviaciones y nombres parciales de entidades hídricas.
"""

import unicodedata
from typing import Any, Dict, List, Optional, Set
from difflib import SequenceMatcher

from src.memory.graph import DomainKnowledgeGraph, DomainNode
from src.memory.sqlite_store import SQLiteKnowledgeStore


def normalize_text(text: str) -> str:
    """Elimina tildes, diacríticos y normaliza a minúsculas."""
    nfkd = unicodedata.normalize('NFKD', text.lower().strip())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def fuzzy_similarity(a: str, b: str) -> float:
    """Calcula la similitud de caracteres (0.0 a 1.0) entre dos cadenas normalizadas."""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


class HybridSearchEngine:
    """
    Combina el índice invertido en memoria O(1) con búsqueda FTS5 BM25 y concordancia difusa.
    """

    def __init__(self, graph: DomainKnowledgeGraph, sqlite_store: Optional[SQLiteKnowledgeStore] = None):
        self.graph = graph
        self.sqlite_store = sqlite_store or SQLiteKnowledgeStore()
        self._token_index: Dict[str, Set[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Construye el índice invertido de tokens en memoria."""
        self._token_index = {}
        for node in self.graph.nodes.values():
            words = node.name.lower().split()
            tokens = {w.strip("¿?.,;:!\"'()[]{}") for w in words if len(w) > 2}
            tokens.add(node.id.lower())
            for t in tokens:
                if t not in self._token_index:
                    self._token_index[t] = set()
                self._token_index[t].add(node.id)

    def search(
        self,
        query: str,
        limit: int = 15,
        min_score: float = 0.45,
        context_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la búsqueda híbrida y clasifica los resultados por relevancia compuesta.
        Permite filtrar por Bounded Context o Label de nodo.
        """
        clean_q = query.lower().strip()
        if not clean_q:
            return []

        def matches_context(node: DomainNode) -> bool:
            if not context_filter:
                return True
            cf = context_filter.lower()
            return cf in (node.bounded_context or "").lower() or cf in (node.label or "").lower()

        query_tokens = [w.strip("¿?.,;:!\"'()[]{}") for w in clean_q.split() if len(w) > 2]
        scored_nodes: Dict[str, Dict[str, Any]] = {}

        # 1. Pista O(1): Coincidencias exactas de tokens
        exact_node_ids = set()
        for qt in query_tokens:
            matches = self._token_index.get(qt, set())
            exact_node_ids.update(matches)

        for nid in exact_node_ids:
            node = self.graph.get_node(nid)
            if node and matches_context(node):
                sim = fuzzy_similarity(clean_q, node.name)
                score = 0.70 + (0.30 * sim)
                scored_nodes[nid] = {
                    "node": node,
                    "score": round(score, 3),
                    "match_type": "EXACT_TOKEN"
                }

        # 2. Pista FTS5 BM25 (SQLite)
        try:
            fts_results = self.sqlite_store.search_fts_bm25(clean_q, limit=limit * 2)
            for r in fts_results:
                nid = r["id"]
                node = self.graph.get_node(nid)
                if node and matches_context(node):
                    bm25_normalized = min(0.95, max(0.50, 0.90 / (1.0 + abs(r.get("bm25_rank", 1.0)))))
                    if nid in scored_nodes:
                        scored_nodes[nid]["score"] = min(1.0, scored_nodes[nid]["score"] + 0.15)
                        scored_nodes[nid]["match_type"] = "HYBRID_EXACT_BM25"
                    else:
                        scored_nodes[nid] = {
                            "node": node,
                            "score": round(bm25_normalized, 3),
                            "match_type": "FTS5_BM25"
                        }
        except Exception:
            pass

        # 3. Pista Fuzzy: Si hay pocos resultados (< 5), aplicar similitud difusa sobre tokens
        if len(scored_nodes) < 5 and query_tokens:
            for qt in query_tokens:
                for idx_token, nids in self._token_index.items():
                    sim = fuzzy_similarity(qt, idx_token)
                    if sim >= 0.78:
                        for nid in nids:
                            node = self.graph.get_node(nid)
                            if node and nid not in scored_nodes and matches_context(node):
                                name_sim = fuzzy_similarity(clean_q, node.name)
                                final_score = round(0.50 * sim + 0.50 * name_sim, 3)
                                if final_score >= min_score:
                                    scored_nodes[nid] = {
                                        "node": node,
                                        "score": final_score,
                                        "match_type": "FUZZY_MATCH"
                                    }

        # Ordenar por score decreciente
        ranked = sorted(scored_nodes.values(), key=lambda x: x["score"], reverse=True)
        results = []
        for item in ranked[:limit]:
            node: DomainNode = item["node"]
            results.append({
                "id": node.id,
                "label": node.label,
                "name": node.name,
                "bounded_context": node.bounded_context,
                "relevance_score": item["score"],
                "match_type": item["match_type"],
                "properties": node.properties
            })

        return results
