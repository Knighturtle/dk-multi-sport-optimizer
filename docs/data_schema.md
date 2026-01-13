# Input Data Schema (CSV)

The optimizer expects a CSV file with the following columns.

## Required Columns

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `player_id` | string/int | Unique identifier for the player |
| `player_name` | string | Name of the player |
| `position` | string | Position(s) of the player, slash-separated (e.g., "PG/SG") |
| `salary` | number | Salary of the player |
| `team` | string | Team abbreviation (e.g., "LAL", "KC") |
| `ownership` | number (optional) | Projected ownership percentage (0-100 or 0-1) |
| `ceiling` | number (optional) | Projected ceiling score (for GPP) |
| `[projection_column]` | number | Projected points. Column name is defined in rules YAML (e.g., "AvgPointsPerGame") |

## Standardized Projection Columns

Based on current YAML configurations:

- **NBA**: `AvgPointsPerGame`
- **NFL**: `AvgPointsPerGame`
- **MLB**: `AvgPointsPerGame`
- **GOLF**: `AvgPointsPerGame`

## Example (NBA)

```csv
player_id,player_name,position,salary,team,AvgPointsPerGame
1001,LeBron James,SF/PF,9500,LAL,55.0
1002,Stephen Curry,PG,9200,GSW,52.5
```
