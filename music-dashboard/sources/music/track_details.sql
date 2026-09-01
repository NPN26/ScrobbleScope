select 
    t.id,
    t.name,
    a.name as artist,
    t.album_name as album,
    t.global_playcount,
    t.duration_ms / 1000 / 60 / 60 / 24 as duration,
    (count(*)::double / t.global_playcount) as pct_global_plays,
    count(*) as scrobbles,
    min(to_timestamp(s.timestamp + 14400) ) as first_scrobble,
    max(to_timestamp(s.timestamp + 14400) ) as last_scrobble,
    COUNT(*) FILTER (WHERE to_timestamp(s.timestamp + 14400)  >= (now() at time zone 'Asia/Dubai') - interval '7 day') as scrobbles_last_week,
    COUNT(*) FILTER (WHERE to_timestamp(s.timestamp + 14400)  >= (now() at time zone 'Asia/Dubai') - interval '1 month') as scrobbles_last_month,
    COUNT(*) FILTER (WHERE to_timestamp(s.timestamp + 14400)  >= (now() at time zone 'Asia/Dubai') - interval '3 month') as scrobbles_last_quarter,
    COUNT(*) FILTER (WHERE to_timestamp(s.timestamp + 14400)  >= (now() at time zone 'Asia/Dubai') - interval '6 month') as scrobbles_last_half_year,
    COUNT(*) FILTER (WHERE to_timestamp(s.timestamp + 14400)  >= (now() at time zone 'Asia/Dubai') - interval '1 year') as scrobbles_last_year,
from scrobbles s
join warehouse.tracks t on t.id = s.track_id
join warehouse.artists a on t.artist_id = a.id 
group by t.id, t.name, a.name, t.album_name, t.global_playcount, t.duration_ms