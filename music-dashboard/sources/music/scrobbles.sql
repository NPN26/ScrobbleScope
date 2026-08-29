select
    id,
    track_id,
    is_loved,
    timestamp as ts_utc,
    to_timestamp(timestamp + 14400)              as ts_local,
    to_timestamp(timestamp + 14400)::date         as listen_date,
    extract(hour from to_timestamp(timestamp+14400))   as listen_hour,
    strftime(to_timestamp(timestamp+14400), '%A')      as day_of_week,
    date_trunc('month', to_timestamp(timestamp+14400)) as listen_month
from scrobbles