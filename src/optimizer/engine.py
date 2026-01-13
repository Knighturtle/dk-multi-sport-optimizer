# src/optimizer/engine.py
# DraftKings Multi-Sport Optimizer (Rule-driven via rules/dk/*.yaml)
#
# Requires:
#   pip install pandas pyyaml pulp
#
# Notes:
# - This engine reads your YAML format exactly as shown in screenshots:
#     sport, site, slate, salary_cap, lineup_size, projection_column, num_lineups
#     roster_slots:
#       slots: [{slot, eligible, count}, ...]
#     team_limits: {max_from_team, min_teams}
# - It supports multi-lineup generation with optional max_overlap setting
# - Team constraints are auto-skipped if team column is missing
#
# Example usage (from UI or CLI):
#   from src.optimizer.engine import OptimizerEngine
#   engine = OptimizerEngine(rules_dir="rules/dk")
#   lineups = engine.optimize_csv("data/players.csv", sport="NBA", settings={"num_lineups": 20, "max_overlap": 6})
#
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import yaml
from pulp import (
    LpBinary,
    LpMaximize,
    LpProblem,
    LpStatusOptimal,
    LpVariable,
    lpSum,
    value,
    PULP_CBC_CMD,
)

# ----------------------------
# Utilities
# ----------------------------

def _as_upper(s: Any) -> str:
    return str(s).strip().upper()

def _parse_positions(pos_value: Any) -> Set[str]:
    """
    Accepts:
      - "PG/SG" style string
      - "PG,SG" style string
      - list/tuple/set of positions
    Returns a set of uppercase position tokens.
    """
    if pos_value is None or (isinstance(pos_value, float) and pd.isna(pos_value)):
        return set()

    if isinstance(pos_value, (list, tuple, set)):
        toks = [str(x) for x in pos_value]
    else:
        s = str(pos_value)
        # normalize common delimiters
        s = s.replace("|", "/").replace(",", "/").replace(" ", "")
        toks = [t for t in s.split("/") if t]

    return {_as_upper(t) for t in toks if str(t).strip()}

def _safe_int(x: Any, default: int) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, float) and pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

# ----------------------------
# Rules model
# ----------------------------

@dataclass(frozen=True)
class SlotRule:
    name: str
    eligible: Set[str]
    count: int

@dataclass(frozen=True)
class TeamLimits:
    max_from_team: Optional[int] = None
    min_teams: Optional[int] = None

@dataclass(frozen=True)
class DkRules:
    sport: str
    site: str
    slate: Optional[str]
    salary_cap: int
    lineup_size: Optional[int]
    projection_column: str
    num_lineups: int
    slots: List[SlotRule]
    team_limits: TeamLimits

# ----------------------------
# Engine
# ----------------------------

