from .cards import Deck
from .hand import Hand


class Table:
    """Deals blackjack rounds and settles each round against a fixed bet size."""

    def __init__(self, player_strategy, dealer_strategy, num_decks=1, bet: float = 10):
        self.player_strategy = player_strategy
        self.dealer_strategy = dealer_strategy
        self.num_decks = num_decks
        self.bet = bet

    def play_round(self):
        deck = Deck(self.num_decks)
        player_hand = Hand()
        dealer_hand = Hand()

        player_hand.add(deck.draw())
        dealer_hand.add(deck.draw())
        player_hand.add(deck.draw())
        dealer_hand.add(deck.draw())

        while not player_hand.is_bust() and self.player_strategy.should_hit(
            player_hand, dealer_hand.cards[0]
        ):
            player_hand.add(deck.draw())

        if player_hand.is_bust():
            return self._outcome("dealer", player_hand, dealer_hand)

        while not dealer_hand.is_bust() and self.dealer_strategy.should_hit(dealer_hand):
            dealer_hand.add(deck.draw())

        if dealer_hand.is_bust():
            return self._outcome("player", player_hand, dealer_hand)

        if player_hand.value() > dealer_hand.value():
            winner = "player"
        elif player_hand.value() < dealer_hand.value():
            winner = "dealer"
        else:
            winner = "push"

        return self._outcome(winner, player_hand, dealer_hand)

    def _outcome(self, winner, player_hand, dealer_hand):
        return {
            "winner": winner,
            "player_strategy": self.player_strategy.name,
            "dealer_strategy": self.dealer_strategy.name,
            "player_value": player_hand.value(),
            "dealer_value": dealer_hand.value(),
            "payout": self._payout(winner, player_hand),
        }

    def _payout(self, winner, player_hand):
        """Net change to the player's bankroll for the round.

        A push returns the bet, so payout is 0. A natural blackjack (two
        cards totalling 21) pays 3:2. Any other player win, including a
        21 made with three or more cards, pays 1:1. A dealer win costs
        the player the bet.
        """
        if winner == "push":
            return 0
        if winner == "dealer":
            return -self.bet
        if player_hand.is_blackjack():
            return self.bet * 1.5
        return self.bet
