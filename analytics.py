from typing import List, Dict, Any

def calculate_scores(teams_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates performance scores and classifies student teams."""
    if not teams_data:
        return []

    # Step 1 - Find Class Maximums
    max_commits = max(t.get('total_commits', 0) for t in teams_data) or 1
    use_code_size_fallback = (
        max(t.get('lines_added', 0) for t in teams_data) == 0
        and max(t.get('code_bytes', 0) for t in teams_data) > 0
    )
    loc_metric_key = 'code_bytes' if use_code_size_fallback else 'lines_added'
    loc_metric_source = 'language bytes fallback' if use_code_size_fallback else 'LOC added'
    max_loc = max(t.get(loc_metric_key, 0) for t in teams_data) or 1

    scored_data = []
    for team in teams_data:
        team_copy = dict(team)
        
        # Step 2 - Normalize Metrics
        norm_commits = team_copy.get('total_commits', 0) / max_commits
        loc_metric_value = team_copy.get(loc_metric_key, 0)
        norm_loc = loc_metric_value / max_loc
        
        # Step 3 - Weighted Base Score
        base_score = (norm_commits * 0.3) + (norm_loc * 0.7)
        
        # Step 4 - Consistency Bonus
        consistency_multiplier = 1.1 if team_copy.get('active_days', 0) >= 3 else 1.0
        final_score = min(base_score * consistency_multiplier, 1.0)
        
        # Step 5 - Status Classification
        progress_pct = final_score * 100
        if progress_pct >= 70:
            status = "On Track"
        elif progress_pct >= 30:
            status = "Lagging"
        else:
            status = "Inactive"
            
        team_copy['normalized_commits'] = norm_commits
        team_copy['normalized_loc'] = norm_loc
        team_copy['score_loc_value'] = loc_metric_value
        team_copy['score_loc_source'] = loc_metric_source
        team_copy['final_score'] = final_score
        team_copy['progress_pct'] = progress_pct
        team_copy['status'] = status
        
        scored_data.append(team_copy)

    # Sort deterministically for stable charts and exports.
    return sorted(scored_data, key=lambda x: (-x['progress_pct'], str(x.get('team_id', ''))))
