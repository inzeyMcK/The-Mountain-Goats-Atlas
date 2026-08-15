"""
Merge songs into locations

Attaches song references onto each location feature's properties.songs, for every geojson file in shapefiles/.

USAGE:
    python merge_songs_into_locations.py

Expects this folder layout:
    songLocation_junction.json
    shapefiles/
        adr.geojson
        bdr.geojson
        ...

        Writes merged files into a new "shapefiles_merged/" folder.
        Original files are not modified.
"""

import json
import os
from pickle import TRUE

JUNCTION_FILE = "songLocation_junction.json"
SHAPEFILES_DIR = "shapefiles"
OUTPUT_DIR = "shapefiles_merged"

def load_junction_table(path):
    with open(path, "r") as f:
        return json.load(f)

def build_location_lookup(junction_rows):
    lookup = {}
    skipped = 0

    for row in junction_rows:
        loc_id = row.get("locationID", "").strip()
        if not loc_id:
            skipped += 1
            continue
        lookup.setdefault(loc_id, []).append(row)

    print(f" Skipped{skipped} junction row(s) with no locationID (expected -- unresolved references).")
    return lookup

def build_albums_list(row):
    albums = []

    primary = row.get("Album", "").strip()
    if primary:
        albums.append(primary)

    also = row.get("Also Appears On", "").strip()
    if also:
        for part in also.split(","):
            part = part.strip()
            if part and part not in albums:
                albums.append(part)
    return albums

def build_song_entry(row):
    return{
        "title": row.get("Song title", ""),
        "album": row.get("Album", ""),
        "albums": build_albums_list(row),
        "lyric": row.get("Lyric and/or mention", "")
    }

def merge_file(filename, location_lookup):
    in_path = os.path.join(SHAPEFILES_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename)

    with open(in_path, "r") as f:
        data = json.load(f)

    matched_feature_count = 0

    for feature in data.get("features", []):
        loc_id = feature["properties"].get("locationID", "")
        matching_rows = location_lookup.get(loc_id, [])

        songs = [build_song_entry(row) for row in matching_rows]
        feature["properties"]["songs"] = songs

        if songs:
            matched_feature_count += 1
    os.makedirs(OUTPUT_DIR, exist_ok=TRUE)
    with open(out_path, "w") as f:
        json.dump(data, f, indent="\t")

    total_features = len(data.get("features", []))
    print(f" {filename}: {matched_feature_count}/{total_features} features got at least 1 song")

def main():
    print("Loading junction table...")
    junction_rows = load_junction_table(JUNCTION_FILE)
    print(f" Loaded {len(junction_rows)} junction rows.")

    print("\nBuilding location lookup...")
    location_lookup = build_location_lookup(junction_rows)

    print(f"\nMerging songs into every file in {SHAPEFILES_DIR}/ ...")
    geojson_files = sorted(f for f in os.listdir(SHAPEFILES_DIR) if f.endswith(".geojson"))

    for filename in geojson_files:
        merge_file(filename, location_lookup)

    print(f"\nDone! Merged files written to {OUTPUT_DIR}/ -- review before replacing your originals.")

if __name__ == "__main__":
    main()