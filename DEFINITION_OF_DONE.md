# Definition of done

Every pull request opened by the coder must satisfy all five items. The
coder gives one line of evidence per item in the PR body. The reviewer
verifies each item against the diff, not against the checkbox.

| # | Item | Coder evidence | Reviewer check |
|---|------|----------------|----------------|
| 1 | Acceptance criteria met | Each criterion mapped to a file and function | Every criterion covered. Nothing outside the ticket's "Out of scope" |
| 2 | Tests | Test file per changed module, `python -m pytest tests/ -q` green | Changed module has a changed or new test. Edge cases, not only the happy path |
| 3 | Docs | README section, docstrings on public functions, `CHANGELOG.md` entry | Docs describe behavior, not code. Nothing stale left behind |
| 4 | Dependencies current | `requirements.txt` bumped, unused entries removed, or "none outdated" stated | Claim matches `requirements.txt` and the imports |
| 5 | Self-review | Diff read against this list before opening the PR | PR body claims match the diff |

A fail on any item sends the PR to one fix round. After the fix round CI
is the merge gate.
