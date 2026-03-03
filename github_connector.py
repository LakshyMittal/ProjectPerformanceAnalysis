import httpx
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def fetch_repo_details(client, repo_url):
    """
    Fetches key metrics for a single repository asynchronously.
    """
    if not GITHUB_TOKEN:
        return {"error": "Missing GitHub Token"}

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Parse URL to get 'owner/repo'
    try:
        parts = repo_url.rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        api_base = f"https://api.github.com/repos/{owner}/{repo}"
    except Exception:
        return {"error": "Invalid URL format", "url": repo_url}

    print(f"Fetching: {owner}/{repo}...")

    try:
        # 2. Check if Repo Exists & Get Basic Info
        resp = await client.get(api_base, headers=headers)
        if resp.status_code == 404:
            return {"error": "Repository not found (404)", "url": repo_url}
        elif resp.status_code != 200:
            return {"error": f"API Error {resp.status_code}", "url": repo_url}
        
        repo_data = resp.json()
        
        # Extract last push date (YYYY-MM-DD)
        last_pushed = repo_data.get("pushed_at", "N/A")
        if last_pushed != "N/A":
            last_pushed = last_pushed.split("T")[0]
        
        # 3. Fetch Contributor Stats (Commits, Additions, Deletions)
        # This endpoint returns the total activity per contributor
        stats_url = f"{api_base}/stats/contributors"
        
        total_commits = 0
        total_additions = 0
        total_deletions = 0
        contributor_commits = [] # Store individual counts for Gini calculation
        
        # RETRY LOGIC: GitHub returns 202 if stats are being computed. 
        # We must wait to ensure we don't return 0 and ruin the analysis.
        for attempt in range(3):
            stats_resp = await client.get(stats_url, headers=headers)
            
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                if isinstance(stats, list): # Ensure we got a list of contributors
                    # Sum up stats from all contributors
                    for contributor in stats:
                        total_commits += contributor['total']
                        contributor_commits.append(contributor['total'])
                        for week in contributor['weeks']:
                            total_additions += week['a']
                            total_deletions += week['d']
                break # Success, exit loop
            elif stats_resp.status_code == 202:
                # Wait and retry
                print(f"⚠️ Stats computing for {repo}... Retrying ({attempt+1}/3)")
                await asyncio.sleep(2)
            else:
                break # Other error, exit loop
            
        # --- ADVANCED METRIC: Gini Coefficient (Inequality Index) ---
        # 0.0 = Perfect Equality (Everyone contributed equally)
        # 1.0 = Perfect Inequality (One person did everything)
        gini_score = 0.0
        if contributor_commits and total_commits > 0:
            contributor_commits.sort()
            n = len(contributor_commits)
            numerator = sum((i + 1) * c for i, c in enumerate(contributor_commits))
            # Standard Gini Formula
            gini_score = (2 * numerator) / (n * total_commits) - (n + 1) / n
            gini_score = max(0.0, min(gini_score, 1.0)) # Clamp between 0 and 1

        # 4. Fetch Commit Activity (Active Days)
        # This endpoint returns activity per day for the last year
        activity_url = f"{api_base}/stats/commit_activity"
        activity_resp = await client.get(activity_url, headers=headers)
        active_days = 0
        weekly_activity = []
        
        if activity_resp.status_code == 200:
            activity_data = activity_resp.json()
            # Sum up days with > 0 commits across all weeks
            for week in activity_data:
                active_days += sum(1 for day_count in week['days'] if day_count > 0)
                weekly_activity.append({
                    "week_start": datetime.fromtimestamp(week['week']).strftime('%Y-%m-%d'),
                    "commits": week['total']
                })
        
        # 5. Fetch Primary Language
        lang_url = f"{api_base}/languages"
        lang_resp = await client.get(lang_url, headers=headers)
        primary_language = "Unknown"
        if lang_resp.status_code == 200:
            langs = lang_resp.json()
            if langs:
                primary_language = max(langs, key=langs.get) # Get key with max value

        return {
            "team_id": f"{owner[:2].upper()}-{repo[:2].upper()}", # Simple ID generation
            "repo_name": repo,
            "total_commits": total_commits,
            "lines_added": total_additions,
            "lines_deleted": total_deletions,
            "active_days": active_days,
            "last_pushed": last_pushed,
            "weekly_activity": weekly_activity,
            "gini_coefficient": gini_score,
            "primary_language": primary_language,
            "url": repo_url
        }

    except Exception as e:
        return {"error": str(e), "url": repo_url}

# --- TEST BLOCK (Runs only when executing this file directly) ---
async def main_test():
    # Test with a popular repo (pandas)
    test_url = "https://github.com/pandas-dev/pandas"
    
    async with httpx.AsyncClient() as client:
        print("--- Starting Test Connection ---")
        data = await fetch_repo_details(client, test_url)
        print("\n--- Result ---")
        print(data)

if __name__ == "__main__":
    asyncio.run(main_test())
