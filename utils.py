def parse_github_url(url):
    """
    Parses a GitHub URL to extract owner and repo name.
    Handles .git extension and trailing slashes.
    """
    try:
        parts = url.rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo
    except Exception:
        return None, None