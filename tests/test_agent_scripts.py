"""Focused tests for the pure functions in agents/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))

import janitor_scan  # noqa: E402
import watchdog_check  # noqa: E402
from select_ticket import pick  # noqa: E402


def _issue(number, created, *labels):
    return {"number": number, "title": f"t{number}", "createdAt": created,
            "labels": [{"name": n} for n in labels]}


def test_pick_skips_hold_and_prefers_priority_then_oldest():
    issues = [
        _issue(1, "2026-01-01T00:00:00Z", "ready", "hold"),
        _issue(2, "2026-01-03T00:00:00Z", "ready"),
        _issue(3, "2026-01-02T00:00:00Z", "ready"),
        _issue(4, "2026-01-04T00:00:00Z", "ready", "priority:high"),
    ]
    assert pick(issues)["number"] == 4
    assert pick(issues[:3])["number"] == 3
    assert pick([issues[0]]) is None
    assert pick([]) is None


def _repo(tmp_path, readme="x" * 400, requirements="", **casino_files):
    (tmp_path / "casino").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "casino" / "__init__.py").write_text("")
    (tmp_path / "README.md").write_text(readme)
    (tmp_path / "requirements.txt").write_text(requirements)
    for name, src in casino_files.items():
        (tmp_path / "casino" / f"{name}.py").write_text(src)
    return tmp_path


def test_missing_tests(tmp_path):
    root = _repo(tmp_path, hand='"""doc"""\n', table='"""doc"""\n')
    (root / "tests" / "test_hand.py").write_text("")
    gaps = janitor_scan.missing_tests(root)
    assert [g["target"] for g in gaps] == ["casino/table.py"]


def test_unused_dependency(tmp_path):
    root = _repo(tmp_path, requirements="requests==2.6.0  # old\nRich-Lib>=1\n",
                 hand='"""doc"""\nimport rich_lib\n')
    gaps = janitor_scan.unused_dependency(root)
    assert [g["target"] for g in gaps] == ["requests"]


def test_dead_code(tmp_path):
    root = _repo(tmp_path, hand='"""doc"""\nclass H:\n    def used(self): pass\n    def unused(self): pass\n    def _priv(self): pass\n')
    (root / "tests" / "test_hand.py").write_text("H().used()\n")
    gaps = janitor_scan.dead_code(root)
    assert [g["target"] for g in gaps] == ["casino/hand.py::unused"]


def test_missing_docs(tmp_path):
    root = _repo(tmp_path, readme="short", hand='"""doc"""\n', table="x = 1\n")
    gaps = janitor_scan.missing_docs(root)
    assert [g["target"] for g in gaps] == ["casino/table.py", "README.md"]


def test_scan_skips_venv_and_orders_by_kind(tmp_path):
    root = _repo(tmp_path, readme="short", requirements="requests\n", hand="x = 1\n")
    (root / ".venv" / "lib").mkdir(parents=True)
    (root / ".venv" / "lib" / "requests.py").write_text("import requests\n")
    kinds = [g["kind"] for g in janitor_scan.scan(root)]
    assert kinds == ["unused_dependency", "missing_tests", "missing_docs", "missing_docs"]


def _o(winner, p, d):
    return {"winner": winner, "player_value": p, "dealer_value": d}


def test_check_outcomes_clean():
    clean = [_o("player", 20, 18), _o("dealer", 22, 17), _o("push", 19, 19), _o("player", 18, 23)]
    # 2 of 4 wins is 0.5, outside the band; add dealer wins to land inside it
    clean += [_o("dealer", 16, 19)] * 1
    assert watchdog_check.check_outcomes(clean, [12, 16]) == []


def test_check_outcomes_flags_dealer_rule_breaks():
    fails = watchdog_check.check_outcomes([_o("dealer", 18, 16)] * 5 + [_o("player", 20, 17)] * 4, [17])
    checks = {f["check"] for f in fails}
    assert {"dealer_hits_on_17_plus", "dealer_stood_under_17", "dealer_win_mismatch"} <= checks


def test_check_outcomes_flags_bad_winners_and_band():
    outcomes = [_o("push", 20, 19), _o("player", 22, 17), _o("player", 18, 17)]
    checks = {f["check"] for f in watchdog_check.check_outcomes(outcomes, [])}
    assert {"push_mismatch", "player_win_mismatch", "win_rate_out_of_band"} <= checks


def test_fingerprint_is_stable_and_order_free():
    a = [{"check": "x", "detail": "1"}, {"check": "y", "detail": "2"}]
    assert watchdog_check.fingerprint(a) == watchdog_check.fingerprint(list(reversed(a)))
    assert watchdog_check.fingerprint([]) != watchdog_check.fingerprint(a)
