"""Blackjack hand tracking and scoring for a player or the dealer."""


class Hand:
    """A player's or dealer's cards, with blackjack scoring rules applied."""

    def __init__(self):
        self.cards = []

    def add(self, card):
        """Add a card to the hand."""
        self.cards.append(card)

    def value(self):
        """Return the best blackjack total, counting aces as 11 or 1 to avoid busting."""
        total = 0
        aces = 0
        for c in self.cards:
            if c.rank == "A":
                aces += 1
                total += 11
            elif c.rank in ("J", "Q", "K"):
                total += 10
            else:
                total += int(c.rank)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_bust(self):
        """Return True if the hand's value exceeds 21."""
        return self.value() > 21

    def is_blackjack(self):
        """Return True if the hand is a two-card natural blackjack (value 21)."""
        return len(self.cards) == 2 and self.value() == 21
