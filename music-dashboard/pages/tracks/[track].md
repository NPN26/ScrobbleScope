```sql date_ranges
select
    (now() at time zone 'Asia/Dubai') - interval '7 day' as last_week,
    (now() at time zone 'Asia/Dubai') - interval '1 month' as last_month,
    (now() at time zone 'Asia/Dubai') - interval '3 month' as last_quarter,
    (now() at time zone 'Asia/Dubai') - interval '6 month' as last_half_year,
    (now() at time zone 'Asia/Dubai') - interval '1 year' as last_year
```

```sql track_details
select 
    id,
    name,
    artist,
    album,
    global_playcount,
    duration,
    pct_global_plays,
    scrobbles,
    first_scrobble,
    last_scrobble,
    scrobbles_last_week,
    scrobbles_last_month,
    scrobbles_last_quarter,
    scrobbles_last_half_year,
    scrobbles_last_year,
from music.track_details
where id = cast('${params.track}' as integer)
```

```sql track_rank
select 
    id,
    play_count_4w,
    prev_play_count_4w,
    play_count_6m,
    prev_play_count_6m,
    rank_4w,
    prev_rank_4w,
    rank_6m,
    prev_rank_6m,
    play_delta_4w,
    play_delta_6m,
    rank_delta_4w,
    rank_delta_6m,
    rank_status_4w,
    rank_status_6m,
    has_rank_delta_4w,
    has_rank_delta_6m
from music.track_ranks
where id = cast('${params.track}' as integer)
```

```sql track_scrobbles_by_day
select
    date_trunc('day', s.ts_local) as day,
    t.name as track,
    sum(count(*)) over (partition by t.name order by date_trunc('day', s.ts_local)) as accum_scrobbles,
    count(*) as scrobbles
from music.scrobbles s
join music.tracks t on t.id = s.track_id
where t.id = cast('${params.track}' as integer)
group by date_trunc('day', s.ts_local), t.name
order by date_trunc('day', s.ts_local) desc
```

```sql similar_tracks
select
    t.id,
    t.name as track,
    '/tracks/' || t.id as track_url
from music.tracks t
join music.tracks p
  on p.id = cast('${params.track}' as integer)
where
    trim(
        regexp_replace(
            regexp_replace(
                t.name,
                '[[:space:]]*[(][^)]*[)].*$',
                ''
            ),
            '[[:space:]]+-.*$',
            ''
        )
    ) =
    trim(
        regexp_replace(
            regexp_replace(
                p.name,
                '[[:space:]]*[(][^)]*[)].*$',
                ''
            ),
            '[[:space:]]+-.*$',
            ''
        )
    )
    and t.id <> p.id;
```

```sql hours_of_day
select
    extract(hour from ts_local) as hour,
    count(*) as plays
from music.scrobbles s
join music.tracks t on t.id = s.track_id
where t.id = cast('${params.track}' as integer)
group by hour
order by hour
```

```sql day_of_week
select
    day_of_week,
    count(*) as plays
from music.scrobbles s
join music.tracks t on t.id = s.track_id
where t.id = cast('${params.track}' as integer)
group by day_of_week
order by case LOWER(TRIM(day_of_week))
    when 'monday' then 1
    when 'tuesday' then 2
    when 'wednesday' then 3
    when 'thursday' then 4
    when 'friday' then 5
    when 'saturday' then 6
    when 'sunday' then 7
    else 8 
end;
```

```sql album_summary
select 
    t.name as track,
    count(*) as plays,
    sum(count(*)) over () as total_album_plays,
    (count(*)::decimal / sum(count(*)) over ()) as pct_of_album
from music.scrobbles s
join music.tracks t on t.id = s.track_id
where t.id = cast('${params.track}' as integer)
  and t.album_name = (select album_name from music.tracks where id = cast('${params.track}' as integer))
  and t.artist_id = (select artist_id from music.tracks where id = cast('${params.track}' as integer))
group by t.name
order by plays desc
limit 10
```

<BigValue title="Artist" data={track_details} value="artist" />

<BigValue title="Track" data={track_details} value="name" />

<BigValue title="Album" data={track_details} value="album" />

<BigValue title="Global Play Count" data={track_details} value="global_playcount" fmt="0,0" />

<BigValue title="Pct of Global Plays" data={track_details} value="pct_global_plays" fmt="0.00%" />

<BigValue title="Duration" data={track_details} value="duration" fmt="mm:ss" />

