"""
Interactive CLI for Querying the National Chilean Water Knowledge Graph.
Demonstrates query sanitization via ACL, bounded context filtering,
and topological graph neighborhood exploration.
"""

import json
from pathlib import Path
import sys

from src.harness.runner import KnowledgeHarness
from src.memory.graph import DomainKnowledgeGraph


def run_interactive_explorer():
    graph_path = Path(__file__).parent.parent.parent / "data" / "knowledge_graph_chile.json"
    if not graph_path.exists():
        print("[!] No se encontró el grafo persistido. Ejecuta primero 'src.harness.batch_ingestion'.")
        return

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    harness = KnowledgeHarness()
    harness.graph = DomainKnowledgeGraph.from_dict(graph_data)

    print("=" * 80)
    print("   EXPLORADOR AGÉNTICO DEL GRAFO NACIONAL DE AGUAS EN CHILE   ")
    print(f"   Base de Conocimiento: {len(harness.graph.nodes)} Nodos | {len(harness.graph.edges)} Relaciones")
    print("=" * 80)
    print("Escribe una consulta (ej: '¿Quién administra el Río Aconcagua?', 'Río Maipo', 'Río Maule')")
    print("o escribe 'salir' para terminar.\n")

    while True:
        try:
            query = input("\n[?] Ingrese consulta de aguas: ").strip()
            if not query or query.lower() in ("salir", "exit", "quit"):
                print("Finalizando explorador.")
                break

            ctx = harness.prepare_agent_context(query)
            print(f"\n-> Consulta original:  {ctx['original_query']}")
            print(f"-> Consulta sanitizada: {ctx['sanitized_query']}")
            
            nodes = ctx["relevant_graph_nodes"]
            print(f"-> Nodos recuperados en el grafo ({len(nodes)}):")
            for nd in nodes[:8]: # Show top 8
                print(f"   * [{nd['label']}] {nd['name']} (Contexto: {nd['bounded_context']})")
                props = nd.get("properties", {})
                if "region" in props:
                    print(f"     Región: {props['region']} | Código DGA: {props.get('codigo_dga', 'N/A')}")
                if "decreto_escasez_activo" in props and props["decreto_escasez_activo"]:
                    print(f"     [!] ALERTA: Decreto de Escasez Activo ({props.get('decreto_vigente_numero', '')})")
            
            if len(nodes) > 8:
                print(f"     ... y {len(nodes) - 8} nodos más.")

        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    run_interactive_explorer()
