# ♠ Klondike Solitaire — CSC200 DSA Mid-Term Project

**Course:** CSC200 - Data Structures & Algorithms  
**Instructor:** Nazeef Ul Haq  
**Term:** Fall 2026  

A complete, graphical **Klondike Solitaire** game built in Python (`PyQt5` & `Pillow`) where every core game mechanic—dealing, tableau cascades, stockpile cycling, foundation stacks, move history, and state lookup—is powered by **custom data structures built from scratch** using nodes, pointers, arrays, and separate-chaining hash tables.

---

## ✨ Key Features

* **100% Custom Data Structures:** Built without relying on Python's built-in `deque` or shortcut list methods for core game structures.
* **Complete Klondike Rules:** Alternating-color descending tableau cascades, suit-matched Ace-to-King foundation piles, automatic face-down card flipping, and Kings on empty columns.
* **Draw 1 & Draw 3 Modes:** Toggle between classic 1-card and 3-card stockpile drawing with order-preserving waste recycling.
* **Full Undo / Redo System:** Unlimited step-by-step undo and redo powered by dual LIFO `Stack`s (`MoveCommand` pattern).
* **Smart Hint Engine:** Highlights the highest-priority legal move on the board with a glowing indicator.
* **Auto-Complete:** Automatically cascades remaining cards to the foundation piles once all hidden cards are revealed.
* **Live DSA Inspector:** Built-in toggleable sidebar that visualizes the real-time state of every `Queue`, `Stack`, `SinglyLinkedList`, and `HashMap` as you play.
* **Auto-Generated Vector Card Assets:** Automatically generates all 52 crisp, anti-aliased playing card PNGs plus an ornate card back on first launch—no manual image downloads required.

---

## 🧱 Data Structures Architecture

All custom data structures live in `data_structures.py`:

| Data Structure | Implementation | Role in Solitaire | Key Time Complexities |
| :--- | :--- | :--- | :--- |
| **`DeckArray`** | Fixed-capacity array with index access & Fisher-Yates shuffle | Stores the initial 52-card deck before shuffling and dealing | Shuffle: $O(n)$, Deal: $O(1)$ |
| **`Stack` (LIFO)** | Singly linked `Node` pointers (`push`, `pop`, `peek`) | 4 Foundation piles, 7 Tableau face-down piles, Waste pile, Undo & Redo history stacks | `push`, `pop`, `peek`: $O(1)$ |
| **`Queue` (FIFO)** | Front & Rear `Node` pointers (`enqueue`, `dequeue`, `peek`) | Stockpile (Draw Pile) ensuring cards are drawn in strict FIFO order | `enqueue`, `dequeue`: $O(1)$ |
| **`SinglyLinkedList`** | Head & Tail `Node` pointers (`append`, `split_from`, `attach_sublist`) | Face-up cascading cards in each of the 7 Tableau columns; moves multi-card stacks via pointer re-linking | `append`, `attach_sublist`: $O(1)$, `split_from`: $O(k)$ |
| **`HashMap`** | Hash table with separate chaining (`put`, `get`, `remove`) | Tracks all 52 card positions/face-up states (`card_registry`) and pile references (`piles_map`) | Average `put`, `get`, `remove`: $O(1)$ |

---

## 📁 Project Structure

```text
solitare-DSA Mid proj/
├── data_structures.py   # Custom Node, DeckArray, Stack, Queue, SinglyLinkedList, HashMap
├── models.py            # Phase 1 & 2: Card, Deck, FoundationPile, TableauPile
├── game_engine.py       # Phase 3 & Bonus: Rules, MoveCommand, Undo/Redo, Hints, Scoring
├── generate_assets.py   # Procedural Pillow generator for all 52 card PNGs + back.png
├── main.py              # Phase 4: PyQt5 GUI, Drag/Click/Double-Click, Live DSA Inspector
├── requirements.txt     # Python dependencies (PyQt5, Pillow)
├── README.md            # Project documentation
└── assets/
    └── cards/           # Auto-generated on first launch (53 PNG files)
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
* Python 3.8+ installed on your system.

### 2. Create & Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

*(Ensure `requirements.txt` contains `PyQt5` and `Pillow`.)*

### 4. Run the Game
```powershell
python main.py
```

On the first run, `generate_assets.py` automatically creates the `assets/cards/` folder with all 52 cards and the card back, then launches the game window.

---

## 🎮 Controls & Shortcuts

### Mouse Controls
* **Click Stockpile (top-left):** Draw 1 or 3 cards into the Waste pile (or recycle Waste back into Stock when empty).
* **Drag & Drop:** Drag any face-up card or valid face-up tableau stack onto another tableau column or foundation pile.
* **Click-to-Move:** Click a card/stack to highlight it, then click the destination pile.
* **Double-Click:** Quickly sends an eligible top card from the Waste or Tableau straight to its matching Foundation stack.

### Keyboard Shortcuts
| Shortcut | Action |
| :--- | :--- |
| `Ctrl + Z` | Undo last move (LIFO Undo Stack) |
| `Ctrl + Y` | Redo undone move (LIFO Redo Stack) |
| `H` | Highlight a valid hint move |
| `I` | Toggle the Live DSA Inspector panel |
| `Ctrl + N` | Start a new shuffled game |

---

## 🏆 Scoring & Victory Condition

* **Waste $\rightarrow$ Tableau:** $+5$ points
* **Waste $\rightarrow$ Foundation:** $+10$ points
* **Tableau $\rightarrow$ Foundation:** $+10$ points ($+15$ if it flips a face-down card)
* **Flipping a face-down Tableau card:** $+5$ points
* **Foundation $\rightarrow$ Tableau:** $-15$ points
* **Recycling Waste (Draw 1 mode):** $-20$ points
* **Undo:** Reverses move score delta and applies a $-2$ point penalty
* **Win Condition:** All 4 Foundation `Stack`s reach 13 cards ($4 \times 13 = 52$ cards total).
