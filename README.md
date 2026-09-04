# Casino Skeleton, maintained by agents

Blackjack simulator with a layer of agents that maintains it. The casino is
the workload, the agents are the deliverable.

- Screen recording: TODO link
- Repo: https://github.com/henriquehirako/openhands-casino
- Design: [ARCHITECTURE.md](ARCHITECTURE.md). Contracts: [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md), [CONVENTIONS.md](CONVENTIONS.md)

## What we built

Five agents run in GitHub Actions and maintain this repo without a human in
the loop. The engineer writes tickets and labels them `ready`. Nothing else.
Agents pick the ticket, implement it through a definition of done, review
the PR from two angles, fix findings, merge, and file new tickets from what
they observe in the code and in the casino's output. Issue labels are the
whole state machine. Every step is a job in the Actions graph and a comment
on the PR or issue, so anyone can reconstruct what happened later.

Detection is code, judgment is LLM. Python scripts decide that a test file
is missing, a dependency is unused, or the dealer hit at 17. The LLM is
called only to write code, review code, or turn evidence into a ticket. Each
role commits under its own bot name. On `main` today: 16 commits by
`coder-agent[bot]`, 6 agent-filed tickets, 6 agent PRs merged, all marked 🤖.

## How it runs

Three workflows dispatch each other. No run ever goes red. A failing test, a
failed review, or a stuck coder becomes a label and a comment, and the loop
moves on.

```
 you: label a ticket "ready"        (or the 10-min timer, or a bot ticket)
            │
            ▼
 ┌─ sdlc ───────────────────────────────────┐
 │  janitor picks ticket ──► coder opens PR │
 └──────────────────────────────┬───────────┘
                                │ dispatch
                                ▼
 ┌─ pr (one round per run) ─────────────────┐
 │  reviewer ┐                              │
 │  security ├──► route ──► green? ──yes──┐ │
 │  ci       ┘        │                   │ │
 │                    └──no──► coder fix  │ │
 │                              (max 2)   │ │
 │                                 │      │ │
 └─────────────────────────────────┼──────┼─┘
             next round ◄──────────┘      │ dispatch
                                          ▼
 ┌─ sdlc (merge mode) ──────────────────────┐
 │  merge PR ──► close ticket ──► chain ────┼──► next ready ticket ──► sdlc (top)
 └──────────────┬───────────────────────────┘
                │ push to main
                ▼
 ┌─ watchdog ───────────────────────────────┐
 │  tests + 2000 seeded rounds              │
 │  invariant broken? ──► new ticket "ready"┼──► sdlc (top)
 └──────────────────────────────────────────┘
```

Queue empty: the janitor scans the repo for a gap and files one ticket
itself. Anything the agents cannot finish gets `needs-human`. Guardrails:
`AGENTS_ENABLED` stops everything at the next job, chain depth caps at 20,
one agent PR in flight at a time, label `hold` parks a ticket, watchdog
tickets carry a fingerprint so one failure makes one ticket.

## Running the agent layer

Secrets: `CLAUDE_CODE_OAUTH_TOKEN` for the agents. `GH_PAT`, optional, so
agent PRs fire real `pull_request` events. Then one switch:

```
gh variable set AGENTS_ENABLED --body true    # timers start, off stops every workflow at its first job
gh workflow run sdlc.yml -f issue=6           # optional: start a ticket now instead of at the next tick
```

Locally, one entry point runs one role, same command as in Actions:

```
python agents/run.py <role> [--issue N] [--pr N] [--fix findings.json] [--evidence evidence.json]
```

## Agents and triggers

| Agent    | Trigger                                  | Does                                                                                    | Commits as             |
|----------|------------------------------------------|-----------------------------------------------------------------------------------------|------------------------|
| Janitor  | `ready` label, 10-min timer, chained run | Picks the oldest `ready` ticket. None: scans the repo for a gap and files a ticket.      | `janitor-agent[bot]`   |
| Coder    | ticket from Janitor; review findings     | Implements the definition of done, one commit per step, opens a 🤖 PR. Fix mode addresses findings. | `coder-agent[bot]`     |
| Reviewer | PR opened by Coder                       | Audits the definition of done against diff, ticket, and conventions. Pass or fail per item. | `reviewer-agent[bot]`  |
| Security | PR opened by Coder, in parallel          | Security-only review. Pass or fail.                                                     | `security-agent[bot]`  |
| Watchdog | push to `main`, 10-min timer             | Runs tests plus 2000 seeded rounds. Each broken invariant becomes a `ready` ticket and dispatches sdlc. | `watchdog-agent[bot]`  |

## AI tools used and how

Two separate things. Claude Code (Claude Fable 5.1) built this layer, with
the engineer directing and reviewing every commit before it landed. The
agents themselves are the deliverable: `agents/run.py` loads a role prompt
from `agents/roles/<role>.md`, gathers context with `gh`, and calls
`claude -p` with a per-role tool allowlist. Coder may edit, run git, python
and gh. Reviewer and Security read, run tests and post a review, they cannot
push. Janitor and Watchdog only file issues.

## What did not go as planned, and with more time

TODO: HH fills this after the recording.

Found in shakedown runs and fixed before recording: a bash redirect sent
pytest output into `$GITHUB_OUTPUT`; a `#` in a one-line YAML step started
a comment; GitHub search missed the watchdog fingerprint and filed a
duplicate; `Closes #N` did not close the ticket on a bot merge; a squash
merge re-authored the coder's commits as `github-actions`; one fix round
reverted a previous fix, caught by the watchdog on the next push.

With more time: deterministic definition-of-done checks in CI (diff
coverage, docstring lint) instead of the reviewer LLM doing them; a human
merge gate for feature tickets; a golden-file regression harness; a
dashboard from `outcomes.jsonl`.

## The casino itself

Standard library only. `pip install pytest`, `python -m pytest tests/ -q`,
`python -m casino.simulate`. `run(num_rounds, seed=None, bet=10,
starting_bankroll=1000)` seeds the session for reproducible output, settles
each round against a bet, pays 3:2 on a natural blackjack, and prints the
final bankroll.
