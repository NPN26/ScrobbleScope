---
title: Welcome to my Music Dashboard
description: A dashboard to visualize my music listening history and statistics.
---

<script>
    let loading = false;
    let message = "";
    let messageType = "";

    function getToken() {
        return localStorage.getItem('gh_pat') || '';
    }

    function promptForToken() {
        const token = prompt('Enter your GitHub Personal Access Token (with "actions" scope).\nCreate one at: https://github.com/settings/tokens');
        if (token) localStorage.setItem('gh_pat', token);
        return token;
    }

    async function handleRefresh() {
        let token = getToken();
        if (!token) token = promptForToken();
        if (!token) { message = "Token required to trigger a rebuild."; messageType = "error"; return; }

        loading = true;
        message = "Triggering data refresh & rebuild...";
        messageType = "info";
        try {
            const resp = await fetch(
                "https://api.github.com/repos/NPN26/Spotify-Streaming-History-Analysis/actions/workflows/deploy.yml/dispatches",
                {
                    method: "POST",
                    headers: {
                        "Authorization": `token ${token}`,
                        "Accept": "application/vnd.github.v3+json"
                    },
                    body: JSON.stringify({ ref: "main" })
                }
            );
            if (resp.status === 204) {
                message = "✅ Build triggered! Dashboard will update in ~20 minutes. Check progress on the Actions tab.";
                messageType = "success";
            } else if (resp.status === 401 || resp.status === 403) {
                localStorage.removeItem('gh_pat');
                message = "❌ Invalid or expired token. Click again to re-enter.";
                messageType = "error";
            } else {
                message = "❌ GitHub API returned status " + resp.status;
                messageType = "error";
            }
        } catch (e) {
            message = "❌ Network error: " + e.message;
            messageType = "error";
        }
        loading = false;
    }
</script>

