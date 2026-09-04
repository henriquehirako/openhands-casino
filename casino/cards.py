"""Card and Deck primitives shared by every game in casino/."""

import random

SUITS = ["hearts", "diamonds", "clubs", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


class Card:
    """A single playing card with a rank (e.g. "K") and a suit (e.g. "spades")."""

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit[0].upper()}"


class Deck:
    """A shuffled deck of one or more standard 52-card decks."""

    def __init__(self, num_decks=1):
        self.cards = [Card(r, s) for _ in range(num_decks) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def draw(self):
        """Remove and return the top card of the deck."""
        return self.cards.pop()
