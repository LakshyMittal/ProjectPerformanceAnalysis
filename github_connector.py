import os
import asyncio
import httpx
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple
from utils import parse_github_url

load_dotenv()

STATS_RETRY_ATTEMPTS = max(1, int(os.getenv("GITHUB_STATS_RETRIES", "3")))
STATS_RETRY_BASE_SEC = max(0.1, float(os.getenv("GITHUB_STATS_BACKOFF_SEC", "1.0")))
STATS_MAX_WAIT_SEC = max(0.5, float(os.getenv("GITHUB_STATS_MAX_WAIT_SEC", "8.0")))

async def fetch_endpoint_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    label: str,
    attempts: Optional[int] = None,
) -> Tuple[Optional[Any], Optional[str]]:
    """Helper to fetch GitHub stats endpoints which may return 202 Accepted while computing."""
    attempts = attempts or STATS_RETRY_ATTEMPTS
    last_status = None
    last_message = ""
    total_wait = 0.0

    for attempt in range(attempts):
        try:
            resp = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            return None, f"{label} request failed: {exc}"

        last_status = resp.status_code
        if resp.status_code == 200:
            try:
                return resp.json(), None
            except ValueError:
                return None, f"{label} returned invalid JSON"

        try:
            body = resp.json()
            last_message = body.get("message", "")
        except ValueError:
            last_message = resp.text[:120]

        if resp.status_code == 202:
            if attempt >= attempts - 1:
                break
            delay = min(STATS_RETRY_BASE_SEC * (2 ** attempt), 3.0)
            if total_wait + delay > STATS_MAX_WAIT_SEC:
                break
            await asyncio.sleep(delay)
            total_wait += delay
            continue

        if resp.status_code in (403, 429):
            retry_after = resp.headers.get("Retry-After")
            if retry_after and attempt < attempts - 1:
                try:
                    await asyncio.sleep(min(int(retry_after), 10))
                    continue
                except ValueError:
                    pass
            return None, f"{label} unavailable ({resp.status_code}: {last_message or 'rate limited'})"

        return None, f"{label} unavailable ({resp.status_code}: {last_message or 'API error'})"

    if last_status == 202:
        return None, f"{label} still computing (attempted {attempts} retries, waited {total_wait:.1f}s)"
    return None, f"{label} unavailable ({last_status}: {last_message or 'API error'})"


async def fetch_contributor_summary(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict[str, str],
) -> Tuple[list[int], Optional[str]]:
    """Fallback commit counts when /stats/contributors is still computing or unavailable."""
    try:
        resp = await client.get(f"{base_url}/contributors?per_page=100&anon=true", headers=headers)
    except httpx.HTTPError as exc:
        return [], f"Contributor summary request failed: {exc}"

    if resp.status_code != 200:
        return [], f"Contributor summary unavailable ({resp.status_code})"

    try:
        data = resp.json()
    except ValueError:
        return [], "Contributor summary returned invalid JSON"

    if not isinstance(data, list):
        return [], "Contributor summary returned an unexpected shape"

    return [int(c.get("contributions", 0)) for c in data if c.get("contributions", 0) > 0], None


async def fetch_response(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    label: str,
) -> Tuple[Optional[httpx.Response], Optional[str]]:
    try:
        return await client.get(url, headers=headers), None
    except httpx.HTTPError as exc:
        return None, f"{label} request failed: {exc}"


async def fetch_recent_commit_activity(
    client: httpx.AsyncClient,
    base_url: str,
    headers: Dict[str, str],
) -> Tuple[int, list[Dict[str, Any]], Optional[str]]:
    """Fallback active-day and trend data from the latest commit page."""
    try:
        resp = await client.get(f"{base_url}/commits?per_page=100", headers=headers)
    except httpx.HTTPError as exc:
        return 0, [], f"Recent commits request failed: {exc}"

    if resp.status_code != 200:
        return 0, [], f"Recent commits unavailable ({resp.status_code})"

    try:
        commits = resp.json()
    except ValueError:
        return 0, [], "Recent commits returned invalid JSON"

    if not isinstance(commits, list):
        return 0, [], "Recent commits returned an unexpected shape"

    active_dates = set()
    weekly_counts = defaultdict(int)
    for item in commits:
        commit = item.get("commit", {}) if isinstance(item, dict) else {}
        date_str = (
            commit.get("committer", {}).get("date")
            or commit.get("author", {}).get("date")
        )
        if not date_str:
            continue
        try:
            commit_dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

        commit_date = commit_dt.date()
        week_start = commit_date - timedelta(days=commit_date.weekday())
        active_dates.add(commit_date.isoformat())
        weekly_counts[week_start.isoformat()] += 1

    weekly_activity = [
        {"week_start": week_start, "commits": commits}
        for week_start, commits in sorted(weekly_counts.items())
    ]
    return len(active_dates), weekly_activity, None

