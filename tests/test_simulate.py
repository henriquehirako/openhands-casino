import random

from casino import simulate
from casino.monitor import Monitor


def _run_with_tmp_monitor(monkeypatch, tmp_path, name, **kwargs):
    path = tmp_path / name
    monkeypatch.setattr(simulate, "Monitor", lambda: Monitor(path=str(path)))
    simulate.run(**kwargs)
    return path.read_text()


def test_same_seed_and_rounds_produce_identical_outcomes(monkeypatch, tmp_path):
    first = _run_with_tmp_monitor(monkeypatch, tmp_path, "a.jsonl", num_rounds=25, seed=7)
    second = _run_with_tmp_monitor(monkeypatch, tmp_path, "b.jsonl", num_rounds=25, seed=7)
    assert first == second
    assert first != ""


def test_different_seeds_can_produce_different_outcomes(monkeypatch, tmp_path):
    first = _run_with_tmp_monitor(monkeypatch, tmp_path, "a.jsonl", num_rounds=25, seed=1)
    second = _run_with_tmp_monitor(monkeypatch, tmp_path, "b.jsonl", num_rounds=25, seed=2)
    assert first != second


def test_seed_none_leaves_random_unseeded(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(random, "seed", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(simulate, "Monitor", lambda: Monitor(path=str(tmp_path / "c.jsonl")))

    simulate.run(num_rounds=1, seed=None)

    assert calls == []


def test_seed_given_seeds_random(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(random, "seed", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(simulate, "Monitor", lambda: Monitor(path=str(tmp_path / "c.jsonl")))

    simulate.run(num_rounds=1, seed=42)

    assert calls == [((42,), {})]
