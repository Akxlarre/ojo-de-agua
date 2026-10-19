import urllib.request
import json
import ssl

ctx = ssl._create_unverified_context()
url = "https://ide-energia.minenergia.cl/server/rest/services/IDE_Energia/Visor_IDE_Energ%C3%ADa/MapServer/6/query?where=1%3D1&outFields=*&f=geojson"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        features = data.get("features", [])
        print(f"Total Centrales Hidroeléctricas fetched: {len(features)}")
        if features:
            print("Sample feature properties:", json.dumps(features[0]["properties"], indent=2, ensure_ascii=False))
            print("Sample coordinates:", features[0]["geometry"]["coordinates"])
            with open("data/dga_raw/cne_centrales_hidroelectricas.geojson", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("Saved to data/dga_raw/cne_centrales_hidroelectricas.geojson")
except Exception as e:
    print("Error:", e)
