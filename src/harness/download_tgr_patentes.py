import os
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://datos.gob.cl/dataset/9eb1f7c2-0b53-4c00-9a28-e2275012bf82/resource/4d1d615f-5935-4760-b399-1dd76b281715/download/tb_patentes_aguas_december_2025_data.csv"
target_dir = os.path.join(os.getcwd(), "data", "dga_raw")
os.makedirs(target_dir, exist_ok=True)
target_file = os.path.join(target_dir, "tgr_patentes_aguas_2025.csv")

print(f"Descargando nómina oficial de Patentes de Aguas TGR desde:\n{url}")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

try:
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        with open(target_file, "wb") as f_out:
            total_bytes = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f_out.write(chunk)
                total_bytes += len(chunk)
                if total_bytes % (1024 * 1024) < 65536:
                    print(f" -> Descargados {total_bytes / (1024*1024):.2f} MB...")
            print(f"\nDescarga finalizada con éxito: {total_bytes} bytes ({total_bytes / (1024*1024):.2f} MB)")
            print(f"Guardado en: {target_file}")
except Exception as e:
    print(f"Error descargando patentes TGR: {e}")
