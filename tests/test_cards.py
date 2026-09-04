import random

import pytest

from casino.cards import RANKS, SUITS, Card, Deck


def test_deck_single_has_52_unique_cards():
    random.seed(0)
    deck = Deck(num_decks=1)
    assert len(deck.cards) == 52
    combos = {(card.rank, card.suit) for card in deck.cards}
    assert len(combos) == 52
    assert {suit for _, suit in combos} == set(SUITS)
    assert {rank for rank, _ in combos} == set(RANKS)


def test_deck_double_has_104_cards():
    random.seed(0)
    deck = Deck(num_decks=2)
    assert len(deck.cards) == 104
    for rank in RANKS:
        for suit in SUITS:
            count = sum(1 for card in deck.cards if card.rank == rank and card.suit == suit)
            assert count == 2


def test_draw_removes_and_returns_a_card():
    random.seed(0)
    deck = Deck(num_decks=1)
    size_before = len(deck.cards)
    card = deck.draw()
    assert len(deck.cards) == size_before - 1
    assert isinstance(card, Card)
    assert card.rank in RANKS
    assert card.suit in SUITS


def test_draw_all_cards_empties_deck_then_raises():
    random.seed(0)
    deck = Deck(num_decks=1)
    for _ in range(52):
        deck.draw()
    assert deck.cards == []
    with pytest.raises(IndexError):
        deck.draw()
