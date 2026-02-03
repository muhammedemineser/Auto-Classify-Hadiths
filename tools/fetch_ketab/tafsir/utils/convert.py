#!/usr/bin/env python3
import json

INPUT = "data/gefiltert.json"
OUTPUT = "data/gefiltert.ndjson"

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(OUTPUT, "w", encoding="utf-8") as out:
    for i, block in enumerate(data["blocks"], 1):
        out.write(json.dumps({"id": i, "text": block}, ensure_ascii=False) + "\n")

print("✅ written:", OUTPUT)
