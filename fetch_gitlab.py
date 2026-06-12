"""
GitLab REST API v4 client.
Pulls MRs, commits, and review comments per team member, caches to JSON.
"""
import json
import time
from pathlib import Path
from typing import Any

import requests
from dateutil.parser import parse as parse_dt

from config import Config, Member


class GitLabClient:
    def __init__(self, cfg: Config):
        self.base = f"{cfg.gitlab_url}/api/v4"
        self.headers = {"PRIVATE-TOKEN": cfg.gitlab_token}
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        Path(cfg.cache_dir).mkdir(exist_ok=True)

    # ── low-level ──────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base}{path}"
        for attempt in range(5):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Too many retries for {url}")

    def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch all pages for a list endpoint."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results = []
        page = 1
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

    # ── cache helpers ──────────────────────────────────────────────────────────

    def _cache_path(self, key: str) -> Path:
        return Path(self.cfg.cache_dir) / f"gitlab_{key}.json"

    def _load_cache(self, key: str) -> Any | None:
        p = self._cache_path(key)
        if p.exists():
            return json.loads(p.read_text())
        return None

    def _save_cache(self, key: str, data: Any):
        self._cache_path(key).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── group / project discovery ──────────────────────────────────────────────

    def get_group_projects(self) -> list[dict]:
        """Return all projects in the configured group."""
        cache_key = "projects"
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached
        group = self.cfg.gitlab_group.strip("/")
        import urllib.parse
        group_encoded = urllib.parse.quote(group, safe="")
        projects = self._paginate(
            f"/groups/{group_encoded}/projects",
            {"include_subgroups": "true", "archived": "false"},
        )
        self._save_cache(cache_key, projects)
        return projects

    # ── MRs ───────────────────────────────────────────────────────────────────

    def get_mrs_for_member(self, member: Member, period: str, start: str, end: str) -> list[dict]:
        """Fetch all merged/closed MRs authored by member in the date range."""
        cache_key = f"mrs_{member.gitlab_username}_{period}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            print(f"[gitlab] MRs {member.name} {period}: loaded from cache ({len(cached)} items)")
            return cached

        projects = self.get_group_projects()
        mrs = []
        for proj in projects:
            pid = proj["id"]
            raw = self._paginate(f"/projects/{pid}/merge_requests", {
                "author_username": member.gitlab_username,
                "state": "merged",
                "created_after": f"{start}T00:00:00Z",
                "created_before": f"{end}T23:59:59Z",
            })
            for mr in raw:
                parsed = self._parse_mr(mr, proj["path_with_namespace"])
                # fetch notes (comments) for this MR
                parsed["comments"] = self._get_mr_comments(pid, mr["iid"])
                mrs.append(parsed)

        self._save_cache(cache_key, mrs)
        print(f"[gitlab] MRs {member.name} {period}: fetched {len(mrs)} items")
        return mrs

    def get_commits_for_member(self, member: Member, period: str, start: str, end: str) -> list[dict]:
        """Fetch all commits by member across group projects in date range."""
        cache_key = f"commits_{member.gitlab_username}_{period}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            print(f"[gitlab] commits {member.name} {period}: loaded from cache ({len(cached)} items)")
            return cached

        projects = self.get_group_projects()
        commits = []
        for proj in projects:
            pid = proj["id"]
            raw = self._paginate(f"/projects/{pid}/repository/commits", {
                "author": member.gitlab_username,
                "since": f"{start}T00:00:00Z",
                "until": f"{end}T23:59:59Z",
            })
            for c in raw:
                commits.append({
                    "id": c["id"],
                    "date": c["created_at"][:10],
                    "hour": parse_dt(c["created_at"]).hour,
                    "project": proj["path_with_namespace"],
                    "title": c.get("title", "")[:80],
                })

        self._save_cache(cache_key, commits)
        print(f"[gitlab] commits {member.name} {period}: fetched {len(commits)} items")
        return commits

    # ── helpers ────────────────────────────────────────────────────────────────

    def _parse_mr(self, raw: dict, project_path: str) -> dict:
        created = parse_dt(raw["created_at"])
        merged = parse_dt(raw["merged_at"]) if raw.get("merged_at") else None
        review_hours = (merged - created).total_seconds() / 3600 if merged else None

        return {
            "iid": raw["iid"],
            "project": project_path,
            "title": raw["title"][:80],
            "state": raw["state"],
            "created_at": raw["created_at"][:10],
            "merged_at": (raw.get("merged_at") or "")[:10],
            "additions": raw.get("changes_count") or 0,  # lines added+deleted summary
            "diff_size": (raw.get("additions") or 0) + (raw.get("deletions") or 0),
            "review_hours": round(review_hours, 2) if review_hours is not None else None,
            "iterations": raw.get("user_notes_count", 0),  # refined in analyze
            "first_pass": False,  # refined after comments loaded
        }

    def _get_mr_comments(self, project_id: int, mr_iid: int) -> list[dict]:
        notes = self._paginate(f"/projects/{project_id}/merge_requests/{mr_iid}/notes")
        result = []
        for n in notes:
            if n.get("system"):
                continue
            result.append({
                "author": n.get("author", {}).get("username", ""),
                "body": n.get("body", "")[:300],
                "created_at": n["created_at"][:10],
                "resolvable": n.get("resolvable", False),
                "resolved": n.get("resolved", False),
            })
        return result
