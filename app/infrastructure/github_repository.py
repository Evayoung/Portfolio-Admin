"""GitHub activity stats for the admin overview."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


@dataclass(frozen=True)
class GitHubStats:
    username: str
    public_repos: int
    followers: int
    stars: int
    recent_commits: int
    source: str


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "neo-admin-github-stats",
    }
    if settings.github_access_token.strip():
        headers["Authorization"] = f"Bearer {settings.github_access_token.strip()}"
    return headers


def _request(path: str) -> object:
    request = Request(f"https://api.github.com{path}", headers=_headers())
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


@lru_cache(maxsize=1)
def get_github_stats() -> GitHubStats:
    username = settings.github_username.strip() or "Evayoung"
    try:
        profile = _request(f"/users/{username}")
        repos = _request(f"/users/{username}/repos?per_page=100&type=owner&sort=updated")
        events = _request(f"/users/{username}/events/public?per_page=100")
        if not isinstance(profile, dict) or not isinstance(repos, list) or not isinstance(events, list):
            raise ValueError("Unexpected GitHub payload.")
        stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos if isinstance(repo, dict))
        recent_commits = sum(
            len((event.get("payload") or {}).get("commits") or [])
            for event in events
            if isinstance(event, dict) and event.get("type") == "PushEvent"
        )
        return GitHubStats(
            username=username,
            public_repos=int(profile.get("public_repos") or 0),
            followers=int(profile.get("followers") or 0),
            stars=stars,
            recent_commits=recent_commits,
            source="github",
        )
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return GitHubStats(
            username=username,
            public_repos=0,
            followers=0,
            stars=0,
            recent_commits=0,
            source="fallback",
        )