<div style="margin-bottom: 2rem; padding: 1rem; border: 1px solid #737272; border-radius: 8px; background-color: var(--grey-900);">
    <h3 style="margin-top: 0;">🔄 Data Sync</h3>
    <p style="margin-bottom: 1rem;">Pull latest scrobbles from Last.fm and rebuild the dashboard. Takes ~20 minutes.</p>
    <button
        on:click={handleRefresh}
        disabled={loading}
        style="padding: 8px 16px; font-size: 14px; cursor: pointer; background-color: #1ed760; color: white; border: none; border-radius: 20px; font-weight: bold; opacity: {loading ? 0.7 : 1};"
    >
        {loading ? "Triggering..." : "🔄 Update Data"}
    </button>
    <a href="https://github.com/NPN26/Spotify-Streaming-History-Analysis/actions" target="_blank" style="margin-left: 12px; font-size: 13px; color: var(--blue-600);">View build progress →</a>
    {#if message}
        <p style="margin-top: 10px; font-size: 14px; font-weight: 500; color: {messageType === 'error' ? '#dc2626' : messageType === 'success' ? '#16a34a' : '#2563eb'};">{message}</p>
    {/if}
</div>


```sql recent_scrobbles
select
    s.id,
    s.ts_local,
    t.name as track,
    a.name as artist,
    t.album_name as album,
    t.duration_ms / 1000 / 60 as duration_min
from music.scrobbles s
join music.tracks t on s.track_id = t.id
join music.artists a on t.artist_id = a.id
order by s.ts_local desc
limit 10
```

```sql total_scrobbles
  select count(*) as total_scrobbles
  from music.scrobbles
```

```sql total_artists
  select count(distinct a.id) as total_artists
  from music.artists a
```

```sql total_time_minutes
  select sum(t.duration_ms)/1000/60 as total_time
  from music.scrobbles s
  join music.tracks t on s.track_id = t.id
```

<BigValue title="Total Scrobbles" data={total_scrobbles} value=total_scrobbles />
<BigValue title="Total Artists" data={total_artists} value=total_artists />
<BigValue title="Total Time (minutes)" data={total_time_minutes} value=total_time />

```sql artists_scrobbles_counts
    select
        a.name as artist,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    join music.artists a on t.artist_id = a.id
    group by a.name
    order by scrobbles desc
```

```sql top_artist
    select
        artist,
        scrobbles
    from ${artists_scrobbles_counts}
    order by scrobbles desc
```

```sql album_scrobbles_counts
    select
        t.album_name as album,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    group by t.album_name
    having t.album_name is not null
    order by scrobbles desc
```

```sql top_album
    select
        album,
        scrobbles
    from ${album_scrobbles_counts}
    order by scrobbles desc
```

```sql track_scrobbles_counts
    select
        t.name as track,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    group by t.name
    order by scrobbles desc
```

```sql top_track
    select
        track,
        scrobbles
    from ${track_scrobbles_counts}
    order by scrobbles desc
```

```sql daily_scrobbles
    select
        date_trunc('day', ts_local) as day,
        count(*) as scrobbles
    from music.scrobbles
    group by day
    order by day desc
```

```sql top_scrobbles_day
    select
        day,
        scrobbles
    from ${daily_scrobbles}
    order by scrobbles desc
    limit 1
```

<BigValue title="Top Artist" data={top_artist.limit(1)} value=artist comparison=scrobbles comparisonFmt="num0" comparisonDelta=false/>
<BigValue title="Top Album" data={top_album.limit(1)} value=album comparison=scrobbles comparisonFmt="num0" comparisonDelta=false/>
<BigValue title="Top Track" data={top_track.limit(1)} value=track comparison=scrobbles comparisonFmt="num0" comparisonDelta=false/>
<BigValue title="Top Scrobbles Day" data={top_scrobbles_day} value=day comparison=scrobbles comparisonFmt="num0" comparisonDelta=false/>

```sql hour_of_day
SELECT
    CASE
        WHEN h.hour = 0 THEN '12 AM'
        WHEN h.hour < 12 THEN CONCAT(h.hour, ' AM')
        WHEN h.hour = 12 THEN '12 PM'
        ELSE CONCAT(h.hour - 12, ' PM')
    END as hour,
    COUNT(*) as plays
FROM generate_series(0, 23) AS h(hour)
LEFT JOIN music.scrobbles s ON EXTRACT(HOUR FROM s.ts_local) = h.hour
GROUP BY hour
ORDER BY h.hour
```

<ECharts
  config={{
    title: [{ text: 'Plays by Hour of Day' }],
    polar: { radius: [15, '85%'] },
    angleAxis: {
      type: 'category',
      data: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23],
      startAngle: 97.5
    },
    radiusAxis: { axisLabel: { show: false } },
    tooltip: {},
    series: {
      type: 'bar',
      data: [...Array(24)].map((_, h) =>
        hours_of_day?.find(r => Number(r.hour) === h)?.plays ?? 0
      ),
      coordinateSystem: 'polar',
      label: {
        show: false
      }
    },
    animation: false
  }}
/>

```sql weekly_scrobbles
SELECT
    date_trunc('week', ts_local) as week,
    avg(count(*)) over (
        order by week
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) as plays,
    avg(sum(t.duration_ms/1000/60/60)) over (
        order by week
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) as hours
from music.scrobbles s
join music.tracks t on s.track_id = t.id
group by week
order by week
```

<LineChart data={weekly_scrobbles} x=week y=plays y2=hours title="Weekly Scrobbles" labels=false sort=false />

```sql available_years
  select distinct extract(year from ts_local) as year
  from music.scrobbles
  order by year desc
```

<Dropdown 
    data={available_years} 
    name=year 
    value=year 
    multiple=true
    selectAllByDefault=true
    order= "year desc">
</Dropdown>

```sql total_scrobbles_by_year
  select count(*) as total_scrobbles
  from music.scrobbles
  where extract(year from ts_local) in ${inputs.year.value}
```

```sql total_artists_by_year
  select count(distinct a.id) as total_artists
  from music.scrobbles s
  join music.tracks t on s.track_id = t.id
  join music.artists a on t.artist_id = a.id
  where extract(year from s.ts_local) in ${inputs.year.value}
```

```sql total_time_by_year
  select sum(t.duration_ms)/1000/60 as total_time
  from music.scrobbles s
  join music.tracks t on s.track_id = t.id
  where extract(year from s.ts_local) in ${inputs.year.value}
```

