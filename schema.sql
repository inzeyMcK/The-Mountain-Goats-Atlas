CREATE TABLE songs (
    songID TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    album TEXT,
    release_date INTEGER,
    also_appears_on TEXT,
    original_characters_present TEXT,
    real_life_subjects_present TEXT
);

CREATE TABLE locations (
    locationID TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    geometry_type TEXT,
    geography_type TEXT,
    country TEXT,
    region TEXT,
    state_province TEXT,
    county TEXT,
    city TEXT,
    neighborhood TEXT,
    street_address TEXT,
    notes TEXT,
    source TEXT,
    geometry_geojson TEXT
);

CREATE TABLE song_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    songID TEXT NOT NULL,
    locationID TEXT,
    location_name_as_referenced TEXT,
    location_in_lyrics INTEGER,
    location_in_title INTEGER,
    location_not_explicit INTEGER,
    song_set_in_location INTEGER,
    lyric_or_mention TEXT,
    FOREIGN KEY (songID) REFERENCES songs(songID),
    FOREIGN KEY (locationID) REFERENCES locations(locationID)
);