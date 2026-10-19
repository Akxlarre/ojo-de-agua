"""
Pipeline de procesamiento masivo de datos abiertos de la Dirección General de Aguas (DGA - MOP Chile).
Procesa:
1. INV_ACUIFEROS_SHAC: 740 Sectores Hidrogeológicos de Aprovechamiento Común.
2. Red_Hidrometrica_Nacional: 3.843 Estaciones de Monitoreo BNA.
3. Inv_Embalses_DGA_DOH: 1.367 Embalses oficiales.
4. Decretos de Escasez Hídrica Históricos y Vigentes (2008-2026).
"""

import os
import json
import shapefile
import pandas as pd
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'dga_raw')
DATA_DIR = os.path.join(BASE_DIR, 'data')

def clean_val(val):
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    return s.replace('\n', ' ').replace('\r', '')

def process_shac() -> List[Dict[str, Any]]:
    shp_path = os.path.join(RAW_DIR, 'shac', 'Acuiferos_SHAC', 'INV_ACUIFEROS_SHAC.shp')
    print(f"Procesando SHAC desde {shp_path}...")
    shac_list = []
    
    with shapefile.Reader(shp_path, encoding='utf-8') as sf:
        for idx, (shape, rec) in enumerate(zip(sf.shapes(), sf.records())):
            d = rec.as_dict()
            bbox = shape.bbox  # [minx, miny, maxx, maxy] (longitud min, latitud min, longitud max, latitud max)
            centroid_lon = (bbox[0] + bbox[2]) / 2.0
            centroid_lat = (bbox[1] + bbox[3]) / 2.0
            
            # Limpiar nombre
            nombre = clean_val(d.get('SHAC')) or clean_val(d.get('NOM_ACUIF')) or f"SHAC-{idx+1}"
            acuifero = clean_val(d.get('NOM_ACUIF'))
            cuenca_bna = clean_val(d.get('NOM_BNA'))
            cod_bna = clean_val(d.get('COD_BNA'))
            cod_shac = clean_val(d.get('COD_SHAC')) or clean_val(d.get('ID_UNICO')) or f"SHAC_{idx+1}"
            region = clean_val(d.get('REGION')) or clean_val(d.get('REGIONES'))
            area_km2 = float(clean_val(d.get('a_km2')) or 0.0)
            res_dga = clean_val(d.get('RES_DGA'))
            fecha_dga = clean_val(d.get('F_RES_DGA'))
            
            shac_item = {
                'id': f"shac_{cod_shac}",
                'codigo_shac': cod_shac,
                'nombre': nombre,
                'acuifero': acuifero,
                'cuenca_asociada': cuenca_bna,
                'codigo_cuenca_bna': cod_bna,
                'region': region,
                'area_km2': round(area_km2, 2),
                'resolucion_dga': res_dga,
                'fecha_resolucion': fecha_dga,
                'centroide': [round(centroid_lat, 6), round(centroid_lon, 6)],
                'bbox': [round(b, 4) for b in bbox]
            }
            shac_list.append(shac_item)
            
    out_file = os.path.join(DATA_DIR, 'shac_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(shac_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardados {len(shac_list)} SHACs en {out_file}")
    return shac_list

def process_red_bna() -> List[Dict[str, Any]]:
    shp_path = os.path.join(RAW_DIR, 'red_bna', 'Red_Hidrometrica_Nacional', 'Red_Hidrometrica_Nacional.shp')
    print(f"Procesando Red BNA desde {shp_path}...")
    stations_list = []
    
    with shapefile.Reader(shp_path, encoding='utf-8') as sf:
        for idx, (shape, rec) in enumerate(zip(sf.shapes(), sf.records())):
            d = rec.as_dict()
            cod_bna = clean_val(d.get('COD_BNA'))
            nombre = clean_val(d.get('NOM_ESTACI'))
            lat = float(clean_val(d.get('LATITUD')) or 0.0)
            lon = float(clean_val(d.get('LONGITUD')) or 0.0)
            tipo = clean_val(d.get('TIPO_EST_1')) or clean_val(d.get('TIPO_ESTAC'))
            cuenca = clean_val(d.get('NOM_CUEN'))
            cod_cuen = clean_val(d.get('COD_CUEN'))
            subcuenca = clean_val(d.get('NOM_SUBC'))
            subsubcuenca = clean_val(d.get('NOM_SSUBC'))
            region = clean_val(d.get('REGION'))
            comuna = clean_val(d.get('COMUNA'))
            shac = clean_val(d.get('SHAC'))
            acuifero = clean_val(d.get('NOM_ACUIF'))
            altitud = int(clean_val(d.get('ALTITUD_MS')) or 0)
            institucion = clean_val(d.get('INSTITUCIO'))
            parametros = clean_val(d.get('PARAMETROS'))
            
            if lat == 0.0 or lon == 0.0:
                continue
                
            station_item = {
                'id': f"bna_{cod_bna}",
                'codigo_bna': cod_bna,
                'nombre': nombre,
                'tipo': tipo,
                'cuenca': cuenca,
                'codigo_cuenca': cod_cuen,
                'subcuenca': subcuenca,
                'subsubcuenca': subsubcuenca,
                'region': region,
                'comuna': comuna,
                'shac': shac,
                'acuifero': acuifero,
                'altitud_msnm': altitud,
                'institucion': institucion,
                'parametros': parametros[:120] if parametros else "",
                'coordenadas': [round(lat, 6), round(lon, 6)]
            }
            stations_list.append(station_item)
            
    out_file = os.path.join(DATA_DIR, 'estaciones_bna_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(stations_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardadas {len(stations_list)} Estaciones BNA en {out_file}")
    return stations_list

def process_embalses() -> List[Dict[str, Any]]:
    shp_path = os.path.join(RAW_DIR, 'embalses', 'Inventario_de_Embalses', 'Inv_Embalses_DGA_DOH.shp')
    print(f"Procesando Embalses desde {shp_path}...")
    embalses_list = []
    
    with shapefile.Reader(shp_path, encoding='utf-8') as sf:
        for idx, (shape, rec) in enumerate(zip(sf.shapes(), sf.records())):
            d = rec.as_dict()
            nombre = clean_val(d.get('NOM_EMBALS'))
            lat = float(clean_val(d.get('LATITUD')) or 0.0)
            lon = float(clean_val(d.get('LONGITUD')) or 0.0)
            region = clean_val(d.get('REGION'))
            comuna = clean_val(d.get('COMUNA'))
            altura = float(clean_val(d.get('ALTURA_MUR')) or 0.0)
            uso = clean_val(d.get('USO_EMBALS'))
            tamano = clean_val(d.get('TAMAÑO_EM')) or clean_val(d.get('TAMA\x91O_EM')) or "DESCONOCIDO"
            ano = clean_val(d.get('AÑO_CONTR')) or clean_val(d.get('A\x91O_CONTR')) or ""
            monitoreo = clean_val(d.get('MONITOREO_'))
            
            if lat == 0.0 or lon == 0.0:
                continue
                
            emb_item = {
                'id': f"emb_{idx+1}",
                'nombre': nombre,
                'region': region,
                'comuna': comuna,
                'altura_muro_m': altura,
                'uso': uso,
                'tamano': tamano,
                'ano_construccion': str(ano),
                'monitoreo_dga': 'Monitoreo DGA' in monitoreo,
                'coordenadas': [round(lat, 6), round(lon, 6)]
            }
            embalses_list.append(emb_item)
            
    out_file = os.path.join(DATA_DIR, 'embalses_oficiales_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(embalses_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardados {len(embalses_list)} Embalses Oficiales en {out_file}")
    return embalses_list

def process_decretos_escasez() -> List[Dict[str, Any]]:
    xls_path = os.path.join(RAW_DIR, 'decretos_escasez_historico.xls')
    print(f"Procesando Decretos de Escasez desde {xls_path}...")
    df = pd.read_excel(xls_path)
    
    # Identificar columna año
    col_ano = [c for c in df.columns if 'A' in c and 'o' in c][0]
    col_reg = [c for c in df.columns if 'Reg' in c][0]
    col_dec = [c for c in df.columns if 'Dec' in c][0]
    col_cad = [c for c in df.columns if 'Caducidad' in c][0]
    col_cober = [c for c in df.columns if 'Cuenca' in c or 'Comuna' in c][0]

    # Filtrar filas que repiten nombres de cabecera
    df = df[df[col_dec].notna()]
    df = df[df[col_dec].astype(str).str.strip().str.lower() != 'decreto']
    
    # Forward fill para columnas agrupadas como 'Año' y 'Región'
    df[col_ano] = df[col_ano].replace(to_replace=r'[^0-9]', value=None, regex=True)
    df[col_ano] = df[col_ano].ffill()
    df[col_reg] = df[col_reg].ffill()
    
    decretos_list = []
    for idx, row in df.iterrows():
        decreto_num = clean_val(row.get(col_dec))
        if not decreto_num or decreto_num.lower() == 'decreto':
            continue
        try:
            ano = int(float(str(row.get(col_ano) or 2024)))
        except (ValueError, TypeError):
            ano = 2024
            
        region = clean_val(row.get(col_reg))
        caducidad = clean_val(row.get(col_cad))
        cobertura = clean_val(row.get(col_cober))
        
        # Vigencia (caducidad en 2025, 2026, 2027)
        cad_str = str(caducidad)
        es_vigente = any(yr in cad_str for yr in ['2025', '2026', '2027'])
            
        dec_item = {
            'id': f"dec_escasez_{ano}_{idx+1}",
            'decreto': decreto_num,
            'ano': ano,
            'region': region,
            'fecha_caducidad': cad_str,
            'cobertura_territorial': cobertura,
            'es_vigente': es_vigente
        }
        decretos_list.append(dec_item)
        
    out_file = os.path.join(DATA_DIR, 'decretos_escasez_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(decretos_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardados {len(decretos_list)} Decretos de Escasez en {out_file}")
    return decretos_list

def process_agotamiento() -> List[Dict[str, Any]]:
    xls_path = os.path.join(RAW_DIR, 'declaracion_agotamiento.xls')
    print(f"Procesando Declaraciones de Agotamiento desde {xls_path}...")
    df = pd.read_excel(xls_path, skiprows=5)
    agot_list = []
    for idx, row in df.iterrows():
        nombre = clean_val(row.iloc[1] if len(row) > 1 else "")
        if not nombre or 'nombre' in nombre.lower():
            continue
        region = clean_val(row.iloc[2] if len(row) > 2 else "")
        resolucion = clean_val(row.iloc[3] if len(row) > 3 else "")
        fecha_res = clean_val(row.iloc[4] if len(row) > 4 else "")
        tipo = clean_val(row.iloc[5] if len(row) > 5 else "DECLARACION DE AGOTAMIENTO")
        publicacion = clean_val(row.iloc[7] if len(row) > 7 else "")
        
        item = {
            'id': f"agot_{idx+1}",
            'fuente_superficial': nombre,
            'region': region,
            'resolucion_dga': resolucion,
            'fecha_resolucion': str(fecha_res),
            'tipo': tipo,
            'fecha_publicacion': str(publicacion)
        }
        agot_list.append(item)
        
    out_file = os.path.join(DATA_DIR, 'declaraciones_agotamiento_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(agot_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardadas {len(agot_list)} Declaraciones de Agotamiento en {out_file}")
    return agot_list

def process_zonas_prohibicion() -> List[Dict[str, Any]]:
    xlsx_path = os.path.join(RAW_DIR, 'zonas_prohibicion.xlsx')
    print(f"Procesando Zonas de Prohibición desde {xlsx_path}...")
    df = pd.read_excel(xlsx_path, skiprows=7)
    zp_list = []
    for idx, row in df.iterrows():
        shac_nombre = clean_val(row.iloc[2] if len(row) > 2 else "")
        if not shac_nombre or 'sector' in shac_nombre.lower():
            continue
        region = clean_val(row.iloc[14] if len(row) > 14 else (row.iloc[0] if len(row) > 0 else ""))
        tipo_lim = clean_val(row.iloc[3] if len(row) > 3 else "ZONA DE PROHIBICION")
        res_dga = clean_val(row.iloc[4] if len(row) > 4 else "")
        fecha_res = clean_val(row.iloc[5] if len(row) > 5 else "")
        fecha_pub = clean_val(row.iloc[7] if len(row) > 7 else "")
        
        item = {
            'id': f"zp_{idx+1}",
            'shac': shac_nombre,
            'region': region,
            'tipo_limitacion': tipo_lim,
            'resolucion_dga': res_dga,
            'fecha_resolucion': str(fecha_res),
            'fecha_publicacion_do': str(fecha_pub)
        }
        zp_list.append(item)
        
    out_file = os.path.join(DATA_DIR, 'zonas_prohibicion_chile.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(zp_list, f, indent=2, ensure_ascii=False)
    print(f" -> Guardadas {len(zp_list)} Zonas de Prohibición en {out_file}")
    return zp_list

if __name__ == '__main__':
    print("Iniciando procesamiento masivo de datos oficiales DGA...")
    shacs = process_shac()
    bna = process_red_bna()
    embalses = process_embalses()
    decretos = process_decretos_escasez()
    agot = process_agotamiento()
    zp = process_zonas_prohibicion()
    print("\nPROCESAMIENTO OFICIAL EXITOSO:")
    print(f" - SHACs (Acuíferos): {len(shacs)}")
    print(f" - Estaciones BNA: {len(bna)}")
    print(f" - Embalses DGA/DOH: {len(embalses)}")
    print(f" - Decretos de Escasez: {len(decretos)}")
    print(f" - Declaraciones Agotamiento Superficial: {len(agot)}")
    print(f" - Zonas de Prohibición Subterránea: {len(zp)}")
