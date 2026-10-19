"""
Pipeline de procesamiento del Catastro Nacional de Plantas Desaladoras y Reúso de Chile (ACADES / MOP).
Normaliza la capacidad de desalinización de agua de mar (L/s y m³/día), clasifica por sector de destino
(Minería, Agua Potable / Sanitaria, Industrial), asigna las cuencas costeras DGA beneficiadas,
y mide el alivio de presión hídrica sobre las fuentes continentales en cuencas bajo estrés o sequía.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_JSON = BASE_DIR / "data" / "dga_raw" / "desaladoras_chile_acades.json"
DATA_DIR = BASE_DIR / "data"


def process_desaladoras() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro ACADES/MOP de Plantas Desaladoras desde {RAW_JSON}...")
    if not RAW_JSON.exists():
        raise FileNotFoundError(f"Archivo JSON no encontrado en {RAW_JSON}")

    cuencas = load_cuencas_index()

    with open(RAW_JSON, "r", encoding="utf-8") as f:
        features = json.load(f)

    print(f"    -> {len(features)} plantas desaladoras registradas en el catastro.")

    desaladoras_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_desaladoras": 0,
        "capacidad_total_lps": 0.0,
        "capacidad_total_m3_dia": 0.0,
        "capacidad_operacion_lps": 0.0,
        "plantas_en_operacion": 0,
        "plantas_en_proyecto": 0,
        "sectores": set(),
        "operadores": set(),
        "plantas": []
    })

    total_lps_nacional = 0.0
    total_lps_operacion = 0.0
    count_operacion = 0
    count_proyecto = 0

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        coords = geom.get("coordinates") if geom else None
        lon = float(coords[0]) if coords and len(coords) >= 2 else None
        lat = float(coords[1]) if coords and len(coords) >= 2 else None

        nombre = (props.get("Planta") or f"Desaladora {idx+1}").strip()
        operador = (props.get("Propietario_Operador") or "Sin operador registrado").strip()
        sector = (props.get("Sector") or "Industrial / Minero").strip()
        estado = (props.get("Estado") or "En operación").strip()
        tecnologia = (props.get("Tecnología") or props.get("Tecnologia") or "Ósmosis Inversa").strip()
        region = (props.get("Región") or "").strip()
        capacidad_raw = props.get("Capacidad_Ls")
        try:
            cap_lps = round(float(capacidad_raw or 0.0), 2)
        except (ValueError, TypeError):
            cap_lps = 0.0

        cap_m3_dia = round(cap_lps * 86.4, 2)
        is_operativa = "operaci" in estado.lower()

        if is_operativa:
            count_operacion += 1
            total_lps_operacion += cap_lps
        else:
            count_proyecto += 1

        total_lps_nacional += cap_lps

        c_obj = find_cuenca_for_point(lat, lon, region, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        item = {
            "id": f"desaladora_{idx+1}",
            "nombre": nombre,
            "operador": operador,
            "sector_destino": sector,
            "estado_operativo": estado,
            "es_operativa": is_operativa,
            "tecnologia": tecnologia,
            "capacidad_lps": cap_lps,
            "capacidad_m3_dia": cap_m3_dia,
            "region": region,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas": {"latitud": round(lat, 6), "longitud": round(lon, 6)} if lat and lon else None,
            "fuente_oficial": "ACADES / MOP (Catastro de Plantas Desaladoras de Chile)"
        }
        desaladoras_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_desaladoras"] += 1
            agg["capacidad_total_lps"] = round(agg["capacidad_total_lps"] + cap_lps, 2)
            agg["capacidad_total_m3_dia"] = round(agg["capacidad_total_m3_dia"] + cap_m3_dia, 2)
            if is_operativa:
                agg["capacidad_operacion_lps"] = round(agg["capacidad_operacion_lps"] + cap_lps, 2)
                agg["plantas_en_operacion"] += 1
            else:
                agg["plantas_en_proyecto"] += 1
            agg["sectores"].add(sector)
            agg["operadores"].add(operador)
            agg["plantas"].append({
                "nombre": nombre,
                "operador": operador,
                "sector": sector,
                "estado": estado,
                "capacidad_lps": cap_lps
            })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["plantas"].sort(key=lambda x: x["capacidad_lps"], reverse=True)
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_desaladoras": d["total_desaladoras"],
            "plantas_en_operacion": d["plantas_en_operacion"],
            "plantas_en_proyecto": d["plantas_en_proyecto"],
            "capacidad_total_lps": d["capacidad_total_lps"],
            "capacidad_operacion_lps": d["capacidad_operacion_lps"],
            "capacidad_total_m3_dia": d["capacidad_total_m3_dia"],
            "sectores": sorted(list(d["sectores"])),
            "operadores": sorted(list(d["operadores"])),
            "plantas_destacadas": d["plantas"][:5]
        })

    cuencas_summary.sort(key=lambda x: x["capacidad_total_lps"], reverse=True)

    out_desal = DATA_DIR / "desaladoras_chile.json"
    out_cuencas = DATA_DIR / "desaladoras_resumen_cuencas.json"

    print(f"    -> Exportando {len(desaladoras_list)} desaladoras a {out_desal}...")
    with open(out_desal, "w", encoding="utf-8") as f:
        json.dump(desaladoras_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando balance de desalinización de {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_desaladoras": len(desaladoras_list),
        "plantas_en_operacion": count_operacion,
        "plantas_en_proyecto": count_proyecto,
        "capacidad_total_nacional_lps": round(total_lps_nacional, 2),
        "capacidad_operativa_nacional_lps": round(total_lps_operacion, 2),
        "capacidad_operativa_m3_dia": round(total_lps_operacion * 86.4, 2),
        "cuencas_beneficiadas": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_desaladoras()
    print("\n[OK] Procesamiento Desaladoras completado exitosamente:")
    for k, v in report.items():
        print(f"    - {k}: {v:,.2f}" if isinstance(v, float) else f"    - {k}: {v}")
