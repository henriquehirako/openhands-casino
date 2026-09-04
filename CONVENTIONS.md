# Conventions

Read by every agent and every human working on this repo.

## Code

- Python 3, standard library only unless the ticket says otherwise.
- Type hints on public functions. Docstring on every public class and
  function saying how it is used, one to three lines.
- Keep it simple. No abstraction for a single use. No speculative options.
- Casino logic lives in `casino/`. Agent code lives in `agents/`. Agents do
  not edit `agents/` or `.github/` unless the ticket asks for it.

## Tests

- `tests/test_<module>.py` mirrors `casino/<module>.py`.
- Test behavior, not implementation. One assertion idea per test.
- Seed `random` in any test that draws cards.
- Run: `python -m pytest tests/ -q`.

## Git

- Branch names: `agent/<issue>-<slug>` for agent work, `<topic>` for humans.
- Commit prefixes: `feat`, `fix`, `test`, `docs`, `chore(deps)`, `refactor`.
- One logical change per commit. Agents commit once per definition-of-done
  step so the log shows the pipeline.
- Never push to `main`. Never force-push. Never rewrite published history.
- PR body links the ticket with `Closes #N` and carries the
  definition-of-done checklist with evidence.

## Docs

- `README.md` stays current with how to run and what exists.
- `CHANGELOG.md` gets one line per PR under "Unreleased".

## Dependencies

- `requirements.txt` pins exact versions. Remove what is not imported.
