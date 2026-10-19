"""
Unit tests for Bitemporal Modeling in Water Rights (DAA).
"""

from datetime import date, datetime, timezone
from src.domain.legal.bitemporal import IntervaloBitemporal, RegistroBitemporalDAA


def test_bitemporal_daa_retroactive_recognition():
    # Hecho: Derecho existe en el río desde el 1 de Enero de 2020 (valido_desde = 2020-01-01)
    # Trámite: La resolución DGA / CBR se registró en el sistema el 15 de Octubre de 2022 (registrado_el = 2022-10-15)
    registro_daa = RegistroBitemporalDAA(
        id="daa-001",
        codigo_dga="RES-2022-500",
        titular="Agrícola del Valle",
        caudal_lps=150.0,
        temporalidad=IntervaloBitemporal(
            valido_desde=date(2020, 1, 1),
            valido_hasta=None,
            registrado_el=datetime(2022, 10, 15, 12, 0, tzinfo=timezone.utc),
            reemplazado_el=None
        )
    )

    # Consulta 1: ¿Era válido físicamente el 1 de Marzo de 2021 según lo que el sistema sabía en 2021?
    # Respuesta: Físicamente sí existía en el mundo, pero el sistema aún NO lo sabía en 2021 -> False
    tiempo_consulta_2021 = datetime(2021, 5, 1, tzinfo=timezone.utc)
    assert registro_daa.es_valido_en(date(2021, 3, 1), tiempo_consulta_2021) is False

    # Consulta 2: ¿Era válido físicamente el 1 de Marzo de 2021 según lo que el sistema sabe hoy (en 2026)?
    # Respuesta: Sí, hoy en día se sabe con certeza que era válido retroactivamente -> True
    tiempo_consulta_hoy = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert registro_daa.es_valido_en(date(2021, 3, 1), tiempo_consulta_hoy) is True


def test_bitemporal_amendment_superseded_record():
    # Versión 1: Se registró en 2022 que el titular era 'Agrícola A'
    v1 = RegistroBitemporalDAA(
        id="daa-v1",
        codigo_dga="RES-100",
        titular="Agrícola A",
        caudal_lps=100.0,
        temporalidad=IntervaloBitemporal(
            valido_desde=date(2020, 1, 1),
            registrado_el=datetime(2022, 1, 1, tzinfo=timezone.utc),
            reemplazado_el=datetime(2024, 6, 1, tzinfo=timezone.utc) # Reemplazado por compraventa en 2024
        )
    )

    # Si consultamos la base de datos "As of 2023" -> v1 está activa
    assert v1.es_valido_en(date(2022, 6, 1), datetime(2023, 1, 1, tzinfo=timezone.utc)) is True

    # Si consultamos la base de datos "As of 2025" -> v1 fue reemplazada (superseded)
    assert v1.es_valido_en(date(2022, 6, 1), datetime(2025, 1, 1, tzinfo=timezone.utc)) is False
