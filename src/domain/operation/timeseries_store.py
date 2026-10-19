"""
Bounded Context: Telemetría, Series de Tiempo y Tendencias Hidrológicas Históricas.
Permite la persistencia, consulta y analítica de tendencias (hidrogramas de caudales,
abatimiento de niveles freáticos en pozos y reservas de embalses).
"""

import json
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LecturaTelemetrica(BaseModel):
    sensor_id: str = Field(description="Identificador único del sensor, estación BNA o bocatoma MEE")
    cuenca_codigo: Optional[str] = Field(None, description="Código DGA de la cuenca receptora (ej. 057)")
    tipo_medicion: str = Field(
        default="CAUDAL_SUPERFICIAL_LPS",
        description="'CAUDAL_SUPERFICIAL_LPS', 'NIVEL_FREATICO_POZO_M', 'NIVEL_EMBALSE_MSNM', 'PRECIPITACION_MM'"
    )
    valor: float = Field(ge=-2000.0, description="Magnitud física registrada")
    unidad: str = Field(default="L/s", description="Unidad de medida (L/s, m, msnm, mm)")
    fecha_hora: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    calidad: str = Field(default="VALIDA", description="'VALIDA', 'ESTIMADA', 'DUDOSA', 'ANOMALA'")
    origen: str = Field(default="MEE_DGA", description="'MEE_DGA', 'SENSOR_OUA', 'TELEMETRIA_BNA'")


class TendenciaAbatimiento(BaseModel):
    sensor_id: str
    cuenca_codigo: Optional[str]
    total_lecturas: int
    primer_registro: Optional[str]
    ultimo_registro: Optional[str]
    nivel_inicial_m: Optional[float]
    nivel_final_m: Optional[float]
    delta_total_m: Optional[float]
    tasa_abatimiento_m_mes: Optional[float]
    alerta_sobreexplotacion: bool
    diagnostico_shac: str


