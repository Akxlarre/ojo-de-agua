"""
Pipeline de procesamiento de la Nómina Oficial de Patentes por No Uso de Aguas
de la Tesorería General de la República (TGR) y Dirección General de Aguas (DGA, Art. 129 bis Código de Aguas).
Mide la especulación y acaparamiento hídrico, asigna las patentes a macrocuencas DGA mediante índice comunal,
y cuantifica la deuda en UTM y CLP en cuencas con estrés hídrico.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.harness.process_sma_sanciones import find_cuenca_for_point, load_cuencas_index

BASE_DIR = Path(__file__).parent.parent.parent
RAW_CSV = BASE_DIR / "data" / "dga_raw" / "tgr_patentes_aguas_2025.csv"
DATA_DIR = BASE_DIR / "data"


def build_comuna_spatial_index(cuencas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Construye un índice espacial Comuna -> Cuenca DGA a partir de los catastros de APR y BNA."""
    comuna_coords: Dict[str, Tuple[float, float, str]] = {}

    apr_file = DATA_DIR / "sistemas_ssr_apr_chile.json"
    if apr_file.exists():
        with open(apr_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                com = (item.get("comuna") or "").strip().upper()
                reg = (item.get("region") or "").strip()
                coords = item.get("coordenadas")
                if com and coords and len(coords) == 2 and coords[0] != 0 and com not in comuna_coords:
                    comuna_coords[com] = (coords[0], coords[1], reg)

    bna_file = DATA_DIR / "estaciones_bna_chile.json"
    if bna_file.exists():
        with open(bna_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                com = (item.get("comuna") or "").strip().upper()
                reg = (item.get("region") or "").strip()
                coords = item.get("coordenadas")
                if com and coords and len(coords) == 2 and coords[0] != 0 and com not in comuna_coords:
                    comuna_coords[com] = (coords[0], coords[1], reg)

    comuna_cuenca_map: Dict[str, Dict[str, Any]] = {}
    for com, (lat, lon, reg) in comuna_coords.items():
        c_obj = find_cuenca_for_point(lat, lon, reg, cuencas)
        if c_obj:
            comuna_cuenca_map[com] = {
                "codigo": c_obj["codigo_dga"],
                "nombre": c_obj["nombre"],
                "lat": lat,
                "lon": lon
            }

    return comuna_cuenca_map


def process_tgr_patentes() -> Dict[str, Any]:
    print(f"\n[+] Procesando Nómina Oficial TGR/DGA de Patentes por No Uso desde {RAW_CSV}...")
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Archivo CSV no encontrado en {RAW_CSV}")

    cuencas = load_cuencas_index()
    comuna_map = build_comuna_spatial_index(cuencas)

    df = pd.read_csv(RAW_CSV, encoding="latin1", low_memory=False)
    df.columns = [c.strip().upper() for c in df.columns]

    df["MONTO"] = pd.to_numeric(df["MONTO"], errors="coerce").fillna(0.0)
    df["SALDO"] = pd.to_numeric(df["SALDO"], errors="coerce").fillna(0.0)
    df["PAGADO"] = pd.to_numeric(df["PAGADO"], errors="coerce").fillna(0.0)
    df["UTM"] = pd.to_numeric(df["UTM"], errors="coerce").fillna(0.0)

    total_registros = len(df)
    print(f"    -> {total_registros:,} registros de patentes por no uso cargados.")

    patentes_destacadas: List[Dict[str, Any]] = []
    cuencas_agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "cuenca_codigo": "",
        "cuenca_nombre": "",
        "total_patentes": 0,
        "monto_total_clp": 0.0,
        "saldo_pendiente_clp": 0.0,
        "pagado_clp": 0.0,
        "total_utm": 0.0,
        "comunas": set(),
        "morosos": []
    })

    total_saldo_nacional = 0.0
    total_utm_nacional = 0.0
    total_monto_nacional = 0.0

    for idx, row in df.iterrows():
        comuna_raw = str(row.get("COMUNA") or "").strip().upper()
        reg_raw = str(row.get("TESORERIA_REGIONAL") or "").strip()
        rut_rol = str(row.get("RUT_ROL") or "").strip()
        tipo_pers = str(row.get("TIPO_PERSONA") or "JURIDICA").strip()
        folio = str(row.get("FORM_FOLIO") or idx + 1).strip()
        cuenta = str(row.get("CUENTA") or "").strip()
        monto = float(row.get("MONTO") or 0.0)
        saldo = float(row.get("SALDO") or 0.0)
        pagado = float(row.get("PAGADO") or 0.0)
        utm = float(row.get("UTM") or 0.0)
        ano_pat = str(row.get("ANIO_PATENTE") or "2024").split(".")[0]

        total_saldo_nacional += saldo
        total_utm_nacional += utm
        total_monto_nacional += monto

        c_info = comuna_map.get(comuna_raw)
        cuenca_cod = c_info["codigo"] if c_info else ""
        cuenca_nom = c_info["nombre"] if c_info else ""
        lat = c_info["lat"] if c_info else None
        lon = c_info["lon"] if c_info else None

        # Guardar en patentes destacadas las patentes con deuda >= 20 UTM o saldo >= $1.500.000 CLP
        if utm >= 20.0 or saldo >= 1_500_000.0 or idx < 500:
            item = {
                "id": f"tgr_patente_{idx+1}",
                "cuenta_tgr": cuenta,
                "folio": folio,
                "rut_rol_titular": rut_rol,
                "tipo_persona": tipo_pers,
                "monto_liquidado_clp": round(monto, 0),
                "saldo_deuda_clp": round(saldo, 0),
                "monto_pagado_clp": round(pagado, 0),
                "utm_liquidada": round(utm, 2),
                "ano_patente": ano_pat,
                "comuna": comuna_raw,
                "tesoreria_regional": reg_raw,
                "cuenca_codigo": cuenca_cod,
                "cuenca_nombre": cuenca_nom,
                "coordenadas": {"latitud": round(lat, 6), "longitud": round(lon, 6)} if lat and lon else None,
                "es_moroso": saldo > 0
            }
            patentes_destacadas.append(item)

        if cuenca_cod:
            agg = cuencas_agg[cuenca_cod]
            agg["cuenca_codigo"] = cuenca_cod
            agg["cuenca_nombre"] = cuenca_nom
            agg["total_patentes"] += 1
            agg["monto_total_clp"] += monto
            agg["saldo_pendiente_clp"] += saldo
            agg["pagado_clp"] += pagado
            agg["total_utm"] += utm
            agg["comunas"].add(comuna_raw)
            if saldo > 0:
                agg["morosos"].append({
                    "rut_rol": rut_rol,
                    "saldo_clp": saldo,
                    "utm": utm,
                    "ano": ano_pat
                })

    cuencas_summary = []
    for cod in sorted(cuencas_agg.keys()):
        d = cuencas_agg[cod]
        d["morosos"].sort(key=lambda x: x["saldo_clp"], reverse=True)
        monto_tot = d["monto_total_clp"]
        pagado_tot = d["pagado_clp"]
        morosidad_pct = round((d["saldo_pendiente_clp"] / monto_tot * 100), 1) if monto_tot > 0 else 0.0

        cuencas_summary.append({
            "cuenca_codigo": d["cuenca_codigo"],
            "cuenca_nombre": d["cuenca_nombre"],
            "total_patentes_no_uso": d["total_patentes"],
            "deuda_total_utm": round(d["total_utm"], 1),
            "monto_total_clp": round(monto_tot, 0),
            "saldo_pendiente_clp": round(d["saldo_pendiente_clp"], 0),
            "monto_pagado_clp": round(pagado_tot, 0),
            "porcentaje_morosidad": morosidad_pct,
            "comunas": sorted(list(d["comunas"])),
            "top_especuladores_no_uso": d["morosos"][:5]
        })

    # Ordenar cuencas por mayor deuda en UTM (mayor nivel de acaparamiento sin uso)
    cuencas_summary.sort(key=lambda x: x["deuda_total_utm"], reverse=True)

    out_destacadas = DATA_DIR / "tgr_patentes_destacadas.json"
    out_cuencas = DATA_DIR / "tgr_patentes_resumen_cuencas.json"

    print(f"    -> Exportando {len(patentes_destacadas)} patentes destacadas a {out_destacadas}...")
    with open(out_destacadas, "w", encoding="utf-8") as f:
        json.dump(patentes_destacadas, f, ensure_ascii=False, indent=2)

    print(f"    -> Exportando balance de patentes por no uso en {len(cuencas_summary)} cuencas a {out_cuencas}...")
    with open(out_cuencas, "w", encoding="utf-8") as f:
        json.dump(cuencas_summary, f, ensure_ascii=False, indent=2)

    return {
        "total_registros_procesados": total_registros,
        "patentes_destacadas": len(patentes_destacadas),
        "deuda_total_nacional_utm": round(total_utm_nacional, 1),
        "saldo_pendiente_nacional_clp": round(total_saldo_nacional, 0),
        "cuencas_con_patentes_no_uso": len(cuencas_summary)
    }


if __name__ == "__main__":
    report = process_tgr_patentes()
    print("\n[OK] Procesamiento TGR Patentes completado exitosamente:")
    for k, v in report.items():
        print(f"    - {k}: {v:,.1f}" if isinstance(v, float) else f"    - {k}: {v:,}" if isinstance(v, int) else f"    - {k}: {v}")
