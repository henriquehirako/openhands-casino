# Casino Skeleton

Blackjack simulator. `pip install pytest`, then `python -m pytest tests/ -q` to test and `python -m casino.simulate` to run a session.

The casino is standard library only. Beyond pytest there is nothing to install.

Pass `seed` to `run()` for a reproducible session: the same `seed` and
`num_rounds` always write the same `outcomes.jsonl`.

```
python -c "from casino.simulate import run; run(num_rounds=100, seed=42)"
```

Leave `seed` unset (the default, `None`) for a fresh, unseeded run each time.

## Agent layer

The casino is not the point. The point is the layer of agents that maintains it. The engineer is the product owner and writes tickets. Nothing else. Agents pick tickets, implement them, review the PR, fix findings, merge, and file new tickets from what they observe. Issue labels are the whole state machine. Every agent step shows up as a job in the GitHub Actions graph and as a comment on the PR or issue, so you can reconstruct what happened without having watched it.

Detection is code. A Python script decides that a dependency is unused, a module has no test file, or the dealer hit at 17. The LLM is called only where judgment is needed: writing the code, reviewing the code, turning evidence into a ticket.

### How to run it

Secrets: `CLAUDE_CODE_OAUTH_TOKEN` for the agents. `GH_PAT`, optional, a user
token so agent PRs fire real `pull_request` events and the board moves.
Then one switch:

```
gh variable set AGENTS_ENABLED --body true     # off: every workflow exits at its first job
```

From here nothing needs a click. To start a ticket now instead of at the
next timer tick: `gh workflow run sdlc.yml -f issue=6`.

Locally, one entry point runs one role per call, same command as in Actions:
`python agents/run.py <role> [--issue N] [--pr N] [--fix findings.json] [--evidence evidence.json]`.

### How it runs on its own

Three workflows trigger each other. No run ever fails: a red test, a failed
review or a stuck coder becomes a label and a comment, and the loop moves on.

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

Anything the agents cannot finish gets `needs-human` and the loop moves on.
Queue empty: the janitor scans the repo and files one gap ticket itself.
Humans only ever set `ready`.

Guardrails: `AGENTS_ENABLED` stops everything at the next job. Chain depth
caps at 20. One agent PR in flight at a time. Label `hold` keeps a ticket
out of the queue. Watchdog tickets carry a fingerprint, one open ticket per
failure.

### What each agent does and its trigger

| Agent    | Trigger                       | Action                                                                                         | Identity              |
|----------|-------------------------------|------------------------------------------------------------------------------------------------|-----------------------|
| Janitor  | timer, chained run            | Picks the oldest `ready` ticket. If none, scans the repo for a gap, files a ticket born `ready`, picks it. | `janitor-agent[bot]`  |
| Coder    | ticket from Janitor; findings | Implements the definition of done, one commit per step, opens a PR. In fix mode it addresses review findings. | `coder-agent[bot]`    |
| Reviewer | PR opened by Coder            | Audits the definition of done against the diff, the ticket and `CONVENTIONS.md`. Pass or fail per item. | `reviewer-agent[bot]` |
| Security | PR opened by Coder, parallel  | Security-only review. Pass or fail.                                                            | `security-agent[bot]` |
| Watchdog | timer, push to main           | Runs the test suite and a seeded 2000-round simulation. A failing test or broken invariant becomes a ticket born `ready` and dispatches sdlc. | `watchdog-agent[bot]` |

### AI tools used and how

Two separate things. Claude Code (Claude Fable 5.1) built this layer, with the engineer directing the work and reviewing every commit before it landed. The agents themselves are the deliverable. Each one is `agents/run.py` loading a role prompt from `agents/roles/<role>.md`, gathering context with `gh`, then calling `claude -p` with a per-role tool allowlist. Coder may edit, write, run git, python and gh. Reviewer and Security read, run tests and post a review, they cannot push. Each role commits under its own bot name so its work is easy to tell apart from the engineer's in the history.

### What did not go as planned, and with more time

TODO: HH fills this after the recording.

Found by shakedown runs before recording, fixed: a bash redirect sent
pytest output into `$GITHUB_OUTPUT`; a `#` in a single-line YAML step
started a comment; GitHub search missed the watchdog fingerprint so a
duplicate ticket was filed; `Closes #N` did not close the ticket on a bot
merge; a squash merge re-authored the coder's commits as `github-actions`.

Cut for the 2-hour budget:

- Golden-file regression harness. Invariants and a win-rate band now.
- Deterministic definition-of-done checks in CI (diff coverage, docstring lint). The Reviewer LLM does them from the diff now.
- Human merge gate for feature tickets. None now, `needs-human` is the escape.
- Dashboard from `outcomes.jsonl`.

Design and reasoning are in [ARCHITECTURE.md](ARCHITECTURE.md). The contracts the agents work to are [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) and [CONVENTIONS.md](CONVENTIONS.md).
