import os
import json
import requests

BASE_URL = "https://terminology.hl7.org"
TABLES_INDEX = f"{BASE_URL}/2.0.0/CodeSystem-v2-tables.json"
STATIC_DIR = "app/static"  # adjust path as needed

def download_all_tables():
    # Ensure static directory exists
    os.makedirs(STATIC_DIR, exist_ok=True)

    print(f"Fetching table index from {TABLES_INDEX}...")
    resp = requests.get(TABLES_INDEX)
    resp.raise_for_status()
    tables_data = resp.json()

    top_concepts = tables_data.get("concept", [])
    print(f"Found {len(top_concepts)} tables in index.")

    for table in top_concepts:
        table_id = table.get("code")
        if not table_id:
            continue

        table_url = f"{BASE_URL}/CodeSystem-v2-{table_id}.json"
        out_path = os.path.join(STATIC_DIR, f"CodeSystem-v2-{table_id}.json")

        # Skip if already exists
        if os.path.exists(out_path):
            print(f"[SKIP] {table_id} already exists.")
            continue

        try:
            print(f"Downloading {table_url}...")
            r = requests.get(table_url)
            r.raise_for_status()
            with open(out_path, "w") as f:
                f.write(r.text)
        except Exception as e:
            print(f"[WARN] Failed to download {table_url}: {e}")

    print("Download complete!")

if __name__ == "__main__":
    download_all_tables()
