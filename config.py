import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Jira
    jira_url: str = field(default_factory=lambda: os.environ["JIRA_URL"].rstrip("/"))
    jira_token: str = field(default_factory=lambda: os.environ["JIRA_TOKEN"])
    # Project for QBS tasks (issues by status)
    jira_project: str = field(default_factory=lambda: os.environ.get("JIRA_PROJECT", "QBS"))
    # Project for epics
    jira_epics_project: str = field(default_factory=lambda: os.environ.get("JIRA_EPICS_PROJECT", "QPAY"))
    # Team Link field: key of the team (used in epics filter)
    jira_team_key: str = field(default_factory=lambda: os.environ.get("JIRA_TEAM_KEY", ""))

    # GitLab
    gitlab_url: str = field(default_factory=lambda: os.environ["GITLAB_URL"].rstrip("/"))
    gitlab_token: str = field(default_factory=lambda: os.environ["GITLAB_TOKEN"])
    gitlab_group: str = field(default_factory=lambda: os.environ.get("GITLAB_GROUP", ""))

    # Team usernames in GitLab (comma-separated in env, list here)
    gitlab_usernames: list = field(default_factory=list)

    # Periods
    q1_start: str = field(default_factory=lambda: os.environ.get("Q1_START", "2025-01-01"))
    q1_end: str = field(default_factory=lambda: os.environ.get("Q1_END", "2025-03-31"))
    q2_start: str = field(default_factory=lambda: os.environ.get("Q2_START", "2025-04-01"))
    q2_end: str = field(default_factory=lambda: os.environ.get("Q2_END", "2025-06-30"))

    # Cache directory
    cache_dir: str = field(default_factory=lambda: os.environ.get("CACHE_DIR", ".cache"))

    def __post_init__(self):
        if not self.gitlab_usernames:
            raw = os.environ.get("GITLAB_USERNAMES", "")
            self.gitlab_usernames = [u.strip() for u in raw.split(",") if u.strip()]


# ── Edit your team GitLab usernames here (alternative to env var) ──────────────
# GITLAB_USERNAMES = ["ivan.petrov", "anna.sidorova", "dmitry.kovalev"]
# ──────────────────────────────────────────────────────────────────────────────
