"""
Unit test for the National Batch Ingestion Pipeline.
"""

from pathlib import Path
from src.harness.batch_ingestion import NationalBatchIngestionPipeline


def test_national_batch_ingestion_pipeline():
    pipeline = NationalBatchIngestionPipeline()
    result = pipeline.run_pipeline()

    assert result["success"] is True
    assert result["total_nodos_en_memoria"] >= 150
    assert result["total_aristas_en_memoria"] >= 100
    assert result["desglose_por_tipo_entidad"]["Cuenca"] >= 20
    assert result["desglose_por_tipo_entidad"]["JuntaVigilancia"] >= 40
    assert Path(result["output_file"]).exists()
