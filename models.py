"""
models.py
Phase 1 & Phase 2: Card, Deck, FoundationPile (Stack), and TableauPile (Stack + SinglyLinkedList).
"""
from data_structures import DeckArray, Stack, SinglyLinkedList

SUITS = ["spades", "hearts", "clubs", "diamonds"]
SUIT_SYMBOLS = {
    "spades": "♠",
    "hearts": "♥",
    "clubs": "♣",
    "diamonds": "♦",
}
RANK_NAMES = {
    1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K",
}


class Card:
    """Represents a single standard playing card."""
    def __init__(self, suit: str, rank: int, face_up: bool = False):
        self.suit = suit
        self.rank = rank
        self.face_up = face_up
        self.color = "red" if suit in ("hearts", "diamonds") else "black"
        self.id = f"{RANK_NAMES[rank]}_{suit}"
        self.filename = f"{RANK_NAMES[rank].lower()}_of_{suit}.png"

    @property
    def label(self):
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def flip(self):
        self.face_up = not self.face_up

    def __repr__(self):
        state = "UP" if self.face_up else "DN"
        return f"Card({self.label}, {state})"


class Deck:
    """Stores 52 Card objects in a custom DeckArray and handles Fisher-Yates shuffling."""
    def __init__(self):
        self.cards = DeckArray(52)
        for suit in SUITS:
            for rank in range(1, 14):
                self.cards.append(Card(suit, rank, face_up=False))

    def shuffle(self):
        self.cards.shuffle()

    def deal_card(self):
        return self.cards.pop_last()

    def remaining(self):
        return self.cards.size()


class FoundationPile:
    """
    Represents one of the 4 Foundation piles using a custom LIFO Stack.
    Builds Ace (1) -> King (13) of the same suit.
    """
    def __init__(self, index: int, suit_hint: str = None):
        self.index = index
        self.pile_id = f"foundation_{index}"
        self.suit_hint = suit_hint
        self.stack = Stack()

    def can_accept(self, card: Card) -> bool:
        if card is None:
            return False
        if self.stack.is_empty():
            return card.rank == 1
        top = self.stack.peek()
        return card.suit == top.suit and card.rank == top.rank + 1

    def push(self, card: Card):
        self.stack.push(card)

    def pop(self):
        return self.stack.pop()

    def peek(self):
        return self.stack.peek()

    def is_complete(self) -> bool:
        return self.stack.size() == 13

    def size(self) -> int:
        return self.stack.size()


class TableauPile:
    """
    Represents one of the 7 Tableau columns:
    - face_down: custom LIFO Stack storing unrevealed cards
    - face_up: custom SinglyLinkedList storing cascading face-up cards
    """
    def __init__(self, index: int):
        self.index = index
        self.pile_id = f"tableau_{index}"
        self.face_down = Stack()
        self.face_up = SinglyLinkedList()

    def can_accept(self, card: Card) -> bool:
        """Klondike rule: alternating colors and descending rank; Kings on empty columns."""
        if card is None:
            return False
        if self.face_up.is_empty():
            if not self.face_down.is_empty():
                return False
            return card.rank == 13
        top_card = self.face_up.get_tail()
        return card.color != top_card.color and card.rank == top_card.rank - 1

    def flip_top_if_needed(self):
        """If no face-up cards remain, pops top face-down card and flips it face-up."""
        if self.face_up.is_empty() and not self.face_down.is_empty():
            card = self.face_down.pop()
            card.face_up = True
            self.face_up.append(card)
            return card
        return None

    def total_cards(self) -> int:
        return self.face_down.size() + self.face_up.size()