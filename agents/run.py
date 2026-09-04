#!/usr/bin/env python3
"""Run one agent role.

    python agents/run.py <role> [--issue N] [--pr N] [--fix findings.json]
                                [--evidence evidence.json] [--gap gap.json]
                                [--dry-run]

Loads agents/roles/<role>.md, gathers context with gh, calls `claude -p`
with the role's allowed tools, then writes a report to the PR or issue and
to $GITHUB_STEP_SUMMARY. Machine-readable results go to $GITHUB_OUTPUT:
pr, issue, verdict. Same command locally and in GitHub Actions.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLES = ROOT / "agents" / "roles"
CONTRACTS = ["DEFINITION_OF_DONE.md", "CONVENTIONS.md"]

# Tools each role may call. Coder edits and pushes. Reviewers only read
# and post reviews. Janitor and watchdog only file issues. Non-coders get
# Write only for their own ticket or review body file under /tmp.
ALLOWED_TOOLS = {
    "coder": [
        "Read", "Glob", "Grep", "Edit", "Write",
        "Bash(git *)", "Bash(gh pr *)", "Bash(gh issue view*)",
        "Bash(python*)", "Bash(pip*)", "Bash(ls*)", "Bash(cat*)",
    ],
    "reviewer": [
        "Read", "Glob", "Grep", "Write",
        "Bash(git diff*)", "Bash(git log*)", "Bash(gh pr view*)",
        "Bash(gh pr diff*)", "Bash(gh pr review*)", "Bash(gh issue view*)",
        "Bash(python -m pytest*)", "Bash(grep*)", "Bash(ls*)", "Bash(cat*)",
    ],
    "janitor": ["Read", "Glob", "Grep", "Write", "Bash(gh issue *)"],
    "watchdog": ["Read", "Write", "Bash(gh issue *)"],
}
ALLOWED_TOOLS["security"] = ALLOWED_TOOLS["reviewer"]
MAX_TURNS = {"coder": 120, "reviewer": 40, "security": 40, "janitor": 20, "watchdog": 20}


def sh(*cmd: str, check: bool = True, env: dict | None = None) -> str:
    """Run a command and return stdout. Used for gh and git lookups."""
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    if check and res.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} failed:\n{res.stderr}")
    return res.stdout


def gh_json(*args: str) -> dict:
    """Call gh with --json and parse the result."""
    return json.loads(sh("gh", *args))


def gather_context(args: argparse.Namespace) -> str:
    """Build the context block: contracts, ticket, PR, findings, evidence."""
    parts = []
    for name in CONTRACTS:
        parts.append(f"## {name}\n\n{(ROOT / name).read_text()}")
    if args.issue:
        issue = gh_json("issue", "view", str(args.issue), "--json", "number,title,body,labels")
        labels = ", ".join(l["name"] for l in issue["labels"])
        parts.append(f"## Ticket #{issue['number']}: {issue['title']}\n\nLabels: {labels}\n\n{issue['body']}")
    if args.pr:
        pr = gh_json("pr", "view", str(args.pr), "--json", "number,title,body,headRefName,baseRefName")
        parts.append(
            f"## PR #{pr['number']}: {pr['title']}\n\nBranch `{pr['headRefName']}` into `{pr['baseRefName']}`\n\n{pr['body']}"
        )
        diff = sh("gh", "pr", "diff", str(args.pr))
        parts.append(f"## PR diff\n\n```diff\n{diff}\n```")
        m = re.search(r"[Cc]loses #(\d+)", pr["body"] or "")
        if m and not args.issue:
            issue = gh_json("issue", "view", m.group(1), "--json", "number,title,body")
            parts.append(f"## Ticket #{issue['number']}: {issue['title']}\n\n{issue['body']}")
    for flag in ("fix", "evidence", "gap"):
        path = getattr(args, flag)
        if path:
            parts.append(f"## {flag}.json\n\n```json\n{Path(path).read_text()}\n```")
    return "\n\n".join(parts)


def task_line(args: argparse.Namespace) -> str:
    """One sentence telling the role which mode it is in."""
    if args.role == "coder" and args.fix:
        return f"Mode: fix. Address every finding in fix.json on PR #{args.pr}."
    if args.role == "coder":
        return f"Mode: implement. Deliver ticket #{args.issue} end to end and open the PR."
    if args.role in ("reviewer", "security"):
        return f"Review PR #{args.pr}."
    if args.role == "janitor":
        return "File one ticket for the gap in gap.json."
    if args.role == "watchdog":
        return "File one bug ticket for the failures in evidence.json."
    return ""


def watchdog_duplicate(evidence_path: str) -> str | None:
    """Return the URL of an open watchdog ticket with the same fingerprint, if any."""
    fp = json.loads(Path(evidence_path).read_text()).get("fingerprint", "")
    if not fp:
        return None
    found = json.loads(
        sh("gh", "issue", "list", "--state", "open", "--label", "agent:watchdog",
           "--search", f"watchdog-fingerprint:{fp}", "--json", "url")
    )
    return found[0]["url"] if found else None


def run_claude(role: str, prompt: str) -> dict:
    """Call claude -p as the role. Git identity comes from env so no repo config changes."""
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)  # allow nesting when launched from a Claude Code session
    ident = f"{role}-agent[bot]"
    env.update({
        "GIT_AUTHOR_NAME": ident, "GIT_COMMITTER_NAME": ident,
        "GIT_AUTHOR_EMAIL": f"{role}-agent@users.noreply.github.com",
        "GIT_COMMITTER_EMAIL": f"{role}-agent@users.noreply.github.com",
    })
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--max-turns", str(MAX_TURNS[role]),
        "--allowedTools", *ALLOWED_TOOLS[role],
    ]
    if os.environ.get("AGENT_MODEL"):
        cmd += ["--model", os.environ["AGENT_MODEL"]]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
    if res.returncode != 0 and not res.stdout.strip():
        raise SystemExit(f"claude failed ({res.returncode}):\n{res.stderr[-2000:]}")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"result": res.stdout, "is_error": True}


def parse_verdict(text: str) -> dict | None:
    """Pull the last ```json block from the role's final message."""
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if "verdict" in data:
            return data
    return None


def set_output(key: str, value: str) -> None:
    """Write a key=value line to $GITHUB_OUTPUT when running in Actions."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def report(role: str, text: str, pr: int | None, issue: int | None, cost: float) -> None:
    """Post the role's report to the PR or issue and to the step summary."""
    body = f"### {role}-agent report\n\n{text}\n\n<sub>cost ${cost:.2f}</sub>"
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(body + "\n\n")
    if pr:
        sh("gh", "pr", "comment", str(pr), "--body", body, check=False)
    elif issue:
        sh("gh", "issue", "comment", str(issue), "--body", body, check=False)
    print(body)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role", choices=sorted(ALLOWED_TOOLS))
    ap.add_argument("--issue", type=int)
    ap.add_argument("--pr", type=int)
    ap.add_argument("--fix", help="findings.json from a failed review")
    ap.add_argument("--evidence", help="evidence.json from watchdog_check.py")
    ap.add_argument("--gap", help="gap.json from janitor_scan.py")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    args = ap.parse_args()

    if args.role == "watchdog" and args.evidence:
        dup = watchdog_duplicate(args.evidence)
        if dup:
            print(f"duplicate of open ticket {dup}, nothing filed")
            set_output("issue", "")
            return

    role_text = (ROLES / f"{args.role}.md").read_text()
    prompt = f"{role_text}\n\n{task_line(args)}\n\n# Context\n\n{gather_context(args)}"
    if args.dry_run:
        print(prompt)
        return

    out = run_claude(args.role, prompt)
    text = out.get("result", "") or ""
    cost = float(out.get("total_cost_usd") or 0)

    pr = args.pr
    issue = args.issue
    m = re.search(r"/pull/(\d+)", text)
    if m and not pr:
        pr = int(m.group(1))
        set_output("pr", str(pr))
    m = re.search(r"/issues/(\d+)", text)
    if m and not issue:
        issue = int(m.group(1))
        set_output("issue", str(issue))
    verdict = parse_verdict(text)
    if verdict:
        set_output("verdict", verdict["verdict"])
        Path(f"{args.role}-findings.json").write_text(json.dumps(verdict, indent=2))

    report(args.role, text, pr, issue, cost)
    if out.get("is_error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
