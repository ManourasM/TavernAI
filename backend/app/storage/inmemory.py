"""
In-memory storage implementation for TavernAI.

Wraps the current global dictionaries (orders_by_table, table_meta).
Behavior is identical to the existing MVP implementation.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from .base import Storage


class InMemoryStorage(Storage):
    """In-memory storage using dictionaries."""

    def __init__(self):
        """Initialize with empty storage."""
        # List of orders per table
        self._orders_by_table: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        # Metadata per table (people count, bread preference)
        self._table_meta: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"people": None, "bread": False}
        )

    def get_table(self, table_id: int) -> Dict[str, Any]:
        """Get metadata for a table."""
        return self._table_meta[table_id]

    def set_table(self, table_id: int, data: Dict[str, Any]) -> None:
        """Set metadata for a table."""
        self._table_meta[table_id] = data

    def delete_table(self, table_id: int) -> None:
        """Delete a table and all its associated orders."""
        if table_id in self._orders_by_table:
            del self._orders_by_table[table_id]
        if table_id in self._table_meta:
            del self._table_meta[table_id]

    def list_tables(self) -> List[int]:
        """List all table IDs that have orders or metadata."""
        all_tables = set(self._orders_by_table.keys()) | set(self._table_meta.keys())
        return sorted(list(all_tables))

    def table_exists(self, table_id: int) -> bool:
        """Check if a table has any orders or metadata."""
        return table_id in self._orders_by_table or table_id in self._table_meta

    def add_order(self, table_id: int, order: Dict[str, Any]) -> None:
        """Add an order (item) to a table's order list."""
        self._orders_by_table[table_id].append(order)

    def get_orders(self, table_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a table."""
        return self._orders_by_table[table_id]

    def update_order_status(
        self, table_id: int, item_id: str, status: str
    ) -> bool:
        """Update order status by item_id."""
        orders = self._orders_by_table.get(table_id, [])
        for order in orders:
            if order["id"] == item_id:
                order["status"] = status
                return True
        return False

    def delete_order(self, table_id: int, item_id: str) -> bool:
        """Delete/remove an order by item_id."""
        orders = self._orders_by_table.get(table_id, [])
        for i, order in enumerate(orders):
            if order["id"] == item_id:
                orders.pop(i)
                return True
        return False

    def get_order_by_id(self, table_id: int, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single order by item_id."""
        orders = self._orders_by_table.get(table_id, [])
        for order in orders:
            if order["id"] == item_id:
                return order
        return None

    def purge_done_orders(self, table_id: int, older_than_seconds: int = 0) -> int:
        """Remove all done/cancelled orders from a table."""
        orders = self._orders_by_table.get(table_id, [])
        initial_count = len(orders)

        if older_than_seconds <= 0:
            # Remove all done/cancelled
            self._orders_by_table[table_id] = [
                o for o in orders if o.get("status") == "pending"
            ]
        else:
            # Remove only those created before the cutoff time
            now = datetime.utcnow().isoformat()
            cutoff_time = now
            # Simple comparison: keep pending and recent done/cancelled
            self._orders_by_table[table_id] = [
                o
                for o in orders
                if o.get("status") == "pending"
                or (o.get("created_at", "") > cutoff_time)
            ]

        return initial_count - len(self._orders_by_table[table_id])

    def clear(self) -> None:
        """Clear all state."""
        self._orders_by_table.clear()
        self._table_meta.clear()
