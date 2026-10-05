"""Inspect local official CSV assets. Does not fetch, import rules, or generate layouts."""

import argparse
import csv
import hashlib
import io
import json
import lzma
from pathlib import Path


def decode(raw):
    if raw.startswith(b"Sig:"):
        payload = raw[68:]
        return lzma.decompress(payload[:9] + b"\0" * 4 + payload[9:],
                               format=lzma.FORMAT_ALONE, memlimit=64_000_000)
    return raw


def inspect(path):
    raw = Path(path).read_bytes()
    rows = list(csv.DictReader(io.StringIO(decode(raw).decode("utf-8"))))[1:]
    entities, current, inherited = {}, None, {}
    for row in rows:
        if row["Name"]:
            current = row["Name"]
            inherited = {}
            entities[current] = []
        inherited.update({k:v for k,v in row.items() if v != ""})
        entities[current].append({k:v for k,v in inherited.items() if k in
            {"Name", "GlobalID", "Width", "Height", "BuildingLevel", "Level", "TownHallLevel", "MergeRequirement"}})
    return {"file": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest(), "entities": entities}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--name", help="Show only a named entity")
    args = parser.parse_args()
    result = inspect(args.file)
    if args.name:
        result["entities"] = {args.name: result["entities"].get(args.name, [])}
    print(json.dumps(result, indent=2))
