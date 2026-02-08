def calculate_scores(teams_data):
    """
    Calculates relative performance scores for all teams.
    """
    if not teams_data:
        return []
    
    # 1. Find Maximums (Class Benchmarks)
    # We use 'max' to compare teams against the best performer, not an arbitrary number.
    max_commits = max(t['total_commits'] for t in teams_data) or 1
    max_loc = max(t['lines_added'] for t in teams_data) or 1
    
    scored_teams = []
    
    for team in teams_data:
        # 2. Normalize Metrics (0.0 to 1.0)
        norm_commits = team['total_commits'] / max_commits
        norm_loc = team['lines_added'] / max_loc
        
        # 3. Calculate Base Score
        # Weights: 30% Commits, 70% LOC (Sum = 1.0)
        base_score = (norm_commits * 0.3) + (norm_loc * 0.7)
        
        # 4. Consistency Bonus
        # Bonus if work is spread across at least 3 separate days
        consistency_multiplier = 1.1 if team.get('active_days', 0) >= 3 else 1.0
        
        final_score = base_score * consistency_multiplier
        
        # Cap at 1.0 (100%)
        final_score = min(final_score, 1.0)
        
        # 5. Determine Status
        progress_pct = final_score * 100
        if progress_pct >= 70:
            status = "On Track"
        elif progress_pct >= 30:
            status = "Lagging"
        else:
            status = "Inactive"
            
        # Create a new dictionary with scores
        team_with_score = team.copy()
        team_with_score.update({
            "normalized_commits": norm_commits,
            "normalized_loc": norm_loc,
            "final_score": final_score,
            "progress_pct": progress_pct,
            "status": status
        })
        scored_teams.append(team_with_score)
        
    # Sort by progress (Highest first)
    scored_teams.sort(key=lambda x: x['progress_pct'], reverse=True)
    
    return scored_teams