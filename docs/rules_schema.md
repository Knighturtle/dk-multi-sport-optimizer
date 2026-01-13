# DraftKings Rules Schema (YAML)

All rule files in `rules/dk/*.yaml` must adhere to this structure.

## Root Object

| Key | Type | Description | Required | Output Example |
| :--- | :--- | :--- | :--- | :--- |
| `sport` | string | Sport identifier (e.g., "NBA", "NFL") | Yes | "NBA" |
| `site` | string | Platform identifier | Yes | "DraftKings" |
| `salary_cap` | integer | Total salary cap | Yes | 50000 |
| `lineup_size` | integer | Number of players in a lineup | Yes | 8 |
| `projection_column` | string | Name of the CSV column to use for projections | Yes | "AvgPointsPerGame" |
| `num_lineups` | integer | Default number of lineups to generate | No | 20 |
| `roster_slots` | object | Container for slot definitions | Yes | (see below) |
| `team_limits` | object | Team constraints | No | (see below) |

## Roster Slots (`roster_slots`)

Contains a list of `slots`.

### Slot Object

| Key | Type | Description |
| :--- | :--- | :--- |
| `slot` | string | Display name of the slot (e.g., "PG", "FLEX") |
| `eligible` | list[str] | List of eligible player positions (e.g., ["PG", "SG"]) |
| `count` | integer | Number of players required in this slot |

## Team Limits (`team_limits`)

| Key | Type | Description |
| :--- | :--- | :--- |
| `max_from_team` | integer | Max players allowed from a single team |
| `min_teams` | integer | Minimum number of unique teams required |
