```sql track
select 
    name,
    'tracks/' || id as link
from music.tracks
```

<TextInput
    name=name_of_input
    title="Search"
/>

```sql search_tracks
select
    t.name,
    a.name as artist,
    t.album_name as album,
    t.id as link
from music.tracks t
join music.artists a on a.id = t.artist_id
where case when '${inputs.name_of_input}' = '' then true else t.name ilike '%' || '${inputs.name_of_input}' || '%' end
limit 10
```

searching: {inputs.name_of_input}

<DataTable data={search_tracks} link=link />

```sql all_tracks
select
    t.name as track,
    a.name as artist,
    t.album_name as album,
    count(s.id) as scrobbles,
    '/tracks/' || t.id as link
from music.tracks t
join music.artists a on a.id = t.artist_id
left join music.scrobbles s on s.track_id = t.id
group by t.id, t.name, a.name, t.album_name
order by scrobbles desc
```

## All Tracks

<DataTable data={all_tracks} link=link rows=20>
    <Column id="track" title="Track" />
    <Column id="artist" title="Artist" />
    <Column id="album" title="Album" />
    <Column id="scrobbles" title="Scrobbles" />
</DataTable>