"""
Unit and integration tests for Continuous Update Architecture:
- Automated Synchronization Pipeline (GitHub Actions runner)
- Real-time MEE Telemetry Ingestion & Guardrails
- Historical Timeseries Persistence & Drawdown (Abatimiento) Analytics
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from src.api.server import app
from src.domain.operation.timeseries_store import LecturaTelemetrica, TimeseriesStore
from src.harness.sync_pipeline import WaterIntelligenceSyncRunner

client = TestClient(app)
DATA_DIR = Path(__file__).parent.parent / "data"


def test_timeseries_store_ingestion_and_statistics(tmp_path):
    """Verify that TimeseriesStore correctly persists and computes statistics on telemetry."""
    store = TimeseriesStore(storage_dir=tmp_path)
    sensor_id = "BNA_05701001_FLU"

    ahora = datetime.now(timezone.utc)
    lecturas = [
        LecturaTelemetrica(
            sensor_id=sensor_id,
            cuenca_codigo="057",
            tipo_medicion="CAUDAL_SUPERFICIAL_LPS",
            valor=float(val),
            fecha_hora=ahora + timedelta(hours=i)
        )
        for i, val in enumerate([100.0, 150.0, 200.0, 250.0, 300.0])
    ]

    count = store.ingestar_lecturas(lecturas)
    assert count == 5

    # Hidrograma
    puntos = store.obtener_hidrograma(sensor_id)
    assert len(puntos) == 5
    assert puntos[0]["valor"] == 100.0
    assert puntos[-1]["valor"] == 300.0

    # Estadísticas
    stats = store.calcular_estadisticas_sensor(sensor_id)
    assert stats["total_lecturas"] == 5
    assert stats["valor_medio"] == 200.0
    assert stats["valor_minimo"] == 100.0
    assert stats["valor_maximo"] == 300.0


def test_groundwater_drawdown_overexploitation_alert(tmp_path):
    """Verify that severe water table drop triggers Art. 63 overexploitation alert."""
    store = TimeseriesStore(storage_dir=tmp_path)
    pozo_id = "POZO_SHAC_MAIPO_MEDIO_01"

    t0 = datetime.now(timezone.utc) - timedelta(days=180)
    lecturas = [
        LecturaTelemetrica(
            sensor_id=pozo_id,
            cuenca_codigo="057",
            tipo_medicion="NIVEL_FREATICO_POZO_M",
            valor=12.0,
            fecha_hora=t0
        ),
        LecturaTelemetrica(
            sensor_id=pozo_id,
            cuenca_codigo="057",
            tipo_medicion="NIVEL_FREATICO_POZO_M",
            valor=15.5,  # Drop of 3.5 meters in ~6 months
            fecha_hora=datetime.now(timezone.utc)
        )
    ]

    store.ingestar_lecturas(lecturas)
    tendencia = store.analizar_abatimiento_pozo(pozo_id)

    assert tendencia.total_lecturas == 2
    assert tendencia.delta_total_m == 3.5
    assert tendencia.tasa_abatimiento_m_mes > 0.04
    assert tendencia.alerta_sobreexplotacion is True
    assert "sobreexplotación" in tendencia.diagnostico_shac.lower()
    assert "Art. 63" in tendencia.diagnostico_shac


def test_api_telemetry_batch_ingestion_and_audit():
    """Test POST /api/telemetria/lote with automatic extraction guardrail violation detection."""
    payload = {
        "lecturas": [
            {
                "sensor_id": "BOCATOMA_SAN_CARLOS_01",
                "cuenca_codigo": "057",
                "tipo_medicion": "CAUDAL_SUPERFICIAL_LPS",
                "valor": 120.0,  # Flow without authorized order -> illegal extraction
                "unidad": "L/s"
            },
            {
                "sensor_id": "POZO_SSR_PAINE_02",
                "cuenca_codigo": "057",
                "tipo_medicion": "NIVEL_FREATICO_POZO_M",
                "valor": 24.3,
                "unidad": "m"
            }
        ],
        "ordenes_activas": []
    }

    resp = client.post("/api/telemetria/lote", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["total_lecturas_ingestadas"] == 2
    assert data["total_alertas_infraccion"] >= 1
    assert data["alertas_infraccion"][0]["bocatoma_id"] == "BOCATOMA_SAN_CARLOS_01"


def test_api_telemetry_hidrograma_and_stats_endpoints():
    """Test GET endpoints for station hydrograph, stats and drawdown."""
    # Insert test point
    sensor = "TEST_BNA_SENSOR_001"
    client.post("/api/telemetria/lote", json={
        "lecturas": [
            {"sensor_id": sensor, "valor": 55.0, "tipo_medicion": "CAUDAL_SUPERFICIAL_LPS"},
            {"sensor_id": sensor, "valor": 75.0, "tipo_medicion": "CAUDAL_SUPERFICIAL_LPS"}
        ]
    })

    resp_hidro = client.get(f"/api/telemetria/estacion/{sensor}/hidrograma")
    assert resp_hidro.status_code == 200
    assert resp_hidro.json()["total_puntos"] >= 2

    resp_stats = client.get(f"/api/telemetria/estacion/{sensor}/estadisticas")
    assert resp_stats.status_code == 200
    assert resp_stats.json()["valor_maximo"] >= 75.0


def test_sync_pipeline_execution():
    """Verify that the full sync runner executes cleanly and produces sync_report.json."""
    runner = WaterIntelligenceSyncRunner(data_dir=DATA_DIR)
    report = runner.run_full_sync()

    assert report["estado"] == "EXITOSO"
    assert report["grafo_nodos"] >= 40000
    assert report["grafo_aristas"] >= 30000
    assert report["mapa_html_bytes"] > 1000000

    report_path = DATA_DIR / "sync_report.json"
    assert report_path.exists()

    resp_sync = client.get("/api/sync/ultimo-reporte")
    assert resp_sync.status_code == 200
    sync_data = resp_sync.json()
    assert sync_data["estado"] == "EXITOSO"
    assert sync_data["grafo_nodos"] >= 40000
