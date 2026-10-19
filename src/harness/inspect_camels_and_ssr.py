import os
import sys
import pandas as pd

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

raw_dir = os.path.join(os.getcwd(), 'data', 'dga_raw')

print("=== 1. CAMELS-CL ATRIBUTOS HIDROLÓGICOS (CR2) ===")
camels_path = os.path.join(raw_dir, 'camels_cl', '1_CAMELScl_attributes.txt')
if os.path.exists(camels_path):
    # Check separator (tab or semicolon or comma)
    with open(camels_path, 'r', encoding='utf-8') as f:
        head = [f.readline() for _ in range(5)]
    print(f"Header preview:\n{head[0][:150]}...")
    
    # Try tab separated
    df_camels = pd.read_csv(camels_path, sep=r'\s+', engine='python') if '\t' not in head[0] else pd.read_csv(camels_path, sep='\t')
    print(f"CAMELS-CL Shape: {df_camels.shape}")
    print(f"Columns ({len(df_camels.columns)}): {df_camels.columns.tolist()[:15]}...")
    print(df_camels.head(3).iloc[:, :8])

print("\n=== 2. DOH MOP - SISTEMAS SANITARIOS RURALES (SSR / APR) ===")
ssr_path = os.path.join(raw_dir, 'base_ssr.xlsx')
if os.path.exists(ssr_path):
    df_ssr = pd.read_excel(ssr_path)
    print(f"SSR Shape: {df_ssr.shape}")
    print(f"Columns ({len(df_ssr.columns)}): {df_ssr.columns.tolist()}")
    print(df_ssr.head(3))

print("\n=== 3. COOPERATIVAS DE AGUA POTABLE ===")
coop_path = os.path.join(raw_dir, 'cooperativas_agua_potable.csv')
if os.path.exists(coop_path):
    df_coop = pd.read_csv(coop_path, sep=';', encoding='latin1')
    print(f"Cooperativas Shape: {df_coop.shape}")
    print(f"Columns: {df_coop.columns.tolist()}")
    print(df_coop.head(3))
