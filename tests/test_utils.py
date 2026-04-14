from utils import normalize_repo_url, parse_github_url


def test_normalize_repo_url_trims_spaces_and_trailing_slash() -> None:
    assert normalize_repo_url(" https://github.com/a/b/ ") == "https://github.com/a/b"


def test_parse_github_url_valid_https() -> None:
    assert parse_github_url("https://github.com/LakshyMittal/pontis") == ("LakshyMittal", "pontis")


def test_parse_github_url_valid_www_and_git_suffix() -> None:
    assert parse_github_url("https://www.github.com/org/repo.git") == ("org", "repo")


def test_parse_github_url_rejects_non_github_domain() -> None:
    assert parse_github_url("https://gitlab.com/org/repo") == (None, None)


def test_parse_github_url_rejects_missing_repo_segment() -> None:
    assert parse_github_url("https://github.com/owner") == (None, None)


def test_parse_github_url_rejects_invalid_scheme() -> None:
    assert parse_github_url("ftp://github.com/org/repo") == (None, None)
