import json
import sqlite3
from pathlib import Path

DB_PATH = Path("tmg_atlas.db")
SHAPEFILES_DIR = Path("shapefiles")

# Line and polygon categories only -- points already came in via lat/lon
GEOMETRY_FILES = [
    "bdr.geojson",
    "nli.geojson",
    "rte.geojson",
    "str.geojson",
    "cou.geojson",
    "ctr.geojson",
    "nhd.geojson",
    "npg.geojson",
]


def migrate_file(cur, filepath):
    if not filepath.exists():
        print(f"Skipping (not found): {filepath.name}")
        return 0, 0, 0

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    updated = 0
    missing = 0
    skipped_points = 0

    for feature in features:
        props = feature.get("properties", {})
        location_id = props.get("locationID", "").strip()
        geometry = feature.get("geometry")

        if not location_id:
            print(f"  Feature with no locationID in {filepath.name}: "
                  f"{props.get('Location/feature name (incl. historical names)')}")
            continue

        # Safety net: never touch point geometry here, regardless of which
        # file it came from -- points are handled only by the original
        # lat/lon migration.
        if props.get("Geometry type", "").strip().lower() == "point":
            print(f"  Skipping point feature found in {filepath.name}: {location_id}")
            skipped_points += 1
            continue

        cur.execute(
            "UPDATE locations SET geometry_geojson = ? WHERE locationID = ?",
            (json.dumps(geometry), location_id)
        )

        if cur.rowcount == 0:
            print(f"  WARNING: {location_id} not found in locations table "
                  f"(from {filepath.name})")
            missing += 1
        else:
            updated += 1

    return updated, missing, skipped_points


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    total_updated = 0
    total_missing = 0
    total_skipped = 0

    for filename in GEOMETRY_FILES:
        filepath = SHAPEFILES_DIR / filename
        print(f"Processing {filename}...")
        updated, missing, skipped = migrate_file(cur, filepath)
        print(f"  Updated {updated}, missing {missing}, skipped points {skipped}.")
        total_updated += updated
        total_missing += missing
        total_skipped += skipped

    conn.commit()
    conn.close()

    print(f"\nDone. Total updated: {total_updated}, "
          f"total missing: {total_missing}, total points skipped: {total_skipped}")


if __name__ == "__main__":
    main()