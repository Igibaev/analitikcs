"""
Compute all metrics from raw Jira + GitLab data.
Returns a single dict that the dashboard renderer consumes.
"""
import statistics
from collections import defaultdict
from datetime import date, timedelta
from dateutil.parser import parse as parse_dt

from config import Config, Member


# ── Jira metrics ───────────────────────────────────────────────────────────────

def epic_metrics(epics: list[dict]) -> dict:
    done = [e for e in epics if e["status"].lower() in ("done", "closed", "resolved")]
    cycle_times = [e["cycle_days"] for e in done if e["cycle_days"] is not None]
    return {
        "total": len(epics),
        "done": len(done),
        "in_progress": len([e for e in epics if "progress" in e["status"].lower()]),
        "overdue": len([e for e in epics
                        if e["status"].lower() not in ("done", "closed", "resolved")
                        and e.get("resolved")]),
        "avg_cycle_days": round(statistics.mean(cycle_times), 1) if cycle_times else None,
        "median_cycle_days": round(statistics.median(cycle_times), 1) if cycle_times else None,
        "epics": epics,
    }


def issue_status_breakdown(issues: list[dict]) -> dict:
    """Group issues by status, count, avg cycle time per status."""
    by_status: dict[str, list] = defaultdict(list)
    for issue in issues:
        by_status[issue["status"]].append(issue)

    result = {}
    for status, items in by_status.items():
        cycles = [i["cycle_days"] for i in items if i.get("cycle_days") is not None]
        result[status] = {
            "count": len(items),
            "avg_cycle_days": round(statistics.mean(cycles), 1) if cycles else None,
        }
    return result


def monthly_issue_counts(issues: list[dict]) -> dict[str, dict[str, int]]:
    """{ "2025-01": { "Done": 12, "In Progress": 3, ... }, ... }"""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for issue in issues:
        month = issue["created"][:7]  # YYYY-MM
        counts[month][issue["status"]] += 1
    return {k: dict(v) for k, v in sorted(counts.items())}


# ── GitLab metrics ─────────────────────────────────────────────────────────────

def mr_metrics(mrs: list[dict]) -> dict:
    diff_sizes = [m["diff_size"] for m in mrs if m["diff_size"]]
    review_hours = [m["review_hours"] for m in mrs if m["review_hours"] is not None]

    # First-pass: MRs with 0 resolvable comments from reviewers
    first_pass = sum(
        1 for m in mrs
        if not any(
            c["resolvable"] and not c["resolved"]
            for c in m.get("comments", [])
        )
    )

    # Comment classification (simple keyword heuristics)
    crit, nitpick, approval = 0, 0, 0
    for m in mrs:
        for c in m.get("comments", []):
            body = c["body"].lower()
            if any(w in body for w in ("bug", "error", "wrong", "broken", "crash", "fail", "security")):
                crit += 1
            elif any(w in body for w in ("nit:", "nitpick", "style", "naming", "typo", "format", "lint")):
                nitpick += 1
            elif any(w in body for w in ("lgtm", "looks good", "approved", "nice", "great", ":+1:", "👍")):
                approval += 1

    n = len(mrs) or 1
    return {
        "count": len(mrs),
        "median_diff_size": round(statistics.median(diff_sizes), 0) if diff_sizes else 0,
        "p90_diff_size": round(sorted(diff_sizes)[int(len(diff_sizes) * 0.9)], 0) if diff_sizes else 0,
        "avg_review_hours": round(statistics.mean(review_hours), 2) if review_hours else 0,
        "median_review_hours": round(statistics.median(review_hours), 2) if review_hours else 0,
        "first_pass_rate": round(first_pass / n * 100, 1),
        "avg_critical_comments": round(crit / n, 2),
        "avg_nitpick_comments": round(nitpick / n, 2),
        "avg_approval_comments": round(approval / n, 2),
    }


