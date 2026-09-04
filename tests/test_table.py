import random

from casino.cards import Card
from casino.hand import Hand
from casino.strategies import BasicPlayerStrategy, StandardDealerStrategy
from casino.table import Table


def _table(bet=10):
    return Table(BasicPlayerStrategy(), StandardDealerStrategy(), bet=bet)


def _hand(*cards):
    hand = Hand()
    for card in cards:
        hand.add(card)
    return hand


def test_natural_blackjack_pays_three_to_two():
    table = _table(bet=10)
    player_hand = _hand(Card("A", "hearts"), Card("K", "spades"))
    dealer_hand = _hand(Card("9", "hearts"), Card("7", "clubs"))

    outcome = table._outcome("player", player_hand, dealer_hand)

    assert outcome["payout"] == 15.0


def test_three_card_21_pays_one_to_one_not_blackjack_odds():
    table = _table(bet=10)
    player_hand = _hand(Card("7", "hearts"), Card("7", "spades"), Card("7", "clubs"))
    dealer_hand = _hand(Card("9", "hearts"), Card("7", "clubs"))

    outcome = table._outcome("player", player_hand, dealer_hand)

    assert outcome["payout"] == 10


def test_push_returns_bet_with_zero_payout():
    table = _table(bet=10)
    player_hand = _hand(Card("10", "hearts"), Card("9", "spades"))
    dealer_hand = _hand(Card("10", "clubs"), Card("9", "hearts"))

    outcome = table._outcome("push", player_hand, dealer_hand)

    assert outcome["payout"] == 0


def test_dealer_win_costs_the_player_the_bet():
    table = _table(bet=10)
    player_hand = _hand(Card("10", "hearts"), Card("8", "spades"))
    dealer_hand = _hand(Card("10", "clubs"), Card("9", "hearts"))

    outcome = table._outcome("dealer", player_hand, dealer_hand)

    assert outcome["payout"] == -10


def test_table_stores_configured_bet_size():
    table = _table(bet=25)
    assert table.bet == 25


def test_play_round_outcome_has_payout_field():
    random.seed(1)
    table = _table(bet=10)

    outcome = table.play_round()

    assert "payout" in outcome
