"""
main.py
Phase 4: Graphical User Interface (PyQt5) for CSC200 Klondike Solitaire.
Balanced responsive layout tuned for 1080p & High-DPI Windows displays.
"""
import os
import sys
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter,
    QPixmap,
    QColor,
    QPen,
    QBrush,
    QRadialGradient,
    QFont,
    QKeySequence,
)
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QMessageBox,
    QShortcut,
    QSizePolicy,
)

from game_engine import SolitaireEngine
import generate_assets


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "cards")


def ensure_assets_exist():
    """Automatically generates the 52 card PNGs + back.png if not already present."""
    if not os.path.isdir(ASSETS_DIR) or len(os.listdir(ASSETS_DIR)) < 53:
        generate_assets.generate_all_assets(ASSETS_DIR)


class SolitaireBoardWidget(QWidget):
    """Custom QPainter game table supporting drag-and-drop, click-to-move, and double-click."""
    state_changed = pyqtSignal()

    def __init__(self, engine: SolitaireEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setMouseTracking(True)
        self.setMinimumSize(720, 520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pixmaps = {}
        self._load_pixmaps()

        # Interaction state
        self.selected = None
        self.press_pos = None
        self.press_item = None
        self.dragging = False
        self.drag_cards = []
        self.drag_source = None
        self.drag_offset = QPointF(0, 0)
        self.drag_pos = QPointF(0, 0)

        # Hint visual highlight
        self.active_hint = None
        self.hint_timer = QTimer(self)
        self.hint_timer.setSingleShot(True)
        self.hint_timer.timeout.connect(self._clear_hint)

        # Dynamic layout metrics
        self.card_w = 136
        self.card_h = 190
        self.col_gap = 20
        self.origin_x = 36
        self.top_y = 22
        self.tableau_y = 240

    def _load_pixmaps(self):
        ensure_assets_exist()
        for fname in os.listdir(ASSETS_DIR):
            if fname.endswith(".png"):
                full_path = os.path.join(ASSETS_DIR, fname)
                self.pixmaps[fname] = QPixmap(full_path)

    def show_hint(self, hint: dict):
        self.active_hint = hint
        self.hint_timer.start(3500)
        self.update()

    def _clear_hint(self):
        self.active_hint = None
        self.update()

    def clear_selection(self):
        self.selected = None
        self.dragging = False
        self.drag_cards = []
        self.drag_source = None
        self.update()

    # ------------------------------------------------------------------
    # Balanced Layout Geometry
    # ------------------------------------------------------------------
    def _compute_layout(self):
        w = max(self.width(), 720)
        h = max(self.height(), 520)

        margin_x = 36
        usable_w = w - 2 * margin_x
        gap = max(14, min(26, int(usable_w * 0.018)))

        # Balanced card size: fills 1080p cleanly without overflowing
        cw = min(142, int((usable_w - 6 * gap) / 7))
        cw = max(72, cw)
        ch = int(cw * (160 / 114))

        # Keep enough vertical space for long tableau cascades
        if ch * 4.2 > h:
            ch = int(h / 4.2)
            cw = int(ch * (114 / 160))

        total_row_w = 7 * cw + 6 * gap
        self.card_w = cw
        self.card_h = ch
        self.col_gap = gap
        self.origin_x = (w - total_row_w) / 2.0
        self.top_y = 22
        self.tableau_y = self.top_y + ch + 28

    def _col_x(self, col: int) -> float:
        return self.origin_x + col * (self.card_w + self.col_gap)

    def _stock_rect(self) -> QRectF:
        return QRectF(self._col_x(0), self.top_y, self.card_w, self.card_h)

    def _waste_rect(self, fan_index: int = 0) -> QRectF:
        fan_offset = fan_index * min(26, self.card_w * 0.22)
        return QRectF(self._col_x(1) + fan_offset, self.top_y, self.card_w, self.card_h)

    def _foundation_rect(self, f_idx: int) -> QRectF:
        return QRectF(self._col_x(3 + f_idx), self.top_y, self.card_w, self.card_h)

    def _tableau_base_rect(self, col: int) -> QRectF:
        return QRectF(self._col_x(col), self.tableau_y, self.card_w, self.card_h)

    def _tableau_card_rects(self, col: int):
        pile = self.engine.tableaus[col]
        down_cards = pile.face_down.to_list_bottom_to_top()
        up_cards = pile.face_up.to_list()

        n_down = len(down_cards)
        n_up = len(up_cards)
        avail_h = max(180, self.height() - self.tableau_y - self.card_h - 18)

        down_step = min(16, max(8, int(self.card_h * 0.085)))
        up_step = min(34, max(18, int(self.card_h * 0.20)))

        needed = n_down * down_step + max(0, n_up - 1) * up_step
        if needed > avail_h and needed > 0:
            ratio = avail_h / needed
            down_step = max(6, int(down_step * ratio))
            up_step = max(14, int(up_step * ratio))

        rects = []
        x = self._col_x(col)
        y = self.tableau_y

        for i, card in enumerate(down_cards):
            rects.append((False, i, card, QRectF(x, y, self.card_w, self.card_h)))
            y += down_step

        for i, card in enumerate(up_cards):
            rects.append((True, i, card, QRectF(x, y, self.card_w, self.card_h)))
            y += up_step

        return rects

    def _is_card_being_dragged(self, card) -> bool:
        return self.dragging and any(c.id == card.id for c in self.drag_cards)

    # ------------------------------------------------------------------
    # Painting the Table & Cards
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        self._compute_layout()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1. Emerald-Midnight Felt Gradient Background
        bg_grad = QRadialGradient(
            self.width() * 0.5,
            self.height() * 0.35,
            max(self.width(), self.height()) * 0.8,
        )
        bg_grad.setColorAt(0.0, QColor("#123934"))
        bg_grad.setColorAt(0.55, QColor("#0B2424"))
        bg_grad.setColorAt(1.0, QColor("#07131A"))
        painter.fillRect(self.rect(), QBrush(bg_grad))

        painter.setPen(QPen(QColor(45, 212, 191, 30), 1))
        painter.drawRoundedRect(10, 8, self.width() - 20, self.height() - 16, 16, 16)

        # 2. Stockpile (Queue)
        s_rect = self._stock_rect()
        self._draw_slot(
            painter,
            s_rect,
            "↻" if self.engine.stock.is_empty() else "",
            is_recycle=self.engine.stock.is_empty(),
        )
        if not self.engine.stock.is_empty():
            depth = min(3, max(1, self.engine.stock.size() // 7))
            for d in range(depth, 0, -1):
                self._draw_card_pixmap(
                    painter,
                    "back.png",
                    s_rect.translated(-d * 1.5, -d * 1.5),
                    shadow=(d == depth),
                )
            self._draw_card_pixmap(painter, "back.png", s_rect, shadow=False)

            badge_rect = QRectF(s_rect.right() - 28, s_rect.bottom() - 24, 24, 20)
            painter.setBrush(QColor(10, 20, 32, 225))
            painter.setPen(QPen(QColor("#2DD4BF"), 1.2))
            painter.drawRoundedRect(badge_rect, 6, 6)
            painter.setPen(QColor("#E2F8F5"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(badge_rect, Qt.AlignCenter, str(self.engine.stock.size()))

        if self._is_hint_target("stock"):
            self._draw_glow_border(painter, s_rect, QColor("#FACC15"), 3.5)

        # 3. Waste Pile (Stack)
        w_base = self._waste_rect(0)
        self._draw_slot(painter, w_base, "")
        waste_cards = self.engine.waste.to_list_bottom_to_top()
        visible_waste = waste_cards[-3:] if self.engine.draw_count == 3 else waste_cards[-1:]
        for idx, card in enumerate(visible_waste):
            if self._is_card_being_dragged(card):
                continue
            r = self._waste_rect(idx)
            self._draw_card_pixmap(painter, card.filename, r, shadow=True)
            is_top = idx == len(visible_waste) - 1
            if is_top and self.selected and self.selected[0] == "waste":
                self._draw_glow_border(painter, r, QColor("#2DD4BF"), 3.0)
            if is_top and self._is_hint_source("waste"):
                self._draw_glow_border(painter, r, QColor("#FACC15"), 3.5)

        # 4. Foundation Piles (Stacks)
        suit_icons = ["♠", "♥", "♣", "♦"]
        for f_idx, fpile in enumerate(self.engine.foundations):
            f_rect = self._foundation_rect(f_idx)
            self._draw_slot(painter, f_rect, suit_icons[f_idx])

            cards = fpile.stack.to_list_bottom_to_top()
            display_card = None
            for c in reversed(cards):
                if not self._is_card_being_dragged(c):
                    display_card = c
                    break
            if display_card:
                self._draw_card_pixmap(painter, display_card.filename, f_rect, shadow=True)

            if self.selected and self.selected[0] == "foundation" and self.selected[1] == f_idx:
                self._draw_glow_border(painter, f_rect, QColor("#2DD4BF"), 3.0)
            if self._is_hint_target(fpile.pile_id):
                self._draw_glow_border(painter, f_rect, QColor("#FACC15"), 3.5)
            elif self.dragging and len(self.drag_cards) == 1 and fpile.can_accept(self.drag_cards[0]):
                self._draw_glow_border(painter, f_rect, QColor(45, 212, 191, 180), 2.5)

        # 5. Tableau Columns (Face-down Stack + Face-up SinglyLinkedList)
        for col in range(7):
            base_rect = self._tableau_base_rect(col)
            self._draw_slot(painter, base_rect, "K")

            pile = self.engine.tableaus[col]
            card_rects = self._tableau_card_rects(col)

            last_visible_rect = base_rect
            for is_up, idx, card, rect in card_rects:
                if self._is_card_being_dragged(card):
                    continue
                fname = card.filename if is_up else "back.png"
                self._draw_card_pixmap(painter, fname, rect, shadow=True)
                last_visible_rect = rect

                if (
                    is_up
                    and self.selected
                    and self.selected[0] == "tableau"
                    and self.selected[1] == col
                    and idx >= self.selected[2]
                ):
                    self._draw_glow_border(painter, rect, QColor("#2DD4BF"), 3.0)

                if (
                    is_up
                    and self._is_hint_source(pile.pile_id)
                    and idx >= self.active_hint.get("card_index", 0)
                ):
                    self._draw_glow_border(painter, rect, QColor("#FACC15"), 3.5)

            if self._is_hint_target(pile.pile_id):
                self._draw_glow_border(painter, last_visible_rect, QColor("#FACC15"), 3.5)
            elif self.dragging and self.drag_cards:
                if self.drag_source and not (self.drag_source[0] == "tableau" and self.drag_source[1] == col):
                    if pile.can_accept(self.drag_cards[0]):
                        self._draw_glow_border(painter, last_visible_rect, QColor(45, 212, 191, 180), 2.5)

        # 6. Floating Dragged Card(s)
        if self.dragging and self.drag_cards:
            step = min(30, int(self.card_h * 0.19))
            for i, card in enumerate(self.drag_cards):
                r = QRectF(
                    self.drag_pos.x() - self.drag_offset.x(),
                    self.drag_pos.y() - self.drag_offset.y() + i * step,
                    self.card_w,
                    self.card_h,
                )
                self._draw_card_pixmap(painter, card.filename, r, shadow=True, elevated=True)

    def _draw_slot(self, painter: QPainter, rect: QRectF, symbol: str = "", is_recycle: bool = False):
        painter.save()
        painter.setBrush(QColor(255, 255, 255, 14))
        border_col = QColor(45, 212, 191, 110) if is_recycle else QColor(255, 255, 255, 45)
        pen = QPen(border_col, 1.8, Qt.DashLine if not is_recycle else Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 10, 10)
        if symbol:
            painter.setPen(QColor(45, 212, 191, 150) if is_recycle else QColor(255, 255, 255, 55))
            painter.setFont(QFont("Segoe UI Symbol", int(self.card_w * 0.28), QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, symbol)
        painter.restore()

    def _draw_card_pixmap(self, painter: QPainter, filename: str, rect: QRectF, shadow=True, elevated=False):
        if shadow:
            sh_off = 7 if elevated else 3
            sh_alpha = 110 if elevated else 65
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, sh_alpha))
            painter.drawRoundedRect(rect.translated(sh_off, sh_off), 9, 9)
            painter.restore()

        pm = self.pixmaps.get(filename)
        if pm and not pm.isNull():
            painter.drawPixmap(rect.toRect(), pm)

    def _draw_glow_border(self, painter: QPainter, rect: QRectF, color: QColor, width: float):
        painter.save()
        outer = QColor(color)
        outer.setAlpha(75)
        painter.setPen(QPen(outer, width + 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 10, 10)
        painter.setPen(QPen(color, width))
        painter.drawRoundedRect(rect, 9, 9)
        painter.restore()

    def _is_hint_source(self, pile_id: str) -> bool:
        return self.active_hint is not None and self.active_hint.get("src_id") == pile_id

    def _is_hint_target(self, pile_id: str) -> bool:
        return self.active_hint is not None and self.active_hint.get("dst_id") == pile_id

    # ------------------------------------------------------------------
    # Hit Testing & Mouse Handling
    # ------------------------------------------------------------------
    def _hit_test(self, pos: QPointF):
        if self._stock_rect().contains(pos):
            return ("stock", 0, 0, [], self._stock_rect())

        waste_cards = self.engine.waste.to_list_bottom_to_top()
        if waste_cards:
            vis_count = min(3, len(waste_cards)) if self.engine.draw_count == 3 else 1
            top_rect = self._waste_rect(vis_count - 1)
            if top_rect.contains(pos):
                return ("waste", 0, 0, [waste_cards[-1]], top_rect)

        for f_idx, fpile in enumerate(self.engine.foundations):
            f_rect = self._foundation_rect(f_idx)
            if f_rect.contains(pos):
                top = fpile.peek()
                return ("foundation", f_idx, 0, [top] if top else [], f_rect)

        for col in range(7):
            card_rects = self._tableau_card_rects(col)
            for is_up, idx, card, rect in reversed(card_rects):
                if rect.contains(pos):
                    if is_up:
                        up_cards = self.engine.tableaus[col].face_up.to_list()
                        return ("tableau", col, idx, up_cards[idx:], rect)
                    return ("tableau_facedown", col, idx, [], rect)
            if self._tableau_base_rect(col).contains(pos):
                return ("tableau_empty", col, 0, [], self._tableau_base_rect(col))

        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.engine.game_won:
            return
        self._clear_hint()
        pos = QPointF(event.pos())
        hit = self._hit_test(pos)

        if hit is None:
            self.clear_selection()
            return

        kind, p_idx, c_idx, cards, rect = hit

        if kind == "stock":
            self.clear_selection()
            if self.engine.draw_from_stock():
                self.state_changed.emit()
            return

        self.press_pos = pos
        self.press_item = (kind, p_idx, c_idx, cards, rect)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.press_item is None:
            return
        pos = QPointF(event.pos())
        kind, p_idx, c_idx, cards, rect = self.press_item

        if not self.dragging:
            if kind in ("waste", "tableau", "foundation") and cards:
                if (pos - self.press_pos).manhattanLength() > 7:
                    self.dragging = True
                    self.selected = None
                    self.drag_cards = cards
                    self.drag_source = (kind, p_idx, c_idx)
                    self.drag_offset = self.press_pos - rect.topLeft()
                    self.drag_pos = pos
                    self.update()
        else:
            self.drag_pos = pos
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if self.dragging:
            moved = self._handle_drag_drop()
            self.dragging = False
            self.drag_cards = []
            self.drag_source = None
            self.press_item = None
            self.update()
            if moved:
                self.state_changed.emit()
            return

        if self.press_item is not None:
            kind, p_idx, c_idx, cards, _ = self.press_item
            self.press_item = None

            if self.selected is None:
                if kind in ("waste", "tableau", "foundation") and cards:
                    self.selected = (kind, p_idx, c_idx, cards)
                    self.update()
            else:
                sel_kind, sel_pidx, sel_cidx, sel_cards = self.selected
                if sel_kind == kind and sel_pidx == p_idx and sel_cidx == c_idx:
                    self.selected = None
                    self.update()
                    return

                moved = self._execute_move(sel_kind, sel_pidx, sel_cidx, len(sel_cards), kind, p_idx)
                if moved:
                    self.selected = None
                    self.state_changed.emit()
                else:
                    if kind in ("waste", "tableau", "foundation") and cards:
                        self.selected = (kind, p_idx, c_idx, cards)
                    else:
                        self.selected = None
                self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton or self.engine.game_won:
            return
        self.clear_selection()
        hit = self._hit_test(QPointF(event.pos()))
        if hit is None:
            return
        kind, p_idx, c_idx, cards, _ = hit

        if kind == "waste" and cards:
            f_idx = self.engine.find_valid_foundation_for_card(cards[0])
            if f_idx is not None and self.engine.move_waste_to_foundation(f_idx):
                self.state_changed.emit()
                return
            for col in range(7):
                if self.engine.move_waste_to_tableau(col):
                    self.state_changed.emit()
                    return

        elif kind == "tableau" and len(cards) == 1:
            f_idx = self.engine.find_valid_foundation_for_card(cards[0])
            if f_idx is not None and self.engine.move_tableau_to_foundation(p_idx, f_idx):
                self.state_changed.emit()
                return

    def _handle_drag_drop(self) -> bool:
        if not self.drag_source or not self.drag_cards:
            return False

        drag_rect = QRectF(
            self.drag_pos.x() - self.drag_offset.x(),
            self.drag_pos.y() - self.drag_offset.y(),
            self.card_w,
            self.card_h,
        )

        candidates = []

        if len(self.drag_cards) == 1:
            for f_idx in range(4):
                inter = drag_rect.intersected(self._foundation_rect(f_idx))
                if not inter.isEmpty():
                    candidates.append((inter.width() * inter.height(), "foundation", f_idx))

        for col in range(7):
            card_rects = self._tableau_card_rects(col)
            target_rect = card_rects[-1][3] if card_rects else self._tableau_base_rect(col)
            col_rect = QRectF(
                target_rect.x(),
                self.tableau_y,
                self.card_w,
                max(self.card_h, target_rect.bottom() - self.tableau_y + 40),
            )
            inter = drag_rect.intersected(col_rect)
            if not inter.isEmpty():
                candidates.append((inter.width() * inter.height(), "tableau", col))

        candidates.sort(key=lambda x: x[0], reverse=True)
        src_kind, src_pidx, src_cidx = self.drag_source

        for _, dst_kind, dst_idx in candidates:
            if self._execute_move(src_kind, src_pidx, src_cidx, len(self.drag_cards), dst_kind, dst_idx):
                return True
        return False

    def _execute_move(self, src_kind, src_pidx, src_cidx, count, dst_kind, dst_idx) -> bool:
        if dst_kind == "foundation" and count == 1:
            if src_kind == "waste":
                return self.engine.move_waste_to_foundation(dst_idx)
            if src_kind == "tableau":
                return self.engine.move_tableau_to_foundation(src_pidx, dst_idx)
        elif dst_kind in ("tableau", "tableau_empty"):
            if src_kind == "waste":
                return self.engine.move_waste_to_tableau(dst_idx)
            if src_kind == "tableau":
                return self.engine.move_tableau_to_tableau(src_pidx, src_cidx, dst_idx)
            if src_kind == "foundation":
                return self.engine.move_foundation_to_tableau(src_pidx, dst_idx)
        return False


class DSAInspectorPanel(QFrame):
    """Live sidebar visualizing custom Stack, Queue, SinglyLinkedList & HashMap states."""
    def __init__(self, engine: SolitaireEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setFixedWidth(300)
        self.setObjectName("inspectorPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("LIVE DSA INSPECTOR")
        title.setStyleSheet("color: #2DD4BF; font-size: 14px; font-weight: 800; letter-spacing: 0.8px;")
        layout.addWidget(title)

        subtitle = QLabel("Real-time custom data structures")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content = QLabel()
        self.content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.content.setWordWrap(True)
        self.content.setStyleSheet(
            "color: #E2E8F0; font-family: Consolas, 'Courier New', monospace; font-size: 12px; line-height: 1.45;"
        )
        scroll.setWidget(self.content)
        layout.addWidget(scroll)

    def refresh(self):
        e = self.engine
        stock_front = e.stock.peek().label if not e.stock.is_empty() else "Empty"
        waste_top = e.waste.peek().label if not e.waste.is_empty() else "Empty"

        lines = [
            "<b style='color:#38BDF8;'>[QUEUE - FIFO] Stockpile</b>",
            f"Size: {e.stock.size()} | Front: {stock_front}",
            "",
            "<b style='color:#F472B6;'>[STACK - LIFO] Waste Pile</b>",
            f"Size: {e.waste.size()} | Top: {waste_top}",
            "",
            "<b style='color:#FACC15;'>[STACKS x4] Foundations</b>",
        ]
        for i, f in enumerate(e.foundations):
            top_lbl = f.peek().label if f.peek() else "Empty"
            lines.append(f"  F{i+1}: size={f.size():2d} | top={top_lbl}")

        lines.append("")
        lines.append("<b style='color:#2DD4BF;'>[STACK + LL x7] Tableaus</b>")
        for i, t in enumerate(e.tableaus):
            up_cards = t.face_up.to_list()
            chain = "→".join(c.label for c in up_cards[-3:]) if up_cards else "Empty"
            if len(up_cards) > 3:
                chain = "…→" + chain
            lines.append(f"  C{i+1}: D({t.face_down.size()}) | LL({t.face_up.size()}): {chain}")

        lines.append("")
        lines.append("<b style='color:#A78BFA;'>[STACKS x2] Undo / Redo</b>")
        lines.append(f"  Undo: {e.undo_stack.size()} | Redo: {e.redo_stack.size()}")

        lines.append("")
        lines.append("<b style='color:#34D399;'>[HASHMAP] Registry</b>")
        lines.append(f"  Cards: {e.card_registry.size()}/52 | Piles: {e.piles_map.size()}")

        self.content.setText("<br>".join(lines))


class SolitaireMainWindow(QMainWindow):
    """Main application window with balanced Glassmorphism HUD, Game Board, and DSA Inspector."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klondike Solitaire — CSC200 DSA Mid-Term Project")
        self.resize(1440, 860)

        self.engine = SolitaireEngine(draw_count=1)
        self.elapsed_seconds = 0
        self.win_dialog_shown = False

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._tick_clock)
        self.clock_timer.start(1000)

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._step_auto_complete)

        self._build_ui()
        self._apply_styles()
        self._setup_shortcuts()
        self._sync_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Top HUD Toolbar ---
        hud = QFrame()
        hud.setObjectName("topHud")
        hud.setFixedHeight(58)
        hud_layout = QHBoxLayout(hud)
        hud_layout.setContentsMargins(16, 8, 16, 8)
        hud_layout.setSpacing(10)

        brand = QLabel("♠ KLONDIKE SOLITAIRE")
        brand.setObjectName("brandTitle")
        hud_layout.addWidget(brand)
        hud_layout.addSpacing(8)

        self.score_lbl = QLabel("SCORE: 0")
        self.score_lbl.setObjectName("statPill")
        self.moves_lbl = QLabel("MOVES: 0")
        self.moves_lbl.setObjectName("statPill")
        self.time_lbl = QLabel("TIME: 00:00")
        self.time_lbl.setObjectName("statPill")

        hud_layout.addWidget(self.score_lbl)
        hud_layout.addWidget(self.moves_lbl)
        hud_layout.addWidget(self.time_lbl)
        hud_layout.addStretch()

        self.btn_mode = QPushButton("Draw 1")
        self.btn_mode.clicked.connect(self._toggle_draw_mode)

        self.btn_undo = QPushButton("↶ Undo")
        self.btn_undo.clicked.connect(self._do_undo)

        self.btn_redo = QPushButton("↷ Redo")
        self.btn_redo.clicked.connect(self._do_redo)

        self.btn_hint = QPushButton("✦ Hint")
        self.btn_hint.setObjectName("accentBtn")
        self.btn_hint.clicked.connect(self._do_hint)

        self.btn_auto = QPushButton("⚡ Finish")
        self.btn_auto.setObjectName("goldBtn")
        self.btn_auto.clicked.connect(self._start_auto_complete)
        self.btn_auto.setVisible(False)

        self.btn_inspector = QPushButton("DSA View")
        self.btn_inspector.setCheckable(True)
        self.btn_inspector.setChecked(True)
        self.btn_inspector.clicked.connect(self._toggle_inspector)

        self.btn_new = QPushButton("New Game")
        self.btn_new.setObjectName("primaryBtn")
        self.btn_new.clicked.connect(self._do_new_game)

        for btn in (
            self.btn_mode,
            self.btn_undo,
            self.btn_redo,
            self.btn_hint,
            self.btn_auto,
            self.btn_inspector,
            self.btn_new,
        ):
            btn.setCursor(Qt.PointingHandCursor)
            hud_layout.addWidget(btn)

        root_layout.addWidget(hud)

        # --- Center Workspace (Board + DSA Inspector) ---
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.board = SolitaireBoardWidget(self.engine)
        self.board.state_changed.connect(self._sync_ui)
        body.addWidget(self.board, 1)

        self.inspector = DSAInspectorPanel(self.engine)
        body.addWidget(self.inspector)

        root_layout.addLayout(body, 1)

        # --- Bottom Status Bar ---
        self.footer = QLabel(
            "Tip: Drag cards, click-to-move, or double-click any top card to send it straight to a Foundation Stack."
        )
        self.footer.setObjectName("footerBar")
        self.footer.setFixedHeight(30)
        root_layout.addWidget(self.footer)

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #07131A;
            }
            #topHud {
                background-color: #0B1924;
                border-bottom: 1px solid rgba(45, 212, 191, 0.25);
            }
            #brandTitle {
                color: #F8FAFC;
                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 800;
                letter-spacing: 0.8px;
            }
            #statPill {
                background-color: rgba(15, 36, 52, 0.95);
                color: #E2F8F5;
                border: 1px solid rgba(45, 212, 191, 0.30);
                border-radius: 8px;
                padding: 5px 12px;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #13283A;
                color: #E2E8F0;
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-radius: 7px;
                padding: 7px 13px;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1B3952;
                border-color: #2DD4BF;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #0E1D2A;
                color: #475569;
                border-color: rgba(71, 85, 105, 0.25);
            }
            QPushButton:checked {
                background-color: rgba(45, 212, 191, 0.20);
                border-color: #2DD4BF;
                color: #2DD4BF;
            }
            #primaryBtn {
                background-color: #0D9488;
                border: 1px solid #2DD4BF;
                color: #FFFFFF;
            }
            #primaryBtn:hover {
                background-color: #14B8A6;
            }
            #accentBtn {
                background-color: rgba(250, 204, 21, 0.16);
                border: 1px solid rgba(250, 204, 21, 0.55);
                color: #FDE047;
            }
            #accentBtn:hover {
                background-color: rgba(250, 204, 21, 0.28);
            }
            #goldBtn {
                background-color: #D97706;
                border: 1px solid #FBBF24;
                color: #FFFFFF;
            }
            #goldBtn:hover {
                background-color: #F59E0B;
            }
            #inspectorPanel {
                background-color: #09151F;
                border-left: 1px solid rgba(45, 212, 191, 0.25);
            }
            #footerBar {
                background-color: #071119;
                color: #94A3B8;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                padding-left: 14px;
                font-family: "Segoe UI";
                font-size: 12px;
            }
        """)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, self._do_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._do_redo)
        QShortcut(QKeySequence("H"), self, self._do_hint)
        QShortcut(QKeySequence("Ctrl+N"), self, self._do_new_game)
        QShortcut(QKeySequence("I"), self, self._toggle_inspector_shortcut)

    def _tick_clock(self):
        if not self.engine.game_won:
            self.elapsed_seconds += 1
            mins, secs = divmod(self.elapsed_seconds, 60)
            self.time_lbl.setText(f"TIME: {mins:02d}:{secs:02d}")

    def _sync_ui(self):
        self.score_lbl.setText(f"SCORE: {self.engine.score}")
        self.moves_lbl.setText(f"MOVES: {self.engine.moves_count}")
        self.btn_undo.setEnabled(not self.engine.undo_stack.is_empty())
        self.btn_redo.setEnabled(not self.engine.redo_stack.is_empty())
        self.btn_auto.setVisible(self.engine.can_auto_complete())
        self.inspector.refresh()
        self.board.update()

        if self.engine.game_won and not self.win_dialog_shown:
            self.auto_timer.stop()
            self.win_dialog_shown = True
            mins, secs = divmod(self.elapsed_seconds, 60)
            msg = QMessageBox(self)
            msg.setWindowTitle("Victory! Klondike Solved")
            msg.setIcon(QMessageBox.Information)
            msg.setText("Congratulations! You won Klondike Solitaire!")
            msg.setInformativeText(
                f"All 52 cards reached the 4 Foundation Stacks.\n\n"
                f"Final Score: {self.engine.score}\n"
                f"Total Moves: {self.engine.moves_count}\n"
                f"Time Elapsed: {mins:02d}:{secs:02d}"
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def _do_new_game(self):
        self.auto_timer.stop()
        self.engine.new_game(self.engine.draw_count)
        self.elapsed_seconds = 0
        self.win_dialog_shown = False
        self.time_lbl.setText("TIME: 00:00")
        self.board.clear_selection()
        self.footer.setText(
            f"New game dealt! Mode: Draw {self.engine.draw_count} | DeckArray shuffled with Fisher-Yates."
        )
        self._sync_ui()

    def _toggle_draw_mode(self):
        new_mode = 3 if self.engine.draw_count == 1 else 1
        self.engine.draw_count = new_mode
        self.btn_mode.setText(f"Draw {new_mode}")
        self._do_new_game()

    def _do_undo(self):
        self.auto_timer.stop()
        if self.engine.undo():
            self.board.clear_selection()
            self.footer.setText("Undo executed via LIFO Undo Stack.")
            self._sync_ui()

    def _do_redo(self):
        self.auto_timer.stop()
        if self.engine.redo():
            self.board.clear_selection()
            self.footer.setText("Redo executed via LIFO Redo Stack.")
            self._sync_ui()

    def _do_hint(self):
        hint = self.engine.get_hint()
        if hint:
            self.board.show_hint(hint)
            self.footer.setText(f"HINT: {hint['description']}")
        else:
            self.footer.setText("No further legal moves detected. Try Undo or New Game.")

    def _start_auto_complete(self):
        if self.engine.can_auto_complete():
            self.footer.setText("Auto-Completing all cards to Foundation Stacks...")
            self.auto_timer.start(85)

    def _step_auto_complete(self):
        if self.engine.step_auto_complete():
            self._sync_ui()
        else:
            self.auto_timer.stop()

    def _toggle_inspector(self):
        self.inspector.setVisible(self.btn_inspector.isChecked())

    def _toggle_inspector_shortcut(self):
        self.btn_inspector.setChecked(not self.btn_inspector.isChecked())
        self._toggle_inspector()


def main():
    ensure_assets_exist()
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    window = SolitaireMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()