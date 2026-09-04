import random

from .monitor import Monitor
from .strategies import BasicPlayerStrategy, StandardDealerStrategy
from .table import Table


def run(
    num_rounds: int = 100,
    seed: int | None = None,
    bet: float = 10,
    starting_bankroll: float = 1000,
) -> None:
    """Play `num_rounds` rounds and log each outcome to outcomes.jsonl.

    When `seed` is given, `random` is seeded first so the run is
    reproducible: the same `seed` and `num_rounds` always produce the same
    outcomes. `seed=None` leaves `random` unseeded, the prior behavior.
    Each round is settled against `bet`, starting from `starting_bankroll`,
    and the final bankroll is printed.
    """
    if seed is not None:
        random.seed(seed)
    table = Table(BasicPlayerStrategy(), StandardDealerStrategy(), bet=bet)
    monitor = Monitor()
    bankroll = starting_bankroll
    for _ in range(num_rounds):
        outcome = table.play_round()
        monitor.record(outcome)
        bankroll += outcome["payout"]
    print(f"Simulated {num_rounds} rounds. See outcomes.jsonl")
    print(f"Final bankroll: {bankroll}")


if __name__ == "__main__":
    run()
