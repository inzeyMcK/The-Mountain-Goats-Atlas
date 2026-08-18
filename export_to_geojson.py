import json
import re
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path("tmg_atlas.db")
SHAPEFILES_DIR = Path("shapefiles")

PREFIX_TO_FILENAME = {
    "adr": "adr.geojson",
    "bdr": "bdr.geojson",
    "cou": "cou.geojson",
    "ctr": "ctr.geojson",
    "cty": "cty.geojson",
    "nhd": "nhd.geojson",
    "nli": "nli.geojson",
    "npg": "npg.geojson",
    "npt": "npt.geojson",
    "rgn": "rgn.geojson",
    "rte": "rte.geojson",
    "sta": "sta.geojson",
    "str": "str.geojson",
}


def get_prefix(location_id):
    match = re.match(r"[a-z]+", location_id)
    return match.group() if match else None


def build_albums_list(album, also_appears_on):
    albums = []
    if album:
        albums.append(album)
    if also_appears_on:
        for part in also_appears_on.split(","):
            part = part.strip()
            if part and part not in albums:
                albums.append(part)
    return albums


def build_properties(row):
    (location_id, name, geometry_type, geography_type, country, region,
     state_province, county, city, neighborhood, street_address, notes, source) = row
    return {
        "locationID": location_id,
        "Location/feature name (incl. historical names)": name or "",
        "Geometry type": geometry_type or "",
        "Geography type": geography_type or "",
        "Country": country or "",
        "Region": region or "",
        "State/Province": state_province or "",
        "County": county or "",
        "City": city or "",
        "Neighborhood (incl. boroughs)": neighborhood or "",
        "Street address": street_address or "",
        "Notes": notes or "",
        "Source": source or "",
    }


def build_songs_for_location(cur, location_id):
    cur.execute("""
        SELECT s.title, s.album, s.also_appears_on, sl.lyric_or_mention
        FROM song_locations sl
        JOIN songs s ON sl.songID = s.songID
        WHERE sl.locationID = ?
    """, (location_id,))

    songs = []
    for title, album, also_appears_on, lyric in cur.fetchall():
        songs.append({
            "title": title or "",
            "album": album or "",
            "albums": build_albums_list(album, also_appears_on),
            "lyric": lyric or "",
        })
    return songs


def backup_existing_shapefiles():
    if not SHAPEFILES_DIR.exists():
        print("No existing shapefiles/ folder found -- skipping backup.")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"shapefiles_backup_{timestamp}")
    shutil.copytree(SHAPEFILES_DIR, backup_dir)
    print(f"Backed up existing shapefiles/ to {backup_dir}/")


def main():
    print("Running from:", Path.cwd())
    print("Using db:", DB_PATH.resolve(), "-- exists:", DB_PATH.exists())

    backup_existing_shapefiles()
    SHAPEFILES_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT locationID, name, geometry_type, geography_type, country, region,
               state_province, county, city, neighborhood, street_address, notes,
               source, geometry_geojson
        FROM locations
        ORDER BY locationID
    """)
    all_locations = cur.fetchall()

    features_by_file = {filename: [] for filename in PREFIX_TO_FILENAME.values()}
    skipped_no_geometry = []
    skipped_unknown_prefix = []
    skipped_bad_geometry = []

    for row in all_locations:
        location_id = row[0]
        geometry_geojson = row[-1]
        prefix = get_prefix(location_id)

        if prefix not in PREFIX_TO_FILENAME:
            skipped_unknown_prefix.append(location_id)
            continue

        # Treat NULL, empty string, or whitespace-only as "no geometry yet"
        if not geometry_geojson or not geometry_geojson.strip():
            skipped_no_geometry.append(location_id)
            continue

        try:
            geometry = json.loads(geometry_geojson)
        except json.JSONDecodeError as e:
            skipped_bad_geometry.append((location_id, str(e)))
            continue

        properties = build_properties(row[:-1])
        properties["songs"] = build_songs_for_location(cur, location_id)

        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry,
        }

        features_by_file[PREFIX_TO_FILENAME[prefix]].append(feature)

    for filename, features in features_by_file.items():
        out_path = SHAPEFILES_DIR / filename
        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, indent="\t")
        print(f"{filename}: wrote {len(features)} features")

    if skipped_no_geometry:
        print(f"\nSkipped {len(skipped_no_geometry)} location(s) with no geometry yet:")
        for lid in skipped_no_geometry:
            print(f"  {lid}")

    if skipped_bad_geometry:
        print(f"\nSkipped {len(skipped_bad_geometry)} location(s) with MALFORMED geometry_geojson "
              f"(fix these in DB Browser):")
        for lid, err in skipped_bad_geometry:
            print(f"  {lid}: {err}")

    if skipped_unknown_prefix:
        print(f"\nSkipped {len(skipped_unknown_prefix)} location(s) with an unrecognized ID prefix:")
        for lid in skipped_unknown_prefix:
            print(f"  {lid}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()