# Spotify Extended Streaming History Analysis

This project contains my personal Spotify extended streaming history exports (audio + video) and a Jupyter notebook used to combine and analyze the data.

## Project Contents

- `music_analysis.ipynb`: Main notebook for loading, combining, and analyzing streaming history.
- `Streaming_History_Audio_2019-2021_0.json` ... `Streaming_History_Audio_2025_10.json`: Raw Spotify audio history exports split across date ranges.
- `Streaming_History_Video_2024-2025.json`: Raw Spotify video history export.
- `Streaming_History_Audio.csv`: Combined audio history generated from the notebook.

## Data Format

Each stream record includes fields such as:

- `ts`: Timestamp of the stream event.
- `platform`: Device/OS where playback happened.
- `ms_played`: Milliseconds played.
- `master_metadata_track_name`: Track title.
- `master_metadata_album_artist_name`: Artist name.
- `master_metadata_album_album_name`: Album name.
- `spotify_track_uri`: Spotify URI for the track.
- `reason_start` / `reason_end`: Playback start/end reasons.
- `shuffle`, `skipped`, `offline`, `incognito_mode`: Playback behavior flags.

Some podcast/audiobook fields are present in Spotify exports and may be null for music streams.

## Workflow

1. Load all audio JSON files in `music_analysis.ipynb`.
2. Concatenate into one dataframe.
3. Convert timestamps to local timezone (`Asia/Dubai`).
4. Export merged data to `Streaming_History_Audio.csv`.
5. Run analysis/visualization cells for listening insights.

## Setup

Use Python 3.10+ (recommended) and install:

```bash
pip install pandas numpy matplotlib seaborn jupyter
```

Then open:

```bash
jupyter notebook music_analysis.ipynb
```

## Privacy Note

These files include the personal listening history of the owner and contains sensitive metadata (timestamps, IP addresses, country, device info). Avoid sharing or publishing the raw data without consent.

## Possible Future Analysis Ideas

- Top artists/tracks by total listening time.
- Listening trends by month, day, and hour.
- Skip-rate analysis by artist or track.
- Platform/device usage patterns.
- Shuffle vs non-shuffle listening behavior.