async def fetch_repo_details(client: httpx.AsyncClient, repo_url: str) -> Dict[str, Any]:
    """Fetches and processes metrics from multiple GitHub API endpoints concurrently."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"error": "Missing GitHub Token", "url": repo_url}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    owner, repo = parse_github_url(repo_url)
    if not owner or not repo:
        return {"error": "Invalid GitHub URL", "url": repo_url}

    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    stats_warnings = []
    
    # 1. Check basic info
    try:
        repo_resp = await client.get(base_url, headers=headers)
    except httpx.HTTPError as exc:
        return {"error": f"GitHub request failed: {exc}", "url": repo_url}

    if repo_resp.status_code == 404:
        return {"error": "Repository not found (404)", "url": repo_url}
    elif repo_resp.status_code != 200:
        return {"error": f"API Error {repo_resp.status_code}", "url": repo_url}
    
    repo_data = repo_resp.json()
    rate_limit_remaining = repo_resp.headers.get("X-RateLimit-Remaining")
    rate_limit_reset = repo_resp.headers.get("X-RateLimit-Reset")
    
    # 2. Concurrently fetch the three detail endpoints for speed
    contributors_url = f"{base_url}/stats/contributors"
    activity_url = f"{base_url}/stats/commit_activity"
    languages_url = f"{base_url}/languages"

    contributors_result, activity_result, languages_resp = await asyncio.gather(
        fetch_endpoint_with_retry(client, contributors_url, headers, "Contributor stats"),
        fetch_endpoint_with_retry(client, activity_url, headers, "Commit activity stats"),
        fetch_response(client, languages_url, headers, "Languages"),
    )
    contributors_data, contributors_warning = contributors_result
    activity_data, activity_warning = activity_result
    languages_resp, languages_warning = languages_resp
    if contributors_warning:
        stats_warnings.append(contributors_warning)
    if activity_warning:
        stats_warnings.append(activity_warning)
    if languages_warning:
        stats_warnings.append(languages_warning)

    # Process Contributors & Gini
    total_commits = 0
    lines_added = 0
    lines_deleted = 0
    gini_score = 0.0
    contributor_commits = []
    
    if contributors_data and isinstance(contributors_data, list):
        for c in contributors_data:
            commits = c.get("total", 0)
            if commits > 0:
                contributor_commits.append(commits)
                total_commits += commits
                for week in c.get("weeks", []):
                    lines_added += week.get("a", 0)
                    lines_deleted += week.get("d", 0)

    if not contributor_commits:
        fallback_commits, fallback_warning = await fetch_contributor_summary(client, base_url, headers)
        if fallback_commits:
            contributor_commits = fallback_commits
            total_commits = sum(fallback_commits)
            stats_warnings.append(
                "Using contributor summary fallback for commits; LOC additions/deletions unavailable."
            )
        elif fallback_warning:
            stats_warnings.append(fallback_warning)

    # Calculate Gini Coefficient
    if contributor_commits:
        contributor_commits.sort()
        n = len(contributor_commits)
        if total_commits > 0 and n > 0:
            numerator = sum((i + 1) * c for i, c in enumerate(contributor_commits))
            gini_score = (2 * numerator) / (n * total_commits) - (n + 1) / n
            gini_score = max(0.0, min(gini_score, 1.0))

    # Process Commit Activity
    active_days = 0
    weekly_activity = []
    if activity_data and isinstance(activity_data, list):
        for week in activity_data:
            commits_this_week = week.get("total", 0)
            week_start = datetime.fromtimestamp(week.get("week", 0)).strftime('%Y-%m-%d')
            weekly_activity.append({"week_start": week_start, "commits": commits_this_week})
            
            # Count active days
            active_days += sum(1 for day_count in week.get("days", []) if day_count > 0)

    if not weekly_activity:
        fallback_active_days, fallback_weekly_activity, fallback_warning = await fetch_recent_commit_activity(
            client, base_url, headers
        )
        if fallback_weekly_activity:
            active_days = fallback_active_days
            weekly_activity = fallback_weekly_activity
            stats_warnings.append("Using recent commits fallback for active days and weekly trend.")
        elif fallback_warning:
            stats_warnings.append(fallback_warning)

    # Process Languages
    primary_language = "Unknown"
    language_bytes = {}
    code_bytes = 0
    if languages_resp and languages_resp.status_code == 200:
        try:
            langs = languages_resp.json()
        except ValueError:
            langs = {}
            stats_warnings.append("Languages returned invalid JSON")
        if isinstance(langs, dict) and langs:
            language_bytes = langs
            code_bytes = sum(langs.values())
            primary_language = max(langs, key=langs.get)
    elif languages_resp:
        stats_warnings.append(f"Languages unavailable ({languages_resp.status_code})")

    last_pushed_raw = repo_data.get("pushed_at")
    last_pushed = "N/A"
    if last_pushed_raw:
        try:
            last_pushed = datetime.strptime(last_pushed_raw, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        except ValueError:
            stats_warnings.append("Invalid pushed_at timestamp returned by GitHub")

    # Use stable slug when CSV team_id is unavailable to avoid short-prefix collisions.
    generated_team_id = f"{owner}/{repo}"
    generated_team_slug = f"{owner}-{repo}"

    return {
        "team_id": generated_team_id,
        "team_slug": generated_team_slug,
        "repo_name": repo,
        "total_commits": total_commits,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "active_days": active_days,
        "last_pushed": last_pushed,
        "weekly_activity": weekly_activity,
        "gini_coefficient": gini_score,
        "primary_language": primary_language,
        "language_bytes": language_bytes,
        "code_bytes": code_bytes,
        "rate_limit_remaining": int(rate_limit_remaining) if str(rate_limit_remaining).isdigit() else None,
        "rate_limit_reset_epoch": int(rate_limit_reset) if str(rate_limit_reset).isdigit() else None,
        "stats_warnings": stats_warnings,
        "url": repo_url
    }


if __name__ == "__main__":
    async def _test() -> None:
        async with httpx.AsyncClient(timeout=60.0) as client:
            result = await fetch_repo_details(client, "https://github.com/octocat/Hello-World")
            print(result)

    asyncio.run(_test())
