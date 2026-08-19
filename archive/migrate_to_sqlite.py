import json
import sqlite3
from pathlib import Path

DB_PATH = Path("tmg_atlas.db")
LOCATIONS_JSON = Path("locationIDs.json")
JUNCTION_JSON = Path("songLocation_junction.json")
SCHEMA_SQL = Path("schema.sql")


def to_bool_or_none(value):
    """Junction booleans arrive as True, False, or '' (blank = unknown/not applicable)."""
    if value is True:
        return 1
    if value is False:
        return 0
    return None


def main():
    # Safe to re-run after fixing source data -- always starts from a clean db
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL.read_text())

    # --- locations ---
    with open(LOCATIONS_JSON, encoding="utf-8") as f:
        locations = json.load(f)

    for loc in locations:
        location_id = loc.get("locationID", "").strip()
        if not location_id:
            print(f"Skipping location with no locationID: "
                  f"{loc.get('Location/feature name (incl. historical names)')}")
            continue

        lat_raw = loc.get("Latitude", "")
        lon_raw = loc.get("Longitude", "")
        geometry_geojson = None
        if str(lat_raw).strip() and str(lon_raw).strip():
            lat = float(lat_raw)
            lon = float(lon_raw)
            geometry_geojson = json.dumps({
                "type": "Point",
                "coordinates": [lon, lat]   # GeoJSON order: longitude first, then latitude
            })
        # Lines/polygons stay None here -- filled in during the shapefile migration step

        cur.execute("""
            INSERT INTO locations (
                locationID, name, geometry_type, geography_type,
                country, region, state_province, county, city, neighborhood,
                street_address, notes, source, geometry_geojson
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location_id,
            loc.get("Location/feature name (incl. historical names)", "").strip(),
            loc.get("Geometry type", "").strip(),
            loc.get("Geography type", "").strip(),
            loc.get("Country", "").strip(),
            loc.get("Region", "").strip(),
            loc.get("State/Province", "").strip(),
            loc.get("County", "").strip(),
            loc.get("City", "").strip(),
            loc.get("Neighborhood (incl. boroughs)", "").strip(),
            loc.get("Street address", "").strip(),
            loc.get("Notes", "").strip(),
            loc.get("Source", "").strip(),
            geometry_geojson,
        ))

    print(f"Loaded {len(locations)} locations.")

    # --- songs, derived from the junction file ---
    with open(JUNCTION_JSON, encoding="utf-8") as f:
        junction = json.load(f)

    seen_songs = {}

    for row in junction:
        song_id = row["songID"]
        song_fields = {
            "title": row.get("Song title", "").strip(),
            "album": row.get("Album", "").strip(),
            "release_date": row.get("Release date") or None,
            "also_appears_on": row.get("Also appears on", "").strip(),
            "original_characters_present": row.get("Original characters present", "").strip(),
            "real_life_subjects_present": row.get("Real life subjects present", "").strip(),
        }

        if song_id not in seen_songs:
            seen_songs[song_id] = song_fields
        else:
            # If these ever disagree across rows for the same song, they're NOT
            # purely song-level, and this table split needs rethinking.
            for key, value in song_fields.items():
                if seen_songs[song_id][key] != value:
                    print(f"MISMATCH for {song_id} ({song_fields['title']}), "
                          f"field '{key}': '{seen_songs[song_id][key]}' vs '{value}'")

    for song_id, fields in seen_songs.items():
        cur.execute("""
            INSERT INTO songs (songID, title, album, release_date, also_appears_on,
                                original_characters_present, real_life_subjects_present)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            song_id, fields["title"], fields["album"], fields["release_date"],
            fields["also_appears_on"], fields["original_characters_present"],
            fields["real_life_subjects_present"],
        ))

    print(f"Loaded {len(seen_songs)} unique songs.")

    # --- song_locations (the real junction rows) ---
    known_location_ids = {loc.get("locationID", "").strip() for loc in locations}

    for row in junction:
        location_id = row.get("locationID", "").strip()
        if location_id and location_id not in known_location_ids:
            print(f"WARNING: unknown locationID '{location_id}' referenced by "
                  f"song '{row.get('Song title')}'")

        cur.execute("""
            INSERT INTO song_locations (
                songID, locationID, location_name_as_referenced,
                location_in_lyrics, location_in_title, location_not_explicit,
                song_set_in_location, lyric_or_mention
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["songID"],
            location_id or None,
            row.get("Location name (as referenced in song)", "").strip(),
            to_bool_or_none(row.get("Location in lyrics")),
            to_bool_or_none(row.get("Location in title")),
            to_bool_or_none(row.get("Location not explicit")),
            to_bool_or_none(row.get("Song set in location")),
            row.get("Lyric and/or mention", "").strip(),
        ))

    print(f"Loaded {len(junction)} song_locations rows.")

    conn.commit()
    conn.close()
    print(f"Done. Database written to {DB_PATH}")


if __name__ == "__main__":
    main()