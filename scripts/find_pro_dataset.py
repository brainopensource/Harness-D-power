import urllib.request
import json

for ds in ["ScaleAI/SWE-bench_Pro", "SWE-bench/SWE-bench", "princeton-nlp/SWE-bench"]:
    url = f"https://datasets-server.huggingface.co/rows?dataset={ds}&config=default&split=test&offset=0&length=5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            print(f"[SUCCESS] {ds}: fetched {len(data.get('rows', []))} rows")
            rows = data.get("rows", [])
            if rows:
                print("Keys:", list(rows[0]["row"].keys())[:8])
    except Exception as e:
        print(f"[FAIL] {ds}: {e}")
