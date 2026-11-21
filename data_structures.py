"""
data_structures.py
Custom Data Structures built from scratch for CSC200 - Data Structures & Algorithms.
Implements: Node, DeckArray (Array/List), Stack (LIFO), Queue (FIFO),
SinglyLinkedList, and HashMap (Separate-Chaining Hash Table).
"""
import random


class Node:
    """Basic node with data payload and next pointer for pointer-based structures."""
    def __init__(self, data, next_node=None):
        self.data = data
        self.next = next_node


class DeckArray:
    """
    Custom fixed-capacity Array/List implementation to store the 52-card deck
    before shuffling and dealing.
    """
    def __init__(self, capacity=52):
        self._capacity = capacity
        self._data = [None] * capacity
        self._size = 0

    def append(self, item):
        if self._size >= self._capacity:
            raise OverflowError("DeckArray capacity exceeded")
        self._data[self._size] = item
        self._size += 1

    def get(self, index):
        if index < 0 or index >= self._size:
            raise IndexError("DeckArray index out of range")
        return self._data[index]

    def set(self, index, value):
        if index < 0 or index >= self._size:
            raise IndexError("DeckArray index out of range")
        self._data[index] = value

    def pop_last(self):
        if self._size == 0:
            return None
        self._size -= 1
        item = self._data[self._size]
        self._data[self._size] = None
        return item

    def shuffle(self):
        """Fisher-Yates in-place O(n) shuffle."""
        for i in range(self._size - 1, 0, -1):
            j = random.randint(0, i)
            self._data[i], self._data[j] = self._data[j], self._data[i]

    def size(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def to_list(self):
        return [self._data[i] for i in range(self._size)]


class Stack:
    """
    Custom LIFO Stack implemented using Singly Linked Nodes.
    Used for: Foundation piles, Tableau face-down piles, Waste pile, Undo/Redo stacks.
    """
    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, item):
        new_node = Node(item, self._top)
        self._top = new_node
        self._size += 1

    def pop(self):
        if self.is_empty():
            return None
        item = self._top.data
        self._top = self._top.next
        self._size -= 1
        return item

    def peek(self):
        if self.is_empty():
            return None
        return self._top.data

    def is_empty(self):
        return self._top is None

    def size(self):
        return self._size

    def clear(self):
        self._top = None
        self._size = 0

    def to_list_bottom_to_top(self):
        """Returns items from bottom to top for UI rendering."""
        items = []
        curr = self._top
        while curr is not None:
            items.append(curr.data)
            curr = curr.next
        items.reverse()
        return items


class Queue:
    """
    Custom FIFO Queue implemented using Front & Rear Node pointers.
    Used for: Stockpile (Draw Pile) so cards are drawn in strict FIFO order.
    """
    def __init__(self):
        self._front = None
        self._rear = None
        self._size = 0

    def enqueue(self, item):
        new_node = Node(item)
        if self._rear is None:
            self._front = new_node
            self._rear = new_node
        else:
            self._rear.next = new_node
            self._rear = new_node
        self._size += 1

    def dequeue(self):
        if self.is_empty():
            return None
        item = self._front.data
        self._front = self._front.next
        if self._front is None:
            self._rear = None
        self._size -= 1
        return item

    def peek(self):
        if self.is_empty():
            return None
        return self._front.data

    def is_empty(self):
        return self._front is None

    def size(self):
        return self._size

    def clear(self):
        self._front = None
        self._rear = None
        self._size = 0

    def to_list(self):
        items = []
        curr = self._front
        while curr is not None:
            items.append(curr.data)
            curr = curr.next
        return items


class SinglyLinkedList:
    """
    Custom Singly Linked List with head & tail pointers.
    Used for: Face-up cascading cards in Tableau columns.
    Supports O(1) sublist attachment and pointer-based splitting for multi-card moves.
    """
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def append(self, item):
        new_node = Node(item)
        if self._head is None:
            self._head = new_node
            self._tail = new_node
        else:
            self._tail.next = new_node
            self._tail = new_node
        self._size += 1

    def get_head(self):
        return self._head.data if self._head else None

    def get_tail(self):
        return self._tail.data if self._tail else None

    def get_at(self, index):
        if index < 0 or index >= self._size:
            return None
        curr = self._head
        for _ in range(index):
            curr = curr.next
        return curr.data

    def remove_tail(self):
        if self._head is None:
            return None
        if self._head == self._tail:
            item = self._head.data
            self._head = None
            self._tail = None
            self._size = 0
            return item
        curr = self._head
        while curr.next != self._tail:
            curr = curr.next
        item = self._tail.data
        curr.next = None
        self._tail = curr
        self._size -= 1
        return item

    def split_from(self, index):
        """
        Detaches the sublist starting at `index` up to the tail.
        Returns (sub_head, sub_tail, moved_count).
        """
        if index < 0 or index >= self._size:
            return None, None, 0

        moved_count = self._size - index
        if index == 0:
            sub_head = self._head
            sub_tail = self._tail
            self._head = None
            self._tail = None
            self._size = 0
            return sub_head, sub_tail, moved_count

        prev = self._head
        for _ in range(index - 1):
            prev = prev.next

        sub_head = prev.next
        sub_tail = self._tail
        prev.next = None
        self._tail = prev
        self._size = index
        return sub_head, sub_tail, moved_count

    def attach_sublist(self, sub_head, sub_tail, count):
        """Attaches an existing linked-node chain to the tail in O(1) time."""
        if sub_head is None or count <= 0:
            return
        if self._head is None:
            self._head = sub_head
            self._tail = sub_tail
        else:
            self._tail.next = sub_head
            self._tail = sub_tail
        self._size += count

    def is_empty(self):
        return self._size == 0

    def size(self):
        return self._size

    def clear(self):
        self._head = None
        self._tail = None
        self._size = 0

    def to_list(self):
        items = []
        curr = self._head
        while curr is not None:
            items.append(curr.data)
            curr = curr.next
        return items


class _HashEntry:
    def __init__(self, key, value, next_entry=None):
        self.key = key
        self.value = value
        self.next = next_entry


class HashMap:
    """
    Custom HashMap (Hash Table with Separate Chaining).
    Used for: Tracking card positions, face-up/down states, and pile references in O(1) avg time.
    """
    def __init__(self, capacity=64):
        self._capacity = capacity
        self._buckets = [None] * capacity
        self._size = 0

    def _hash(self, key):
        return hash(key) % self._capacity

    def put(self, key, value):
        idx = self._hash(key)
        curr = self._buckets[idx]
        while curr is not None:
            if curr.key == key:
                curr.value = value
                return
            curr = curr.next
        new_entry = _HashEntry(key, value, self._buckets[idx])
        self._buckets[idx] = new_entry
        self._size += 1

    def get(self, key, default=None):
        idx = self._hash(key)
        curr = self._buckets[idx]
        while curr is not None:
            if curr.key == key:
                return curr.value
            curr = curr.next
        return default

    def remove(self, key):
        idx = self._hash(key)
        curr = self._buckets[idx]
        prev = None
        while curr is not None:
            if curr.key == key:
                if prev is None:
                    self._buckets[idx] = curr.next
                else:
                    prev.next = curr.next
                self._size -= 1
                return curr.value
            prev = curr
            curr = curr.next
        return None

    def contains(self, key):
        return self.get(key) is not None

    def size(self):
        return self._size

    def clear(self):
        self._buckets = [None] * self._capacity
        self._size = 0

    def items(self):
        result = []
        for head in self._buckets:
            curr = head
            while curr is not None:
                result.append((curr.key, curr.value))
                curr = curr.next
        return result