```sql avg_counts_per_day
  select avg(daily_counts.scrobbles) as avg_counts
  from (
      select count(*) as scrobbles
      from music.scrobbles
      where extract(year from ts_local) in ${inputs.year.value}
      group by date_trunc('day', ts_local)
  ) as daily_counts
```

```sql avg_daily_time
  select avg(daily_time.total_time) as avg_time
  from (
      select sum(t.duration_ms)/1000/60/60 as total_time
      from music.scrobbles s
      join music.tracks t on s.track_id = t.id
      where extract(year from s.ts_local) in ${inputs.year.value}
      group by date_trunc('day', s.ts_local)
  ) as daily_time
```

```sql top_scrobbles_day_by_year
    select
        date_trunc('day', ts_local) as day,
        count(*) as scrobbles
    from music.scrobbles
    where extract(year from ts_local) in ${inputs.year.value}
    group by day
    order by scrobbles desc
    limit 1
```


  <BigValue title="Total Scrobbles (Selected)" data={total_scrobbles_by_year} value=total_scrobbles />
  <BigValue title="Total Artists (Selected)" data={total_artists_by_year} value=total_artists />
  <BigValue title="Total Time (min)" data={total_time_by_year} value=total_time />
  <br />
  <BigValue title="Avg Counts per Day" data={avg_counts_per_day} value=avg_counts fmt="num1" />
  <BigValue title="Avg Daily Time (hours)" data={avg_daily_time} value=avg_time fmt="num1" />
  <BigValue title="Top Scrobbles Day" data={top_scrobbles_day_by_year} value=day comparison=scrobbles comparisonFmt="num0" comparisonDelta=false/>


```sql top_artists_by_year
    select
        a.name as artist,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    join music.artists a on t.artist_id = a.id
    where extract(year from s.ts_local) in ${inputs.year.value}
    group by a.name
    order by scrobbles desc
    limit 10
```

```sql top_tracks_by_year
    select
        t.name as track,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    where extract(year from s.ts_local) in ${inputs.year.value}
    group by t.name
    order by scrobbles desc
    limit 10
```

```sql top_albums_by_year
    select
        t.album_name as album,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    where extract(year from s.ts_local) in ${inputs.year.value}
      and t.album_name is not null
    group by t.album_name
    order by scrobbles desc
    limit 10
```

<BarChart
    data={top_artists_by_year}
    title="Top Artists by Year"
    x=artist
    y=scrobbles
    swapXY=true
/>

<BarChart
    data={top_tracks_by_year}
    title="Top Tracks by Year"
    x=track
    y=scrobbles
    swapXY=true
/>

<BarChart
    data={top_albums_by_year}
    title="Top Albums by Year"
    x=album
    y=scrobbles
    swapXY=true
/>


```sql top_missing_duration_tracks
    select
        t.id,
        t.name as track,
        a.name as artist,
        count(s.id) as scrobbles
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    join music.artists a on t.artist_id = a.id
    where t.duration_ms = 0
    group by t.id, t.name, a.name
    having scrobbles > 50
    order by scrobbles desc
```

```sql daily_scrobbles
    select
        date_trunc('day', ts_local) as day,
        count(*) as scrobbles
    from music.scrobbles
    where extract(year from ts_local) in ${inputs.year.value}
    group by day
    order by day desc
```

<CalendarHeatmap data={daily_scrobbles} date=day value=scrobbles title="Scrobbles by Day" filter=true />

```sql daily_listen_time
    select
        date_trunc('day', s.ts_local) as day,
        sum(t.duration_ms)/1000/60/60 as total_listen_time_hrs
    from music.scrobbles s
    join music.tracks t on s.track_id = t.id
    where extract(year from s.ts_local) in ${inputs.year.value}
    group by day
    order by day desc
```

<CalendarHeatmap data={daily_listen_time} date=day value=total_listen_time_hrs title="Listening Time by Day" filter=true />

```sql hours_of_day
select
    extract(hour from ts_local) as hour,
    count(*) as plays
from music.scrobbles
group by hour
order by hour
```
