"""
GitLab REST API v4 client.
Fetches MRs, commits, and review comments for the whole team (list of usernames).
All results are aggregated at team level — no per-person breakdown.
"""
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests
from dateutil.parser import parse as parse_dt

from config import Config


class GitLabClient:
    def __init__(self, cfg: Config):
        self.base = f"{cfg.gitlab_url}/api/v4"
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers["PRIVATE-TOKEN"] = cfg.gitlab_token
        Path(cfg.cache_dir).mkdir(exist_ok=True)

    # ── low-level ──────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base}{path}"
        for attempt in range(5):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(int(resp.headers.get("Retry-After", 2 ** attempt)))
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Too many retries: {url}")

    def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results, page = [], 1
        while True:
            params["page"] = page
            data = self._get(path, params)
            if not data:
                break
            results.extend(data)
            if len(data) < params["per_page"]:
                break
            page += 1
        return results

    # ── cache ──────────────────────────────────────────────────────────────────

    def _cache(self, key: str) -> Path:
        return Path(self.cfg.cache_dir) / f"gitlab_{key}.json"

    def _load(self, key: str) -> Any | None:
        p = self._cache(key)
        return json.loads(p.read_text()) if p.exists() else None

    def _save(self, key: str, data: Any):
        self._cache(key).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── projects ───────────────────────────────────────────────────────────────

    def get_group_projects(self) -> list[dict]:
        cached = self._load("projects")
        if cached is not None:
            return cached
        group = urllib.parse.quote(self.cfg.gitlab_group.strip("/"), safe="")
        projects = self._paginate(
            f"/groups/{group}/projects",
            {"include_subgroups": "true", "archived": "false"},
        )
        self._save("projects", projects)
        return projects

    # ── team MRs ──────────────────────────────────────────────────────────────

    def get_team_mrs(self, period: str, start: str, end: str) -> list[dict]:
        """Fetch merged MRs by any team member across all group projects."""
        cached = self._load(f"mrs_{period}")
        if cached is not None:
            print(f"[gitlab] MRs {period}: loaded from cache ({len(cached)} items)")
            return cached

        projects = self.get_group_projects()
        mrs: list[dict] = []

        for proj in projects:
            pid = proj["id"]
            # Fetch MRs per username (GitLab API filters by one author at a time)
            for username in self.cfg.gitlab_usernames:
                raw = self._paginate(f"/projects/{pid}/merge_requests", {
                    "author_username": username,
                    "state": "merged",
                    "created_after": f"{start}T00:00:00Z",
                    "created_before": f"{end}T23:59:59Z",
                })
                for mr in raw:
                    parsed = self._parse_mr(mr, proj["path_with_namespace"], username)
                    parsed["comments"] = self._get_mr_comments(pid, mr["iid"])
                    mrs.append(parsed)

        self._save(f"mrs_{period}", mrs)
        print(f"[gitlab] MRs {period}: fetched {len(mrs)} items across {len(self.cfg.gitlab_usernames)} users")
        return mrs

    # ── team commits ──────────────────────────────────────────────────────────

    def get_team_commits(self, period: str, start: str, end: str) -> list[dict]:
        """Fetch commits by all team members across all group projects."""
        cached = self._load(f"commits_{period}")
        if cached is not None:
            print(f"[gitlab] commits {period}: loaded from cache ({len(cached)} items)")
            return cached

        projects = self.get_group_projects()
        commits: list[dict] = []

        for proj in projects:
            pid = proj["id"]
            for username in self.cfg.gitlab_usernames:
                raw = self._paginate(f"/projects/{pid}/repository/commits", {
                    "author": username,
                    "since": f"{start}T00:00:00Z",
                    "until": f"{end}T23:59:59Z",
                })
                for c in raw:
                    commits.append({
                        "id": c["id"],
                        "author": username,
                        "date": c["created_at"][:10],
                        "hour": parse_dt(c["created_at"]).hour,
                        "project": proj["path_with_namespace"],
                    })

        self._save(f"commits_{period}", commits)
        print(f"[gitlab] commits {period}: fetched {len(commits)} items")
        return commits

    # ── helpers ────────────────────────────────────────────────────────────────

    def _parse_mr(self, raw: dict, project_path: str, author: str) -> dict:
        created = parse_dt(raw["created_at"])
        merged = parse_dt(raw["merged_at"]) if raw.get("merged_at") else None
        review_hours = (merged - created).total_seconds() / 3600 if merged else None
        return {
            "iid": raw["iid"],
            "project": project_path,
            "author": author,
            "title": raw["title"][:80],
            "state": raw["state"],
            "created_at": raw["created_at"][:10],
            "merged_at": (raw.get("merged_at") or "")[:10],
            "diff_size": (raw.get("additions") or 0) + (raw.get("deletions") or 0),
            "review_hours": round(review_hours, 2) if review_hours is not None else None,
        }

    def _get_mr_comments(self, project_id: int, mr_iid: int) -> list[dict]:
        notes = self._paginate(f"/projects/{project_id}/merge_requests/{mr_iid}/notes")
        return [
            {
                "author": n.get("author", {}).get("username", ""),
                "body": n.get("body", "")[:300],
                "created_at": n["created_at"][:10],
                "resolvable": n.get("resolvable", False),
                "resolved": n.get("resolved", False),
            }
            for n in notes if not n.get("system")
        ]
