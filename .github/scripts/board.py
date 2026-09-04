"""Move a GitHub issue to a Status column on the project board.

Usage:
    python .github/scripts/board.py <issue-number> <status-name>

Example:
    python .github/scripts/board.py 12 "In Progress"

The board is GitHub project number 1 owned by user henriquehirako. The
issue belongs to repo henriquehirako/openhands-casino. The workflows
sdlc.yml and watchdog.yml call this script after each agent step so the
board mirrors the ticket labels.

Auth comes from the env var PROJECT_TOKEN. The default GITHUB_TOKEN has
no project scope. If PROJECT_TOKEN is unset or empty the script prints a
notice and exits 0, so a missing token never fails a workflow.

Exit codes: 0 done or skipped, 1 gh failure, 2 unknown status name.
"""

import json
import os
import subprocess
import sys

OWNER = "henriquehirako"
REPO = "henriquehirako/openhands-casino"
PROJECT_NUMBER = "1"
PROJECT_ID = "PVT_kwHOADH4Ks4BiZ78"
STATUS_FIELD_ID = "PVTSSF_lAHOADH4Ks4BiZ78zhhSIGk"


def gh(args: list[str], token: str) -> str:
    """Run a gh command with GH_TOKEN set. Return stdout, exit 1 on failure."""
    env = dict(os.environ)
    env["GH_TOKEN"] = token
    result = subprocess.run(["gh", *args], env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout


def add_item(issue: int, token: str) -> str:
    """Add the issue to the project (idempotent) and return the item id."""
    url = f"https://github.com/{REPO}/issues/{issue}"
    out = gh(
        ["project", "item-add", PROJECT_NUMBER, "--owner", OWNER, "--url", url, "--format", "json"],
        token,
    )
    return json.loads(out)["id"]


def status_options(token: str) -> dict[str, str]:
    """Return the Status field options as {lowercase name: option id}."""
    out = gh(["project", "field-list", PROJECT_NUMBER, "--owner", OWNER, "--format", "json"], token)
    for field in json.loads(out)["fields"]:
        if field["name"] == "Status":
            return {opt["name"].lower(): opt["id"] for opt in field["options"]}
    print("board: project has no Status field", file=sys.stderr)
    sys.exit(1)


def set_status(item_id: str, option_id: str, token: str) -> None:
    """Set the Status single-select field on one project item."""
    gh(
        [
            "project", "item-edit",
            "--id", item_id,
            "--project-id", PROJECT_ID,
            "--field-id", STATUS_FIELD_ID,
            "--single-select-option-id", option_id,
        ],
        token,
    )


def main() -> None:
    """Parse args, then add the issue to the board and set its Status."""
    if len(sys.argv) != 3:
        print("usage: board.py <issue-number> <status-name>", file=sys.stderr)
        sys.exit(2)
    issue = int(sys.argv[1])
    status = sys.argv[2]

    token = os.environ.get("PROJECT_TOKEN", "")
    if not token:
        print("board: no PROJECT_TOKEN, skipped")
        return

    options = status_options(token)
    option_id = options.get(status.lower())
    if option_id is None:
        names = ", ".join(sorted(options))
        print(f"board: unknown status '{status}'. Valid: {names}", file=sys.stderr)
        sys.exit(2)

    item_id = add_item(issue, token)
    set_status(item_id, option_id, token)
    print(f"board: #{issue} -> {status}")


if __name__ == "__main__":
    main()
