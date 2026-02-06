import httpx
import asyncio
import os
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
        stats_resp = await client.get(stats_url, headers=headers)
        
        total_commits = 0
        total_additions = 0
        total_deletions = 0
        
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            # Sum up stats from all contributors
            for contributor in stats:
                total_commits += contributor['total']
                for week in contributor['weeks']:
                    total_additions += week['a']
                    total_deletions += week['d']
        elif stats_resp.status_code == 202:
            # 202 means GitHub is calculating stats in background. 
            print(f"Warning: Stats computing for {repo}. Try again in 10s.")
            
        # 4. Fetch Commit Activity (Active Days)
        # This endpoint returns activity per day for the last year
        activity_url = f"{api_base}/stats/commit_activity"
        activity_resp = await client.get(activity_url, headers=headers)
        active_days = 0
        
        if activity_resp.status_code == 200:
            activity_data = activity_resp.json()
            # Sum up days with > 0 commits across all weeks
            for week in activity_data:
                active_days += sum(1 for day_count in week['days'] if day_count > 0)
        
        return {
            "team_id": f"{owner[:2].upper()}-{repo[:2].upper()}", # Simple ID generation
            "repo_name": repo,
            "total_commits": total_commits,
            "lines_added": total_additions,
            "lines_deleted": total_deletions,
            "active_days": active_days,
            "last_pushed": last_pushed,
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
