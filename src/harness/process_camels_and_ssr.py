"""
Pipeline de procesamiento de:
1. CAMELS-CL (Centro de Ciencia del Clima y la Resiliencia - CR2 / U. de Chile):
   Atributos hidroclimáticos y de intervención antrópica para 516 cuencas.
2. DOH MOP - Base Nacional de Sistemas Sanitarios Rurales (SSR / APR):
   2.241 comités y cooperativas de Agua Potable Rural en Chile.
"""

import os
import sys
import json
import pandas as pd
from typing import Dict, Any, List

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'dga_raw')
DATA_DIR = os.path.join(BASE_DIR, 'data')

def clean_val(val):
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip().replace('"', '')
    return s.replace('\n', ' ').replace('\r', '')

def process_camels_cl() -> List[Dict[str, Any]]:
    txt_path = os.path.join(RAW_DIR, 'camels_cl', '1_CAMELScl_attributes.txt')
    print(f"\n[+] Procesando CAMELS-CL desde {txt_path}...")
    if not os.path.exists(txt_path):
        print(f"Error: {txt_path} no encontrado.")
        return []

    # Leer el archivo con separador de tabulaciones
    df_raw = pd.read_csv(txt_path, sep='\t')
    
    # La columna 0 es 'gauge_id' (que contiene los nombres de los atributos: gauge_name, gauge_lat, etc.)
    # Las columnas 1..N son las cuencas con sus respectivos gauge_ids
    attr_names = df_raw.iloc[:, 0].str.strip().str.replace('"', '').tolist()
    catchments_list = []

    for col in df_raw.columns[1:]:
        col_clean = str(col).strip().replace('"', '')
        vals = df_raw[col].tolist()
        cat_dict = {"gauge_id": col_clean}
        for attr, val in zip(attr_names, vals):
            cat_dict[attr] = clean_val(val)
            
        # Parse numeric attributes
        try:
            lat = float(cat_dict.get('gauge_lat') or 0.0)
            lon = float(cat_dict.get('gauge_lon') or 0.0)
            area = float(cat_dict.get('area') or 0.0)
            elev = float(cat_dict.get('elev_mean') or 0.0)
            precip = float(cat_dict.get('precip_cr2met') or 0.0)
            pet = float(cat_dict.get('pet_hargreaves') or 0.0)
            aridity = float(cat_dict.get('aridity_cr2met') or (pet / precip if precip > 0 else 0.0))
            q_mean = float(cat_dict.get('q_mean') or 0.0)
            int_degree = str(cat_dict.get('human_intervention_degree') or "Desconocido")
        except (ValueError, TypeError):
            lat, lon, area, elev, precip, pet, aridity, q_mean, int_degree = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "Desconocido"

        item = {
            "id": f"camels_{col_clean}",
            "codigo_bna": col_clean,
            "nombre_estacion": str(cat_dict.get('gauge_name') or f"Estación {col_clean}"),
            "coordenadas": [round(lat, 6), round(lon, 6)],
            "area_cuenca_km2": round(area, 2),
            "elevacion_media_msnm": round(elev, 1),
            "precipitacion_media_anual_mm": round(precip, 1),
            "evapotranspiracion_potencial_mm": round(pet, 1),
            "indice_aridez": round(aridity, 2),
            "caudal_medio_anual_m3s": round(q_mean, 2),
            "grado_intervencion_antropica": int_degree,
            "indices_hidrologicos": {
                "runoff_ratio": clean_val(cat_dict.get('runoff_ratio')),
                "baseflow_index": clean_val(cat_dict.get('baseflow_index')),
                "high_q_freq": clean_val(cat_dict.get('high_q_freq')),
                "low_q_freq": clean_val(cat_dict.get('low_q_freq')),
                "zero_q_freq": clean_val(cat_dict.get('zero_q_freq'))
            }
        }
        catchments_list.append(item)

    out_file = os.path.join(DATA_DIR, 'camels_cl_cuencas.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(catchments_list, f, indent=2, ensure_ascii=False)

    print(f" -> Guardadas {len(catchments_list)} Cuencas Hidroclimáticas CAMELS-CL en {out_file}")
    return catchments_list

def process_sistemas_ssr() -> List[Dict[str, Any]]:
    xlsx_path = os.path.join(RAW_DIR, 'base_ssr.xlsx')
    print(f"\n[+] Procesando Sistemas Sanitarios Rurales (SSR / APR) desde {xlsx_path}...")
    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} no encontrado.")
        return []

    # Leer Excel omitiendo la fila 0 de título
    df = pd.read_excel(xlsx_path, skiprows=1)
    
    # Identificar nombres de columnas
    cols = df.columns.tolist()
    col_id = cols[1]       # 'N°'
    col_reg = cols[2]      # 'Región'
    col_prov = cols[3]     # 'Provincia'
    col_com = cols[4]      # 'Comuna'
    col_nom = cols[5]      # 'Nombre oficial sistema'
    col_ano = cols[6]      # 'año puesta en marcha'
    col_arr = cols[7]      # 'N° de Arranques'
    col_tipo = cols[8]     # 'Tipo' (Concentrado / Semiconcentrado)
    col_ben = cols[10]     # 'Beneficiarios Estimados'
    col_adm = cols[11]     # 'Administración del Sistema' (Comité / Cooperativa)
    col_lon = cols[19]     # 'Coord X grados'
    col_lat = cols[20]     # 'Coord Y grados'

    ssr_list = []
    for idx, row in df.iterrows():
        nom = clean_val(row.get(col_nom))
        cod_ssr = clean_val(row.get(col_id))
        if not nom or cod_ssr == "N°" or "nombre oficial" in nom.lower():
            continue
            
        try:
            lat = float(row.get(col_lat) or 0.0)
            lon = float(row.get(col_lon) or 0.0)
        except (ValueError, TypeError):
            lat, lon = 0.0, 0.0
            
        try:
            arranques = int(float(str(row.get(col_arr) or 0)))
        except (ValueError, TypeError):
            arranques = 0
            
        try:
            beneficiarios = int(float(str(row.get(col_ben) or 0)))
        except (ValueError, TypeError):
            beneficiarios = int(arranques * 3.1)

        item = {
            "id": f"ssr_{clean_val(row.get(col_id)) or (idx+1)}",
            "codigo_ssr": clean_val(row.get(col_id)) or str(idx+1),
            "nombre": nom,
            "region": clean_val(row.get(col_reg)),
            "provincia": clean_val(row.get(col_prov)),
            "comuna": clean_val(row.get(col_com)),
            "ano_inicio": clean_val(row.get(col_ano)),
            "arranques_domiciliarios": arranques,
            "beneficiarios_estimados": beneficiarios,
            "tipo_sistema": clean_val(row.get(col_tipo)),
            "tipo_administracion": clean_val(row.get(col_adm)) or "Comité de Agua Potable Rural",
            "coordenadas": [round(lat, 6), round(lon, 6)] if lat != 0.0 else None
        }
        ssr_list.append(item)

    out_file = os.path.join(DATA_DIR, 'sistemas_ssr_apr_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(ssr_list, f, indent=2, ensure_ascii=False)

    print(f" -> Guardados {len(ssr_list)} Sistemas Sanitarios Rurales (APR) en {out_file}")
    return ssr_list

if __name__ == '__main__':
    print("Iniciando procesamiento de CAMELS-CL y Sistemas Sanitarios Rurales (SSR)...")
    camels = process_camels_cl()
    ssr = process_sistemas_ssr()
    print("\nPROCESAMIENTO CONSOLIDADO EXITOSO:")
    print(f" - Cuencas CAMELS-CL procesadas: {len(camels)}")
    print(f" - Sistemas Sanitarios Rurales (APR) procesados: {len(ssr)}")
