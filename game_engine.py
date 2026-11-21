"""
game_engine.py
Phase 3 & Bonus Features:
- Game Initialization & Dealing
- Legal Move Validation & Execution
- Stockpile FIFO Drawing (1-card and 3-card modes) + Order-Preserving Recycle
- Undo / Redo via Custom LIFO Stacks
- Smart Hint Engine, Auto-Complete, Scoring, and Win Detection
"""
from data_structures import Stack, Queue, HashMap
from models import Deck, FoundationPile, TableauPile, SUITS


class MoveCommand:
    """Encapsulates a single reversible game action for the Undo/Redo Stacks."""
    def __init__(
        self,
        action_type: str,
        src_id: str = None,
        dst_id: str = None,
        card_index: int = 0,
        count: int = 1,
        flipped_source: bool = False,
        score_delta: int = 0,
    ):
        self.action_type = action_type
        self.src_id = src_id
        self.dst_id = dst_id
        self.card_index = card_index
        self.count = count
        self.flipped_source = flipped_source
        self.score_delta = score_delta


class SolitaireEngine:
    """Core Klondike Solitaire Engine powered strictly by custom DSA structures."""

    def __init__(self, draw_count: int = 1):
        self.draw_count = draw_count if draw_count in (1, 3) else 1
        self.stock = Queue()
        self.waste = Stack()
        self.foundations = [FoundationPile(i, SUITS[i]) for i in range(4)]
        self.tableaus = [TableauPile(i) for i in range(7)]

        # Custom HashMaps for O(1) lookup of piles and card states/locations
        self.piles_map = HashMap(32)
        self.card_registry = HashMap(128)

        # Custom Undo/Redo LIFO Stacks
        self.undo_stack = Stack()
        self.redo_stack = Stack()

        self.score = 0
        self.moves_count = 0
        self.game_won = False

        self.new_game(self.draw_count)

    def new_game(self, draw_count: int = None):
        """Resets all data structures, shuffles DeckArray, and deals Klondike layout."""
        if draw_count in (1, 3):
            self.draw_count = draw_count

        self.stock = Queue()
        self.waste = Stack()
        self.foundations = [FoundationPile(i, SUITS[i]) for i in range(4)]
        self.tableaus = [TableauPile(i) for i in range(7)]

        self.piles_map.clear()
        self.card_registry.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()

        self.piles_map.put("stock", self.stock)
        self.piles_map.put("waste", self.waste)
        for f in self.foundations:
            self.piles_map.put(f.pile_id, f)
        for t in self.tableaus:
            self.piles_map.put(t.pile_id, t)

        self.score = 0
        self.moves_count = 0
        self.game_won = False

        deck = Deck()
        deck.shuffle()

        # Deal 7 tableau columns (1 to 7 cards; last card face-up in LinkedList)
        for col in range(7):
            pile = self.tableaus[col]
            for row in range(col + 1):
                card = deck.deal_card()
                if row == col:
                    card.face_up = True
                    pile.face_up.append(card)
                else:
                    card.face_up = False
                    pile.face_down.push(card)
                self._register_card(card, pile.pile_id)

        # Remaining 24 cards go into the FIFO Stockpile Queue
        while deck.remaining() > 0:
            card = deck.deal_card()
            card.face_up = False
            self.stock.enqueue(card)
            self._register_card(card, "stock")

    def _register_card(self, card, pile_id: str):
        self.card_registry.put(
            card.id,
            {"card": card, "pile_id": pile_id, "face_up": card.face_up},
        )

    def _record_move(self, cmd: MoveCommand, is_redo: bool = False):
        self.undo_stack.push(cmd)
        if not is_redo:
            self.redo_stack.clear()
        self.score = max(0, self.score + cmd.score_delta)
        self.moves_count += 1
        self.game_won = self.check_win()

    # ------------------------------------------------------------------
    # Stockpile Queue Operations (Draw 1 / Draw 3 & Recycle)
    # ------------------------------------------------------------------
    def draw_from_stock(self, is_redo: bool = False) -> bool:
        """Draws 1 or 3 cards from FIFO Stock Queue to LIFO Waste Stack, or recycles."""
        if not self.stock.is_empty():
            drawn = 0
            while drawn < self.draw_count and not self.stock.is_empty():
                card = self.stock.dequeue()
                card.face_up = True
                self.waste.push(card)
                self._register_card(card, "waste")
                drawn += 1

            cmd = MoveCommand(
                action_type="stock_draw",
                src_id="stock",
                dst_id="waste",
                count=drawn,
                score_delta=0,
            )
            self._record_move(cmd, is_redo=is_redo)
            return True

        # Recycle Waste Stack back to Stock Queue preserving original draw order
        if not self.waste.is_empty():
            temp_stack = Stack()
            recycled_count = 0
            while not self.waste.is_empty():
                temp_stack.push(self.waste.pop())
                recycled_count += 1
            while not temp_stack.is_empty():
                card = temp_stack.pop()
                card.face_up = False
                self.stock.enqueue(card)
                self._register_card(card, "stock")

            penalty = -20 if self.draw_count == 1 else 0
            cmd = MoveCommand(
                action_type="stock_recycle",
                src_id="waste",
                dst_id="stock",
                count=recycled_count,
                score_delta=penalty,
            )
            self._record_move(cmd, is_redo=is_redo)
            return True

        return False

    # ------------------------------------------------------------------
    # Legal Move Validation & Execution
    # ------------------------------------------------------------------
    def can_move_waste_to_tableau(self, dst_col: int) -> bool:
        if self.waste.is_empty():
            return False
        return self.tableaus[dst_col].can_accept(self.waste.peek())

    def move_waste_to_tableau(self, dst_col: int, is_redo: bool = False) -> bool:
        if not self.can_move_waste_to_tableau(dst_col):
            return False
        card = self.waste.pop()
        dst = self.tableaus[dst_col]
        dst.face_up.append(card)
        self._register_card(card, dst.pile_id)

        cmd = MoveCommand(
            action_type="waste_to_tableau",
            src_id="waste",
            dst_id=dst.pile_id,
            count=1,
            score_delta=5,
        )
        self._record_move(cmd, is_redo=is_redo)
        return True

    def can_move_waste_to_foundation(self, dst_f: int) -> bool:
        if self.waste.is_empty():
            return False
        return self.foundations[dst_f].can_accept(self.waste.peek())

    def move_waste_to_foundation(self, dst_f: int, is_redo: bool = False) -> bool:
        if not self.can_move_waste_to_foundation(dst_f):
            return False
        card = self.waste.pop()
        dst = self.foundations[dst_f]
        dst.push(card)
        self._register_card(card, dst.pile_id)

        cmd = MoveCommand(
            action_type="waste_to_foundation",
            src_id="waste",
            dst_id=dst.pile_id,
            count=1,
            score_delta=10,
        )
        self._record_move(cmd, is_redo=is_redo)
        return True

    def can_move_tableau_to_foundation(self, src_col: int, dst_f: int) -> bool:
        src = self.tableaus[src_col]
        if src.face_up.is_empty():
            return False
        return self.foundations[dst_f].can_accept(src.face_up.get_tail())

    def move_tableau_to_foundation(self, src_col: int, dst_f: int, is_redo: bool = False) -> bool:
        if not self.can_move_tableau_to_foundation(src_col, dst_f):
            return False
        src = self.tableaus[src_col]
        dst = self.foundations[dst_f]

        card = src.face_up.remove_tail()
        dst.push(card)
        self._register_card(card, dst.pile_id)

        flipped = src.flip_top_if_needed()
        if flipped:
            self._register_card(flipped, src.pile_id)

        cmd = MoveCommand(
            action_type="tableau_to_foundation",
            src_id=src.pile_id,
            dst_id=dst.pile_id,
            count=1,
            flipped_source=(flipped is not None),
            score_delta=15 if flipped else 10,
        )
        self._record_move(cmd, is_redo=is_redo)
        return True

    def can_move_tableau_to_tableau(self, src_col: int, card_index: int, dst_col: int) -> bool:
        if src_col == dst_col:
            return False
        src = self.tableaus[src_col]
        card = src.face_up.get_at(card_index)
        if card is None:
            return False
        return self.tableaus[dst_col].can_accept(card)

    def move_tableau_to_tableau(
        self, src_col: int, card_index: int, dst_col: int, is_redo: bool = False
    ) -> bool:
        if not self.can_move_tableau_to_tableau(src_col, card_index, dst_col):
            return False
        src = self.tableaus[src_col]
        dst = self.tableaus[dst_col]

        # Pointer-based SinglyLinkedList split & O(1) attach
        sub_head, sub_tail, moved_count = src.face_up.split_from(card_index)
        dst.face_up.attach_sublist(sub_head, sub_tail, moved_count)

        # Update HashMap entries for all moved cards
        curr = sub_head
        for _ in range(moved_count):
            self._register_card(curr.data, dst.pile_id)
            curr = curr.next

        flipped = src.flip_top_if_needed()
        if flipped:
            self._register_card(flipped, src.pile_id)

        cmd = MoveCommand(
            action_type="tableau_to_tableau",
            src_id=src.pile_id,
            dst_id=dst.pile_id,
            card_index=card_index,
            count=moved_count,
            flipped_source=(flipped is not None),
            score_delta=5 if flipped else 0,
        )
        self._record_move(cmd, is_redo=is_redo)
        return True

    def can_move_foundation_to_tableau(self, src_f: int, dst_col: int) -> bool:
        src = self.foundations[src_f]
        if src.stack.is_empty():
            return False
        return self.tableaus[dst_col].can_accept(src.peek())

    def move_foundation_to_tableau(self, src_f: int, dst_col: int, is_redo: bool = False) -> bool:
        if not self.can_move_foundation_to_tableau(src_f, dst_col):
            return False
        src = self.foundations[src_f]
        dst = self.tableaus[dst_col]

        card = src.pop()
        dst.face_up.append(card)
        self._register_card(card, dst.pile_id)

        cmd = MoveCommand(
            action_type="foundation_to_tableau",
            src_id=src.pile_id,
            dst_id=dst.pile_id,
            count=1,
            score_delta=-15,
        )
        self._record_move(cmd, is_redo=is_redo)
        return True

    def find_valid_foundation_for_card(self, card):
        for i, f in enumerate(self.foundations):
            if f.can_accept(card):
                return i
        return None

    # ------------------------------------------------------------------
    # Undo & Redo System (LIFO Stacks)
    # ------------------------------------------------------------------
    def undo(self) -> bool:
        if self.undo_stack.is_empty():
            return False
        cmd = self.undo_stack.pop()
        self.redo_stack.push(cmd)

        if cmd.action_type == "stock_draw":
            # Restore drawn cards back to front of FIFO Stock Queue using pure Stack+Queue ops
            temp_stack = Stack()
            for _ in range(cmd.count):
                temp_stack.push(self.waste.pop())
            new_stock = Queue()
            while not temp_stack.is_empty():
                card = temp_stack.pop()
                card.face_up = False
                new_stock.enqueue(card)
                self._register_card(card, "stock")
            while not self.stock.is_empty():
                new_stock.enqueue(self.stock.dequeue())
            self.stock = new_stock
            self.piles_map.put("stock", self.stock)

        elif cmd.action_type == "stock_recycle":
            while not self.stock.is_empty():
                card = self.stock.dequeue()
                card.face_up = True
                self.waste.push(card)
                self._register_card(card, "waste")

        elif cmd.action_type == "waste_to_tableau":
            dst = self.piles_map.get(cmd.dst_id)
            card = dst.face_up.remove_tail()
            self.waste.push(card)
            self._register_card(card, "waste")

        elif cmd.action_type == "waste_to_foundation":
            dst = self.piles_map.get(cmd.dst_id)
            card = dst.pop()
            self.waste.push(card)
            self._register_card(card, "waste")

        elif cmd.action_type == "tableau_to_foundation":
            src = self.piles_map.get(cmd.src_id)
            dst = self.piles_map.get(cmd.dst_id)
            if cmd.flipped_source:
                unflip = src.face_up.remove_tail()
                unflip.face_up = False
                src.face_down.push(unflip)
                self._register_card(unflip, src.pile_id)
            card = dst.pop()
            src.face_up.append(card)
            self._register_card(card, src.pile_id)

        elif cmd.action_type == "tableau_to_tableau":
            src = self.piles_map.get(cmd.src_id)
            dst = self.piles_map.get(cmd.dst_id)
            if cmd.flipped_source:
                unflip = src.face_up.remove_tail()
                unflip.face_up = False
                src.face_down.push(unflip)
                self._register_card(unflip, src.pile_id)
            split_idx = dst.face_up.size() - cmd.count
            sub_head, sub_tail, moved_count = dst.face_up.split_from(split_idx)
            src.face_up.attach_sublist(sub_head, sub_tail, moved_count)
            curr = sub_head
            for _ in range(moved_count):
                self._register_card(curr.data, src.pile_id)
                curr = curr.next

        elif cmd.action_type == "foundation_to_tableau":
            src = self.piles_map.get(cmd.src_id)
            dst = self.piles_map.get(cmd.dst_id)
            card = dst.face_up.remove_tail()
            src.push(card)
            self._register_card(card, src.pile_id)

        self.score = max(0, self.score - cmd.score_delta - 2)
        self.moves_count = max(0, self.moves_count - 1)
        self.game_won = self.check_win()
        return True

    def redo(self) -> bool:
        if self.redo_stack.is_empty():
            return False
        cmd = self.redo_stack.pop()

        if cmd.action_type in ("stock_draw", "stock_recycle"):
            return self.draw_from_stock(is_redo=True)
        elif cmd.action_type == "waste_to_tableau":
            dst_idx = int(cmd.dst_id.split("_")[1])
            return self.move_waste_to_tableau(dst_idx, is_redo=True)
        elif cmd.action_type == "waste_to_foundation":
            dst_idx = int(cmd.dst_id.split("_")[1])
            return self.move_waste_to_foundation(dst_idx, is_redo=True)
        elif cmd.action_type == "tableau_to_foundation":
            src_idx = int(cmd.src_id.split("_")[1])
            dst_idx = int(cmd.dst_id.split("_")[1])
            return self.move_tableau_to_foundation(src_idx, dst_idx, is_redo=True)
        elif cmd.action_type == "tableau_to_tableau":
            src_idx = int(cmd.src_id.split("_")[1])
            dst_idx = int(cmd.dst_id.split("_")[1])
            return self.move_tableau_to_tableau(src_idx, cmd.card_index, dst_idx, is_redo=True)
        elif cmd.action_type == "foundation_to_tableau":
            src_idx = int(cmd.src_id.split("_")[1])
            dst_idx = int(cmd.dst_id.split("_")[1])
            return self.move_foundation_to_tableau(src_idx, dst_idx, is_redo=True)
        return False

    # ------------------------------------------------------------------
    # Smart Hint Engine, Auto-Complete & Victory Detection
    # ------------------------------------------------------------------
    def get_hint(self):
        """Scans board for the highest-priority valid legal move."""
        # Priority 1: Tableau top card -> Foundation
        for col, t in enumerate(self.tableaus):
            if not t.face_up.is_empty():
                card = t.face_up.get_tail()
                f_idx = self.find_valid_foundation_for_card(card)
                if f_idx is not None:
                    return {
                        "src_id": t.pile_id,
                        "dst_id": self.foundations[f_idx].pile_id,
                        "card_index": t.face_up.size() - 1,
                        "description": f"Move {card.label} from Column {col+1} to Foundation {f_idx+1}",
                    }

        # Priority 2: Waste top card -> Foundation
        if not self.waste.is_empty():
            card = self.waste.peek()
            f_idx = self.find_valid_foundation_for_card(card)
            if f_idx is not None:
                return {
                    "src_id": "waste",
                    "dst_id": self.foundations[f_idx].pile_id,
                    "card_index": 0,
                    "description": f"Move {card.label} from Waste to Foundation {f_idx+1}",
                }

        # Priority 3: Tableau sublist -> Tableau
        for src_col, src in enumerate(self.tableaus):
            if src.face_up.is_empty():
                continue
            head_card = src.face_up.get_head()
            for dst_col, dst in enumerate(self.tableaus):
                if src_col == dst_col:
                    continue
                if dst.can_accept(head_card):
                    # Avoid pointless King bounce between empty-hidden columns
                    if head_card.rank == 13 and src.face_down.is_empty() and dst.face_up.is_empty():
                        continue
                    return {
                        "src_id": src.pile_id,
                        "dst_id": dst.pile_id,
                        "card_index": 0,
                        "description": f"Move {head_card.label} stack from Column {src_col+1} to Column {dst_col+1}",
                    }

        # Priority 4: Waste top card -> Tableau
        if not self.waste.is_empty():
            card = self.waste.peek()
            for dst_col, dst in enumerate(self.tableaus):
                if dst.can_accept(card):
                    return {
                        "src_id": "waste",
                        "dst_id": dst.pile_id,
                        "card_index": 0,
                        "description": f"Move {card.label} from Waste to Column {dst_col+1}",
                    }

        # Priority 5: Draw from Stockpile or Recycle
        if not self.stock.is_empty():
            return {
                "src_id": "stock",
                "dst_id": "waste",
                "card_index": 0,
                "description": "Draw next card(s) from the Stockpile Queue",
            }
        if not self.waste.is_empty():
            return {
                "src_id": "stock",
                "dst_id": "stock",
                "card_index": 0,
                "description": "Click empty Stockpile to recycle Waste cards",
            }
        return None

    def can_auto_complete(self) -> bool:
        """True when all face-down cards are revealed and Stock/Waste are empty."""
        if self.game_won:
            return False
        if not self.stock.is_empty() or not self.waste.is_empty():
            return False
        for t in self.tableaus:
            if not t.face_down.is_empty():
                return False
        return True

    def step_auto_complete(self) -> bool:
        """Moves one eligible card to its Foundation pile during auto-complete."""
        for col, t in enumerate(self.tableaus):
            if not t.face_up.is_empty():
                card = t.face_up.get_tail()
                f_idx = self.find_valid_foundation_for_card(card)
                if f_idx is not None:
                    return self.move_tableau_to_foundation(col, f_idx)
        return False

    def check_win(self) -> bool:
        """Win condition: all 4 Foundation Stacks contain 13 cards (52 total)."""
        return all(f.is_complete() for f in self.foundations)