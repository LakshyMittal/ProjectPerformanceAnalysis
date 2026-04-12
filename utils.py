from typing import Tuple, Optional
from urllib.parse import urlparse


def normalize_repo_url(url: str) -> str:
    """Normalize GitHub URLs for stable cache keys and CSV merges."""
    return str(url).strip().rstrip("/")


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses a GitHub URL to extract owner and repo name.
    Handles .git extension and trailing slashes.
    Returns (owner, repo) tuple or (None, None) on failure.
    """
    normalized = normalize_repo_url(url)
    parsed = urlparse(normalized)

    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
        "github.com",
        "www.github.com",
    }:
        return None, None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None, None

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        return None, None

    return owner, repo
