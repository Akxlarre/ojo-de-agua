"""
Motor Relacional y de Búsqueda Full-Text (FTS5 / BM25) Embebido para el Knowledge Graph.
Permite consultas analíticas SQL instantáneas, búsquedas por relevancia textual BM25
y filtrado espacial por coordenadas WGS84 sobre los 42.000+ nodos del dominio hídrico.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.memory.graph import DomainKnowledgeGraph, DomainNode, DomainEdge


class SQLiteKnowledgeStore:
    """
    Almacén relacional embebido y motor FTS5 para el Domain Knowledge Graph.
    """

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "knowledge_graph_chile.db")
        self.db_path = db_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path == ":memory:" and self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def _init_db(self) -> None:
        """Crea tablas relacionales e índice virtual FTS5 si no existen."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    bounded_context TEXT NOT NULL,
                    name TEXT NOT NULL,
                    cuenca_codigo TEXT,
                    lat REAL,
                    lon REAL,
                    properties_json TEXT
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_label ON domain_nodes(label);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_cuenca ON domain_nodes(cuenca_codigo);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_spatial ON domain_nodes(lat, lon);
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    bounded_context TEXT NOT NULL,
                    properties_json TEXT,
                    FOREIGN KEY (source_id) REFERENCES domain_nodes(id),
                    FOREIGN KEY (target_id) REFERENCES domain_nodes(id)
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_src ON domain_edges(source_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_tgt ON domain_edges(target_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_rel ON domain_edges(relation_type);
            """)

            # Tabla virtual FTS5 para búsqueda semántica con ranking BM25
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    node_id UNINDEXED,
                    label,
                    name,
                    properties_text,
                    tokenize='unicode61 remove_diacritics 1'
                );
            """)

    def sync_from_graph(self, graph: DomainKnowledgeGraph) -> Dict[str, int]:
        """
        Sincroniza masivamente el grafo de conocimiento en memoria hacia la base SQLite.
        Utiliza transacciones masivas para completar la sincronización en menos de un segundo.
        """
        nodes_data = []
        fts_data = []

        for n in graph.nodes.values():
            props = n.properties or {}
            c_cod = props.get("cuenca_codigo") or props.get("codigo_cuenca") or props.get("cuenca")
            coords = props.get("coordenadas")
            lat, lon = None, None
            if isinstance(coords, list) and len(coords) == 2:
                lat, lon = coords[0], coords[1]
            elif isinstance(coords, dict):
                lat = coords.get("latitud") or coords.get("lat")
                lon = coords.get("longitud") or coords.get("lon")

            props_json = json.dumps(props, ensure_ascii=False)
            props_text = " ".join(f"{k}:{v}" for k, v in props.items() if isinstance(v, (str, int, float)))

            nodes_data.append((
                n.id,
                n.label,
                n.bounded_context,
                n.name,
                str(c_cod) if c_cod else None,
                lat,
                lon,
                props_json
            ))
            fts_data.append((
                n.id,
                n.label,
                n.name,
                props_text
            ))

        edges_data = [
            (e.source_id, e.target_id, e.relation_type, e.bounded_context, json.dumps(e.properties or {}, ensure_ascii=False))
            for e in graph.edges
        ]

        with self._get_connection() as conn:
            conn.execute("DELETE FROM domain_edges;")
            conn.execute("DELETE FROM domain_nodes;")
            conn.execute("DELETE FROM nodes_fts;")

            conn.executemany("""
                INSERT INTO domain_nodes (id, label, bounded_context, name, cuenca_codigo, lat, lon, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, nodes_data)

            conn.executemany("""
                INSERT INTO domain_edges (source_id, target_id, relation_type, bounded_context, properties_json)
                VALUES (?, ?, ?, ?, ?);
            """, edges_data)

            conn.executemany("""
                INSERT INTO nodes_fts (node_id, label, name, properties_text)
                VALUES (?, ?, ?, ?);
            """, fts_data)

        return {
            "nodes_indexed": len(nodes_data),
            "edges_indexed": len(edges_data),
            "fts_indexed": len(fts_data)
        }

    def search_fts_bm25(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Búsqueda full-text sobre nombres, etiquetas y propiedades ordenadas por ranking BM25.
        """
        clean_q = query.replace('"', '').replace("'", "").strip()
        if not clean_q:
            return []

        # Formatear consulta para FTS5 con comodines de prefijo
        tokens = [f"{t}*" for t in clean_q.split() if len(t) > 1]
        fts_query = " ".join(tokens)
        if not fts_query:
            return []

        sql = """
            SELECT n.id, n.label, n.bounded_context, n.name, n.cuenca_codigo, n.lat, n.lon, n.properties_json,
                   bm25(nodes_fts) AS rank
            FROM nodes_fts
            JOIN domain_nodes n ON n.id = nodes_fts.node_id
            WHERE nodes_fts MATCH ?
            ORDER BY rank
            LIMIT ?;
        """
        with self._get_connection() as conn:
            try:
                rows = conn.execute(sql, (fts_query, limit)).fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "label": r["label"],
                        "bounded_context": r["bounded_context"],
                        "name": r["name"],
                        "cuenca_codigo": r["cuenca_codigo"],
                        "coordenadas": [r["lat"], r["lon"]] if r["lat"] is not None else None,
                        "bm25_rank": round(r["rank"], 4),
                        "properties": json.loads(r["properties_json"]) if r["properties_json"] else {}
                    })
                return results
            except sqlite3.OperationalError:
                return []

    def spatial_bbox_query(
        self,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        label: Optional[str] = None,
        context: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Filtrado espacial por Bounding Box WGS84 con índice B-Tree sobre coordenadas.
        Soporta nombres lat_min/lat_max o min_lat/max_lat.
        """
        lat_min = lat_min if lat_min is not None else kwargs.get("min_lat")
        lat_max = lat_max if lat_max is not None else kwargs.get("max_lat")
        lon_min = lon_min if lon_min is not None else kwargs.get("min_lon")
        lon_max = lon_max if lon_max is not None else kwargs.get("max_lon")

        if None in (lat_min, lat_max, lon_min, lon_max):
            raise ValueError("Bounding box requiere lat_min/min_lat, lat_max/max_lat, lon_min/min_lon, lon_max/max_lon")

        sql = """
            SELECT id, label, bounded_context, name, cuenca_codigo, lat, lon, properties_json
            FROM domain_nodes
            WHERE lat >= ? AND lat <= ? AND lon >= ? AND lon <= ?
        """
        params = [lat_min, lat_max, lon_min, lon_max]
        if label:
            sql += " AND label = ?"
            params.append(label)
        if context:
            sql += " AND bounded_context = ?"
            params.append(context)
        sql += " LIMIT ?;"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                {
                    "id": r["id"],
                    "label": r["label"],
                    "bounded_context": r["bounded_context"],
                    "name": r["name"],
                    "cuenca_codigo": r["cuenca_codigo"],
                    "lat": r["lat"],
                    "lon": r["lon"],
                    "properties": json.loads(r["properties_json"]) if r["properties_json"] else {}
                }
                for r in rows
            ]

    def count_by_label(self) -> Dict[str, int]:
        """Conteo agregado por etiqueta de entidad."""
        sql = "SELECT label, COUNT(*) as count FROM domain_nodes GROUP BY label ORDER BY count DESC;"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return {r["label"]: r["count"] for r in rows}
