"""
SQLite storage implementation for TavernAI.

Uses SQLAlchemy 2.0 to provide persistent storage backed by SQLite.
Implements the Storage ABC interface exactly with explicit transaction blocks.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta

from app.storage.base import Storage
from app.storage.models import Base, TableMetaModel, OrderModel


class SQLiteStorage(Storage):
    """SQLite-backed storage implementation with transaction blocks."""
    
    def __init__(self, database_url: str = "sqlite:///tavern.db"):
        """
        Initialize SQLite storage.
        
        Args:
            database_url: SQLAlchemy database URL (default: sqlite:///tavern.db)
        """
        self.database_url = database_url
        
        # Create engine with production-safe settings
        # echo=False: suppress SQL logging (set to True for debugging)
        # future=True: use SQLAlchemy 2.0 style execution
        # pool_pre_ping=True: verify connections before use (detect stale connections)
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        
        # Create sessionmaker
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create all tables on startup
        Base.metadata.create_all(self.engine)
    
    def _get_session(self) -> Session:
        """Get a new database session (caller must close)."""
        return self.SessionLocal()
    
    def get_table(self, table_id: int) -> Dict[str, Any]:
        """Get metadata for a table."""
        session = self._get_session()
        try:
            stmt = select(TableMetaModel).where(TableMetaModel.table_id == table_id)
            row = session.execute(stmt).scalar_one_or_none()
            if row:
                return row.to_dict()
            return {"people": None, "bread": False}
        finally:
            session.close()
    
    def set_table(self, table_id: int, data: Dict[str, Any]) -> None:
        """Set metadata for a table. Wrapped in explicit transaction."""
        session = self._get_session()
        try:
            with session.begin():
                # Try to get existing row
                stmt = select(TableMetaModel).where(TableMetaModel.table_id == table_id)
                row = session.execute(stmt).scalar_one_or_none()
                
                if row:
                    # Update existing
                    row.people = data.get("people")
                    row.bread = data.get("bread", False)
                else:
                    # Create new (unique constraint on table_id enforced by DB)
                    row = TableMetaModel(
                        table_id=table_id,
                        people=data.get("people"),
                        bread=data.get("bread", False)
                    )
                    session.add(row)
        finally:
            session.close()
    
    def delete_table(self, table_id: int) -> None:
        """Delete a table and all its associated orders. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                # Delete all orders for this table
                session.execute(
                    delete(OrderModel).where(OrderModel.table_id == table_id)
                )
                # Delete table metadata
                session.execute(
                    delete(TableMetaModel).where(TableMetaModel.table_id == table_id)
                )
        finally:
            session.close()
    
    def list_tables(self) -> List[int]:
        """List all table IDs that have orders or metadata."""
        session = self._get_session()
        try:
            # Get all distinct table_ids from both tables
            meta_stmt = select(TableMetaModel.table_id)
            orders_stmt = select(OrderModel.table_id)
            
            meta_rows = session.execute(meta_stmt).scalars().all()
            order_rows = session.execute(orders_stmt).scalars().all()
            
            # Combine and sort
            all_tables = sorted(set(meta_rows) | set(order_rows))
            return all_tables
        finally:
            session.close()
    
    def table_exists(self, table_id: int) -> bool:
        """Check if a table has any orders or metadata."""
        session = self._get_session()
        try:
            # Check if table has metadata or orders
            meta_stmt = select(TableMetaModel).where(TableMetaModel.table_id == table_id)
            meta_exists = session.execute(meta_stmt).scalar_one_or_none() is not None
            
            orders_stmt = select(OrderModel).where(OrderModel.table_id == table_id)
            orders_exist = session.execute(orders_stmt).scalar_one_or_none() is not None
            
            return meta_exists or orders_exist
        finally:
            session.close()
    
    def add_order(self, table_id: int, order: Dict[str, Any]) -> None:
        """Add an order (item) to a table's order list. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                # Parse created_at if it's a string ISO format
                created_at = order.get("created_at")
                if isinstance(created_at, str):
                    # Remove 'Z' suffix if present
                    created_at = created_at.rstrip("Z")
                    created_at = datetime.fromisoformat(created_at)
                elif created_at is None:
                    created_at = datetime.utcnow()
                
                # Create order model (unique constraint on item_id enforced by DB)
                order_model = OrderModel(
                    table_id=table_id,
                    item_id=order.get("id"),
                    text=order.get("text"),
                    menu_name=order.get("menu_name"),
                    name=order.get("name"),
                    qty=order.get("qty"),
                    unit_price=order.get("unit_price"),
                    line_total=order.get("line_total"),
                    menu_id=order.get("menu_id"),
                    category=order.get("category"),
                    status=order.get("status", "pending"),
                    created_at=created_at,
                )
                session.add(order_model)
        finally:
            session.close()
    
    def get_orders(self, table_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a table."""
        session = self._get_session()
        try:
            stmt = select(OrderModel).where(OrderModel.table_id == table_id)
            rows = session.execute(stmt).scalars().all()
            return [row.to_dict() for row in rows]
        finally:
            session.close()
    
    def update_order_status(
        self, table_id: int, item_id: str, status: str
    ) -> bool:
        """Update order status by item_id. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                stmt = select(OrderModel).where(OrderModel.item_id == item_id)
                row = session.execute(stmt).scalar_one_or_none()
                
                if not row:
                    return False
                
                row.status = status
            return True
        finally:
            session.close()
    
    def delete_order(self, table_id: int, item_id: str) -> bool:
        """Delete/remove an order by item_id. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                stmt = select(OrderModel).where(OrderModel.item_id == item_id)
                row = session.execute(stmt).scalar_one_or_none()
                
                if not row:
                    return False
                
                session.delete(row)
            return True
        finally:
            session.close()
    
    def get_order_by_id(self, table_id: int, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single order by item_id."""
        session = self._get_session()
        try:
            stmt = select(OrderModel).where(OrderModel.item_id == item_id)
            row = session.execute(stmt).scalar_one_or_none()
            
            if not row:
                return None
            
            return row.to_dict()
        finally:
            session.close()
    
    def purge_done_orders(self, table_id: int, older_than_seconds: int = 0) -> int:
        """Remove all done/cancelled orders from a table. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                if older_than_seconds <= 0:
                    # Remove all done/cancelled orders
                    stmt = delete(OrderModel).where(
                        (OrderModel.table_id == table_id) &
                        (OrderModel.status.in_(["done", "cancelled"]))
                    )
                    result = session.execute(stmt)
                    removed = result.rowcount
                else:
                    # Remove only those created before cutoff time
                    cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
                    stmt = delete(OrderModel).where(
                        (OrderModel.table_id == table_id) &
                        (OrderModel.status.in_(["done", "cancelled"])) &
                        (OrderModel.created_at < cutoff)
                    )
                    result = session.execute(stmt)
                    removed = result.rowcount
            return removed
        finally:
            session.close()
    
    def clear(self) -> None:
        """Clear all state. Wrapped in transaction."""
        session = self._get_session()
        try:
            with session.begin():
                # Delete all orders and metadata
                session.execute(delete(OrderModel))
                session.execute(delete(TableMetaModel))
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connections. Optional cleanup method."""
        self.engine.dispose()