{#if track_details[0].scrobbles_last_week > 0}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" comparison=scrobbles_last_week comparisonTitle=" Scrobbles over Last Week" comparisonDelta=false/>

{:else if track_details[0].scrobbles_last_month > 0}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" comparison=scrobbles_last_month comparisonTitle=" Scrobbles over Last Month" comparisonDelta=false/>

{:else if track_details[0].scrobbles_last_quarter > 0}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" comparison=scrobbles_last_quarter comparisonTitle=" Scrobbles over Last 3 months" comparisonDelta=false/>

{:else if track_details[0].scrobbles_last_half_year > 0}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" comparison=scrobbles_last_half_year comparisonTitle=" Scrobbles over Last Half Year" comparisonDelta=false/>
 
{:else if track_details[0].scrobbles_last_year > 0}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" comparison=scrobbles_last_year comparisonTitle=" Scrobbles over Last Year" comparisonDelta=false/>

{:else}
<BigValue title="Scrobbles" data={track_details} value="scrobbles" />

{/if}

<br />

{#if track_rank.length > 0}

  <BigValue
    title="Plays (4 weeks)"
    data={track_rank}
    value="play_count_4w"
    comparison="play_delta_4w"
    comparisonTitle="vs previous 4 weeks"
    comparisonDelta=true
    fmt="0,0"
  />

  {#if track_rank[0]?.rank_4w != null}
    {#if track_rank[0]?.has_rank_delta_4w}
      <BigValue
        title="Rank (4 weeks)"
        data={track_rank}
        value="rank_4w"
        comparison="rank_delta_4w"
        comparisonTitle="positions vs previous 4 weeks"
        comparisonDelta=true
        fmt="0,0"
      />
    {:else}
      <BigValue
        title="Rank (4 weeks)"
        data={track_rank}
        value="rank_4w"
        comparison="rank_status_4w"
        comparisonTitle=""
        comparisonDelta=false
        fmt="0,0"
      />
    {/if}
  {:else}
    <BigValue
      title="Rank (4 weeks)"
      data={track_rank}
      value="rank_status_4w"
    />
  {/if}

  <BigValue
    title="Plays (6 months)"
    data={track_rank}
    value="play_count_6m"
    comparison="play_delta_6m"
    comparisonTitle="vs previous 6 months"
    comparisonDelta=true
    fmt="0,0"
  />

  {#if track_rank[0]?.rank_6m != null}
    {#if track_rank[0]?.has_rank_delta_6m}
      <BigValue
        title="Rank (6 months)"
        data={track_rank}
        value="rank_6m"
        comparison="rank_delta_6m"
        comparisonTitle="positions vs previous 6 months"
        comparisonDelta=true
        fmt="0,0"
      />
    {:else}
      <BigValue
        title="Rank (6 months)"
        data={track_rank}
        value="rank_6m"
        comparison="rank_status_6m"
        comparisonTitle=""
        comparisonDelta=false
        fmt="0,0"
      />
    {/if}
  {:else}
    <BigValue
      title="Rank (6 months)"
      data={track_rank}
      value="rank_status_6m"
    />
  {/if}

{/if}

<BigValue title="First Scrobble" data={track_details} value="first_scrobble" fmt="dddd, d mmmm yyyy" />

<BigValue title="Last Scrobble" data={track_details} value="last_scrobble" fmt="dddd, d mmmm yyyy" />

<LineChart data={track_scrobbles_by_day} x=day y=accum_scrobbles y2=scrobbles title="Scrobbles by Day">
    <ReferenceLine data={date_ranges} x=last_week fontSize=10 labelBackground=false 
    label={'Last Week (' + (track_details[0]?.scrobbles_last_week ?? 0) + ' plays)'} hideValue />
    <ReferenceLine data={date_ranges} x=last_month fontSize=10      
    label={'Last Month (' + (track_details[0]?.scrobbles_last_month ?? 0) + ' plays)'} hideValue />
    <ReferenceLine data={date_ranges} x=last_quarter fontSize=10
    label={'Last Quarter (' + (track_details[0]?.scrobbles_last_quarter ?? 0) + ' plays)'} hideValue />
    <ReferenceLine data={date_ranges} x=last_half_year fontSize=10
    label={'Last Half Year (' + (track_details[0]?.scrobbles_last_half_year ?? 0) + ' plays)'} hideValue />
    <ReferenceLine data={date_ranges} x=last_year fontSize=10
    label={'Last Year (' + (track_details[0]?.scrobbles_last_year ?? 0) + ' plays)'} hideValue />
</LineChart>

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

<BarChart
    data={day_of_week}
    x=day_of_week
    y=plays
    sort=false
/>

<CalendarHeatmap
    data={track_scrobbles_by_day}
    date=day
    value=scrobbles
/>

<BarChart 
    data={album_summary} 
    x="track" 
    y="plays" 
    title="How this track compares to the rest of the Album" 
    labels=true 
/>
{#if similar_tracks.length > 0}
<DataTable data={similar_tracks} title="Similar Tracks" link=track_url>
    <Column id="track" title="Track" />
</DataTable>
{/if}