import urllib.request
import ssl
import os
import zipfile

ctx = ssl._create_unverified_context()
url = "https://lineasdebasepublicas.mma.gob.cl/datos_abiertos/dataset/6f95dcf8-51fd-474c-b34e-79521e50a4cf/resource/cd03641d-ef56-4ab2-876e-4c19b1ebbcf1/download/humedales-urbanos_geojson.zip"
dest = "data/dga_raw/mma_humedales_urbanos_geojson.zip"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp, open(dest, "wb") as f:
        data = resp.read()
        f.write(data)
        print("Downloaded MMA Humedales:", len(data), "bytes")
    
    with zipfile.ZipFile(dest, "r") as z:
        print("Zip files:", z.namelist())
except Exception as e:
    print("Error:", e)