class TimeseriesStore:
    """
    Motor de persistencia y análisis de series temporales de telemetría hídrica.
    Almacena registros estructurados en formato particionado JSON Lines (JSONL).
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        if not storage_dir:
            storage_dir = Path(__file__).parent.parent.parent.parent / "data" / "historical"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_sensor_path(self, sensor_id: str) -> Path:
        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in sensor_id)
        return self.storage_dir / f"sensor_{safe_id}.jsonl"

    def ingestar_lecturas(self, lecturas: List[LecturaTelemetrica]) -> int:
        """
        Inserta un lote de mediciones telemétricas en los archivos correspondientes (thread-safe).
        """
        ingestadas = 0
        por_sensor: Dict[str, List[LecturaTelemetrica]] = {}
        for l in lecturas:
            por_sensor.setdefault(l.sensor_id, []).append(l)

        with self._lock:
            for sensor_id, items in por_sensor.items():
                path = self._get_sensor_path(sensor_id)
                with open(path, "a", encoding="utf-8") as f:
                    for item in items:
                        linea = item.model_dump(mode="json")
                        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
                        ingestadas += 1

        return ingestadas


    def obtener_hidrograma(
        self,
        sensor_id: str,
        limite_puntos: int = 500,
        horas_atras: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna la serie temporal ordenada para graficar el hidrograma de caudales o niveles.
        """
        path = self._get_sensor_path(sensor_id)
        if not path.exists():
            return []

        registros = []
        corte_tiempo = None
        if horas_atras:
            corte_tiempo = datetime.now(timezone.utc) - timedelta(hours=horas_atras)

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if corte_tiempo:
                        dt = datetime.fromisoformat(obj["fecha_hora"])
                        if dt < corte_tiempo:
                            continue
                    registros.append(obj)
                except Exception:
                    continue

        registros.sort(key=lambda x: x["fecha_hora"])
        return registros[-limite_puntos:]

    def calcular_estadisticas_sensor(self, sensor_id: str) -> Dict[str, Any]:
        """
        Calcula estadísticos clave (caudal medio, máx, mín, percentiles).
        """
        lecturas = self.obtener_hidrograma(sensor_id, limite_puntos=5000)
        if not lecturas:
            return {"error": "Sin datos telemétricos históricos para este sensor."}

        valores = [float(r["valor"]) for r in lecturas]
        valores.sort()
        n = len(valores)

        q_medio = sum(valores) / n
        q_min = valores[0]
        q_max = valores[-1]
        p5 = valores[int(n * 0.05)] if n >= 20 else q_min
        p95 = valores[int(n * 0.95)] if n >= 20 else q_max

        primera = lecturas[0]["fecha_hora"]
        ultima = lecturas[-1]["fecha_hora"]

        return {
            "sensor_id": sensor_id,
            "total_lecturas": n,
            "primera_lectura": primera,
            "ultima_lectura": ultima,
            "tipo_medicion": lecturas[-1]["tipo_medicion"],
            "unidad": lecturas[-1]["unidad"],
            "ultimo_valor": lecturas[-1]["valor"],
            "valor_medio": round(q_medio, 2),
            "valor_minimo": round(q_min, 2),
            "valor_maximo": round(q_max, 2),
            "percentil_5_estiaje": round(p5, 2),
            "percentil_95_crecida": round(p95, 2)
        }

    def analizar_abatimiento_pozo(self, sensor_id: str) -> TendenciaAbatimiento:
        """
        Evalúa si un pozo hidrogeológico (SHAC) presenta tendencia descendente crítica.
        Un descenso sostenido > 0.5 m/año activa alerta de sobreexplotación (Art. 63 Código de Aguas).
        """
        lecturas = self.obtener_hidrograma(sensor_id, limite_puntos=5000)
        cuenca = lecturas[0].get("cuenca_codigo") if lecturas else None

        if len(lecturas) < 2:
            return TendenciaAbatimiento(
                sensor_id=sensor_id,
                cuenca_codigo=cuenca,
                total_lecturas=len(lecturas),
                primer_registro=None,
                ultimo_registro=None,
                nivel_inicial_m=None,
                nivel_final_m=None,
                delta_total_m=None,
                tasa_abatimiento_m_mes=None,
                alerta_sobreexplotacion=False,
                diagnostico_shac="Datos insuficientes (se requieren al menos 2 lecturas temporales)."
            )

        # En hidrogeología, nivel freático medido desde superficie: valores más altos = más profundo (abatimiento)
        # o cota piezométrica msnm: valores menores = abatimiento.
        t0 = datetime.fromisoformat(lecturas[0]["fecha_hora"])
        t1 = datetime.fromisoformat(lecturas[-1]["fecha_hora"])
        dias = max((t1 - t0).total_seconds() / 86400.0, 0.1)

        val0 = float(lecturas[0]["valor"])
        val1 = float(lecturas[-1]["valor"])
        delta = val1 - val0 # Positivo = descenso de nivel desde brocal (pozo se profundiza)

        meses = max(dias / 30.4375, 0.01)
        tasa_mes = delta / meses

        alerta = tasa_mes > 0.04 # Más de 4 cm/mes (~0.5 m/año de descenso acumulado)

        if alerta:
            diag = (
                f"ALERTA CRÍTICA: Descenso freático acelerado de {round(tasa_mes * 12, 2)} m/año. "
                "Acuífero en condición de sobreexplotación. Requiere zona de prohibición (Art. 63)."
            )
        else:
            diag = "Nivel freático estable dentro de márgenes de recarga hidrogeológica estacional."

        return TendenciaAbatimiento(
            sensor_id=sensor_id,
            cuenca_codigo=cuenca,
            total_lecturas=len(lecturas),
            primer_registro=lecturas[0]["fecha_hora"],
            ultimo_registro=lecturas[-1]["fecha_hora"],
            nivel_inicial_m=round(val0, 2),
            nivel_final_m=round(val1, 2),
            delta_total_m=round(delta, 2),
            tasa_abatimiento_m_mes=round(tasa_mes, 3),
            alerta_sobreexplotacion=alerta,
            diagnostico_shac=diag
        )
