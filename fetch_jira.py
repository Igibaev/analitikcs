"""
Jira REST API v2 client.
Pulls epics and issues for the team, caches results to JSON.
"""
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from config import Config


class JiraClient:
    def __init__(self, cfg: Config):
        self.base = cfg.jira_url
        self.auth = HTTPBasicAuth(cfg.jira_user, cfg.jira_token)
        self.cfg = cfg
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers["Accept"] = "application/json"
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

    def _search(self, jql: str, fields: list[str]) -> list[dict]:
        """Paginated JQL search — returns all issues."""
        results, start = [], 0
        page_size = 100
        while True:
            data = self._get("/rest/api/2/search", {
                "jql": jql,
                "startAt": start,
                "maxResults": page_size,
                "fields": ",".join(fields),
            })
            results.extend(data["issues"])
            start += len(data["issues"])
            if start >= data["total"]:
                break
        return results

    # ── cache helpers ──────────────────────────────────────────────────────────

    def _cache_path(self, key: str) -> Path:
        return Path(self.cfg.cache_dir) / f"jira_{key}.json"

    def _load_cache(self, key: str) -> Any | None:
        p = self._cache_path(key)
        if p.exists():
            return json.loads(p.read_text())
        return None

    def _save_cache(self, key: str, data: Any):
        self._cache_path(key).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── public API ─────────────────────────────────────────────────────────────

    def discover_field_id(self, field_name: str) -> str | None:
        """Find the customfield_XXXXX id for a field by name."""
        fields = self._get("/rest/api/2/field")
        for f in fields:
            if f.get("name", "").lower() == field_name.lower():
                return f["id"]
        return None

    def get_epics(self, period: str, start: str, end: str) -> list[dict]:
        """Return epics for the project/team updated in the given date range."""
        cache_key = f"epics_{period}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            print(f"[jira] epics {period}: loaded from cache ({len(cached)} items)")
            return cached

        jql = self._build_jql("Epic", start, end)
        fields = [
            "summary", "status", "created", "resolutiondate",
            "assignee", "priority", "subtasks",
            self.cfg.jira_team_field,
        ]
        raw = self._search(jql, fields)
        epics = [self._parse_epic(i) for i in raw]
        self._save_cache(cache_key, epics)
        print(f"[jira] epics {period}: fetched {len(epics)} items")
        return epics

    def get_issues(self, period: str, start: str, end: str) -> list[dict]:
        """Return all issues (all types) for the project/team updated in the date range."""
        cache_key = f"issues_{period}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            print(f"[jira] issues {period}: loaded from cache ({len(cached)} items)")
            return cached

        jql = self._build_jql(None, start, end)
        fields = [
            "summary", "issuetype", "status", "created", "resolutiondate",
            "assignee", "priority", "customfield_10014",  # epic link (classic)
            "parent",                                      # epic link (next-gen)
            self.cfg.jira_team_field,
        ]
        raw = self._search(jql, fields)
        issues = [self._parse_issue(i) for i in raw]
        self._save_cache(cache_key, issues)
        print(f"[jira] issues {period}: fetched {len(issues)} items")
        return issues

    def get_changelogs(self, issue_key: str) -> list[dict]:
        """Fetch status transition history for a single issue (for cycle time)."""
        data = self._get(
            f"/rest/api/2/issue/{issue_key}",
            {"expand": "changelog", "fields": "status"},
        )
        transitions = []
        for history in data.get("changelog", {}).get("histories", []):
            for item in history.get("items", []):
                if item["field"] == "status":
                    transitions.append({
                        "date": history["created"],
                        "from": item["fromString"],
                        "to": item["toString"],
                    })
        return transitions

    # ── helpers ────────────────────────────────────────────────────────────────

    def _build_jql(self, issue_types: str | None, start: str, end: str) -> str:
        parts = [
            f'project = "{self.cfg.jira_project}"',
            f'updated >= "{start}"',
            f'updated <= "{end}"',
        ]
        if issue_types:
            parts.append(f'issuetype in ({issue_types})')
        if self.cfg.jira_team_value and self.cfg.jira_team_field:
            parts.append(
                f'"Team Link" = "{self.cfg.jira_team_value}"'
            )
        jql = " AND ".join(parts) + " ORDER BY updated ASC"
        print(f"[jira] JQL: {jql}")
        return jql

    def _parse_epic(self, raw: dict) -> dict:
        fields = raw["fields"]
        created = fields.get("created", "")[:10]
        resolved = (fields.get("resolutiondate") or "")[:10]
        cycle_days = None
        if created and resolved:
            from dateutil.parser import parse
            cycle_days = (parse(resolved) - parse(created)).days
        return {
            "key": raw["key"],
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "created": created,
            "resolved": resolved,
            "cycle_days": cycle_days,
            "assignee": (fields.get("assignee") or {}).get("displayName", ""),
            "subtask_count": len(fields.get("subtasks", [])),
        }

    def _parse_issue(self, raw: dict) -> dict:
        fields = raw["fields"]
        created = fields.get("created", "")[:10]
        resolved = (fields.get("resolutiondate") or "")[:10]
        cycle_days = None
        if created and resolved:
            from dateutil.parser import parse
            cycle_days = (parse(resolved) - parse(created)).days
        # Epic link: classic Jira uses customfield_10014, next-gen uses parent
        epic_key = fields.get("customfield_10014") or (
            (fields.get("parent") or {}).get("key")
        )
        return {
            "key": raw["key"],
            "summary": fields.get("summary", ""),
            "type": fields.get("issuetype", {}).get("name", ""),
            "status": fields.get("status", {}).get("name", ""),
            "created": created,
            "resolved": resolved,
            "cycle_days": cycle_days,
            "assignee": (fields.get("assignee") or {}).get("displayName", ""),
            "epic_key": epic_key,
        }
