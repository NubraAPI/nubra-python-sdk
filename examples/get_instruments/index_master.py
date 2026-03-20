import requests
import csv
from io import StringIO

INDEX_URL = "https://api.nubra.io/public/indexes?format=csv"

def fetch_indices_master():
    response = requests.get(INDEX_URL, timeout=10)
    response.raise_for_status()

    csv_buffer = StringIO(response.text)
    reader = csv.DictReader(csv_buffer)
    return list(reader)

indices = fetch_indices_master()
print(f"Total indices fetched: {len(indices)}")
print(indices)
