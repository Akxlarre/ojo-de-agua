"""
National OUA Registry Ingestor.
Loads all 76 Juntas de Vigilancia and 32 Canalistas associations from
data/registro_nacional_ouas.json into the Knowledge Graph, connecting them to their
respective Cuenca and Río nodes.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from src.harness.runner import IngestionReport, KnowledgeHarness
from src.memory.graph import DomainEdge, DomainNode


class NationalOUAIngestor:
    """
    Ingests official Juntas de Vigilancia and Asociaciones de Canalistas into the graph.
    """

    def __init__(self, harness: KnowledgeHarness, registry_path: Optional[str] = None):
        self.harness = harness
        if not registry_path:
            registry_path = str(Path(__file__).parent.parent.parent / "data" / "registro_nacional_ouas.json")
        self.registry_path = registry_path

    def load_and_ingest(self) -> IngestionReport:
        with open(self.registry_path, "r", encoding="utf-8") as f:
            ouas = json.load(f)

        nodes: List[DomainNode] = []
        edges: List[DomainEdge] = []

        for o in ouas:
            oua_id = o["id"]
            tipo = o["tipo"]
            nombre = o["nombre"]
            cuenca_cod = o["cuenca_codigo"]
            cuenca_node_id = f"cuenca-{cuenca_cod}"

            if "Junta" in tipo or "Comité" in tipo:
                node = DomainNode(
                    id=oua_id,
                    label="JuntaVigilancia",
                    bounded_context="OUA",
                    name=nombre,
                    properties={
                        "cuenca_codigo": cuenca_cod,
                        "rio": o.get("rio", ""),
                        "region": o.get("region", ""),
                        "tipo_organizacion": "Junta de Vigilancia"
                    }
                )
                nodes.append(node)

                # Arista hacia la Cuenca
                edges.append(
                    DomainEdge(
                        source_id=oua_id,
                        target_id=cuenca_node_id,
                        relation_type="ADMINISTRA_CUENCA",
                        bounded_context="OUA"
                    )
                )

                # Si tiene río específico, enlazar al nodo del río
                rio_nombre = o.get("rio")
                if rio_nombre:
                    clean_rio_id = f"rio-{cuenca_cod}-{rio_nombre.lower().replace(' ', '-').replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ñ', 'n')}"
                    # Solo enlazar si el nodo de río existe en el grafo
                    if self.harness.graph.get_node(clean_rio_id):
                        edges.append(
                            DomainEdge(
                                source_id=oua_id,
                                target_id=clean_rio_id,
                                relation_type="JURISDICCION_SOBRE_CAUCE",
                                bounded_context="OUA"
                            )
                        )

            elif "Canalistas" in tipo:
                canal_nombre = o.get("canal_matriz", "")
                canal_id = f"canal-{oua_id}"

                # Nodo Asociación
                ac_node = DomainNode(
                    id=oua_id,
                    label="AsociacionCanalistas",
                    bounded_context="OUA",
                    name=nombre,
                    properties={
                        "cuenca_codigo": cuenca_cod,
                        "canal_matriz": canal_nombre,
                        "region": o.get("region", "")
                    }
                )
                nodes.append(ac_node)

                # Nodo Canal Matriz
                canal_node = DomainNode(
                    id=canal_id,
                    label="Canal",
                    bounded_context="Fisico",
                    name=canal_nombre,
                    properties={"cuenca_codigo": cuenca_cod}
                )
                nodes.append(canal_node)

                # Aristas
                edges.append(
                    DomainEdge(
                        source_id=oua_id,
                        target_id=canal_id,
                        relation_type="ADMINISTRA_CANAL",
                        bounded_context="OUA"
                    )
                )
                edges.append(
                    DomainEdge(
                        source_id=canal_id,
                        target_id=cuenca_node_id,
                        relation_type="UBICADO_EN_CUENCA",
                        bounded_context="Fisico"
                    )
                )

        return self.harness.ingest_candidate_elements(
            nodes=nodes,
            edges=edges,
            source_doc="Registro Público Nacional de Organizaciones de Usuarios DGA Chile"
        )
