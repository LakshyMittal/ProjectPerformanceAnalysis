from typing import Any, Dict, List

# Absolute baselines make grading stable across different class cohorts.
COMMIT_TARGET = 100
LOC_ADDED_TARGET = 5000
ACTIVE_DAYS_TARGET = 20
CODE_BYTES_TARGET = 250_000
WEIGHTS = {"commits": 0.30, "loc": 0.50, "active_days": 0.20}


def calculate_scores(teams_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate absolute-baseline performance scores and classify teams."""
    if not teams_data:
        return []

    use_code_size_fallback = (
        max(t.get("lines_added", 0) for t in teams_data) == 0
        and max(t.get("code_bytes", 0) for t in teams_data) > 0
    )
    loc_metric_key = "code_bytes" if use_code_size_fallback else "lines_added"
    loc_metric_source = "language bytes fallback" if use_code_size_fallback else "LOC added"
    loc_target = CODE_BYTES_TARGET if use_code_size_fallback else LOC_ADDED_TARGET

    scored_data = []
    for team in teams_data:
        team_copy = dict(team)

        commits = max(0, int(team_copy.get("total_commits", 0)))
        loc_metric_value = max(0, int(team_copy.get(loc_metric_key, 0)))
        active_days = max(0, int(team_copy.get("active_days", 0)))

        # Absolute normalization prevents one top performer from distorting everyone else.
        norm_commits = min(commits / COMMIT_TARGET, 1.0)
        norm_loc = min(loc_metric_value / loc_target, 1.0)
        norm_active_days = min(active_days / ACTIVE_DAYS_TARGET, 1.0)

        base_score = (
            norm_commits * WEIGHTS["commits"]
            + norm_loc * WEIGHTS["loc"]
            + norm_active_days * WEIGHTS["active_days"]
        )

        consistency_multiplier = 1.1 if active_days >= 3 else 1.0
        final_score = min(base_score * consistency_multiplier, 1.0)

        progress_pct = final_score * 100
        if progress_pct >= 70:
            status = "On Track"
        elif progress_pct >= 30:
            status = "Lagging"
        else:
            status = "Inactive"

        team_copy["normalized_commits"] = norm_commits
        team_copy["normalized_loc"] = norm_loc
        team_copy["normalized_active_days"] = norm_active_days
        team_copy["score_loc_value"] = loc_metric_value
        team_copy["score_loc_source"] = loc_metric_source
        team_copy["score_baseline"] = "absolute"
        team_copy["final_score"] = final_score
        team_copy["progress_pct"] = progress_pct
        team_copy["status"] = status

        scored_data.append(team_copy)

    return scored_data
