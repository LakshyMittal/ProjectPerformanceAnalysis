from analytics import calculate_scores


def _team(team_id: str, commits: int, loc: int, days: int, code_bytes: int = 0) -> dict:
    return {
        "team_id": team_id,
        "total_commits": commits,
        "lines_added": loc,
        "active_days": days,
        "code_bytes": code_bytes,
    }


def test_calculate_scores_empty_input_returns_empty_list() -> None:
    assert calculate_scores([]) == []


def test_absolute_baseline_scoring_uses_fixed_targets() -> None:
    teams = [_team("A", 100, 5000, 20)]
    scored = calculate_scores(teams)[0]
    assert scored["normalized_commits"] == 1.0
    assert scored["normalized_loc"] == 1.0
    assert scored["normalized_active_days"] == 1.0
    assert scored["score_baseline"] == "absolute"


def test_consistency_bonus_applies_for_three_or_more_days() -> None:
    teams = [_team("A", 50, 2500, 3)]
    scored = calculate_scores(teams)[0]
    # Base = 0.5, Bonus = 1.1 => 0.55
    assert round(scored["final_score"], 2) == 0.55


def test_status_on_track_threshold() -> None:
    teams = [_team("A", 100, 5000, 20)]
    assert calculate_scores(teams)[0]["status"] == "On Track"


def test_status_lagging_threshold() -> None:
    teams = [_team("A", 30, 1000, 3)]
    assert calculate_scores(teams)[0]["status"] == "Lagging"


def test_status_inactive_threshold() -> None:
    teams = [_team("A", 0, 0, 0)]
    assert calculate_scores(teams)[0]["status"] == "Inactive"


def test_code_bytes_fallback_is_used_when_all_loc_zero() -> None:
    teams = [
        _team("A", 10, 0, 5, code_bytes=250_000),
        _team("B", 5, 0, 5, code_bytes=125_000),
    ]
    scored = calculate_scores(teams)
    a = next(item for item in scored if item["team_id"] == "A")
    b = next(item for item in scored if item["team_id"] == "B")
    assert a["score_loc_source"] == "language bytes fallback"
    assert a["normalized_loc"] == 1.0
    assert b["normalized_loc"] == 0.5
