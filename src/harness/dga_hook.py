"""
DGA Automated Lifecycle Hook.
Monitors gauging station telemetry and legal drought decrees,
updating the Knowledge Graph and activating drought protocols automatically.
"""

from typing import List, Optional
from src.core.base import DomainEvent
from src.core.hooks import HookContext, HookStage
from src.domain.legal.dga_client import DGAClientAdapter, DecretoEscasezDGA, LecturaEstacionBNA
from src.harness.runner import KnowledgeHarness


class DGAAutomationHook:
    """
    Hook that connects the KnowledgeHarness to continuous DGA updates.
    """

    def __init__(self, harness: KnowledgeHarness, dga_client: Optional[DGAClientAdapter] = None):
        self.harness = harness
        self.dga_client = dga_client or DGAClientAdapter()

    def sync_drought_decrees(self) -> int:
        """
        Polls active DGA drought decrees and updates affected Juntas de Vigilancia
        in the knowledge graph to mark emergency distribution mode.
        """
        decretos = self.dga_client.list_decretos_escasez_activos()
        updated_count = 0

        for dec in decretos:
            for cuenca_cod in dec.cuencas_afectadas:
                # Find all Juntas in this basin
                juntas = self.harness.graph.find_nodes_by_label("JuntaVigilancia", bounded_context="OUA")
                for jv in juntas:
                    if jv.properties.get("cuenca_codigo") == cuenca_cod:
                        jv.properties["decreto_escasez_activo"] = True
                        jv.properties["decreto_vigente_numero"] = dec.numero_decreto
                        updated_count += 1

        return updated_count

    def process_station_telemetry(self, codigo_bna: str, caudal_ecologico_minimo_m3s: float) -> Optional[DomainEvent]:
        """
        Receives real-time telemetry from a DGA station.
        If flow drops below ecological minimum, records an alert event in the aggregate.
        """
        lectura = self.dga_client.get_estacion_lectura(codigo_bna)
        if not lectura:
            return None

        if lectura.caudal_instantaneo_m3s < caudal_ecologico_minimo_m3s:
            event = DomainEvent(
                event_name="CaudalCriticoDetectado",
                bounded_context="Operacion",
                payload={
                    "codigo_bna": codigo_bna,
                    "estacion": lectura.estacion_nombre,
                    "caudal_medido": lectura.caudal_instantaneo_m3s,
                    "caudal_ecologico_minimo": caudal_ecologico_minimo_m3s,
                    "deficit": caudal_ecologico_minimo_m3s - lectura.caudal_instantaneo_m3s
                }
            )
            return event
        return None
