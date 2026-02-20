"""
Abstract Storage interface for TavernAI.

Defines the contract for order and table metadata storage.
Implementations can be in-memory, database-backed, or other backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class Storage(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    def get_table(self, table_id: int) -> Dict[str, Any]:
        """
        Get metadata for a table.
        
        Returns dict with "people" and "bread" keys.
        If table doesn't exist, returns default: {"people": None, "bread": False}
        """
        ...

    @abstractmethod
    def set_table(self, table_id: int, data: Dict[str, Any]) -> None:
        """Set metadata for a table."""
        ...

    @abstractmethod
    def delete_table(self, table_id: int) -> None:
        """Delete a table and all its associated orders."""
        ...

    @abstractmethod
    def list_tables(self) -> List[int]:
        """List all table IDs that have orders or metadata."""
        ...

    @abstractmethod
    def table_exists(self, table_id: int) -> bool:
        """Check if a table has any orders or metadata."""
        ...

    @abstractmethod
    def add_order(self, table_id: int, order: Dict[str, Any]) -> None:
        """Add an order (item) to a table's order list."""
        ...

    @abstractmethod
    def get_orders(self, table_id: int) -> List[Dict[str, Any]]:
        """
        Get all orders for a table.
        
        Returns empty list if table doesn't exist.
        Returns all orders including pending/done/cancelled.
        """
        ...

    @abstractmethod
    def update_order_status(
        self, table_id: int, item_id: str, status: str
    ) -> bool:
        """
        Update order status by item_id.
        
        Status values: "pending", "done", "cancelled"
        Returns True if item found and updated, False otherwise.
        """
        ...

    @abstractmethod
    def delete_order(self, table_id: int, item_id: str) -> bool:
        """
        Delete/remove an order by item_id.
        
        Returns True if item found and deleted, False otherwise.
        """
        ...

    @abstractmethod
    def get_order_by_id(self, table_id: int, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single order by item_id.
        
        Returns None if not found.
        """
        ...

    @abstractmethod
    def purge_done_orders(self, table_id: int, older_than_seconds: int = 0) -> int:
        """
        Remove all done/cancelled orders from a table.
        
        If older_than_seconds > 0, only remove items created before that timestamp.
        Returns count of removed items.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all state (orders and metadata for all tables)."""
        ...
