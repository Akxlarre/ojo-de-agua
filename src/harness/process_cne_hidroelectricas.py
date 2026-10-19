"""
Pipeline de procesamiento del Catastro de Centrales Hidroeléctricas en Operación
de la Comisión Nacional de Energía (CNE - Chile / SEN).
Normaliza la capacidad instalada (MW), clasifica por tecnología (Pasada vs Embalse),
asigna las cuencas hidrográficas DGA y genera los balances de generación hídrica.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_GEOJSON = BASE_DIR / "data" / "dga_raw" / "cne_centrales_hidroelectricas.geojson"
DATA_DIR = BASE_DIR / "data"

REGION_NAMES = {
    "01": "Tarapacá",
    "02": "Antofagasta",
    "03": "Atacama",
    "04": "Coquimbo",
    "05": "Valparaíso",
    "06": "O'Higgins",
    "07": "Maule",
    "08": "Biobío",
    "09": "La Araucanía",
    "10": "Los Lagos",
    "11": "Aysén",
    "12": "Magallanes",
    "13": "Metropolitana",
    "14": "Los Ríos",
    "15": "Arica y Parinacota",
    "16": "Ñuble"
}


def process_cne_hidroelectricas() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro CNE de Centrales Hidroeléctricas desde {RAW_GEOJSON}...")
    if not RAW_GEOJSON.exists():
        raise FileNotFoundError(f"Archivo GeoJSON no encontrado en {RAW_GEOJSON}")

    cuencas = load_cuencas_index()

    with open(RAW_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"    -> {len(features)} centrales hidroeléctricas registradas por la CNE.")

    centrales_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_centrales": 0,
        "potencia_total_mw": 0.0,
        "potencia_pasada_mw": 0.0,
        "potencia_embalse_mw": 0.0,
        "centrales_pasada": 0,
        "centrales_embalse": 0,
        "operadores": set(),
        "centrales": []
    })

    total_mw_nacional = 0.0
    total_mw_pasada = 0.0
    total_mw_embalse = 0.0

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        coords = geom.get("coordinates") if geom else None
        lon = float(coords[0]) if coords and len(coords) >= 2 else None
        lat = float(coords[1]) if coords and len(coords) >= 2 else None

        obj_id = props.get("OBJECTID") or idx + 1
        ge_id = props.get("ID_GE_HIDRO") or obj_id
        nombre = (props.get("NOMBRE") or f"Central {obj_id}").strip()
        propiedad = (props.get("PROPIEDAD") or "Sin titular registrado").strip()
        tipo_raw = (props.get("TIPO") or "HIDRAULICA PASADA").strip().upper()
        
        is_embalse = "EMBALSE" in tipo_raw
        tipo_normalizado = "Embalse" if is_embalse else "Pasada"
        
        mw = round(float(props.get("POTENCIAMW") or 0.0), 3)
        unidades = int(props.get("UNIDADES") or 1)
        rca = (props.get("RCA") or "").strip()
        sistema = (props.get("SIST_ELECT") or "SEN").strip()
        estado = (props.get("ESTADO") or "EN OPERACION").strip()
        reg_code = str(props.get("REGION") or "").zfill(2)
        region_nombre = REGION_NAMES.get(reg_code, f"Región {reg_code}")

        c_obj = find_cuenca_for_point(lat, lon, region_nombre, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        total_mw_nacional += mw
        if is_embalse:
            total_mw_embalse += mw
        else:
            total_mw_pasada += mw

        item = {
            "id": f"cne_hidro_{ge_id}",
            "objectid": obj_id,
            "id_ge_hidro": ge_id,
            "nombre": nombre,
            "propietario": propiedad,
            "tipo_tecnologia": tipo_normalizado,
            "tipo_original": tipo_raw,
            "potencia_mw": mw,
            "unidades_generacion": unidades,
            "sistema_electrico": sistema,
            "estado_operativo": estado,
            "resolucion_calificacion_ambiental": rca if rca and rca != "NO APLICA" else None,
            "region": region_nombre,
            "codigo_region": reg_code,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas": {"latitud": round(lat, 6), "longitud": round(lon, 6)} if lat and lon else None,
            "fuente_oficial": "CNE / SEN (Ministerio de Energía)"
        }
        centrales_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_centrales"] += 1
            agg["potencia_total_mw"] = round(agg["potencia_total_mw"] + mw, 3)
            if is_embalse:
                agg["potencia_embalse_mw"] = round(agg["potencia_embalse_mw"] + mw, 3)
                agg["centrales_embalse"] += 1
            else:
                agg["potencia_pasada_mw"] = round(agg["potencia_pasada_mw"] + mw, 3)
                agg["centrales_pasada"] += 1
            agg["operadores"].add(propiedad)
            agg["centrales"].append({
                "id": item["id"],
                "nombre": nombre,
                "potencia_mw": mw,
                "tipo": tipo_normalizado,
                "propietario": propiedad
            })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["centrales"].sort(key=lambda x: x["potencia_mw"], reverse=True)
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_centrales": d["total_centrales"],
            "potencia_total_mw": round(d["potencia_total_mw"], 2),
            "potencia_pasada_mw": round(d["potencia_pasada_mw"], 2),
            "potencia_embalse_mw": round(d["potencia_embalse_mw"], 2),
            "centrales_pasada": d["centrales_pasada"],
            "centrales_embalse": d["centrales_embalse"],
            "operadores": sorted(list(d["operadores"])),
            "centrales_destacadas": d["centrales"][:5]
        })

    # Ordenar cuencas por mayor potencia instalada
    cuencas_summary.sort(key=lambda x: x["potencia_total_mw"], reverse=True)

    out_centrales = DATA_DIR / "cne_hidroelectricas_chile.json"
    out_cuencas = DATA_DIR / "cne_hidro_resumen_cuencas.json"

    print(f"    -> Exportando {len(centrales_list)} centrales hidroeléctricas a {out_centrales}...")
    with open(out_centrales, "w", encoding="utf-8") as f:
        json.dump(centrales_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando balance hidroeléctrico de {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_centrales_hidro": len(centrales_list),
        "potencia_total_mw": round(total_mw_nacional, 2),
        "potencia_pasada_mw": round(total_mw_pasada, 2),
        "potencia_embalse_mw": round(total_mw_embalse, 2),
        "cuencas_con_hidroelectricas": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_cne_hidroelectricas()
    print("\n[OK] Procesamiento CNE completado exitosamente:")
    for k, v in report.items():
        print(f"    - {k}: {v:,.2f}" if isinstance(v, float) else f"    - {k}: {v}")
