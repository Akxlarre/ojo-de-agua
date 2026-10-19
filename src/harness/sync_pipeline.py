"""
Automated Synchronization Pipeline for Chile Water Intelligence Platform.
Designed to be executed periodically (e.g., via GitHub Actions CRON or local scheduler).
Steps:
1. Re-evaluates expiration of Decretos de Escasez Hídrica (Art. 314) vs current date.
2. Executes full Knowledge Graph consolidation via NationalBatchIngestionPipeline.
3. Recalculates cross-domain causal edges (Mining tailings vs APR, PTAS vs Wetlands, Hydro vs OUA).
4. Re-renders the interactive GIS Dashboard (mapa_cuencas_chile.html).
5. Generates sync_report.json for audit and CI/CD observability.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.harness.batch_ingestion import NationalBatchIngestionPipeline
from src.domain.physical.map_generator import ChileWaterMapGenerator


class WaterIntelligenceSyncRunner:
    """
    Orchestrates continuous synchronization and produces execution audit artifacts.
    """

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or (Path(__file__).parent.parent.parent / "data")

    def sync_decrees_validity(self) -> Dict[str, int]:
        """
        Updates 'es_vigente' on Decretos de Escasez based on real expiration date.
        """
        dec_path = self.data_dir / "decretos_escasez_chile.json"
        if not dec_path.exists():
            return {"vigentes": 0, "caducados": 0}

        with open(dec_path, "r", encoding="utf-8") as f:
            decretos = json.load(f)

        hoy = datetime.now(timezone.utc).date()
        vigentes = 0
        caducados = 0

        for d in decretos:
            fecha_cad = d.get("fecha_caducidad")
            if fecha_cad:
                try:
                    f_dt = datetime.fromisoformat(fecha_cad).date()
                    es_vig = f_dt >= hoy
                    d["es_vigente"] = es_vig
                    if es_vig:
                        vigentes += 1
                    else:
                        caducados += 1
                except Exception:
                    pass

        with open(dec_path, "w", encoding="utf-8") as f:
            json.dump(decretos, f, ensure_ascii=False, indent=2)

        return {"vigentes": vigentes, "caducados": caducados}

    def run_full_sync(self) -> Dict[str, Any]:
        """
        Executes the end-to-end continuous update workflow.
        """
        inicio = datetime.now(timezone.utc)
        print("=" * 80)
        print(f"[*] INICIANDO SINCRONIZACIÓN AUTOMÁTICA DEL GEMELO DIGITAL: {inicio.isoformat()}")
        print("=" * 80)

        # 1. Actualizar vigencia de decretos
        print("[+] Paso 1: Verificando vigencia jurídica de Decretos de Escasez (Art. 314)...")
        dec_stats = self.sync_decrees_validity()
        print(f"    -> Decretos vigentes: {dec_stats['vigentes']} | Caducados: {dec_stats['caducados']}")

        # 2. Pipeline de Ingestión y Grafo
        print("\n[+] Paso 2: Reejecutando consolidación del Knowledge Graph de 18 Bounded Contexts...")
        pipeline = NationalBatchIngestionPipeline(
            output_graph_path=str(self.data_dir / "knowledge_graph_chile.json")
        )
        batch_summary = pipeline.run_pipeline()

        # 2.5 Sincronizar Base Relacional y FTS5 Embebida (SQLite)
        print("\n[+] Paso 2.5: Sincronizando motor analítico relacional y Full-Text (FTS5 / BM25)...")
        from src.memory.sqlite_store import SQLiteKnowledgeStore
        sqlite_store = SQLiteKnowledgeStore(db_path=str(self.data_dir / "knowledge_graph_chile.db"))
        sqlite_stats = sqlite_store.sync_from_graph(pipeline.harness.graph)
        print(f"    -> Nodos indexados en SQLite/FTS5: {sqlite_stats['nodes_indexed']} | Aristas: {sqlite_stats['edges_indexed']}")

        # 3. Regenerar Mapa GIS
        print("\n[+] Paso 3: Regenerando dashboard cartográfico Leaflet...")
        map_gen = ChileWaterMapGenerator(data_dir=str(self.data_dir))
        map_path = map_gen.generate_html_map(str(self.data_dir / "mapa_cuencas_chile.html"))
        map_size = os.path.getsize(map_path) if os.path.exists(map_path) else 0
        print(f"    -> Mapa GIS generado: {map_path} ({round(map_size / (1024 * 1024), 2)} MB)")

        fin = datetime.now(timezone.utc)
        duracion_seg = (fin - inicio).total_seconds()

        reporte = {
            "estado": "EXITOSO",
            "timestamp_inicio": inicio.isoformat(),
            "timestamp_fin": fin.isoformat(),
            "duracion_segundos": round(duracion_seg, 2),
            "decretos_escasez": dec_stats,
            "grafo_nodos": batch_summary.get("total_nodos_en_memoria", 0),
            "grafo_aristas": batch_summary.get("total_aristas_en_memoria", 0),
            "mapa_html_bytes": map_size,
            "entidades_resumen": batch_summary.get("desglose_por_tipo_entidad", {})
        }

        report_file = self.data_dir / "sync_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 80)
        print(f"[OK] SINCRONIZACIÓN FINALIZADA EN {round(duracion_seg, 2)}s | Nodos: {reporte['grafo_nodos']} | Aristas: {reporte['grafo_aristas']}")
        print("=" * 80)
        return reporte


if __name__ == "__main__":
    runner = WaterIntelligenceSyncRunner()
    res = runner.run_full_sync()
    print(json.dumps(res, indent=2, ensure_ascii=False))
