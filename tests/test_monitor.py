import json

from casino import monitor
from casino.monitor import Monitor


def test_record_writes_one_json_line_that_round_trips(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    outcome = {"result": "win", "bet": 10, "payout": 15}

    Monitor(path=str(path)).record(outcome)

    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == outcome


def test_record_appends_without_truncating_prior_lines(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    m = Monitor(path=str(path))
    first = {"result": "win"}
    second = {"result": "loss"}

    m.record(first)
    m.record(second)

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == first
    assert json.loads(lines[1]) == second


def test_default_path_is_outcomes_path():
    assert Monitor().path == monitor.OUTCOMES_PATH
