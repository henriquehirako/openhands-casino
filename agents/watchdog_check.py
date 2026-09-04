"""Watchdog harness: run the test suite and a seeded simulation, check invariants.

Used by the watchdog workflow:

    python agents/watchdog_check.py [--rounds 2000] [--seed 7] [--out evidence.json]

Exit 0 when every check passes, 1 otherwise. Writes `evidence.json` either
way. Detection is code; the LLM only writes the ticket from the evidence.
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from casino.strategies import BasicPlayerStrategy, StandardDealerStrategy  # noqa: E402
from casino.table import Table  # noqa: E402

WIN_RATE_BAND = (0.37, 0.46)  # measured 0.40 to 0.42 over five seeds on the starter code


class SpyDealer(StandardDealerStrategy):
    """Standard dealer that records every hand value at which it chose to hit."""

    def __init__(self):
        self.hit_values: list[int] = []

    def should_hit(self, hand):
        hit = super().should_hit(hand)
        if hit:
            self.hit_values.append(hand.value())
        return hit


def run_pytest() -> tuple[bool, str]:
    """Run the suite, return (passed, tail of output)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "-x"],
        cwd=ROOT, capture_output=True, text=True,
    )
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-15:])
    return proc.returncode == 0, tail


def play(rounds: int, seed: int) -> tuple[list[dict], list[int], str | None]:
    """Play seeded rounds. Return (outcomes, dealer hit values, exception text or None)."""
    random.seed(seed)
    dealer = SpyDealer()
    table = Table(BasicPlayerStrategy(), dealer)
    outcomes = []
    try:
        for _ in range(rounds):
            outcomes.append(table.play_round())
    except Exception:
        return outcomes, dealer.hit_values, traceback.format_exc()
    return outcomes, dealer.hit_values, None


def check_outcomes(outcomes: list[dict], hit_values: list[int]) -> list[dict]:
    """Apply every blackjack invariant. Pure. Returns a list of failures."""
    failures = []

    def fail(check: str, detail: str):
        failures.append({"check": check, "detail": detail})

    bad_hits = sorted({v for v in hit_values if v >= 17})
    if bad_hits:
        fail("dealer_hits_on_17_plus", f"dealer hit at values {bad_hits}")

    for i, o in enumerate(outcomes):
        p, d, w = o["player_value"], o["dealer_value"], o["winner"]
        where = f"round {i}: player={p} dealer={d} winner={w}"
        if p <= 21 and d < 17:
            fail("dealer_stood_under_17", where)
        if not (2 <= p <= 26) or not (2 <= d <= 26):
            fail("value_out_of_range", where)
        if w == "push" and (p != d or p > 21):
            fail("push_mismatch", where)
        if w == "player" and (p > 21 or (d <= 21 and d >= p)):
            fail("player_win_mismatch", where)
        if w == "dealer" and p <= 21 and d <= 21 and d <= p:
            fail("dealer_win_mismatch", where)

    if outcomes:
        rate = sum(o["winner"] == "player" for o in outcomes) / len(outcomes)
        lo, hi = WIN_RATE_BAND
        if not lo <= rate <= hi:
            fail("win_rate_out_of_band", f"player win rate {rate:.3f} outside [{lo}, {hi}]")

    return _dedupe(failures)


def _dedupe(failures: list[dict]) -> list[dict]:
    """Keep the first example per check so the evidence stays short."""
    seen, out = set(), []
    for f in failures:
        if f["check"] not in seen:
            seen.add(f["check"])
            out.append(f)
    return out


def stats(outcomes: list[dict]) -> dict:
    counts = {k: sum(o["winner"] == k for o in outcomes) for k in ("player", "dealer", "push")}
    counts["win_rate"] = round(counts["player"] / len(outcomes), 4) if outcomes else 0.0
    return counts


def fingerprint(failures: list[dict]) -> str:
    """Stable id for this set of failing checks, used to dedupe tickets."""
    key = ",".join(sorted(f["check"] for f in failures))
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="evidence.json")
    args = parser.parse_args()

    failures = []
    tests_ok, pytest_tail = run_pytest()
    if not tests_ok:
        failures.append({"check": "tests_failing", "detail": pytest_tail})

    outcomes, hit_values, error = play(args.rounds, args.seed)
    if error:
        failures.append({"check": "exception", "detail": error.strip().splitlines()[-1]})
    failures.extend(check_outcomes(outcomes, hit_values))

    evidence = {
        "ok": not failures,
        "seed": args.seed,
        "rounds": args.rounds,
        "stats": stats(outcomes),
        "failures": failures,
        "pytest_tail": pytest_tail,
        "fingerprint": fingerprint(failures),
    }
    Path(args.out).write_text(json.dumps(evidence, indent=2) + "\n")

    for f in failures:
        print(f"FAIL {f['check']}: {f['detail'].splitlines()[-1]}")
    print(f"stats: {evidence['stats']} ok={evidence['ok']} fingerprint={evidence['fingerprint']}")
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
