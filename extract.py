import sys
import time
import duckdb
import pandas as pd
from lastfm import call_lastfm 

DB_PATH = "music-dashboard/sources/music/warehouse.duckdb"
RATE_LIMIT_DELAY = 0.25  

def get_connection():
    return duckdb.connect(DB_PATH)

def ensure_schema(con):
    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_artist_id START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_track_id START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_scrobble_id START 1;

        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_artist_id'),
            name VARCHAR UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_track_id'),
            artist_id INTEGER REFERENCES artists(id),
            name VARCHAR NOT NULL,
            album_name VARCHAR,
            duration_ms INTEGER,
            global_playcount INTEGER,
            UNIQUE(artist_id, name)
        );     
        
        CREATE TABLE IF NOT EXISTS scrobbles (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_scrobble_id'),
            track_id INTEGER REFERENCES tracks(id),
            timestamp BIGINT,
            is_loved BOOLEAN,
            UNIQUE(track_id, timestamp)
        );
    """)

def load_caches(con):
    """Load existing dimensions into memory using Pandas DataFrames."""
    df_artists = con.execute("SELECT id, name FROM artists").fetchdf()
    df_tracks = con.execute("""
        SELECT t.id, t.name AS track_name, a.name AS artist_name 
        FROM tracks t JOIN artists a ON t.artist_id = a.id
    """).fetchdf()
    
    artist_cache = dict(zip(df_artists['name'], df_artists['id'])) if not df_artists.empty else {}
    
    track_cache = {}
    if not df_tracks.empty:
        for _, row in df_tracks.iterrows():
            track_cache[(row['artist_name'], row['track_name'])] = row['id']
            
    return artist_cache, track_cache

def get_scrobbles(username, from_ts=None, to_ts=None):
    page = 1
    total_pages = 1
    all_scrobbles = []
    
    while page <= total_pages:
        params = {"user": username, "page": page, "limit": 200}
        if from_ts: params["from"] = from_ts
        if to_ts: params["to"] = to_ts
        
        # --- BULLETPROOF RETRY LOGIC ---
        data = None
        max_retries = 5
        for attempt in range(max_retries):
            try:
                data = call_lastfm("user.getRecentTracks", **params)
                break  # Success! Exit retry loop
            except Exception as e:
                print(f"\n  [!] API Timeout/Error on page {page}: {type(e).__name__}")
                if attempt < max_retries - 1:
                    wait_time = 10 * (attempt + 1)
                    print(f"      Last.fm is slow. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print("      Failed after 5 attempts. Saving current progress and stopping.")
                    return all_scrobbles # Returns what we have so far
        # -------------------------------

        if not data or "recenttracks" not in data: break
            
        recenttracks = data["recenttracks"]
        total_pages = int(recenttracks["@attr"]["totalPages"])
        tracks = recenttracks.get("track", [])
        
        print(f"Fetching page {page}/{total_pages} for user '{username}'... (Found {len(tracks)} tracks)")
        
        for t in tracks:
            if t.get("@attr", {}).get("nowplaying") == "true": continue
            
            # ROBUST EXTRACTION: Handles "name", "#text", or raw strings
            artist_obj = t.get("artist", {})
            if isinstance(artist_obj, dict):
                artist_name = artist_obj.get("name") or artist_obj.get("#text")
            else:
                artist_name = str(artist_obj) if artist_obj else None
                
            track_name = t.get("name") or t.get("#text")
            
            # NEW: Extract album name from recent tracks
            album_obj = t.get("album", {})
            if isinstance(album_obj, dict):
                album_name = album_obj.get("#text") or album_obj.get("title")
            else:
                album_name = str(album_obj) if album_obj else None
            
            if not artist_name or not track_name:
                print(f"DEBUG SKIPPED: Missing name. Artist: {artist_name}, Track: {track_name}")
                continue
                
            clean_artist = str(artist_name).strip()
            clean_track = str(track_name).strip()
            clean_album = str(album_name).strip() if album_name else None
            
            if not clean_artist or not clean_track:
                continue
                
            if clean_album == "":
                clean_album = None
                
            timestamp = int(t.get("date", {}).get("uts", 0))
            is_loved = t.get("loved") == "1"
            
            all_scrobbles.append({
                "artist": clean_artist,
                "track": clean_track,
                "album": clean_album,
                "timestamp": timestamp,
                "is_loved": is_loved
            })
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
        
    return all_scrobbles

def resolve_dimensions(con, scrobbles, artist_cache, track_cache):
    """Find new artists/tracks, insert them, and update the cache."""
    new_artists = set()
    new_tracks = set()  
    
    # NEW: Build a map of recent track albums to use as a fallback
    recent_albums = {}
    for s in scrobbles:
        track_key = (s["artist"], s["track"])
        if s.get("album") and track_key not in recent_albums:
            recent_albums[track_key] = s["album"]
    
    # 1. Identify what's missing from our cache
    for s in scrobbles:
        artist = s["artist"]
        track = s["track"]
        
        if artist not in artist_cache:
            new_artists.add(artist)
            
        track_key = (artist, track)
        if track_key not in track_cache:
            new_tracks.add(track_key)  
            
    # 2. Bulk Insert new artists
    if new_artists:
        df_new_artists = pd.DataFrame({"name": list(new_artists)})
        con.execute("INSERT OR IGNORE INTO artists (name) SELECT name FROM df_new_artists")
        
    # 3. Refresh artist cache to get the new IDs DuckDB just generated
    df_artists = con.execute("SELECT id, name FROM artists").fetchdf()
    artist_cache = dict(zip(df_artists['name'], df_artists['id']))
    
    # 4. Fetch metadata for new tracks and bulk insert them
    if new_tracks:
        track_metadata = []
        print(f"Fetching detailed metadata for {len(new_tracks)} UNIQUE new tracks... (This will be MUCH faster!)")
        
        for i, track_key in enumerate(new_tracks):
            artist_name = track_key[0]
            track_name = track_key[1]
            
            if i % 100 == 0 or i == len(new_tracks) - 1:
                print(f"  [{i+1}/{len(new_tracks)}] Fetching: {artist_name} - {track_name}")
            
            # --- RETRY LOGIC FOR TRACK INFO ---
            res = None
            for attempt in range(5):
                try:
                    res = call_lastfm("track.getInfo", artist=artist_name, track=track_name)
                    break
                except Exception:
                    if attempt < 4:
                        time.sleep(5 * (attempt + 1))
                    else:
                        print(f"      [!] Failed to fetch info for {track_name}. Skipping.")
            # ----------------------------------
            
            info = res.get("track", {}) if res else {}
            
            # Extract album from track.getInfo
            album_obj = info.get("album")
            if isinstance(album_obj, dict):
                album_name = album_obj.get("title") or album_obj.get("#text")
            else:
                album_name = None
            
            # NEW: FALLBACK LOGIC
            # If track.getInfo doesn't return an album, use the one from recent tracks
            if not album_name:
                album_name = recent_albums.get(track_key)
            
            duration_str = info.get("duration")
            duration_ms = int(duration_str) if duration_str and str(duration_str).isdigit() else 0
            
            playcount_str = info.get("playcount")
            global_playcount = int(playcount_str) if playcount_str and str(playcount_str).isdigit() else 0

            track_metadata.append({
                "artist_id": artist_cache.get(artist_name),
                "name": track_name,
                "album_name": album_name if album_name else None,
                "duration_ms": duration_ms,
                "global_playcount": global_playcount
            })
            time.sleep(RATE_LIMIT_DELAY)
            
        df_new_tracks = pd.DataFrame(track_metadata)
        df_new_tracks = df_new_tracks.where(pd.notnull(df_new_tracks), None)
        
        con.execute("""
            INSERT OR IGNORE INTO tracks (artist_id, name, album_name, duration_ms, global_playcount) 
            SELECT * FROM df_new_tracks
        """)
        
    # 5. Refresh track cache
    df_tracks = con.execute("""
        SELECT t.id, t.name AS track_name, a.name AS artist_name 
        FROM tracks t JOIN artists a ON t.artist_id = a.id
    """).fetchdf()
    
    track_cache = {}
    for _, row in df_tracks.iterrows():
        track_cache[(row['artist_name'], row['track_name'])] = row['id']
        
    return track_cache

def store_scrobbles(con, scrobbles, track_cache):
    """Map string names to integer IDs and bulk insert."""
    db_scrobbles = []
    for s in scrobbles:
        track_id = track_cache.get((s["artist"], s["track"]))
        if track_id:
            db_scrobbles.append({
                "track_id": track_id,
                "timestamp": s["timestamp"],
                "is_loved": s["is_loved"]
            })
            
    if db_scrobbles:
        df_scrobbles = pd.DataFrame(db_scrobbles)
        con.execute("INSERT OR IGNORE INTO scrobbles (track_id, timestamp, is_loved) SELECT * FROM df_scrobbles")
        return len(df_scrobbles)
    return 0

def parse_duration_to_ms(value):
    """
    Accepts:
      - "mm:ss"
      - "hh:mm:ss"
      - raw milliseconds as a string/int
    """
    value = value.strip()
    if not value:
        return None

    if ":" in value:
        parts = value.split(":")
        try:
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return (minutes * 60 + seconds) * 1000

            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return (hours * 3600 + minutes * 60 + seconds) * 1000

        except ValueError:
            raise ValueError(f"Invalid duration: {value}")

    return int(value)


def get_top_missing_duration_artist(con, rank_by="plays"):
    """
    Returns the artist with the largest missing-duration workload.

    rank_by:
      - "plays": artist whose missing-duration tracks have the most total scrobbles
      - "tracks": artist with the most missing-duration tracks
    """
    if rank_by not in ("plays", "tracks"):
        rank_by = "plays"

    order_by = (
        "total_scrobbles DESC, missing_tracks DESC, a.name"
        if rank_by == "plays"
        else "missing_tracks DESC, total_scrobbles DESC, a.name"
    )

    query = f"""
        WITH missing_tracks AS (
            SELECT
                t.id AS track_id,
                t.artist_id,
                COUNT(s.id) AS scrobble_count
            FROM tracks t
            LEFT JOIN scrobbles s ON s.track_id = t.id
            WHERE t.duration_ms IS NULL OR t.duration_ms = 0
            GROUP BY t.id, t.artist_id
        )
        SELECT
            a.name AS artist_name,
            COUNT(m.track_id) AS missing_tracks,
            COALESCE(SUM(m.scrobble_count), 0) AS total_scrobbles
        FROM missing_tracks m
        JOIN artists a ON a.id = m.artist_id
        GROUP BY a.name
        ORDER BY {order_by}
        LIMIT 1
    """

    df = con.execute(query).fetchdf()

    if df.empty:
        return None

    return df.iloc[0]


def get_missing_tracks_for_artist(con, artist_name, limit=15):
    """
    Returns up to `limit` missing-duration tracks for one artist.
    """
    query = f"""
        WITH missing_tracks AS (
            SELECT
                t.id AS track_id,
                t.artist_id,
                t.name AS track_name,
                COUNT(s.id) AS scrobble_count
            FROM tracks t
            LEFT JOIN scrobbles s ON s.track_id = t.id
            WHERE t.duration_ms IS NULL OR t.duration_ms = 0
            GROUP BY t.id, t.artist_id, t.name
        )
        SELECT
            m.track_id AS id,
            m.track_name AS track_name,
            m.scrobble_count AS scrobble_count
        FROM missing_tracks m
        JOIN artists a ON a.id = m.artist_id
        WHERE a.name = ?
        ORDER BY m.scrobble_count DESC, m.track_name
        LIMIT {int(limit)}
    """

    return con.execute(query, [artist_name]).fetchdf()


def fix_missing_durations(con, limit=15, artist_name=None, rank_by="plays"):
    """
    Finds missing-duration tracks grouped by artist.

    If artist_name is not provided, it chooses the top artist automatically.

    rank_by:
      - "plays": artist whose missing tracks have the most total scrobbles
      - "tracks": artist with the most missing tracks
    """
    print("\n--- Fix Missing Track Durations by Artist ---")

    if artist_name is None:
        top_artist = get_top_missing_duration_artist(con, rank_by=rank_by)

        if top_artist is None:
            print("No missing durations found! Your data is clean.")
            return

        artist_name = str(top_artist["artist_name"])

        print(
            f"Selected artist: {artist_name} "
            f"({int(top_artist['missing_tracks'])} missing tracks, "
            f"{int(top_artist['total_scrobbles'])} plays across missing tracks)"
        )

    missing_tracks = get_missing_tracks_for_artist(
        con,
        artist_name,
        limit=limit
    )

    if missing_tracks.empty:
        print(f"No missing durations found for artist: {artist_name}")
        return

    print(f"Showing up to {limit} tracks for '{artist_name}'.")
    print("Enter time as mm:ss or hh:mm:ss.")
    print("Commands: blank/skip = skip, done = stop this artist, q = quit.")

    for _, row in missing_tracks.iterrows():
        track_id = int(row["id"])
        track = row["track_name"]
        count = int(row["scrobble_count"])

        try:
            user_input = input(
                f"[{count} plays] {artist_name} - {track}\n > Duration: "
            ).strip()

        except EOFError:
            print("\nNo input available. Quitting duration updates.")
            return

        if user_input.lower() == "q":
            print("Quitting duration updates.")
            return

        if user_input.lower() in ("done", "d"):
            print(f"Finished artist: {artist_name}")
            return

        if user_input.lower() in ("skip", "s", ""):
            continue

        try:
            duration_ms = parse_duration_to_ms(user_input)

            if duration_ms and duration_ms > 0:
                con.execute(
                    "UPDATE tracks SET duration_ms = ? WHERE id = ?",
                    [duration_ms, track_id]
                )
                print(f"   ✓ Updated to {duration_ms} ms\n")
            else:
                print("   ✗ Duration must be greater than 0. Skipped.\n")

        except ValueError:
            print("   ✗ Invalid input. Use mm:ss, hh:mm:ss, or milliseconds. Skipped.\n")

def get_last_scrobble_timestamp(con):
    result = con.execute("SELECT MAX(timestamp) FROM scrobbles").fetchone()
    return result[0] if result and result[0] is not None else None

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python extract.py <lastfm_username>")
        
    username = sys.argv[1]
    
    with get_connection() as con:
        ensure_schema(con)
        
        from_ts = int(sys.argv[2]) if len(sys.argv) > 2 else get_last_scrobble_timestamp(con)
        to_ts = int(sys.argv[3]) if len(sys.argv) > 3 else None
        
        print("Fetching scrobbles...")
        scrobbles = get_scrobbles(username, from_ts=from_ts, to_ts=to_ts)
        
        if scrobbles:
            print(f"Fetched {len(scrobbles)} valid scrobbles. Resolving dimensions...")
            artist_cache, track_cache = load_caches(con)
            updated_track_cache = resolve_dimensions(con, scrobbles, artist_cache, track_cache)
            
            print("Storing scrobbles...")
            count = store_scrobbles(con, scrobbles, updated_track_cache)
            print(f"Successfully stored {count} new scrobbles for '{username}'.")
            fix_missing_durations(con, limit=15)
        else:
            print(f"No new scrobbles found for '{username}'.")

if __name__ == "__main__":
    main()