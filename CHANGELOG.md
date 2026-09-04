# Changelog

## Unreleased

- fix(strategies): dealer now hits on 16 instead of standing, matching the documented "hit until 17" rule (#22)
- chore(deps): remove unused `requests` pin from `requirements.txt` (#2)
- test: add `tests/test_cards.py` covering `Deck` construction, `draw()`, and empty-deck behavior (#10)
- feat(simulate): `run()` takes a `seed` parameter for reproducible `outcomes.jsonl` runs (#6)
- feat(table): `Table` takes a bet size, pays 3:2 on a natural blackjack and 1:1 otherwise, and `simulate.run()` tracks and prints the final bankroll (#7)
