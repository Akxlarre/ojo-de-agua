"""
Demostración Integral del Agentic Knowledge Harness para la Gestión Hídrica en Chile.
Ejecuta el ciclo de vida completo:
1. Ingestión de datos de la Cuenca del Río Maipo.
2. Detección y bloqueo de términos no canónicos (Guardrail de Lenguaje Ubicuo).
3. Verificación de balance de masa e invariantes de prorrateo (Guardrail Hidráulico).
4. Consulta agéntica con capa anticorrupción (ACL Hook).
"""

import json
from src.harness.runner import KnowledgeHarness
from src.memory.graph import DomainNode, DomainEdge
from src.domain.operation.models import BalanceHidricoSeccion


def main():
    print("=" * 80)
    print("   HARNESS DE CONOCIMIENTO AGÉNTICO - GESTIÓN HÍDRICA EN CHILE (DDD)   ")
    print("=" * 80)

    # 1. Inicializar el Harness
    harness = KnowledgeHarness()
    print("\n[+] Harness inicializado con registro de Lenguaje Ubicuo y Hooks.")

    # 2. Ingestar infraestructura y gobernanza canónica del Río Maipo
    print("\n--- PASO 1: Ingestión de Estructura de Dominio (Río Maipo) ---")
    nodes = [
        DomainNode(
            id="cuenca-057",
            label="Cuenca",
            bounded_context="Fisico",
            name="Cuenca del Río Maipo",
            properties={"codigo_dga": "057", "region": "Región Metropolitana", "superficie_km2": 15380}
        ),
        DomainNode(
            id="jv-maipo-1",
            label="JuntaVigilancia",
            bounded_context="OUA",
            name="Junta de Vigilancia del Río Maipo Primera Sección",
            properties={"seccion": 1, "rio": "Río Maipo", "total_acciones": 1824.5}
        ),
        DomainNode(
            id="bocatoma-san-carlos",
            label="Bocatoma",
            bounded_context="Fisico",
            name="Bocatoma Canal San Carlos",
            properties={"capacidad_m3s": 65.0, "telemetria_mee": True}
        ),
        DomainNode(
            id="ac-san-carlos",
            label="AsociacionCanalistas",
            bounded_context="OUA",
            name="Sociedad del Canal de Maipo (Canal San Carlos)",
            properties={"canal_matriz": "Canal San Carlos", "total_acciones": 1000.0}
        ),
        DomainNode(
            id="celador-sector-1",
            label="Celador",
            bounded_context="Operacion",
            name="Don Juan Perez",
            properties={"sector": "Bocatoma km 0 a km 12", "telefono": "+56912345678"}
        )
    ]

    edges = [
        DomainEdge(source_id="jv-maipo-1", target_id="cuenca-057", relation_type="JURISDICCION_EN", bounded_context="OUA"),
        DomainEdge(source_id="jv-maipo-1", target_id="bocatoma-san-carlos", relation_type="REGULA_EXTRACCION", bounded_context="OUA"),
        DomainEdge(source_id="bocatoma-san-carlos", target_id="ac-san-carlos", relation_type="ABASTECE_A", bounded_context="Fisico"),
        DomainEdge(source_id="celador-sector-1", target_id="bocatoma-san-carlos", relation_type="OPERA_COMPUERTAS", bounded_context="Operacion"),
    ]

    report = harness.ingest_candidate_elements(nodes, edges, source_doc="Estatutos JV Río Maipo & DGA")
    print(f"-> Ingestión completada exitosamente: {report.success}")
    print(f"-> Nodos incorporados al Grafo de Conocimiento: {report.nodes_added}")
    print(f"-> Relaciones topológicas añadidas: {report.edges_added}")

    # 3. Prueba de Guardrail de Lenguaje Ubicuo (Intento de contaminación léxica)
    print("\n--- PASO 2: Guardrail de Lenguaje Ubicuo (Detección de Jerga Prohibida) ---")
    dirty_text = "El comite de rio envió un guardia de compuerta a revisar la toma de agua sin telemetria casera."
    violations = harness.ubiquitous_guard.validate(dirty_text)
    print(f"Texto analizado: '{dirty_text}'")
    print(f"Violaciones detectadas ({len(violations)}):")
    for v in violations:
        print(f"   [!] Término prohibido: '{v.forbidden_term_found}' -> Usar canónico: '{v.suggested_canonical_term}' (Contexto: {v.bounded_context})")

    # 4. Prueba de Invariante de Masa e Hidráulica (Simulación de Escasez Hídrica)
    print("\n--- PASO 3: Verificación de Invariante Hidráulica (Balance de Masa en Sequía) ---")
    balance_deficit = BalanceHidricoSeccion(
        seccion_id="sec-maipo-1",
        caudal_afluente_m3s=35.0, # Río trae 35 m3/s en verano
        caudal_ecologico_minimo_m3s=8.0, # Ley exige 8 m3/s pasantes
        extracciones_bocatomas_m3s={
            "Bocatoma San Carlos": 20.0,
            "Bocatoma Pirque": 12.0,
            "Bocatoma Clarillo": 7.0 # Total extracciones: 39 m3/s + 8 m3/s = 47 m3/s > 35 m3/s
        }
    )
    invariants_check = balance_deficit.check_invariants()
    if invariants_check:
        print("[!] ALERTA CRÍTICA DE INVARIANTE:")
        for inv in invariants_check:
            print(f"   {inv}")

    # 5. Consulta Agéntica con Capa Anti-Corrupción (Pre-Query Hook)
    print("\n--- PASO 4: Consulta Agéntica con Hook Anti-Corrupción (Pre-Query Hook) ---")
    pregunta_usuario = "¿Quién es el guardia de compuerta a cargo en el comite de rio Maipo?"
    print(f"Consulta original del usuario: '{pregunta_usuario}'")
    
    contexto_agente = harness.prepare_agent_context(pregunta_usuario, active_context=None)
    print(f"Consulta sanitizada por el Hook: '{contexto_agente['sanitized_query']}'")
    print(f"Nodos relevantes recuperados del grafo ({len(contexto_agente['relevant_graph_nodes'])}):")
    for n in contexto_agente["relevant_graph_nodes"]:
        print(f"   * [{n['label']}] {n['name']} (Contexto: {n['bounded_context']})")

    print("\n" + "=" * 80)
    print("   DEMOSTRACIÓN FINALIZADA CON ÉXITO   ")
    print("=" * 80)


if __name__ == "__main__":
    main()
