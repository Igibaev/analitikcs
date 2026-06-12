import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Member:
    name: str
    role: str                    # "dev" | "qa"
    jira_account_id: str         # Jira accountId (get via /rest/api/2/user/search)
    gitlab_username: str         # GitLab username
    initials: str = ""
    color: str = "#6366f1"

    def __post_init__(self):
        if not self.initials:
            parts = self.name.split()
            self.initials = "".join(p[0] for p in parts[:2]).upper()


@dataclass
class Config:
    # Jira
    jira_url: str = field(default_factory=lambda: os.environ["JIRA_URL"].rstrip("/"))
    jira_user: str = field(default_factory=lambda: os.environ["JIRA_USER"])
    jira_token: str = field(default_factory=lambda: os.environ["JIRA_TOKEN"])
    jira_project: str = field(default_factory=lambda: os.environ.get("JIRA_PROJECT", "QBS"))
    jira_team_field: str = field(default_factory=lambda: os.environ.get("JIRA_TEAM_FIELD", "customfield_10100"))
    jira_team_value: str = field(default_factory=lambda: os.environ.get("JIRA_TEAM_VALUE", ""))

    # GitLab
    gitlab_url: str = field(default_factory=lambda: os.environ["GITLAB_URL"].rstrip("/"))
    gitlab_token: str = field(default_factory=lambda: os.environ["GITLAB_TOKEN"])
    # GitLab group or project IDs/paths where team works; comma-separated
    gitlab_group: str = field(default_factory=lambda: os.environ.get("GITLAB_GROUP", ""))

    # Periods
    q1_start: str = field(default_factory=lambda: os.environ.get("Q1_START", "2025-01-01"))
    q1_end: str = field(default_factory=lambda: os.environ.get("Q1_END", "2025-03-31"))
    q2_start: str = field(default_factory=lambda: os.environ.get("Q2_START", "2025-04-01"))
    q2_end: str = field(default_factory=lambda: os.environ.get("Q2_END", "2025-06-30"))

    # Cache directory
    cache_dir: str = field(default_factory=lambda: os.environ.get("CACHE_DIR", ".cache"))

    # Team members — edit this list to match your team
    members: list = field(default_factory=list)

    def __post_init__(self):
        if not self.members:
            self.members = TEAM_MEMBERS


# ── Edit your team here ────────────────────────────────────────────────────────
TEAM_MEMBERS: list[Member] = [
    # Member(
    #     name="Ivan Petrov",
    #     role="dev",
    #     jira_account_id="5f3e...abc",   # from Jira user search
    #     gitlab_username="ivan.petrov",
    #     color="#6366f1",
    # ),
    # Member(
    #     name="Anna Sidorova",
    #     role="qa",
    #     jira_account_id="6a1b...xyz",
    #     gitlab_username="anna.sidorova",
    #     color="#dc2626",
    # ),
]
# ──────────────────────────────────────────────────────────────────────────────
