from casino.cards import Card
from casino.hand import Hand
from casino.strategies import BasicPlayerStrategy, StandardDealerStrategy


def _hand(*cards):
    hand = Hand()
    for card in cards:
        hand.add(card)
    return hand


def test_dealer_hits_on_16():
    dealer = StandardDealerStrategy()
    hand = _hand(Card("10", "hearts"), Card("6", "spades"))

    assert dealer.should_hit(hand) is True


def test_dealer_hits_on_other_sub_17_totals():
    dealer = StandardDealerStrategy()
    for total in (12, 13, 14, 15):
        hand = _hand(Card("10", "hearts"), Card(str(total - 10), "spades"))
        assert dealer.should_hit(hand) is True, f"expected hit on {total}"


def test_dealer_stands_on_17():
    dealer = StandardDealerStrategy()
    hand = _hand(Card("10", "hearts"), Card("7", "spades"))

    assert dealer.should_hit(hand) is False


def test_dealer_stands_above_17():
    dealer = StandardDealerStrategy()
    hand = _hand(Card("10", "hearts"), Card("K", "spades"))

    assert dealer.should_hit(hand) is False


def test_basic_player_strategy_hits_below_17():
    player = BasicPlayerStrategy()
    hand = _hand(Card("10", "hearts"), Card("6", "spades"))
    dealer_upcard = Card("9", "clubs")

    assert player.should_hit(hand, dealer_upcard) is True
