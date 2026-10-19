import os
import shapefile
import pandas as pd

base = os.path.join(os.getcwd(), 'data', 'dga_raw')

print("=== 1. SHAC / ACUÍFEROS ===")
shac_path = os.path.join(base, 'shac', 'Acuiferos_SHAC', 'INV_ACUIFEROS_SHAC.shp')
with shapefile.Reader(shac_path, encoding='latin1') as sf:
    print(f"Total SHAC shapes: {len(sf)}")
    fields = [f[0] for f in sf.fields[1:]]
    print(f"Fields: {fields}")
    for i in range(min(5, len(sf))):
        rec = sf.record(i).as_dict()
        print(f" Record {i+1}: {rec}")

print("\n=== 2. RED HIDROMÉTRICA NACIONAL (BNA) ===")
bna_path = os.path.join(base, 'red_bna', 'Red_Hidrometrica_Nacional', 'Red_Hidrometrica_Nacional.shp')
with shapefile.Reader(bna_path, encoding='latin1') as sf:
    print(f"Total BNA stations: {len(sf)}")
    fields = [f[0] for f in sf.fields[1:]]
    print(f"Fields: {fields}")
    for i in range(min(5, len(sf))):
        rec = sf.record(i).as_dict()
        print(f" Record {i+1}: {rec}")

print("\n=== 3. EMBALSES DGA / DOH ===")
emb_path = os.path.join(base, 'embalses', 'Inventario_de_Embalses', 'Inv_Embalses_DGA_DOH.shp')
with shapefile.Reader(emb_path, encoding='latin1') as sf:
    print(f"Total Embalses: {len(sf)}")
    fields = [f[0] for f in sf.fields[1:]]
    print(f"Fields: {fields}")
    for i in range(min(5, len(sf))):
        rec = sf.record(i).as_dict()
        print(f" Record {i+1}: {rec}")

print("\n=== 4. EXCEL DECRETOS ESCASEZ ===")
esc_path = os.path.join(base, 'decretos_escasez_historico.xls')
try:
    df_esc = pd.read_excel(esc_path)
    print("Columns:", df_esc.columns.tolist())
    print("Shape:", df_esc.shape)
    print(df_esc.head(3))
except Exception as e:
    print("Error reading excel decretos:", e)

print("\n=== 5. EXCEL ZONAS PROHIBICIÓN ===")
zp_path = os.path.join(base, 'zonas_prohibicion.xlsx')
try:
    df_zp = pd.read_excel(zp_path)
    print("Columns:", df_zp.columns.tolist())
    print("Shape:", df_zp.shape)
    print(df_zp.head(3))
except Exception as e:
    print("Error reading excel zonas prohibicion:", e)
