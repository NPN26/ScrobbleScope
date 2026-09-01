with play_4w as (
    select 
        t.id,
        count(*) as play_count_4w
    from warehouse.tracks t
    join warehouse.scrobbles s
        on t.id = s.track_id
    where to_timestamp(s.timestamp) >= now() - interval '4 weeks'
    group by t.id
),

prev_play_4w as (
    select 
        t.id,
        count(*) as prev_play_count_4w
    from warehouse.tracks t
    join warehouse.scrobbles s
        on t.id = s.track_id
    where to_timestamp(s.timestamp) >= now() - interval '8 weeks'
      and to_timestamp(s.timestamp) < now() - interval '4 weeks'
    group by t.id
),

ranked_4w as (
    select
        id,
        play_count_4w,
        dense_rank() over (
            order by play_count_4w desc
        ) as rank_4w
    from play_4w
),

prev_ranked_4w as (
    select
        id,
        prev_play_count_4w,
        dense_rank() over (
            order by prev_play_count_4w desc
        ) as prev_rank_4w
    from prev_play_4w
),

play_6m as (
    select 
        t.id,
        count(*) as play_count_6m
    from warehouse.tracks t
    join warehouse.scrobbles s
        on t.id = s.track_id
    where to_timestamp(s.timestamp) >= now() - interval '6 months'
    group by t.id
),

prev_play_6m as (
    select 
        t.id,
        count(*) as prev_play_count_6m
    from warehouse.tracks t
    join warehouse.scrobbles s
        on t.id = s.track_id
    where to_timestamp(s.timestamp) >= now() - interval '12 months'
      and to_timestamp(s.timestamp) < now() - interval '6 months'
    group by t.id
),

ranked_6m as (
    select
        id,
        play_count_6m,
        dense_rank() over (
            order by play_count_6m desc
        ) as rank_6m
    from play_6m
),

prev_ranked_6m as (
    select
        id,
        prev_play_count_6m,
        dense_rank() over (
            order by prev_play_count_6m desc
        ) as prev_rank_6m
    from prev_play_6m
),

all_ids as (
    select id from play_4w
    union
    select id from prev_play_4w
    union
    select id from play_6m
    union
    select id from prev_play_6m
)

select
    a.id,

    --------------------------------------------------------------------
    -- 4-week play metrics
    --------------------------------------------------------------------
    coalesce(p4.play_count_4w, 0) as play_count_4w,
    coalesce(pp4.prev_play_count_4w, 0) as prev_play_count_4w,

    coalesce(p4.play_count_4w, 0) - coalesce(pp4.prev_play_count_4w, 0)
        as play_delta_4w,

    -- Optional: percentage change. Null when previous period is zero/null.
    (coalesce(p4.play_count_4w, 0) - coalesce(pp4.prev_play_count_4w, 0))::decimal
        / nullif(pp4.prev_play_count_4w, 0)
        as play_pct_delta_4w,

        --------------------------------------------------------------------
    -- 4-week rank metrics
    --------------------------------------------------------------------
    r4.rank_4w,
    pr4.prev_rank_4w,

    -- Only show a numeric delta if the track was ranked in both periods.
    case
        when r4.rank_4w is not null
         and pr4.prev_rank_4w is not null
        then pr4.prev_rank_4w - r4.rank_4w
    end as rank_delta_4w,

    case
        when r4.rank_4w is null
         and pr4.prev_rank_4w is null
            then 'not ranked'

        when r4.rank_4w is not null
         and pr4.prev_rank_4w is null
            then 'new entry'

        when r4.rank_4w is null
         and pr4.prev_rank_4w is not null
            then 'dropped out'

        when r4.rank_4w < pr4.prev_rank_4w
            then 'improved'

        when r4.rank_4w > pr4.prev_rank_4w
            then 'declined'

        else 'unchanged'
    end as rank_status_4w,

    -- Useful for Evidence conditional logic.
    case
        when r4.rank_4w is not null
         and pr4.prev_rank_4w is not null
            then true
        else false
    end as has_rank_delta_4w,

    --------------------------------------------------------------------
    -- 6-month play metrics
    --------------------------------------------------------------------
    coalesce(p6.play_count_6m, 0) as play_count_6m,
    coalesce(pp6.prev_play_count_6m, 0) as prev_play_count_6m,

    coalesce(p6.play_count_6m, 0) - coalesce(pp6.prev_play_count_6m, 0)
        as play_delta_6m,

    -- Optional: percentage change. Null when previous period is zero/null.
    (coalesce(p6.play_count_6m, 0) - coalesce(pp6.prev_play_count_6m, 0))::decimal
        / nullif(pp6.prev_play_count_6m, 0)
        as play_pct_delta_6m,

        --------------------------------------------------------------------
    -- 6-month rank metrics
    --------------------------------------------------------------------
    r6.rank_6m,
    pr6.prev_rank_6m,

    -- Only show a numeric delta if the track was ranked in both periods.
    case
        when r6.rank_6m is not null
         and pr6.prev_rank_6m is not null
        then pr6.prev_rank_6m - r6.rank_6m
    end as rank_delta_6m,

    case
        when r6.rank_6m is null
         and pr6.prev_rank_6m is null
            then 'not ranked'

        when r6.rank_6m is not null
         and pr6.prev_rank_6m is null
            then 'new entry'

        when r6.rank_6m is null
         and pr6.prev_rank_6m is not null
            then 'dropped out'

        when r6.rank_6m < pr6.prev_rank_6m
            then 'improved'

        when r6.rank_6m > pr6.prev_rank_6m
            then 'declined'

        else 'unchanged'
    end as rank_status_6m,

    -- Useful for Evidence conditional logic.
    case
        when r6.rank_6m is not null
         and pr6.prev_rank_6m is not null
            then true
        else false
    end as has_rank_delta_6m,

from all_ids a

left join play_4w p4
    on a.id = p4.id

left join prev_play_4w pp4
    on a.id = pp4.id

left join ranked_4w r4
    on a.id = r4.id

left join prev_ranked_4w pr4
    on a.id = pr4.id

left join play_6m p6
    on a.id = p6.id

left join prev_play_6m pp6
    on a.id = pp6.id

left join ranked_6m r6
    on a.id = r6.id

left join prev_ranked_6m pr6
    on a.id = pr6.id

-- If this query is used directly for the track page, filter here:
-- where a.id = cast('${params.track}' as integer)