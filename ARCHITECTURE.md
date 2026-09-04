# Agent layer: architecture and plan

Design for the agent layer that maintains this repo. The README covers how
to run it. This file covers why it is shaped this way, what each part does,
and what was cut for the 2-hour budget.

## Principle

The engineer is the product owner. They write tickets and nothing else.
Agents pick tickets, implement, review, fix, merge, and file new tickets
from what they observe. Labels are the state. Every agent step is visible
as a job in the GitHub Actions graph and as a comment on the PR or issue.

Detection is code. The LLM is called only where judgment is needed:
writing code, reviewing code, writing a ticket from evidence.

## Agents

| Agent    | Trigger                        | Does                                                                 | Identity               |
|----------|--------------------------------|----------------------------------------------------------------------|------------------------|
| Janitor  | timer, chained run             | Picks oldest `ready` ticket. None: scans repo for a gap, files a ticket born `ready`, picks it. | `janitor-agent[bot]`   |
| Coder    | ticket from janitor; findings  | Implements through the definition of done, one commit per step, opens PR. Fix mode addresses findings. | `coder-agent[bot]`     |
| Reviewer | PR opened by coder             | Audits the definition of done against diff, ticket, `CONVENTIONS.md`. Pass or fail per item. | `reviewer-agent[bot]`  |
| Security | PR opened by coder, parallel   | Security-only review. Pass or fail.                                  | `security-agent[bot]`  |
| Watchdog | timer, push to main            | Runs test suite and seeded simulation. Failing test or broken invariant: ticket born `ready`. | `watchdog-agent[bot]`  |

## Workflows

### `sdlc.yml`: one ticket per run, then chain

```
timer / dispatch → guard → janitor → coder → reviewer ‖ security → fix? → ci → merge → chain?
```

- `guard`: `vars.AGENTS_ENABLED == 'true'` and `inputs.depth < 20`.
- `janitor`: `agents/select_ticket.py` picks oldest `ready` without `hold`.
  Empty: `agents/janitor_scan.py` finds one gap, `run.py janitor` files it.
  Output: `issue`.
- `coder`: `run.py coder --issue N`. Branch `agent/N-slug`, one commit per
  definition-of-done step, PR with `Closes #N` and the checklist. Output: `pr`.
- `reviewer`, `security`: `run.py reviewer --pr N`, `run.py security --pr N`.
  Post a review comment. Output: `verdict` pass or fail plus findings file.
- `fix`: only if a verdict is fail. `run.py coder --pr N --fix findings.json`.
- `ci`: pytest on the PR head. Runs inside this workflow because PRs made
  with `GITHUB_TOKEN` do not fire `pull_request` events.
- `merge`: `gh pr merge --squash --delete-branch`. CI red: label
  `needs-human`, comment, continue.
- `chain`: another `ready` ticket exists: `gh workflow run sdlc.yml -f depth=N+1`.
  `workflow_dispatch` is the one event `GITHUB_TOKEN` may trigger.
- `concurrency: group: sdlc, cancel-in-progress: false`. One run at a time.
  Timer ticks during a run are dropped, the chain covers them.
- `run-name: sdlc #${{ inputs.issue || 'pick' }} d${{ inputs.depth || 0 }}`.

### `watchdog.yml`: check, then file

```
timer / push main → agents/watchdog_check.py → anomaly? → run.py watchdog → issue
```

- `watchdog_check.py`: seeds `random`, runs pytest and 2000 rounds. Exit 1
  with `evidence.json` on any failure. Invariants:
  - test suite green
  - no exception in the run
  - dealer final value 17 to 26, never hits at 17 or above
  - player win rate in 0.37 to 0.46 (measured 0.40 to 0.42 over five seeds)
  - `push` means equal values, `player` and `dealer` mean strict order or bust
- `run.py watchdog --evidence evidence.json`: writes the ticket. Fingerprint
  in the body, one open ticket per fingerprint.

### `ci.yml`: pytest on human PRs

Standard. Agent PRs are covered inside `sdlc.yml`.

