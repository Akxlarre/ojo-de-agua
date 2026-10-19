"""
GIS Ingestor for Chile's National Hydrographic Network.
Loads official DGA basins, generates topological subgraphs (Cuencas, Ríos, JVs),
and ingests them through the KnowledgeHarness.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.physical.gis import CuencaHidrograficaDGA, GeoBoundingBox
from src.harness.runner import IngestionReport, KnowledgeHarness
from src.memory.graph import DomainEdge, DomainNode


class ChileGISBasinIngestor:
    """
    Ingests official DGA basins into the agentic knowledge graph.
    """

    def __init__(self, harness: KnowledgeHarness, catalog_path: Optional[str] = None):
        self.harness = harness
        if not catalog_path:
            catalog_path = str(Path(__file__).parent.parent.parent / "data" / "cuencas_dga_chile.json")
        self.catalog_path = catalog_path

    def load_and_ingest(self) -> IngestionReport:
        """
        Reads the DGA catalog, instantiates domain entities, builds nodes and edges,
        and executes pipeline ingestion.
        """
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            raw_basins = json.load(f)

        all_nodes: List[DomainNode] = []
        all_edges: List[DomainEdge] = []

        for b in raw_basins:
            # 1. Validate via Pydantic Domain Model
            bbox_obj = GeoBoundingBox(**b["bbox"])
            cuenca_model = CuencaHidrograficaDGA(
                codigo_dga=b["codigo_dga"],
                nombre=b["nombre"],
                region=b["region"],
                zona_hidrografica=b["zona_hidrografica"],
                superficie_km2=b["superficie_km2"],
                rios_principales=b.get("rios_principales", []),
                juntas_vigilancia=b.get("juntas_vigilancia", []),
                bbox=bbox_obj
            )

            # Invariant check
            violations = cuenca_model.check_invariants()
            if violations:
                print(f"[!] Warning on basin {b['nombre']}: {violations}")

            # 2. Build Cuenca DomainNode
            cuenca_node_id = f"cuenca-{cuenca_model.codigo_dga}"
            cuenca_node = DomainNode(
                id=cuenca_node_id,
                label="Cuenca",
                bounded_context="Fisico",
                name=cuenca_model.nombre,
                properties={
                    "codigo_dga": cuenca_model.codigo_dga,
                    "region": cuenca_model.region,
                    "zona_hidrografica": cuenca_model.zona_hidrografica,
                    "superficie_km2": cuenca_model.superficie_km2,
                    "bbox": cuenca_model.bbox.model_dump()
                }
            )
            all_nodes.append(cuenca_node)

            # 3. Build Rio DomainNodes & Edges
            for rio in cuenca_model.rios_principales:
                clean_rio_id = f"rio-{cuenca_model.codigo_dga}-{rio.lower().replace(' ', '-').replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ñ', 'n')}"
                rio_node = DomainNode(
                    id=clean_rio_id,
                    label="Rio",
                    bounded_context="Fisico",
                    name=rio,
                    properties={"cuenca_codigo": cuenca_model.codigo_dga}
                )
                all_nodes.append(rio_node)
                all_edges.append(
                    DomainEdge(
                        source_id=clean_rio_id,
                        target_id=cuenca_node_id,
                        relation_type="FLUYE_EN_CUENCA",
                        bounded_context="Fisico"
                    )
                )

            # 4. Build JuntaVigilancia DomainNodes & Edges
            for jv_name in cuenca_model.juntas_vigilancia:
                clean_jv_id = f"jv-{cuenca_model.codigo_dga}-{abs(hash(jv_name)) % 100000}"
                jv_node = DomainNode(
                    id=clean_jv_id,
                    label="JuntaVigilancia",
                    bounded_context="OUA",
                    name=jv_name,
                    properties={"cuenca_codigo": cuenca_model.codigo_dga}
                )
                all_nodes.append(jv_node)
                all_edges.append(
                    DomainEdge(
                        source_id=clean_jv_id,
                        target_id=cuenca_node_id,
                        relation_type="ADMINISTRA_CAUCE_EN",
                        bounded_context="OUA"
                    )
                )

        # Ingest through the harness
        return self.harness.ingest_candidate_elements(
            nodes=all_nodes,
            edges=all_edges,
            source_doc="Catastro Oficial de Cuencas Hidrográficas DGA Chile"
        )
