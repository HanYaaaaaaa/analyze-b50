# Diving-Fish B50 Schema

Endpoint:

```text
POST https://www.diving-fish.com/api/maimaidxprober/query/player
Content-Type: application/json
Body: {"qq": 123456, "b50": true}
```

Top-level fields commonly used:

- `nickname`: player display name.
- `username`: Diving-Fish username.
- `rating`: total DX rating.
- `additional_rating`: class/rank side value from the API.
- `charts.sd`: old-version B35 list, 35 records.
- `charts.dx`: current-version B15 list, 15 records.

Chart record fields:

- `song_id`: music id.
- `title`: song title.
- `type`: `SD` or `DX`.
- `level`: display level, e.g. `14+`.
- `level_index`: 0 Basic, 1 Advanced, 2 Expert, 3 Master, 4 Re:MASTER.
- `level_label`: difficulty label.
- `ds`: chart constant.
- `achievements`: achievement percent, e.g. `100.6927`.
- `ra`: single-chart rating.
- `rate`: score rank string.
- `fc`: combo status string, e.g. `fc`, `fcp`, `ap`, `app`, or empty.
- `fs`: sync status string.
- `dxScore`: DX score.

Treat `charts.sd + charts.dx` as the player's current B50. Do not read local bot databases.
