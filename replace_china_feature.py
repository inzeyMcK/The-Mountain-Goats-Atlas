"""
replace_china_feature.py

Replaces the ctr005 (Imperial China) feature inside ctr.geojson with the
corrected, dissolved version -- without needing to hand-edit a 21MB file
in a text editor.

USAGE:
    Run this from your repo root (same folder as shapefiles/):
    python3 replace_china_feature.py

Expects:
    shapefiles/ctr.geojson          <- your current file (has the broken China)
    ctr005_final.geojson            <- the corrected feature (download this
                                        from the chat and place it in the
                                        same folder as this script)

Writes:
    shapefiles/ctr.geojson          <- updated in place, with China fixed

A backup of the original is saved as shapefiles/ctr_before_china_fix.geojson,
just in case.
"""

import json
import shutil

CTR_FILE = "shapefiles/ctr.geojson"
REPLACEMENT_FILE = "ctr005_final.geojson"
BACKUP_FILE = "shapefiles/ctr_before_china_fix.geojson"
TARGET_LOCATION_ID = "ctr005"


def main():
    print(f"Backing up {CTR_FILE} to {BACKUP_FILE} first...")
    shutil.copy(CTR_FILE, BACKUP_FILE)

    print(f"Loading {CTR_FILE}...")
    with open(CTR_FILE, "r") as f:
        ctr_data = json.load(f)

    print(f"Loading corrected feature from {REPLACEMENT_FILE}...")
    with open(REPLACEMENT_FILE, "r") as f:
        replacement_feature = json.load(f)

    found = False
    for i, feature in enumerate(ctr_data["features"]):
        if feature["properties"].get("locationID") == TARGET_LOCATION_ID:
            ctr_data["features"][i] = replacement_feature
            found = True
            print(f"Found and replaced {TARGET_LOCATION_ID} at position {i}.")
            break

    if not found:
        print(f"ERROR: Could not find a feature with locationID = {TARGET_LOCATION_ID}")
        print("Nothing was changed. Check that your ctr.geojson still has this feature.")
        return

    print(f"Writing updated {CTR_FILE}...")
    with open(CTR_FILE, "w") as f:
        # Written compactly (no indent) rather than pretty-printed --
        # this file is already too large to comfortably hand-read or
        # edit in GitHub's browser view, so pretty-printing just adds
        # bytes without adding real readability.
        json.dump(ctr_data, f, separators=(",", ":"))

    print("\nDone. ctr.geojson has been updated with the corrected China geometry.")
    print(f"Your original file is safely backed up at {BACKUP_FILE} if you need to compare or revert.")


if __name__ == "__main__":
    main()
