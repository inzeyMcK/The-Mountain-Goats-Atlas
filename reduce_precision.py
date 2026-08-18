import json
import sqlite3
from pathlib import Path

DB_PATH = Path("tmg_atlas.db")
DECIMAL_PLACES = 5  # ~1 meter accuracy


def round_coordinates(coords, places):
    if isinstance(coords, (int, float)):
        return round(coords, places)
    if isinstance(coords, list):
        return [round_coordinates(c, places) for c in coords]
    return coords


def unwrap_geometry(obj):
    """Handles cases where a full Feature or FeatureCollection got pasted in
    instead of a bare geometry object. Returns (geometry, was_wrapped)."""
    if not isinstance(obj, dict):
        return None, False

    if "coordinates" in obj:
        return obj, False

    obj_type = obj.get("type")

    if obj_type == "Feature":
        return obj.get("geometry"), True

    if obj_type == "FeatureCollection":
        features = obj.get("features", [])
        if len(features) == 1:
            return features[0].get("geometry"), True
        return None, True  # multiple features -- too ambiguous to auto-fix

    return None, False


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT locationID, name, geometry_geojson
        FROM locations
        WHERE geometry_geojson IS NOT NULL
    """)
    rows = cur.fetchall()

    total_before = 0
    total_after = 0
    updated = 0
    problems = []

    for location_id, name, geometry_text in rows:
        before_size = len(geometry_text)

        try:
            parsed = json.loads(geometry_text)
        except json.JSONDecodeError as e:
            problems.append((location_id, name, f"invalid JSON: {e}"))
            continue

        geometry, was_wrapped = unwrap_geometry(parsed)

        if geometry is None or "coordinates" not in geometry:
            found_type = parsed.get("type") if isinstance(parsed, dict) else type(parsed).__name__
            problems.append((location_id, name, f"no usable geometry found (top-level type: {found_type})"))
            continue

        geometry["coordinates"] = round_coordinates(geometry["coordinates"], DECIMAL_PLACES)
        new_text = json.dumps(geometry)
        after_size = len(new_text)

        cur.execute(
            "UPDATE locations SET geometry_geojson = ? WHERE locationID = ?",
            (new_text, location_id)
        )
        conn.commit()  # save immediately -- a later crash can't undo this row anymore

        saved = before_size - after_size
        flag = " [was wrapped in Feature/FeatureCollection -- unwrapped]" if was_wrapped else ""
        if saved > 1000 or was_wrapped:
            print(f"{location_id} ({name}): {before_size:,} -> {after_size:,} bytes "
                  f"(saved {saved:,}){flag}")

        total_before += before_size
        total_after += after_size
        updated += 1

    conn.close()

    print(f"\nUpdated {updated} geometries.")
    print(f"Total: {total_before:,} -> {total_after:,} bytes "
          f"(saved {total_before - total_after:,}, "
          f"{100 * (total_before - total_after) / max(total_before,1):.1f}%)")

    if problems:
        print(f"\n{len(problems)} row(s) NOT updated -- need a look:")
        for lid, name, reason in problems:
            print(f"  {lid} ({name}): {reason}")

    print("\nOnce done: DB Browser -> Execute SQL -> run VACUUM; -> save, to shrink the file on disk.")


if __name__ == "__main__":
    main()