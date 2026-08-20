import json
import sqlite3
from pathlib import Path

DB_PATH = Path("tmg_atlas.db")


def extract_geometry(data):
    """Accepts a bare geometry, a Feature, or a single-feature FeatureCollection."""
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if len(features) != 1:
            raise ValueError(
                f"Expected exactly 1 feature, found {len(features)}. "
                "Combine multi-part geometry into one MultiPolygon/MultiLineString "
                "feature first (mapshaper -merge-layers or similar), per your usual workflow."
            )
        return features[0]["geometry"]
    if data.get("type") == "Feature":
        return data["geometry"]
    if "coordinates" in data:
        return data
    raise ValueError("Unrecognized GeoJSON structure -- expected a geometry, "
                      "Feature, or single-feature FeatureCollection.")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    location_id = input("locationID (e.g. sta027): ").strip()
    cur.execute("SELECT name FROM locations WHERE locationID = ?", (location_id,))
    row = cur.fetchone()

    if row is None:
        print(f"'{location_id}' doesn't exist yet -- let's create it.")
        name = input("Name: ").strip()
        geometry_type = input("Geometry type (point/line/polygon): ").strip()
        geography_type = input("Geography type (e.g. country, county, feature): ").strip()
        country = input("Country: ").strip()
        region = input("Region: ").strip()
        state_province = input("State/Province: ").strip()
        county = input("County: ").strip()
        city = input("City: ").strip()
        neighborhood = input("Neighborhood: ").strip()
        street_address = input("Street address: ").strip()
        notes = input("Notes: ").strip()
        source = input("Source: ").strip()
    else:
        print(f"Found existing location: {row[0]}")

    geojson_path = input("Path to downloaded GeoJSON file: ").strip()
    with open(geojson_path, encoding="utf-8") as f:
        raw = json.load(f)

    geometry = extract_geometry(raw)
    geometry_text = json.dumps(geometry)

    if row is None:
        cur.execute("""
            INSERT INTO locations (
                locationID, name, geometry_type, geography_type,
                country, region, state_province, county, city, neighborhood,
                street_address, notes, source, geometry_geojson
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location_id, name, geometry_type, geography_type,
            country, region, state_province, county, city, neighborhood,
            street_address, notes, source, geometry_text,
        ))
        print(f"Inserted new location '{location_id}'.")
    else:
        cur.execute(
            "UPDATE locations SET geometry_geojson = ? WHERE locationID = ?",
            (geometry_text, location_id)
        )
        print(f"Updated geometry for '{location_id}'.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()