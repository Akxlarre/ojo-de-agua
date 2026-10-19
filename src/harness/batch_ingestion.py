"""
Automated Batch Ingestion Pipeline for Chilean Water Governance.
Processes the entire corpus of national statutes, decrees, and basin topologies,
incorporating them into the persistent Domain Knowledge Graph.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.harness.dga_catastro_ingestor import DGACatastroIngestor
from src.harness.dga_hook import DGAAutomationHook
from src.harness.extractor import DomainDocumentExtractor
from src.harness.gis_ingestor import ChileGISBasinIngestor
from src.harness.oua_national_ingestor import NationalOUAIngestor
from src.harness.runner import KnowledgeHarness
from src.memory.graph import DomainEdge, DomainNode
from src.domain.topological.cross_relations import CrossDomainRelationBuilder


class NationalBatchIngestionPipeline:
    """
    Orchestrates large-scale continuous ingestion of Chilean water governance documents.
    """

    def __init__(self, output_graph_path: Optional[str] = None):
        self.harness = KnowledgeHarness()
        self.gis_ingestor = ChileGISBasinIngestor(self.harness)
        self.oua_ingestor = NationalOUAIngestor(self.harness)
        self.catastro_ingestor = DGACatastroIngestor(self.harness)
        self.extractor = DomainDocumentExtractor(self.harness)
        self.dga_hook = DGAAutomationHook(self.harness)
        if not output_graph_path:
            output_graph_path = str(Path(__file__).parent.parent.parent / "data" / "knowledge_graph_chile.json")
        self.output_graph_path = output_graph_path

    def run_pipeline(self, documents_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the full pipeline:
        1. Ingests all 90 DGA macro-basins and principal rivers.
        2. Ingests the national registry of 108 OUAs (76 Juntas de Vigilancia y 32 Canalistas).
        3. Recursively parses all legal and statute documents.
        4. Synchronizes DGA drought decrees.
        5. Saves consolidated graph to disk.
        """
        print("\n" + "=" * 80)
        print("   INICIANDO PIPELINE NACIONAL DE INGESTIÓN DE CONOCIMIENTO (DDD)   ")
        print("=" * 80)

        # 1. Ingestión Base GIS de Cuencas y Ríos de Chile
        print("\n[+] Paso 1: Ingestando Catastro Oficial de Cuencas DGA...")
        gis_report = self.gis_ingestor.load_and_ingest()
        print(f"    -> Nodos GIS creados: {gis_report.nodes_added}")
        print(f"    -> Aristas topológicas: {gis_report.edges_added}")

        # 2. Ingestión del Catastro Nacional de OUAs (Juntas y Canalistas)
        print("\n[+] Paso 2: Ingestando Catastro Nacional de Organizaciones de Usuarios (OUAs)...")
        oua_report = self.oua_ingestor.load_and_ingest()
        print(f"    -> Nodos OUA/Canales creados: {oua_report.nodes_added}")
        print(f"    -> Aristas creadas: {oua_report.edges_added}")

        # 2.5 Ingestión del Catastro Oficial Abierto DGA (SHAC, BNA, Decretos Escasez)
        print("\n[+] Paso 2.5: Ingestando Catastro Abierto DGA (SHACs, Estaciones BNA, Decretos Escasez)...")
        catastro_rep = self.catastro_ingestor.load_and_ingest()
        print(f"    -> SHACs (Acuíferos) creados: {catastro_rep.shacs_added}")
        print(f"    -> Estaciones BNA telemétricas: {catastro_rep.bna_stations_added}")
        print(f"    -> Decretos de Escasez: {catastro_rep.decrees_added}")
        print(f"    -> Zonas de Prohibición: {catastro_rep.prohibitions_added}")
        print(f"    -> Glaciares Estratégicos (Criósfera): {catastro_rep.glaciares_added}")
        print(f"    -> Canales de Riego Estratégicos (CNR / CIREN): {catastro_rep.canales_added}")
        print(f"    -> Sanciones Ambientales Estratégicas (SMA / SNIFA): {catastro_rep.sma_sanciones_added}")
        print(f"    -> Derechos de Aprovechamiento (CPA / DAA): {catastro_rep.cpa_derechos_added}")
        print(f"    -> Plantas Sanitarias PTAS (SISS): {catastro_rep.siss_ptas_added}")
        print(f"    -> Humedales Urbanos Protegidos (MMA): {catastro_rep.mma_humedales_added}")
        print(f"    -> Centrales Hidroeléctricas (CNE / SEN): {catastro_rep.cne_hidro_added}")
        print(f"    -> Depósitos de Relaves Mineros (SERNAGEOMIN): {catastro_rep.sernageomin_relaves_added}")
        print(f"    -> Patentes por No Uso de Aguas (TGR / DGA): {catastro_rep.tgr_patentes_added}")
        print(f"    -> Áreas Silvestres Protegidas (CONAF / SNASPE): {catastro_rep.conaf_snaspe_added}")
        print(f"    -> Plantas Desalinizadoras (ACADES / MOP): {catastro_rep.desaladoras_added}")
        print(f"    -> Atributos Hidroclimáticos CAMELS-CL: {catastro_rep.camels_added}")
        print(f"    -> Eventos de Incendios Forestales (CONAF / KITRAL): {catastro_rep.incendios_added}")
        print(f"    -> Demanda y Distritos de Riego (CNR / ODEPA): {catastro_rep.riego_added}")
        print(f"    -> Aristas topológicas/telemetría: {catastro_rep.edges_added}")

        # 3. Ingestión de Documentos y Estatutos
        if not documents_dir:
            documents_dir = str(Path(__file__).parent.parent.parent / "data" / "documents")

        print(f"\n[+] Paso 3: Escaneando repositorio de documentos en '{documents_dir}'...")
        doc_files = []
        for root, _, files in os.walk(documents_dir):
            for file in files:
                if file.endswith((".md", ".txt")):
                    doc_files.append(Path(root) / file)

        print(f"    -> {len(doc_files)} documentos oficiales encontrados.")

        total_extracted_nodes = 0
        total_extracted_edges = 0
        docs_summary = []

        for doc_path in doc_files:
            rel_name = doc_path.name
            print(f"    [*] Procesando '{rel_name}'...")
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split into major sections (##) to extract modular aggregates
            sections = content.split("\n## ")
            for idx, sec in enumerate(sections):
                sec_text = sec if idx == 0 else f"## {sec}"
                sub_ref = f"{rel_name}#sec{idx+1}"
                rep = self.extractor.extract_and_ingest(sec_text, source_reference=sub_ref)
                total_extracted_nodes += rep.nodes_added
                total_extracted_edges += rep.edges_added

            docs_summary.append({
                "documento": rel_name,
                "secciones_procesadas": len(sections)
            })

        # 3. Sincronización de Decretos de Escasez DGA
        print("\n[+] Paso 3: Sincronizando Decretos de Escasez Hídrica con DGA...")
        updated_decrees = self.dga_hook.sync_drought_decrees()
        print(f"    -> {updated_decrees} Juntas de Vigilancia actualizadas con alerta de sequía activa.")

        # 3.5 Construcción de Aristas Causales Inter-Entidad de Segundo Orden
        print("\n[+] Paso 3.5: Generando aristas causales de segundo orden (Relaves -> APR, PTAS -> Humedales, Hidro -> OUA)...")
        cross_builder = CrossDomainRelationBuilder(self.harness.graph)
        cross_report = cross_builder.build_all_cross_relations()
        print(f"    -> Amenazas directas de Relaves a Sistemas APR: {cross_report['amenaza_relave_apr_added']}")
        print(f"    -> Descargas PTAS próximas a Humedales Protegidos: {cross_report['descarga_ptas_humedal_added']}")
        print(f"    -> Convenios / Conflictos Hidroelectricidad vs Riego OUA: {cross_report['compite_hidro_riego_added']}")
        print(f"    -> Cuencas con alivio de presión por Desaladoras: {cross_report['alivio_desalacion_added']}")
        print(f"    -> Amenazas de Incendios sobre Embalses Estratégicos: {cross_report.get('amenaza_incendio_embalse_added', 0)}")
        print(f"    -> Competencia de Demanda Agrícola sobre Sistemas APR: {cross_report.get('compite_agricola_apr_added', 0)}")

        # 4. Estadísticas del Grafo Consolidado
        total_nodes = len(self.harness.graph.nodes)
        total_edges = len(self.harness.graph.edges)

        labels_count: Dict[str, int] = {}
        context_count: Dict[str, int] = {}

        for n in self.harness.graph.nodes.values():
            labels_count[n.label] = labels_count.get(n.label, 0) + 1
            context_count[n.bounded_context] = context_count.get(n.bounded_context, 0) + 1

        # 5. Persistencia del Grafo a Disco
        print(f"\n[+] Paso 4: Persistiendo Grafo de Conocimiento en '{self.output_graph_path}'...")
        graph_dict = self.harness.graph.to_dict()
        with open(self.output_graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_dict, f, ensure_ascii=False, indent=2)
        print("    -> Grafo persistido exitosamente en formato JSON estructurado.")

        summary = {
            "success": True,
            "documentos_procesados": len(doc_files),
            "total_nodos_en_memoria": total_nodes,
            "total_aristas_en_memoria": total_edges,
            "desglose_por_tipo_entidad": labels_count,
            "desglose_por_bounded_context": context_count,
            "output_file": self.output_graph_path
        }

        print("\n" + "=" * 80)
        print(f"   INGESTIÓN COMPLETADA: {total_nodes} NODOS Y {total_edges} RELACIONES CONSOLIDADAS")
        print("=" * 80)
        return summary


if __name__ == "__main__":
    from typing import Optional
    pipeline = NationalBatchIngestionPipeline()
    res = pipeline.run_pipeline()
    print(json.dumps(res, indent=2, ensure_ascii=False))