class OptimizerEngine:
    def __init__(self, rules_dir: str | Path = "rules/dk") -> None:
        self.rules_dir = Path(rules_dir)

    # --------
    # Rules
    # --------
    def list_sports(self) -> List[str]:
        """List sports by scanning rules_dir for *.yaml files."""
        if not self.rules_dir.exists():
            return []
        sports = []
        for p in sorted(self.rules_dir.glob("*.yaml")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "sport" in data:
                    sports.append(str(data["sport"]))
                else:
                    sports.append(p.stem)
            except Exception:
                sports.append(p.stem)
        return sports

    def load_rules(self, sport: str) -> DkRules:
        """
        Load rules from rules/dk/<something>.yaml.
        Matches by:
          1) exact filename: <sport>.yaml (case-insensitive)
          2) any yaml whose 'sport' field equals the requested sport (case-insensitive)
        """
        if not self.rules_dir.exists():
            raise FileNotFoundError(f"Rules directory not found: {self.rules_dir}")

        sport_norm = _as_upper(sport)

        # Try direct filename match
        candidates = list(self.rules_dir.glob("*.yaml"))
        direct = None
        for p in candidates:
            if _as_upper(p.stem) == sport_norm:
                direct = p
                break

        rule_path = direct
        if rule_path is None:
            # Try by 'sport' field inside yaml
            for p in candidates:
                with p.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if _as_upper(data.get("sport")) == sport_norm:
                    rule_path = p
                    break

        if rule_path is None:
            raise FileNotFoundError(f"No rules yaml found for sport='{sport}'. Looked in: {self.rules_dir}")

        with rule_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Validate required keys
        missing = []
        for k in ["sport", "site", "salary_cap", "projection_column", "roster_slots"]:
            if k not in raw:
                missing.append(k)
        if missing:
            raise ValueError(f"Rules file {rule_path} missing keys: {missing}")

        roster_slots = raw.get("roster_slots") or {}
        slots_list = roster_slots.get("slots")
        if not isinstance(slots_list, list) or len(slots_list) == 0:
            raise ValueError(f"Rules file {rule_path} must contain roster_slots.slots as a non-empty list")

        slots: List[SlotRule] = []
        total_count = 0
        for s in slots_list:
            if not isinstance(s, dict):
                raise ValueError(f"Invalid slot entry (must be dict): {s}")
            name = str(s.get("slot", "")).strip()
            eligible = s.get("eligible", [])
            count = _safe_int(s.get("count"), 0)

            if not name:
                raise ValueError(f"Slot entry missing 'slot' name: {s}")
            if count <= 0:
                raise ValueError(f"Slot '{name}' has non-positive count: {count}")
            elig_set = set(_as_upper(x) for x in eligible) if isinstance(eligible, list) else _parse_positions(eligible)
            if not elig_set:
                raise ValueError(f"Slot '{name}' has empty eligible list: {s}")

            slots.append(SlotRule(name=_as_upper(name), eligible=elig_set, count=count))
            total_count += count

        lineup_size = raw.get("lineup_size")
        lineup_size_int = _safe_int(lineup_size, total_count) if lineup_size is not None else None
        # We don't hard-fail if mismatch, but keep a guard:
        if lineup_size_int is not None and lineup_size_int != total_count:
            # mismatch is common if someone edits one and not the other; prefer slot sum
            # you can log/warn in UI layer; here we just ignore and use slot sum as "true"
            lineup_size_int = total_count

        team_limits_raw = raw.get("team_limits") or {}
        tl = TeamLimits(
            max_from_team=_safe_int(team_limits_raw.get("max_from_team"), None) if "max_from_team" in team_limits_raw else None,
            min_teams=_safe_int(team_limits_raw.get("min_teams"), None) if "min_teams" in team_limits_raw else None,
        )

        return DkRules(
            sport=_as_upper(raw.get("sport")),
            site=str(raw.get("site")),
            slate=raw.get("slate"),
            salary_cap=_safe_int(raw.get("salary_cap"), 50000),
            lineup_size=lineup_size_int,
            projection_column=str(raw.get("projection_column")),
            num_lineups=_safe_int(raw.get("num_lineups"), 1),
            slots=slots,
            team_limits=tl,
        )

    # --------
    # Data
    # --------
    def load_players_df(
        self,
        df_or_path: pd.DataFrame | str | Path,
        rules: DkRules,
        *,
        sport: Optional[str] = None,
    ) -> pd.DataFrame:
        if isinstance(df_or_path, pd.DataFrame):
            df = df_or_path.copy()
        else:
            df = pd.read_csv(df_or_path)

        # Normalize column names for robustness
        # (We keep originals too; only enforce required existence)
        required = ["player_id", "player_name", "position", "salary", rules.projection_column]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Input CSV missing required columns: {missing}. "
                f"Required: {required}. Your columns: {list(df.columns)}"
            )

        # Optional sport column validation (UI can enforce; engine can warn/error)
        if sport is not None and "sport" in df.columns:
            s_in = df["sport"].astype(str).str.upper().unique().tolist()
            if len(s_in) == 1 and _as_upper(s_in[0]) != _as_upper(sport):
                raise ValueError(f"CSV sport='{s_in[0]}' does not match selected sport='{sport}'")

        # Clean types
        df["player_id"] = df["player_id"].astype(str)
        df["player_name"] = df["player_name"].astype(str)

        df["_salary"] = df["salary"].apply(lambda x: _safe_int(x, 0))
        df["_proj"] = df[rules.projection_column].apply(lambda x: _safe_float(x, 0.0))
        df["_positions"] = df["position"].apply(_parse_positions)

        # Optional team
        if "team" in df.columns:
            df["_team"] = df["team"].astype(str).str.upper()
        else:
            df["_team"] = None

        # Filter unusable rows
        df = df[df["_salary"] > 0].copy()
        df = df[df["_proj"].notna()].copy()
        df = df[df["_positions"].apply(lambda s: len(s) > 0)].copy()

        if df.empty:
            raise ValueError("No valid players after cleaning (salary/projection/position).")

        return df.reset_index(drop=True)

    # --------
    # Optimize
    # --------
    def optimize_csv(
        self,
        csv_path: str | Path,
        sport: str,
        *,
        settings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        rules = self.load_rules(sport)
        df = self.load_players_df(csv_path, rules, sport=sport)
        return self.optimize_df(df, rules, settings=settings)

    def optimize_df(
        self,
        players_df: pd.DataFrame,
        rules: DkRules,
        *,
        settings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of lineups (dicts).
        Settings:
          - num_lineups: int
          - max_overlap: int
          - lock_player_ids: List[str]
          - exclude_player_ids: List[str]
          - objective_mode: "cash" | "gpp" (default cash)
          - gpp_alpha: float (DEPRECATED in favor of EV col, but kept for back-compat)
          - max_chalk_count: int (Max players with > chalk_threshold ownership)
          - chalk_threshold: float (default 0.20)
          - min_total_ceiling: float (Constraint)
          - total_ownership_cap: float (sum of ownership <= X)
          - use_ownership: bool (Enable ownership optimized objective - legacy penalty method)
          - ownership_weight: float (Penalty weight)
        """
        settings = settings or {}
        num_lineups = _safe_int(settings.get("num_lineups"), rules.num_lineups)
        num_lineups = max(1, num_lineups)

        # Ensure Internal Columns
        # If specific columns like _ev are missing but Mode=GPP, we might want to default to Proj
        # But ideally the caller (App) prepares _ev.
        columns_check = ["_proj", "_salary", "_team", "_positions", "_ownership", "_ceiling", "_ev"]
        for c in columns_check:
            if c not in players_df.columns:
                if c == "_ev": players_df["_ev"] = players_df["_proj"] # Fallback
                elif c == "_ceiling": players_df["_ceiling"] = players_df["_proj"]
                elif c == "_ownership": players_df["_ownership"] = 0.0
                elif c == "_positions": pass # Should be handled below
                elif c == "_team": pass # Handled below
                else: pass

        # Optional generation controls
        # max_overlap: maximum number of shared players between any new lineup and ALL previous lineups
        #   - if None, no overlap constraint applied
        max_overlap = settings.get("max_overlap")
        max_overlap = _safe_int(max_overlap, None) if max_overlap is not None else None

        # optional lock/exclude
        locked_ids = set(str(x) for x in (settings.get("lock_player_ids") or []))
        excluded_ids = set(str(x) for x in (settings.get("exclude_player_ids") or []))

        df = players_df.copy()

        # Ensure internal columns exist (robust handling for raw vs pre-processed DFs)
        if "_positions" not in df.columns:
            # Fallback: try to generate from "position"
            if "position" in df.columns:
                df["_positions"] = df["position"].apply(_parse_positions)
            else:
                # Last resort: empty sets (will likely fail eligibility, but prevents crash here)
                df["_positions"] = [set() for _ in range(len(df))]

        if "_salary" not in df.columns:
            # Fallback: try "salary"
            if "salary" in df.columns:
                df["_salary"] = df["salary"].apply(lambda x: _safe_int(x, 0))
            else:
                df["_salary"] = 0

        if "_proj" not in df.columns:
            # Fallback: try rules.projection_column or "proj_points"
            col_to_use = rules.projection_column if rules.projection_column in df.columns else "proj_points"
            if col_to_use in df.columns:
                df["_proj"] = df[col_to_use].apply(lambda x: _safe_float(x, 0.0))
            else:
                df["_proj"] = 0.0

        if "_team" not in df.columns:
            if "team" in df.columns:
                df["_team"] = df["team"].astype(str).str.strip().str.upper()
                df.loc[df["_team"] == "", "_team"] = None
            else:
                df["_team"] = None

        if excluded_ids:
            df = df[~df["player_id"].isin(excluded_ids)].copy()
        if df.empty:
            raise ValueError("All players excluded; nothing left to optimize.")

        # Build slot instances (expand counts)
        slot_instances: List[Tuple[str, Set[str]]] = []
        for sr in rules.slots:
            for i in range(sr.count):
                # Each instance has a unique name to enforce exact count
                inst_name = f"{sr.name}__{i+1}"
                slot_instances.append((inst_name, sr.eligible))

        # Precompute player eligibility by slot instance
        player_ids = df["player_id"].tolist()
        player_pos: Dict[str, Set[str]] = dict(zip(df["player_id"], df["_positions"]))
        player_salary: Dict[str, int] = dict(zip(df["player_id"], df["_salary"]))
        player_proj: Dict[str, float] = dict(zip(df["player_id"], df["_proj"]))
        player_name: Dict[str, str] = dict(zip(df["player_id"], df["player_name"]))
        
        # GPP / Ownership Data
        player_ceiling: Dict[str, float] = {}
        player_own: Dict[str, float] = {}
        
        if "_ceiling" in df.columns:
            player_ceiling = dict(zip(df["player_id"], df["_ceiling"]))
        else:
            # default to proj check logic? Or just 0.
            # If GPP mode requested but no ceiling, fallback to proj
            player_ceiling = player_proj.copy()
            
        if "_ownership" in df.columns:
            player_own = dict(zip(df["player_id"], df["_ownership"]))
        else:
            # Default 0
            player_own = {pid: 0.0 for pid in player_ids}

        # Check for valid team data
        # _team is guaranteed to exist now (though values might be None)
        has_team = df["_team"].notna().any()
        player_team: Dict[str, Optional[str]] = dict(zip(df["player_id"], df["_team"])) if has_team else {}

        # For min_teams we need team->players list
        teams: List[str] = []
        team_to_players: Dict[str, List[str]] = {}
        if has_team:
            teams = sorted(df["_team"].dropna().unique().tolist())
            for t in teams:
                team_to_players[t] = df.loc[df["_team"] == t, "player_id"].tolist()

        # Validate locked players feasibility quickly (optional)
        if locked_ids:
            missing_locks = [pid for pid in locked_ids if pid not in player_ids]
            if missing_locks:
                raise ValueError(f"Locked player_ids not found in input after exclusions: {missing_locks}")

        lineups: List[Dict[str, Any]] = []
        previous_lineup_player_sets: List[Set[str]] = []

        for k in range(num_lineups):
            prob = LpProblem(f"dk_optimizer_{rules.sport}_{k+1}", LpMaximize)

            # Decision vars: x[p, s] indicates player p assigned to slot-instance s
            x: Dict[Tuple[str, str], LpVariable] = {}
            for pid in player_ids:
                for (sname, selig) in slot_instances:
                    # eligibility check
                    if player_pos[pid].intersection(selig):
                        x[(pid, sname)] = LpVariable(f"x_{pid}_{sname}", lowBound=0, upBound=1, cat=LpBinary)

            if not x:
                try:
                    # Fallback attempt: if only 1 lineup and fails, try to see constraints
                    print("Debug: No eligibility variables created. Check positions.")
                except:
                    pass
                raise ValueError("No feasible (player,slot) assignments from eligibility rules.")

            # Each slot instance must be filled by exactly 1 player
            for (sname, _selig) in slot_instances:
                prob += (
                    lpSum(x[(pid, sname)] for pid in player_ids if (pid, sname) in x) == 1,
                    f"fill_{sname}",
                )

            # Each player can be used at most once across all slot instances
            for pid in player_ids:
                prob += (
                    lpSum(x[(pid, sname)] for (sname, _selig) in slot_instances if (pid, sname) in x) <= 1,
                    f"player_once_{pid}",
                )

            # Salary cap
            prob += (
                lpSum(
                    player_salary[pid] * x[(pid, sname)]
                    for (pid, sname) in x.keys()
                )
                <= rules.salary_cap,
                "salary_cap",
            )

            # Locked players (must appear exactly once)
            # Implementation: sum over slot instances == 1
            for pid in locked_ids:
                prob += (
                    lpSum(x[(pid, sname)] for (sname, _selig) in slot_instances if (pid, sname) in x) == 1,
                    f"lock_{pid}",
                )
                
            # Ownership Cap (Sum of ownership <= Cap)
            total_own_cap = settings.get("total_ownership_cap")
            if total_own_cap is not None:
                prob += (
                    lpSum(
                        player_own[pid] * x[(pid, sname)]
                        for (pid, sname) in x.keys()
                    )
                    <= float(total_own_cap),
                    "total_ownership_cap"
                )
                
            # Min Total Ceiling (GPP)
            min_ceil = settings.get("min_total_ceiling")
            if min_ceil is not None:
                 prob += (
                    lpSum(
                        player_ceiling[pid] * x[(pid, sname)]
                        for (pid, sname) in x.keys()
                    )
                    >= float(min_ceil),
                    "min_total_ceiling"
                )
                
            # Max Chalk Count
            # Constraint: Sum of (is_chalk * x) <= max_chalk
            max_chalk = settings.get("max_chalk_count")
            if max_chalk is not None:
                chalk_thresh = float(settings.get("chalk_threshold", 0.20))
                # Precompute chalk status
                is_chalk = {pid: (1 if player_own[pid] >= chalk_thresh else 0) for pid in player_ids}
                
                prob += (
                    lpSum(
                        is_chalk[pid] * x[(pid, sname)]
                        for (pid, sname) in x.keys()
                    )
                    <= int(max_chalk),
                    "max_chalk_count"
                )

            # Team limits (auto-skip if no team data)
            if has_team:
                if rules.team_limits.max_from_team is not None:
                    max_ft = int(rules.team_limits.max_from_team)
                    for t in teams:
                        prob += (
                            lpSum(
                                x[(pid, sname)]
                                for pid in team_to_players.get(t, [])
                                for (sname, _selig) in slot_instances
                                if (pid, sname) in x
                            )
                            <= max_ft,
                            f"max_from_team_{t}",
                        )

                if rules.team_limits.min_teams is not None:
                    # Use binary y[t] indicating whether team t is used
                    # link: sum_x_team >= y[t] and sum_x_team <= M * y[t]
                    min_teams = int(rules.team_limits.min_teams)
                    M = len(slot_instances)  # max players in lineup
                    y: Dict[str, LpVariable] = {t: LpVariable(f"y_team_{t}", 0, 1, LpBinary) for t in teams}

                    for t in teams:
                        team_pick_sum = lpSum(
                            x[(pid, sname)]
                            for pid in team_to_players.get(t, [])
                            for (sname, _selig) in slot_instances
                            if (pid, sname) in x
                        )
                        prob += (team_pick_sum >= y[t], f"team_used_lb_{t}")
                        prob += (team_pick_sum <= M * y[t], f"team_used_ub_{t}")

                    prob += (lpSum(y[t] for t in teams) >= min_teams, "min_teams")

            # Overlap constraint with previous lineups (optional)
            # We constrain overlap against EACH previous lineup to be <= max_overlap
            if max_overlap is not None and previous_lineup_player_sets:
                max_ov = int(max_overlap)
                # Create helper z[pid] = whether pid is selected in this lineup
                # z[pid] = sum_s x[pid,s]
                # To avoid excessive variables, we can just use the sum directly in the constraint
                # But creating a z variable makes it cleaner if used multiple times. 
                # Here we only use it for overlap check.
                # Let's iterate previous sets.
                
                for j, prev_set in enumerate(previous_lineup_player_sets, start=1):
                     # sum of x for p in prev_set <= max_overlap
                    prob += (
                         lpSum(
                             x[(pid, sname)]
                             for pid in prev_set
                             for (sname, _selig) in slot_instances
                             if (pid, sname) in x
                         ) <= max_ov,
                        f"max_overlap_prev_{j}",
                    )

            # Objective
            mode = settings.get("objective_mode", "cash").lower()
            
            if mode == "gpp":
                # Maximize EV (Expected Value)
                # Ensure _ev is populated in DF (or fallback to proj above)
                player_ev = dict(zip(df["player_id"], df["_ev"]))
                
                prob += lpSum(
                    player_ev[pid] * x[(pid, sname)]
                    for (pid, sname) in x.keys()
                )
            else:
                # Cash / Standard: Maximize Projection
                prob += lpSum(
                    player_proj[pid] * x[(pid, sname)]
                    for (pid, sname) in x.keys()
                )
            
            # --- Legacy/Extra Objective Modifiers ---
            # Even in GPP/Cash mode, user might want to subtract Ownership penalty on top
            if settings.get("use_ownership", False):
                own_weight = float(settings.get("ownership_weight", 0.0))
                lev_mode = settings.get("leverage_mode", "penalize_high_own")
                
                if own_weight > 0:
                    if lev_mode == "penalize_high_own":
                        # Objective -= weight * Sum(Ownership)
                        # We want to LOWER ownership sum, so we SUBTRACT it from max objective.
                        # (Maximize Proj - Weight * SumOwn)
                        prob += -1 * own_weight * lpSum(
                            player_own[pid] * x[(pid, sname)]
                            for (pid, sname) in x.keys()
                        )
                    elif lev_mode == "target_leverage":
                        # Minimize deviation from Target Sum
                        # This requires absolute value linearization
                        # |SumOwn - TargetSum| 
                        # TargetSum = target_avg * rules.lineup_size
                        
                        target_avg = float(settings.get("target_ownership", 0.15))
                        target_sum = target_avg * rules.lineup_size
                        
                        # Define slack vars for this specific problem
                        # Since `x` is dict keys, we need a unique name for this solve if run multiple times?
                        # Pulp variables are global to the problem. 
                        
                        # Delta Pos, Delta Neg >= 0
                        d_pos = LpVariable(f"delta_pos_{len(prob.variables())}", lowBound=0)
                        d_neg = LpVariable(f"delta_neg_{len(prob.variables())}", lowBound=0)
                        
                        # Constraint: Sum(Own) - TargetSum = d_pos - d_neg
                        prob += (
                             lpSum(player_own[pid] * x[(pid, sname)] for (pid, sname) in x.keys()) 
                             - target_sum 
                             == d_pos - d_neg,
                             "target_leverage_def"
                        )
                        
                        # Objective penalty: - weight * (d_pos + d_neg)
                        prob += -1 * own_weight * (d_pos + d_neg)

            # Solve
            solver = PULP_CBC_CMD(msg=False)
            status = prob.solve(solver)

            if status != LpStatusOptimal:
                # Stop generating more lineups if infeasible
                break

            # Extract lineup
            chosen: List[Tuple[str, str]] = []
            for (pid, sname), var in x.items():
                if var.value() is not None and var.value() > 0.5:
                    chosen.append((pid, sname))

            # Map slot instance to slot base name
            slot_base = {sname: sname.split("__")[0] for (sname, _elig) in slot_instances}

            # Build ordered slot list: preserve YAML slot order
            # We'll assign in the order of slot_instances list, which already respects YAML order and count expansion.
            instance_order = [sname for (sname, _elig) in slot_instances]
            instance_to_player: Dict[str, str] = {sname: pid for (pid, sname) in chosen}

            slot_rows: List[Dict[str, Any]] = []
            total_salary = 0
            total_proj = 0.0
            selected_player_ids: Set[str] = set()

            for sname in instance_order:
                pid = instance_to_player.get(sname)
                if pid is None:
                    continue
                selected_player_ids.add(pid)
                sal = player_salary[pid]
                prj = player_proj[pid]
                total_salary += sal
                total_proj += prj

                row = {
                    "slot": slot_base[sname],
                    "slot_instance": sname,
                    "player_id": pid,
                    "player_name": player_name[pid],
                    "salary": sal,
                    "proj_points": prj,
                    "position": "/".join(sorted(player_pos[pid])),
                }
                if has_team:
                    row["team"] = player_team.get(pid)
                slot_rows.append(row)

            lineup = {
                "sport": rules.sport,
                "site": rules.site,
                "slate": rules.slate,
                "salary_cap": rules.salary_cap,
                "projection_column": rules.projection_column,
                "total_salary": total_salary,
                "total_proj": float(total_proj),
                "slots": slot_rows,
            }

            lineups.append(lineup)
            previous_lineup_player_sets.append(selected_player_ids)

        return lineups

    # --------
    # Convenience: export
    # --------
    def export_lineups_csv(self, lineups: List[Dict[str, Any]], out_path: str | Path) -> None:
        """
        Flatten lineups to a CSV.
        Columns:
          lineup_index, slot, player_id, player_name, team?, salary, proj_points, position, total_salary, total_proj
        """
        rows: List[Dict[str, Any]] = []
        for i, lu in enumerate(lineups, start=1):
            for r in lu["slots"]:
                row = {
                    "lineup_index": i,
                    "slot": r.get("slot"),
                    "player_id": r.get("player_id"),
                    "player_name": r.get("player_name"),
                    "salary": r.get("salary"),
                    "proj_points": r.get("proj_points"),
                    "position": r.get("position"),
                    "total_salary": lu.get("total_salary"),
                    "total_proj": lu.get("total_proj"),
                    "sport": lu.get("sport"),
                    "slate": lu.get("slate"),
                }
                if "team" in r:
                    row["team"] = r.get("team")
                rows.append(row)

        out_df = pd.DataFrame(rows)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_path, index=False)

# ----------------------------
# Minimal CLI (optional)
# ----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DraftKings Multi-Sport Optimizer (rule-driven)")
    parser.add_argument("--sport", required=True, help="Sport name, e.g., NBA, NFL, LOL, MLB")
    parser.add_argument("--csv", required=True, help="Path to player CSV")
    parser.add_argument("--rules-dir", default="rules/dk", help="Rules directory (default: rules/dk)")
    parser.add_argument("--num-lineups", type=int, default=None, help="Number of lineups to generate (default: from YAML)")
    parser.add_argument("--max-overlap", type=int, default=None, help="Max shared players vs previous lineups")
    parser.add_argument("--out", default="results/lineups.csv", help="Output CSV path")

    args = parser.parse_args()

    engine = OptimizerEngine(rules_dir=args.rules_dir)
    rules = engine.load_rules(args.sport)
    df = engine.load_players_df(args.csv, rules, sport=args.sport)

    settings: Dict[str, Any] = {}
    if args.num_lineups is not None:
        settings["num_lineups"] = args.num_lineups
    if args.max_overlap is not None:
        settings["max_overlap"] = args.max_overlap

    lineups = engine.optimize_df(df, rules, settings=settings)
    engine.export_lineups_csv(lineups, args.out)
    print(f"Generated {len(lineups)} lineup(s) -> {args.out}")
