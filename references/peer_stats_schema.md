# Peer Stats Schema

Peer stats are anonymous aggregate data, not raw player B50 snapshots.

Preferred file names:

- `assets/peer_stats.json`
- `assets/peer_stats.zip`
- `assets/peer_stats.json.gz`

Shape:

```json
{
  "version": "2026-05-09",
  "rating_bucket_size": 200,
  "buckets": {
    "16000-16199": {
      "charts": {
        "834:4": {
          "sample_count": 128,
          "avg_achievement": 99.8421,
          "p50_achievement": 99.91,
          "avg_ra": 331,
          "b50_appear_rate": 0.37
        }
      }
    }
  }
}
```

Chart key format:

```text
{song_id}:{level_index}
```

Calculations:

- `gap = current_achievement - avg_achievement`
- `ARPI = average(gap)` for matched B50 charts
- If `b50_appear_rate <= 1`, convert to percent by multiplying by 100.
- `b50_overlap.value = average(song overlap percent)` for matched B50 charts

If no peer stats exist, set `peer_stats_available=false` and avoid peer comparison claims.