### `.github/scripts/board.py`: board mirror

Both workflows call it after each agent step. It adds the issue to project
board 1 and sets the Status column from the label name. Needs the secret
`PROJECT_TOKEN` (project scope). Unset: prints a notice, exits 0.

## Shared contracts

- `DEFINITION_OF_DONE.md`: criteria met, tests, docs, deps current,
  self-review. Coder gives evidence per item in the PR body. Reviewer
  verifies per item.
- `CONVENTIONS.md`: code style, commit prefixes, branch names, test layout.
- `.github/ISSUE_TEMPLATE/ticket.yml`: Goal, Acceptance criteria as
  checkboxes, Out of scope. Bots fill the same template.
- Labels: `ready`, `in-review`, `hold`, `needs-human`, `agent:janitor`, `agent:watchdog`,
  `priority:high`. Coder moves a ticket from `ready` to `in-review` when its PR opens.

## `agents/run.py`

One entry point, one role per call.

```
python agents/run.py <role> [--issue N] [--pr N] [--fix findings.json] [--evidence evidence.json]
```

1. Load `agents/roles/<role>.md`.
2. Gather context with `gh`: issue body, PR diff, the two contract files.
3. `git config user.name "<role>-agent[bot]"`.
4. `claude -p` with the role's allowed tools. Coder: edit, write, git,
   python, gh. Reviewer and security: read only plus `gh pr review`.
5. Write a report to `$GITHUB_STEP_SUMMARY` and as a PR or issue comment.

Same command locally and in Actions. Develop locally, wire Actions last.

## Guardrails

| Guardrail        | Mechanism                                                     |
|------------------|---------------------------------------------------------------|
| Kill switch      | Repo variable `AGENTS_ENABLED`, checked first in both workflows |
| Chain bound      | `depth` input, stop at 20, timer restarts fresh                |
| WIP              | One ticket per run, one run at a time                          |
| Merge rule       | Reviews pass or fixed once, CI green. Else `needs-human`       |
| Hold             | Label `hold` excludes a ticket                                 |
| Fix loop         | One pass                                                       |
| Watchdog dedupe  | Fingerprint in ticket body                                     |
| Never force-push | Coder role forbids it, branch protection on `main`             |

## Bait in the starter repo and who catches it

| Bait                                  | Catcher  | Detector                                  |
|---------------------------------------|----------|-------------------------------------------|
| `requests==2.6.0`, never imported     | Janitor  | dep declared, not imported                 |
| Tests only for `Hand`                 | Janitor  | module without `tests/test_<module>.py`    |
| README one line, `Monitor` "extend"   | Janitor  | module without docstring, README too short |
| `is_blackjack` never called           | Janitor  | public function with no caller             |
| No bets, no 3:2 payout                | Human    | product ticket                             |
| No seed anywhere                      | Watchdog | harness seeds `random` itself              |

## Cut for 2 hours, with more time

- Second review pass after fix. CI is the gate now.
- Golden-file regression harness. Invariants and a band now.
- Deterministic definition-of-done checks in CI: diff coverage, docstring
  lint. Reviewer LLM does them from the diff now.
- Human merge gate for feature tickets. None now, `needs-human` is the escape.
- Dashboard from `outcomes.jsonl`.

## Build order

| Time | Step                                                                                   |
|------|----------------------------------------------------------------------------------------|
| 0:00 | Branch, secrets, labels, `CONVENTIONS.md`, `DEFINITION_OF_DONE.md`, issue template     |
| 0:15 | `agents/run.py`, `roles/coder.md`. Run locally against one issue. Review the PR.       |
| 0:45 | `select_ticket.py`, `janitor_scan.py`, `roles/janitor.md`, `roles/reviewer.md`, `roles/security.md` |
| 1:00 | `sdlc.yml`, first end-to-end run in Actions                                             |
| 1:20 | `watchdog_check.py`, `roles/watchdog.md`, `watchdog.yml`                                |
| 1:35 | Record. Seed two tickets and one rule bug, walk away 20 min. README meanwhile.          |