def commit_metrics(commits: list[dict], start: str, end: str) -> dict:
    weeks = max(1, (parse_dt(end) - parse_dt(start)).days // 7)
    by_week: dict[int, int] = defaultdict(int)
    for c in commits:
        d = parse_dt(c["date"])
        week_num = (d - parse_dt(start)).days // 7
        by_week[week_num] += 1

    weekly_counts = [by_week.get(w, 0) for w in range(weeks)]
    return {
        "total": len(commits),
        "per_week": round(len(commits) / weeks, 1),
        "weekly_counts": weekly_counts,
    }


def weekly_mr_counts(mrs: list[dict], start: str, end: str) -> list[int]:
    weeks = max(1, (parse_dt(end) - parse_dt(start)).days // 7)
    by_week: dict[int, int] = defaultdict(int)
    for m in mrs:
        d = parse_dt(m["created_at"])
        week_num = (d - parse_dt(start)).days // 7
        by_week[week_num] += 1
    return [by_week.get(w, 0) for w in range(weeks)]


# ── Per-member aggregation ─────────────────────────────────────────────────────

def member_stats(
    member: Member,
    mrs_q1: list[dict], commits_q1: list[dict],
    mrs_q2: list[dict], commits_q2: list[dict],
    q1_start: str, q1_end: str,
    q2_start: str, q2_end: str,
) -> dict:
    m1 = mr_metrics(mrs_q1)
    m2 = mr_metrics(mrs_q2)
    c1 = commit_metrics(commits_q1, q1_start, q1_end)
    c2 = commit_metrics(commits_q2, q2_start, q2_end)

    weeks_q1 = max(1, (parse_dt(q1_end) - parse_dt(q1_start)).days // 7)
    weeks_q2 = max(1, (parse_dt(q2_end) - parse_dt(q2_start)).days // 7)

    return {
        "name": member.name,
        "role": member.role,
        "initials": member.initials,
        "color": member.color,
        "q1": {
            "mr_per_week": round(m1["count"] / weeks_q1, 1),
            "median_diff_size": m1["median_diff_size"],
            "commits_per_week": c1["per_week"],
            "avg_review_hours": m1["avg_review_hours"],
            "first_pass_rate": m1["first_pass_rate"],
            "avg_critical_comments": m1["avg_critical_comments"],
        },
        "q2": {
            "mr_per_week": round(m2["count"] / weeks_q2, 1),
            "median_diff_size": m2["median_diff_size"],
            "commits_per_week": c2["per_week"],
            "avg_review_hours": m2["avg_review_hours"],
            "first_pass_rate": m2["first_pass_rate"],
            "avg_critical_comments": m2["avg_critical_comments"],
        },
        "weekly_commits_q1": c1["weekly_counts"],
        "weekly_commits_q2": c2["weekly_counts"],
    }


# ── Top-level aggregation ──────────────────────────────────────────────────────

def delta(q1_val, q2_val, invert: bool = False) -> dict:
    """Return formatted delta dict for dashboard rendering."""
    if q1_val is None or q2_val is None:
        return {"raw": None, "label": "—", "positive": None}
    diff = q2_val - q1_val
    pct = round(diff / q1_val * 100, 1) if q1_val else 0
    arrow = "▲" if diff > 0 else "▼"
    positive = (diff > 0) if not invert else (diff < 0)
    sign = "+" if diff > 0 else ""
    return {
        "raw": round(diff, 2),
        "pct": pct,
        "label": f"{arrow} {sign}{round(diff, 1)} ({sign}{pct}%)",
        "positive": positive,
    }


def build_report(
    cfg: Config,
    epics_q1: list[dict], epics_q2: list[dict],
    issues_q1: list[dict], issues_q2: list[dict],
    members_data: list[dict],
) -> dict:
    em1 = epic_metrics(epics_q1)
    em2 = epic_metrics(epics_q2)
    sb1 = issue_status_breakdown(issues_q1)
    sb2 = issue_status_breakdown(issues_q2)
    mc1 = monthly_issue_counts(issues_q1)
    mc2 = monthly_issue_counts(issues_q2)

    # Aggregate GitLab across all devs
    all_mrs_q1 = [mr for m in members_data for mr in m.get("_mrs_q1", [])]
    all_mrs_q2 = [mr for m in members_data for mr in m.get("_mrs_q2", [])]
    team_mr1 = mr_metrics(all_mrs_q1)
    team_mr2 = mr_metrics(all_mrs_q2)

    all_commits_q1 = [c for m in members_data for c in m.get("_commits_q1", [])]
    all_commits_q2 = [c for m in members_data for c in m.get("_commits_q2", [])]
    team_c1 = commit_metrics(all_commits_q1, cfg.q1_start, cfg.q1_end)
    team_c2 = commit_metrics(all_commits_q2, cfg.q2_start, cfg.q2_end)

    return {
        "team_name": cfg.jira_team_value or cfg.jira_project,
        "q1_label": f"{cfg.q1_start} – {cfg.q1_end}",
        "q2_label": f"{cfg.q2_start} – {cfg.q2_end}",
        # KPI
        "kpi": {
            "epics_done": {"q1": em1["done"], "q2": em2["done"],
                           "delta": delta(em1["done"], em2["done"])},
            "cycle_days": {"q1": em1["avg_cycle_days"], "q2": em2["avg_cycle_days"],
                           "delta": delta(em1["avg_cycle_days"], em2["avg_cycle_days"], invert=True)},
            "diff_size": {"q1": team_mr1["median_diff_size"], "q2": team_mr2["median_diff_size"],
                          "delta": delta(team_mr1["median_diff_size"], team_mr2["median_diff_size"], invert=True)},
            "review_hours": {"q1": team_mr1["avg_review_hours"], "q2": team_mr2["avg_review_hours"],
                             "delta": delta(team_mr1["avg_review_hours"], team_mr2["avg_review_hours"], invert=True)},
            "commits_per_week": {"q1": team_c1["per_week"], "q2": team_c2["per_week"],
                                 "delta": delta(team_c1["per_week"], team_c2["per_week"])},
        },
        # Charts
        "weekly_commits_q1": team_c1["weekly_counts"],
        "weekly_commits_q2": team_c2["weekly_counts"],
        # Epics
        "epics_q1": em1,
        "epics_q2": em2,
        # QBS issues
        "qbs": {
            "total_q1": len(issues_q1),
            "total_q2": len(issues_q2),
            "status_q1": sb1,
            "status_q2": sb2,
            "monthly_q1": mc1,
            "monthly_q2": mc2,
            "done_rate_q1": round(sb1.get("Done", {}).get("count", 0) / max(len(issues_q1), 1) * 100, 1),
            "done_rate_q2": round(sb2.get("Done", {}).get("count", 0) / max(len(issues_q2), 1) * 100, 1),
        },
        # Review quality
        "review": {
            "q1": team_mr1,
            "q2": team_mr2,
        },
        # Per-member
        "members": [m for m in members_data if "_mrs_q1" not in m],
    }
