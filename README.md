# Casino Skeleton

Blackjack simulator. `pip install pytest`, then `python -m pytest tests/ -q` to test and `python -m casino.simulate` to run a session.

The casino is standard library only. Beyond pytest there is nothing to install.

## Agent layer

The casino is not the point. The point is the layer of agents that maintains it. The engineer is the product owner and writes tickets. Nothing else. Agents pick tickets, implement them, review the PR, fix findings, merge, and file new tickets from what they observe. Issue labels are the whole state machine. Every agent step shows up as a job in the GitHub Actions graph and as a comment on the PR or issue, so you can reconstruct what happened without having watched it.

Detection is code. A Python script decides that a dependency is unused, a module has no test file, or the dealer hit at 17. The LLM is called only where judgment is needed: writing the code, reviewing the code, turning evidence into a ticket.

### How to run it

The repo variable `AGENTS_ENABLED=true` is the kill switch. Both workflows check it first and exit if it is anything else. With it on, `sdlc.yml` and `watchdog.yml` fire on their timers and `pr.yml` is dispatched by `sdlc.yml` for each PR. To fire them by hand run `gh workflow run sdlc.yml` or `gh workflow run watchdog.yml`.

Locally, one entry point runs one role per call: `python agents/run.py <role> [--issue N] [--pr N] [--fix findings.json] [--evidence evidence.json]`. The same command runs in Actions.

Secrets: `CLAUDE_CODE_OAUTH_TOKEN` is required. `PROJECT_TOKEN` is optional and only used to mirror labels onto the project board.

### What each agent does and its trigger

| Agent    | Trigger                       | Action                                                                                         | Identity              |
|----------|-------------------------------|------------------------------------------------------------------------------------------------|-----------------------|
| Janitor  | timer, chained run            | Picks the oldest `ready` ticket. If none, scans the repo for a gap, files a ticket born `ready`, picks it. | `janitor-agent[bot]`  |
| Coder    | ticket from Janitor; findings | Implements the definition of done, one commit per step, opens a PR. In fix mode it addresses review findings. | `coder-agent[bot]`    |
| Reviewer | PR opened by Coder            | Audits the definition of done against the diff, the ticket and `CONVENTIONS.md`. Pass or fail per item. | `reviewer-agent[bot]` |
| Security | PR opened by Coder, parallel  | Security-only review. Pass or fail.                                                            | `security-agent[bot]` |
| Watchdog | timer, push to main           | Runs the test suite and a seeded 2000-round simulation. A failing test or broken invariant becomes a ticket born `ready`. | `watchdog-agent[bot]` |

One ticket in flight at a time. `sdlc.yml` picks it and the coder opens a PR. `pr.yml` then runs reviewer, security and CI in parallel, one round per run: findings or red tests send it to the coder for a fix and the next round, up to two rounds. When both reviews pass and CI is green, `sdlc.yml` merges, and chains to the next `ready` ticket, up to depth 20. No run ever fails: anything the agents cannot finish gets `needs-human` and the loop moves on.

### AI tools used and how

Two separate things. Claude Code (Claude Fable 5.1) built this layer, with the engineer directing the work and reviewing every commit before it landed. The agents themselves are the deliverable. Each one is `agents/run.py` loading a role prompt from `agents/roles/<role>.md`, gathering context with `gh`, then calling `claude -p` with a per-role tool allowlist. Coder may edit, write, run git, python and gh. Reviewer and Security are read-only plus `gh pr review`. Each role commits under its own bot name so its work is easy to tell apart from the engineer's in the history.

### What did not go as planned, and with more time

TODO: HH fills this after the recording.

Cut for the 2-hour budget:

- Second review pass after fix. CI is the gate now.
- Golden-file regression harness. Invariants and a win-rate band now.
- Deterministic definition-of-done checks in CI (diff coverage, docstring lint). The Reviewer LLM does them from the diff now.
- Human merge gate for feature tickets. None now, `needs-human` is the escape.
- Dashboard from `outcomes.jsonl`.

Design and reasoning are in [ARCHITECTURE.md](ARCHITECTURE.md). The contracts the agents work to are [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) and [CONVENTIONS.md](CONVENTIONS.md).
