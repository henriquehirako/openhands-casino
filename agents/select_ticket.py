"""Pick the next ticket for the coder.

Used by the sdlc workflow's janitor job:

    python agents/select_ticket.py   ->  {"number": 12, "title": "..."}  or  {}

Order: skip `hold`, `priority:high` first, then oldest first.
"""

import json
import subprocess
import sys


def pick(issues: list[dict]) -> dict | None:
    """Return the issue to work on next, or None. Pure, testable."""
    candidates = [i for i in issues if "hold" not in _label_names(i)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda i: ("priority:high" not in _label_names(i), i.get("createdAt", ""))
    )
    return candidates[0]


def _label_names(issue: dict) -> set[str]:
    return {label["name"] for label in issue.get("labels", [])}


def fetch_ready_issues() -> list[dict]:
    """Query GitHub for open issues labeled `ready`."""
    out = subprocess.run(
        ["gh", "issue", "list", "--label", "ready", "--state", "open",
         "--json", "number,title,labels,createdAt", "--limit", "100"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def main() -> int:
    chosen = pick(fetch_ready_issues())
    print(json.dumps({"number": chosen["number"], "title": chosen["title"]} if chosen else {}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
