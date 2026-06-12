"""
Entry point.
Usage:
    python main.py                     # fetch + render dashboard.html
    python main.py --no-cache          # ignore cache, re-fetch everything
    python main.py --output report.html
    python main.py --find-fields       # print all Jira custom field IDs (useful for setup)
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

from config import Config
from fetch_jira import JiraClient
from fetch_gitlab import GitLabClient
from analyze import build_report
import dashboard


def main():
    parser = argparse.ArgumentParser(description="Claude Code Impact Dashboard")
    parser.add_argument("--no-cache", action="store_true", help="Delete cache and re-fetch")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file")
    parser.add_argument("--find-fields", action="store_true",
                        help="Print Jira custom field list and exit")
    args = parser.parse_args()

    cfg = Config()

    if args.no_cache and Path(cfg.cache_dir).exists():
        shutil.rmtree(cfg.cache_dir)
        print("[cache] cleared")

    Path(cfg.cache_dir).mkdir(exist_ok=True)

    jira = JiraClient(cfg)
    gitlab = GitLabClient(cfg)

    # ── discover Jira fields ──────────────────────────────────────────────────
    if args.find_fields:
        fields = jira._get("/rest/api/2/field")
        print(f"\n{'ID':<30} {'Name'}")
        print("-" * 60)
        for f in sorted(fields, key=lambda x: x.get("name", "")):
            print(f"{f['id']:<30} {f.get('name', '')}")
        return

    # ── validate ──────────────────────────────────────────────────────────────
    errors = []
    for var in ("jira_url", "jira_token", "gitlab_url", "gitlab_token"):
        if not getattr(cfg, var, None):
            errors.append(f"{var.upper()} not set")
    if not cfg.gitlab_usernames:
        errors.append(
            "GITLAB_USERNAMES not set. Add comma-separated usernames to .env, e.g.:\n"
            "  GITLAB_USERNAMES=ivan.petrov,anna.sidorova"
        )
    if errors:
        print("\n[ERROR] Configuration issues:")
        for e in errors:
            print(f"  • {e}")
        print("\nSee .env.example for setup instructions.")
        sys.exit(1)

    print(f"\nTeam: {cfg.jira_team_value or cfg.jira_project}")
    print(f"GitLab users: {', '.join(cfg.gitlab_usernames)}")

    # ── fetch Jira ────────────────────────────────────────────────────────────
    print("\n=== Fetching Jira data ===")
    epics_q1  = jira.get_epics("q1",  cfg.q1_start, cfg.q1_end)
    epics_q2  = jira.get_epics("q2",  cfg.q2_start, cfg.q2_end)
    issues_q1 = jira.get_issues("q1", cfg.q1_start, cfg.q1_end)
    issues_q2 = jira.get_issues("q2", cfg.q2_start, cfg.q2_end)

    # ── fetch GitLab ──────────────────────────────────────────────────────────
    print("\n=== Fetching GitLab data ===")
    mrs_q1     = gitlab.get_team_mrs("q1",     cfg.q1_start, cfg.q1_end)
    commits_q1 = gitlab.get_team_commits("q1", cfg.q1_start, cfg.q1_end)
    mrs_q2     = gitlab.get_team_mrs("q2",     cfg.q2_start, cfg.q2_end)
    commits_q2 = gitlab.get_team_commits("q2", cfg.q2_start, cfg.q2_end)

    # ── build & render ────────────────────────────────────────────────────────
    print("\n=== Computing metrics ===")
    report = build_report(
        cfg,
        epics_q1, epics_q2,
        issues_q1, issues_q2,
        mrs_q1, mrs_q2,
        commits_q1, commits_q2,
    )

    out = dashboard.render(report, args.output)
    print(f"\n✓ Dashboard written to: {os.path.abspath(out)}")
    print("  Open it in a browser to view.")


if __name__ == "__main__":
    main()
