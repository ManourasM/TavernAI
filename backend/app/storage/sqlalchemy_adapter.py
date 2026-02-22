"""
SQLAlchemy storage implementation for normalized domain models.

Uses canonical Order/OrderItem models from app.db.models while maintaining
backward compatibility with the Storage interface.
"""

from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker, Session

from app.storage.base import Storage
from app.db.models import Base, Order, OrderItem, TableSession, MenuItem
from app.db import init_db


class SQLAlchemyStorage(Storage):
    """
    SQLAlchemy-backed storage using normalized Order/OrderItem models.
    
    Implements the Storage interface while using the canonical domain models
    from app.db.models (Order, OrderItem, TableSession).
    """
    
    def __init__(self, database_url: str = "sqlite:///tavern.db"):
        """
        Initialize SQLAlchemy storage with canonical models.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        
        # Create engine
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        
        # Create sessionmaker
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize database schema using canonical models
        use_alembic = os.getenv("USE_ALEMBIC", "false").lower() == "true"
        init_db(self.engine, use_alembic=use_alembic, base=Base)
        
        # UUID to DB ID mapping (in-memory for backward compat)
        self._uuid_to_db_id: Dict[str, int] = {}
    
    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def _get_or_create_table_session(
        self, 
        session: Session, 
        table_id: int
    ) -> TableSession:
        """Get or create a TableSession for the given table_id."""
        stmt = (
            select(TableSession)
            .where(TableSession.table_label == str(table_id))
            .where(TableSession.closed_at.is_(None))
            .order_by(TableSession.opened_at.desc())
        )
        table_session = session.execute(stmt).scalar_one_or_none()
        
        if not table_session:
            table_session = TableSession(table_label=str(table_id))
            session.add(table_session)
            session.flush()
        
        return table_session
    
    def get_table(self, table_id: int) -> Dict[str, Any]:
        """Get metadata for a table (people count, bread)."""
        db_session = self._get_session()
        try:
            # Table metadata is stored in TableSession
            stmt = (
                select(TableSession)
                .where(TableSession.table_label == str(table_id))
                .where(TableSession.closed_at.is_(None))
            )
            table_session = db_session.execute(stmt).scalar_one_or_none()
            
            if table_session:
                # For now, we don't store people/bread in TableSession
                # Could add these as columns or use extra_data JSON column
                return {"people": None, "bread": False}
            
            return {"people": None, "bread": False}
        finally:
            db_session.close()
    
    def set_table(self, table_id: int, data: Dict[str, Any]) -> None:
        """Set metadata for a table."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Get or create table session
                self._get_or_create_table_session(db_session, table_id)
                # Note: TableSession doesn't have people/bread columns
                # This is a limitation of the normalized model
                # Could add these if needed or store in separate metadata table
        finally:
            db_session.close()
    
    def delete_table(self, table_id: int) -> None:
        """Delete a table and all its associated orders."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Find all table sessions for this table
                stmt = select(TableSession).where(TableSession.table_label == str(table_id))
                sessions = db_session.execute(stmt).scalars().all()
                
                for ts in sessions:
                    # Delete all orders for this session (cascades to OrderItems)
                    db_session.execute(
                        delete(Order).where(Order.table_session_id == ts.id)
                    )
                    # Delete the table session
                    db_session.delete(ts)
        finally:
            db_session.close()
    
    def list_tables(self) -> List[int]:
        """List all table IDs that have orders or metadata."""
        db_session = self._get_session()
        try:
            # Get all distinct table_labels from TableSessions
            stmt = select(TableSession.table_label).distinct()
            labels = db_session.execute(stmt).scalars().all()
            
            # Convert to ints (if possible)
            tables = []
            for label in labels:
                try:
                    tables.append(int(label))
                except ValueError:
                    pass  # Skip non-numeric labels
            
            return sorted(tables)
        finally:
            db_session.close()
    
    def table_exists(self, table_id: int) -> bool:
        """Check if a table has any orders or metadata."""
        db_session = self._get_session()
        try:
            stmt = (
                select(TableSession)
                .where(TableSession.table_label == str(table_id))
            )
            exists = db_session.execute(stmt).scalar_one_or_none() is not None
            return exists
        finally:
            db_session.close()
    
    def add_order(self, table_id: int, order: Dict[str, Any]) -> None:
        """Add an order (item) to a table's order list."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Get or create table session
                table_session = self._get_or_create_table_session(db_session, table_id)
                
                # Create Order if needed (one Order per add_order call for now)
                db_order = Order(
                    table_session_id=table_session.id,
                    created_by_user_id=0,  # Anonymous for legacy compat
                    status="pending",
                    total=int(round(order.get("line_total", 0) * 100))
                )
                db_session.add(db_order)
                db_session.flush()
                
                # Find menu item if menu_id provided
                menu_item_id = None
                if order.get("menu_id"):
                    menu_stmt = select(MenuItem).where(MenuItem.external_id == order["menu_id"])
                    menu_item = db_session.execute(menu_stmt).scalar_one_or_none()
                    if menu_item:
                        menu_item_id = menu_item.id
                
                # Create OrderItem
                item_id = order.get("id", str(uuid4()))
                order_item = OrderItem(
                    order_id=db_order.id,
                    menu_item_id=menu_item_id,
                    name=order.get("menu_name") or order.get("text", "Unknown"),
                    qty=order.get("qty", 1),
                    unit=None,
                    unit_price=int(round(order.get("unit_price", 0) * 100)),
                    line_total=int(round(order.get("line_total", 0) * 100)),
                    status=order.get("status", "pending")
                )
                db_session.add(order_item)
                db_session.flush()
                
                # Store UUID mapping
                self._uuid_to_db_id[item_id] = order_item.id
        finally:
            db_session.close()
    
    def get_orders(self, table_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a table."""
        db_session = self._get_session()
        try:
            # Find all table sessions for this table
            sessions_stmt = (
                select(TableSession)
                .where(TableSession.table_label == str(table_id))
                .where(TableSession.closed_at.is_(None))
            )
            table_sessions = db_session.execute(sessions_stmt).scalars().all()
            
            if not table_sessions:
                return []
            
            # Get all orders for these sessions
            session_ids = [ts.id for ts in table_sessions]
            orders_stmt = select(Order).where(Order.table_session_id.in_(session_ids))
            orders = db_session.execute(orders_stmt).scalars().all()
            
            # Get all order items
            result = []
            for order in orders:
                items_stmt = select(OrderItem).where(OrderItem.order_id == order.id)
                order_items = db_session.execute(items_stmt).scalars().all()
                
                for item in order_items:
                    # Generate or retrieve UUID
                    item_uuid = None
                    for uuid, db_id in self._uuid_to_db_id.items():
                        if db_id == item.id:
                            item_uuid = uuid
                            break
                    if not item_uuid:
                        item_uuid = str(uuid4())
                        self._uuid_to_db_id[item_uuid] = item.id
                    
                    # Convert to legacy format
                    item_dict = {
                        "id": item_uuid,
                        "table": table_id,
                        "text": item.name,
                        "menu_name": item.name,
                        "name": item.name,
                        "qty": item.qty,
                        "unit_price": item.unit_price / 100.0 if item.unit_price else 0,
                        "line_total": item.line_total / 100.0 if item.line_total else 0,
                        "menu_id": item.menu_item.external_id if item.menu_item else None,
                        "category": self._infer_category(item),
                        "status": item.status,
                        "created_at": order.created_at.isoformat() + "Z" if order.created_at else None,
                    }
                    result.append(item_dict)
            
            return result
        finally:
            db_session.close()
    
    def update_order_status(
        self, table_id: int, item_id: str, status: str
    ) -> bool:
        """Update order status by item_id."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Look up DB ID from UUID
                db_id = self._uuid_to_db_id.get(item_id)
                if not db_id:
                    return False
                
                # Update OrderItem
                stmt = select(OrderItem).where(OrderItem.id == db_id)
                item = db_session.execute(stmt).scalar_one_or_none()
                
                if item:
                    item.status = status
                    return True
                
                return False
        finally:
            db_session.close()
    
    def delete_order(self, table_id: int, item_id: str) -> bool:
        """Delete/remove an order by item_id."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Look up DB ID from UUID
                db_id = self._uuid_to_db_id.get(item_id)
                if not db_id:
                    return False
                
                # Delete OrderItem
                stmt = select(OrderItem).where(OrderItem.id == db_id)
                item = db_session.execute(stmt).scalar_one_or_none()
                
                if item:
                    db_session.delete(item)
                    # Remove from UUID mapping
                    del self._uuid_to_db_id[item_id]
                    return True
                
                return False
        finally:
            db_session.close()
    
    def get_order_by_id(self, table_id: int, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single order by item_id."""
        db_session = self._get_session()
        try:
            # Look up DB ID from UUID
            db_id = self._uuid_to_db_id.get(item_id)
            if not db_id:
                return None
            
            # Get OrderItem
            stmt = select(OrderItem).where(OrderItem.id == db_id)
            item = db_session.execute(stmt).scalar_one_or_none()
            
            if not item:
                return None
            
            # Get associated Order for created_at
            order_stmt = select(Order).where(Order.id == item.order_id)
            order = db_session.execute(order_stmt).scalar_one()
            
            # Convert to legacy format
            return {
                "id": item_id,
                "table": table_id,
                "text": item.name,
                "menu_name": item.name,
                "name": item.name,
                "qty": item.qty,
                "unit_price": item.unit_price / 100.0 if item.unit_price else 0,
                "line_total": item.line_total / 100.0 if item.line_total else 0,
                "menu_id": item.menu_item.external_id if item.menu_item else None,
                "category": self._infer_category(item),
                "status": item.status,
                "created_at": order.created_at.isoformat() + "Z" if order.created_at else None,
            }
        finally:
            db_session.close()
    
    def purge_done_orders(self, table_id: int, older_than_seconds: int = 0) -> int:
        """Remove all done/cancelled orders from a table."""
        from datetime import timedelta
        
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Get table sessions
                sessions_stmt = (
                    select(TableSession)
                    .where(TableSession.table_label == str(table_id))
                    .where(TableSession.closed_at.is_(None))
                )
                table_sessions = db_session.execute(sessions_stmt).scalars().all()
                
                if not table_sessions:
                    return 0
                
                # Get orders
                session_ids = [ts.id for ts in table_sessions]
                orders_stmt = select(Order).where(Order.table_session_id.in_(session_ids))
                orders = db_session.execute(orders_stmt).scalars().all()
                
                # Delete done/cancelled items
                count = 0
                for order in orders:
                    items_stmt = (
                        select(OrderItem)
                        .where(OrderItem.order_id == order.id)
                        .where(OrderItem.status.in_(["done", "cancelled"]))
                    )
                    
                    if older_than_seconds > 0:
                        cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
                        items_stmt = items_stmt.where(order.created_at < cutoff)
                    
                    items = db_session.execute(items_stmt).scalars().all()
                    
                    for item in items:
                        # Remove from UUID mapping
                        for uuid, db_id in list(self._uuid_to_db_id.items()):
                            if db_id == item.id:
                                del self._uuid_to_db_id[uuid]
                                break
                        
                        db_session.delete(item)
                        count += 1
                
                return count
        finally:
            db_session.close()
    
    def clear(self) -> None:
        """Clear all state."""
        db_session = self._get_session()
        try:
            with db_session.begin():
                # Delete all orders (cascades to OrderItems)
                db_session.execute(delete(Order))
                # Delete all table sessions
                db_session.execute(delete(TableSession))
                # Clear UUID mapping
                self._uuid_to_db_id.clear()
        finally:
            db_session.close()
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
    
    def _infer_category(self, item: OrderItem) -> str:
        """Infer category from OrderItem."""
        if item.menu_item and item.menu_item.station:
            return item.menu_item.station
        return "kitchen"
