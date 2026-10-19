"""
Pipeline de procesamiento del Catastro Nacional de Depósitos de Relaves de Chile (SERNAGEOMIN 2025).
Normaliza tranques, embalses y depósitos de relaves mineros, clasifica su riesgo estructural/ambiental
(Aguas Arriba vs Aguas Abajo, Activos vs Abandonados), asigna las macrocuencas hidrográficas DGA receptoras,
y evalúa la amenaza de contaminación y colapso aluvial sobre las fuentes de agua potable y riego.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_GEOJSON = BASE_DIR / "data" / "dga_raw" / "sernageomin_relaves_2025.geojson"
DATA_DIR = BASE_DIR / "data"


def classify_risk_level(estado: str, metodo: str, volumen_m3: float) -> str:
    """Clasifica el nivel de riesgo hídrico y geotécnico del depósito de relave."""
    est = (estado or "").upper()
    met = (metodo or "").upper()

    # Relaves abandonados o construidos con método aguas arriba (prohibido por alta susceptibilidad sísmica)
    if "ABANDONADO" in est or "AGUAS ARRIBA" in met:
        return "Crítico / Alto Riesgo"
    elif "INACTIVO" in est and volumen_m3 > 5_000_000:
        return "Alto Riesgo"
    elif "ACTIVO" in est and volumen_m3 > 50_000_000:
        return "Medio-Alto (Megadepósito Operativo)"
    elif "INACTIVO" in est:
        return "Medio (Pasivo Minero Inactivo)"
    return "Monitoreo Estándar"


def process_sernageomin_relaves() -> Dict[str, Any]:
    print(f"\n[+] Procesando Catastro SERNAGEOMIN de Depósitos de Relaves desde {RAW_GEOJSON}...")
    if not RAW_GEOJSON.exists():
        raise FileNotFoundError(f"Archivo GeoJSON no encontrado en {RAW_GEOJSON}")

    cuencas = load_cuencas_index()

    with open(RAW_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    print(f"    -> {len(features)} depósitos de relaves mineros registrados en Chile.")

    relaves_list: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_relaves": 0,
        "relaves_activos": 0,
        "relaves_inactivos": 0,
        "relaves_abandonados": 0,
        "volumen_total_actual_m3": 0.0,
        "tonelaje_total_actual": 0.0,
        "operadores": set(),
        "faenas": set(),
        "relaves_criticos": []
    })

    total_nacional_volumen_m3 = 0.0
    total_activos = 0
    total_inactivos = 0
    total_abandonados = 0

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        coords = geom.get("coordinates") if geom else None
        lon = float(coords[0]) if coords and len(coords) >= 2 else None
        lat = float(coords[1]) if coords and len(coords) >= 2 else None

        obj_id = props.get("OBJECTID") or idx + 1
        cod_id = str(props.get("ID") or f"REL-{obj_id}").strip()
        faena = (props.get("NOMBRE_FAENA") or f"Faena {obj_id}").strip()
        instalacion = (props.get("NOMBRE_INSTALACION") or f"Relave {cod_id}").strip()
        titular = (props.get("NOMBRE_EMPRESA_O_PRODUCTOR_MINE") or "Sin titular registrado").strip()
        rut = (props.get("RUT_EMPRESA_O_PRODUCTOR_MINERO") or "").strip()
        tipo_dep = (props.get("TIPO_DEPOSITO") or "Tranque de Relave").strip()
        recurso = (props.get("RECURSO") or "Cobre").strip()
        estado = (props.get("ESTADO_INSTALACION") or "DESCONOCIDO").strip().upper()
        metodo = (props.get("METODO_CONSTRUCTIVO_MURO") or "No clasificado").strip()

        vol_aut = float(props.get("VOL_AUTORIZADO") or 0.0)
        vol_act = float(props.get("VOL_ACTUAL") or 0.0)
        ton_aut = float(props.get("TONELAJE_AUTORIZADO") or 0.0)
        ton_act = float(props.get("TONELAJE_ACTUAL") or 0.0)

        region = (props.get("REGION") or "").strip()
        provincia = (props.get("PROVINCIA") or "").strip()
        comuna = (props.get("COMUNA") or "").strip()

        c_obj = find_cuenca_for_point(lat, lon, region, cuencas) if lat and lon else None
        cuenca_cod = c_obj["codigo_dga"] if c_obj else ""
        cuenca_nom = c_obj["nombre"] if c_obj else ""

        riesgo = classify_risk_level(estado, metodo, vol_act)

        if "ACTIVO" in estado:
            total_activos += 1
        elif "INACTIVO" in estado:
            total_inactivos += 1
        elif "ABANDONADO" in estado:
            total_abandonados += 1

        total_nacional_volumen_m3 += vol_act

        item = {
            "id": f"sernageomin_relave_{cod_id.replace(' ', '_').replace('-', '_').lower()}",
            "codigo_deposito": cod_id,
            "nombre_faena": faena,
            "nombre_instalacion": instalacion,
            "titular_minero": titular,
            "rut_titular": rut if rut else None,
            "tipo_deposito": tipo_dep,
            "recurso_mineral": recurso,
            "estado_operativo": estado,
            "metodo_constructivo_muro": metodo,
            "clasificacion_riesgo": riesgo,
            "volumen_autorizado_m3": round(vol_aut, 2),
            "volumen_actual_m3": round(vol_act, 2),
            "tonelaje_actual": round(ton_act, 2),
            "region": region,
            "provincia": provincia,
            "comuna": comuna,
            "cuenca_codigo": cuenca_cod,
            "cuenca_nombre": cuenca_nom,
            "coordenadas": {"latitud": round(lat, 6), "longitud": round(lon, 6)} if lat and lon else None,
            "fuente_oficial": "SERNAGEOMIN (Catastro Nacional de Depósitos de Relaves 2025)"
        }
        relaves_list.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_relaves"] += 1
            if "ACTIVO" in estado:
                agg["relaves_activos"] += 1
            elif "INACTIVO" in estado:
                agg["relaves_inactivos"] += 1
            elif "ABANDONADO" in estado:
                agg["relaves_abandonados"] += 1

            agg["volumen_total_actual_m3"] += vol_act
            agg["tonelaje_total_actual"] += ton_act
            agg["operadores"].add(titular)
            agg["faenas"].add(faena)

            if "Crítico" in riesgo or "Alto" in riesgo:
                agg["relaves_criticos"].append({
                    "codigo": cod_id,
                    "faena": faena,
                    "instalacion": instalacion,
                    "titular": titular,
                    "estado": estado,
                    "riesgo": riesgo,
                    "volumen_m3": vol_act
                })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["relaves_criticos"].sort(key=lambda x: x["volumen_m3"], reverse=True)
        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_relaves": d["total_relaves"],
            "relaves_activos": d["relaves_activos"],
            "relaves_inactivos": d["relaves_inactivos"],
            "relaves_abandonados": d["relaves_abandonados"],
            "volumen_total_actual_m3": round(d["volumen_total_actual_m3"], 2),
            "volumen_total_millones_m3": round(d["volumen_total_actual_m3"] / 1_000_000, 2),
            "tonelaje_total_actual": round(d["tonelaje_total_actual"], 2),
            "operadores": sorted(list(d["operadores"]))[:8],
            "total_operadores": len(d["operadores"]),
            "relaves_alta_amenaza": d["relaves_criticos"][:6]
        })

    # Ordenar cuencas por mayor número de depósitos de relave
    cuencas_summary.sort(key=lambda x: x["total_relaves"], reverse=True)

    out_relaves = DATA_DIR / "sernageomin_relaves_chile.json"
    out_cuencas = DATA_DIR / "sernageomin_relaves_resumen_cuencas.json"

    print(f"    -> Exportando {len(relaves_list)} relaves mineros a {out_relaves}...")
    with open(out_relaves, "w", encoding="utf-8") as f:
        json.dump(relaves_list, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando balance de amenazas mineras en {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_depositos_relaves": len(relaves_list),
        "relaves_activos": total_activos,
        "relaves_inactivos": total_inactivos,
        "relaves_abandonados": total_abandonados,
        "volumen_total_nacional_millones_m3": round(total_nacional_volumen_m3 / 1_000_000, 2),
        "cuencas_con_relaves": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_sernageomin_relaves()
    print("\n[OK] Procesamiento SERNAGEOMIN completado exitosamente:")
    for k, v in report.items():
        print(f"    - {k}: {v:,.2f}" if isinstance(v, float) else f"    - {k}: {v}")
