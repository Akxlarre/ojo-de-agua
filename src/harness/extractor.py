"""
Automated Domain Extractor for Chilean Water Governance.
Extracts structured DDD entities, invariants, and topological relationships
from unstructured texts (Estatutos de OUA, Resoluciones DGA, Actas de Reparto).
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.base import Invariant
from src.harness.runner import IngestionReport, KnowledgeHarness
from src.memory.graph import DomainEdge, DomainNode


class CandidateDomainExtraction(BaseModel):
    """
    Structured payload produced by the extractor agent before passing through guardrails.
    """
    source_reference: str = Field(description="Name or ID of the originating document")
    bounded_context: str
    nodes: List[DomainNode] = Field(default_factory=list)
    edges: List[DomainEdge] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)


class DomainDocumentExtractor:
    """
    Extractor Agent that parses unstructured domain texts into candidate DDD structures.
    Uses regex and rule heuristics (or LLM via prompt template) to structure raw facts.
    """

    def __init__(self, harness: KnowledgeHarness):
        self.harness = harness

    def extract_from_text(self, text: str, source_reference: str = "Documento") -> CandidateDomainExtraction:
        """
        Parses text and extracts entities like Juntas de Vigilancia, Canales, Bocatomas,
        Celadores, and business rules/invariants.
        """
        candidate = CandidateDomainExtraction(
            source_reference=source_reference,
            bounded_context="OUA"
        )

        # 1. Detectar Junta de Vigilancia (ej: 'Junta de Vigilancia del Río X')
        jv_match = re.search(r"(Junta de Vigilancia\s+[^\.,;\n]+)", text, re.IGNORECASE)
        jv_id = None
        if jv_match:
            jv_name = jv_match.group(1).strip()
            jv_id = f"jv-{abs(hash(jv_name)) % 100000}"
            candidate.nodes.append(
                DomainNode(
                    id=jv_id,
                    label="JuntaVigilancia",
                    bounded_context="OUA",
                    name=jv_name,
                    properties={"fuente_doc": source_reference}
                )
            )

        # 2. Detectar Asociación de Canalistas / Canal
        canal_match = re.search(r"Canal\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]+?)(?:,|\.|\scon|\sde)", text)
        canal_id = None
        if canal_match:
            canal_name = f"Canal {canal_match.group(1).strip()}"
            canal_id = f"canal-{abs(hash(canal_name)) % 100000}"
            candidate.nodes.append(
                DomainNode(
                    id=canal_id,
                    label="Canal",
                    bounded_context="Fisico",
                    name=canal_name,
                    properties={"fuente_doc": source_reference}
                )
            )

        # 3. Detectar Bocatoma
        bocatoma_match = re.search(r"Bocatoma\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]+?)(?:,|\.|\scon|\sen)", text)
        bocatoma_id = None
        if bocatoma_match:
            bocatoma_name = f"Bocatoma {bocatoma_match.group(1).strip()}"
            bocatoma_id = f"bocatoma-{abs(hash(bocatoma_name)) % 100000}"
            candidate.nodes.append(
                DomainNode(
                    id=bocatoma_id,
                    label="Bocatoma",
                    bounded_context="Fisico",
                    name=bocatoma_name,
                    properties={"fuente_doc": source_reference}
                )
            )

        # 4. Detectar Celador
        celador_match = re.search(
            r"(?:celador|repartidor)\s+(?:don\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)",
            text,
            re.IGNORECASE
        )
        celador_id = None
        if celador_match:
            celador_name = celador_match.group(1).strip()
            celador_id = f"celador-{abs(hash(celador_name)) % 100000}"
            candidate.nodes.append(
                DomainNode(
                    id=celador_id,
                    label="Celador",
                    bounded_context="Operacion",
                    name=celador_name,
                    properties={"fuente_doc": source_reference}
                )
            )

        # 5. Generar aristas de relación topológica
        if jv_id and bocatoma_id:
            candidate.edges.append(
                DomainEdge(
                    source_id=jv_id,
                    target_id=bocatoma_id,
                    relation_type="REGULA_EXTRACCION_EN",
                    bounded_context="OUA"
                )
            )
        if bocatoma_id and canal_id:
            candidate.edges.append(
                DomainEdge(
                    source_id=bocatoma_id,
                    target_id=canal_id,
                    relation_type="ALIMENTA_A",
                    bounded_context="Fisico"
                )
            )
        if celador_id and bocatoma_id:
            candidate.edges.append(
                DomainEdge(
                    source_id=celador_id,
                    target_id=bocatoma_id,
                    relation_type="OPERA_COMPUERTA",
                    bounded_context="Operacion"
                )
            )

        # 6. Detectar Invariantes de Negocio / Prorrateo
        if "prorrateo" in text.lower() or "escasez" in text.lower() or "turno" in text.lower():
            candidate.invariants.append(
                Invariant(
                    code="INV-EXTRACTED-001",
                    name="Prorrateo Obligatorio por Escasez",
                    description="Distribución proporcional obligatoria del caudal disponible entre canales",
                    bounded_context="Operacion",
                    source_legal_ref=source_reference
                )
            )

        return candidate

    def extract_and_ingest(self, text: str, source_reference: str = "Documento") -> IngestionReport:
        """
        End-to-End Extraction: Parses the text and passes candidate elements
        through the KnowledgeHarness hooks and guardrails.
        """
        candidate = self.extract_from_text(text, source_reference)
        return self.harness.ingest_candidate_elements(
            nodes=candidate.nodes,
            edges=candidate.edges,
            source_doc=source_reference
        )
