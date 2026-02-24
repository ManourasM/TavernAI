"""
SQLAlchemy storage implementation for normalized domain models.

Uses canonical Order/OrderItem models from app.db.models while maintaining
backward compatibility with the Storage interface.
"""

from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, select, delete, func
from sqlalchemy.orm import sessionmaker, Session

from app.storage.base import Storage
from app.db.models import Base, Order, OrderItem, TableSession, MenuItem, Receipt
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
        try:
            init_db(self.engine, use_alembic=use_alembic, base=Base)
            print(f"[SQLAlchemyStorage] ✅ Database initialized successfully at {self.database_url}")
        except Exception as e:
            print(f"[SQLAlchemyStorage] ⚠️ Warning during database initialization: {e}")
            # Only create missing tables, don't drop existing data
            try:
                Base.metadata.create_all(self.engine)
                print(f"[SQLAlchemyStorage] ✅ Created missing tables (existing data preserved)")
            except Exception as fallback_error:
                print(f"[SQLAlchemyStorage] ❌ Failed to create tables: {fallback_error}")
                # Don't raise here - allow app to start anyway, may work partially
        
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
    
    def delete_table(self, table_id: int) -> int:
        """Close the current table session and create receipt. Returns the receipt ID."""
        db_session = self._get_session()
        try:
            from datetime import datetime
            import json
            print(f"[delete_table] Closing sessions for table {table_id}")
            
            # Find open table sessions for this table
            stmt = (
                select(TableSession)
                .where(TableSession.table_label == str(table_id))
                .where(TableSession.closed_at.is_(None))
            )
            sessions = db_session.execute(stmt).scalars().all()
            
            print(f"[delete_table] Found {len(sessions)} open sessions")
            
            receipt_id = None
            for ts in sessions:
                # Close the session
                ts.closed_at = datetime.utcnow()
                session_id = ts.id
                print(f"[delete_table] Closing session {session_id} for table {ts.table_label}")
                
                # Find all orders for this session
                orders_stmt = select(Order).where(Order.table_session_id == session_id)
                orders = db_session.execute(orders_stmt).scalars().all()
                print(f"[delete_table] Found {len(orders)} orders for session {session_id}")
                
                # Collect ALL items from ALL orders in this session
                all_items = []
                primary_order_id = None
                for order in orders:
                    if primary_order_id is None:
                        primary_order_id = order.id
                    items_stmt = select(OrderItem).where(OrderItem.order_id == order.id)
                    items = db_session.execute(items_stmt).scalars().all()
                    all_items.extend(items)
                
                print(f"[delete_table] Collected {len(all_items)} total items from all orders")
                
                # Check if receipt already exists for the primary order
                if primary_order_id:
                    existing_receipt = db_session.execute(
                        select(Receipt).where(Receipt.order_id == primary_order_id)
                    ).scalar_one_or_none()
                    
                    if existing_receipt:
                        print(f"[delete_table] Receipt already exists, using receipt_id={existing_receipt.id}")
                        receipt_id = existing_receipt.id
                        continue
                
                # Build receipt content with ALL items from the session
                receipt_content = {
                    "table": ts.table_label,
                    "created_at": ts.opened_at.isoformat() if ts.opened_at else None,
                    "closed_at": ts.closed_at.isoformat() if ts.closed_at else None,
                    "items": [
                        {
                            "name": item.name,
                            "quantity": item.qty or 1,
                            "unit_price": (item.unit_price / 100.0) if item.unit_price else 0,
                            "line_total": ((item.unit_price or 0) * (item.qty or 1)) / 100.0,
                            "status": item.status,
                        }
                        for item in all_items if item.status != 'cancelled'
                    ],
                    "total": sum(
                        ((item.unit_price or 0) * (item.qty or 1)) / 100.0
                        for item in all_items if item.status != 'cancelled'
                    )
                }
                
                # Create ONE receipt record for the entire session
                if primary_order_id:
                    receipt = Receipt(
                        order_id=primary_order_id,
                        content=json.dumps(receipt_content),
                        printed_at=None
                    )
                    db_session.add(receipt)
                    db_session.flush()  # Get the ID
                    receipt_id = receipt.id
                    print(f"[delete_table] Created single receipt_id={receipt_id} for session {session_id} with {len(all_items)} items")
            
            # Commit all changes
            db_session.commit()
            print(f"[delete_table] Successfully closed session and created receipt_id={receipt_id}")
            
            return receipt_id
        except Exception as e:
            print(f"[delete_table] ERROR: {e}")
            import traceback
            traceback.print_exc()
            db_session.rollback()
            raise
        finally:
            db_session.close()

    
    def list_tables(self) -> List[int]:
        """List all table IDs that have open sessions."""
        db_session = self._get_session()
        try:
            # Get all distinct table_labels from OPEN TableSessions only
            stmt = (
                select(TableSession.table_label)
                .where(TableSession.closed_at.is_(None))
                .distinct()
            )
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
                .where(TableSession.closed_at.is_(None))
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
                
                # Handle None values for numeric fields
                line_total = order.get("line_total") or 0
                unit_price = order.get("unit_price") or 0
                qty = order.get("qty") or 1
                
                # Create Order if needed (one Order per add_order call for now)
                db_order = Order(
                    table_session_id=table_session.id,
                    created_by_user_id=0,  # Anonymous for legacy compat
                    status="pending",
                    total=int(round(line_total * 100))
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
                    text=order.get("text"),  # Store original user input
                    qty=int(qty),
                    unit=None,
                    unit_price=int(round(unit_price * 100)),
                    line_total=int(round(line_total * 100)),
                    category=order.get("category"),  # Store category for routing
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
                        "text": item.text or item.name,  # Use original text if available, fallback to name
                        "menu_name": item.name,
                        "name": item.name,
                        "qty": item.qty,
                        "unit_price": item.unit_price / 100.0 if item.unit_price else 0,
                        "line_total": item.line_total / 100.0 if item.line_total else 0,
                        "menu_id": item.menu_item.external_id if item.menu_item else None,
                        "category": item.category or self._infer_category(item),  # Use stored category first
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
    
    def get_history(self, from_date=None, to_date=None, table_id=None, limit=50, offset=0):
        """Get closed table sessions (history) with optional filters."""
        db_session = self._get_session()
        try:
            from datetime import datetime, timedelta
            
            print(f"[get_history] Filters: from_date={from_date}, to_date={to_date}, table_id={table_id}, limit={limit}, offset={offset}")
            
            # Query for closed sessions
            stmt = (
                select(TableSession)
                .where(TableSession.closed_at.isnot(None))
            )
            
            # Apply filters
            if table_id is not None:
                stmt = stmt.where(TableSession.table_label == str(table_id))
            
            if from_date:
                if isinstance(from_date, str):
                    # Handle YYYY-MM-DD format
                    try:
                        from_date = datetime.strptime(from_date, '%Y-%m-%d')
                    except ValueError:
                        from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                stmt = stmt.where(TableSession.closed_at >= from_date)
            
            if to_date:
                if isinstance(to_date, str):
                    # Handle YYYY-MM-DD format
                    try:
                        to_date = datetime.strptime(to_date, '%Y-%m-%d')
                    except ValueError:
                        to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                # End of day
                to_date = to_date + timedelta(days=1)
                stmt = stmt.where(TableSession.closed_at < to_date)
            
            # Order by closed_at descending (newest first)
            stmt = stmt.order_by(TableSession.closed_at.desc())
            
            # Count total before pagination
            count_stmt = select(func.count()).select_from(stmt.alias())
            total = db_session.execute(count_stmt).scalar()
            
            print(f"[get_history] Found {total} total sessions")
            
            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)
            
            sessions = db_session.execute(stmt).scalars().all()
            
            print(f"[get_history] Returning {len(sessions)} sessions for this page")
            
            results = []
            for session in sessions:
                # Get all items for this session
                items_stmt = (
                    select(OrderItem)
                    .join(Order)
                    .where(Order.table_session_id == session.id)
                )
                items = db_session.execute(items_stmt).scalars().all()
                
                # Calculate total using correct field names
                total_amount = sum(
                    ((item.unit_price or 0) / 100.0) * (item.qty or 1)
                    for item in items
                    if item.status != 'cancelled'
                )
                
                results.append({
                    'id': session.id,
                    'table': int(session.table_label) if session.table_label.isdigit() else session.table_label,
                    'items': [self._order_item_to_dict(item) for item in items],
                    'total': total_amount,
                    'closed_at': session.closed_at.isoformat() if session.closed_at else None,
                    'created_at': session.opened_at.isoformat() if session.opened_at else None,
                })
            
            return {
                'items': results,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        finally:
            db_session.close()
    
    def get_session_by_id(self, session_id):
        """Get a specific session (receipt) by ID."""
        db_session = self._get_session()
        try:
            print(f"[get_session_by_id] Looking for session_id={session_id}, type={type(session_id)}")
            
            # Ensure session_id is an integer
            try:
                session_id = int(session_id)
            except (ValueError, TypeError):
                print(f"[get_session_by_id] Invalid session_id format: {session_id}")
                return None
            
            # Get the session - include both open and closed sessions
            stmt = select(TableSession).where(TableSession.id == session_id)
            session = db_session.execute(stmt).scalar_one_or_none()
            
            if not session:
                # Debug: list all sessions
                all_sessions_stmt = select(TableSession)
                all_sessions = db_session.execute(all_sessions_stmt).scalars().all()
                print(f"[get_session_by_id] Session {session_id} not found. Total sessions in DB: {len(all_sessions)}")
                for s in all_sessions:
                    print(f"  Session ID={s.id}, table={s.table_label}, closed_at={s.closed_at}")
                return None
            
            print(f"[get_session_by_id] Found session {session_id}, table={session.table_label}, closed_at={session.closed_at}")
            
            # Get all items for this session
            items_stmt = (
                select(OrderItem)
                .join(Order)
                .where(Order.table_session_id == session.id)
            )
            items = db_session.execute(items_stmt).scalars().all()
            
            print(f"[get_session_by_id] Found {len(items)} items for session {session_id}")
            
            # Calculate total using correct field names
            total_amount = sum(
                ((item.unit_price or 0) / 100.0) * (item.qty or 1)
                for item in items
                if item.status != 'cancelled'
            )
            
            result = {
                'id': session.id,
                'table': int(session.table_label) if session.table_label.isdigit() else session.table_label,
                'items': [self._order_item_to_dict(item) for item in items],
                'total': total_amount,
                'closed_at': session.closed_at.isoformat() if session.closed_at else None,
                'created_at': session.opened_at.isoformat() if session.opened_at else None,
            }
            
            print(f"[get_session_by_id] Returning receipt with {len(result['items'])} items, total={total_amount}")
            return result
        except Exception as e:
            print(f"[get_session_by_id] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            db_session.close()
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
    
    def _infer_category(self, item: OrderItem) -> str:
        """Infer category from OrderItem."""
        # First check if category is stored directly
        if hasattr(item, 'category') and item.category:
            return item.category
        # Then check menu item
        if item.menu_item:
            if hasattr(item.menu_item, 'station') and item.menu_item.station:
                return item.menu_item.station
            if hasattr(item.menu_item, 'category') and item.menu_item.category:
                return item.menu_item.category
        # Default to kitchen
        return "kitchen"
    
    def _order_item_to_dict(self, item: OrderItem) -> Dict[str, Any]:
        """Convert OrderItem to dictionary format."""
        # Generate or retrieve UUID
        item_uuid = None
        for uuid, db_id in self._uuid_to_db_id.items():
            if db_id == item.id:
                item_uuid = uuid
                break
        if not item_uuid:
            item_uuid = str(uuid4())
            self._uuid_to_db_id[item_uuid] = item.id
        
        return {
            "id": item_uuid,
            "name": item.name,
            "menu_name": item.name,
            "text": item.text or item.name,
            "quantity": item.qty or 1,
            "price": (item.unit_price / 100.0) if item.unit_price else 0,
            "line_total": (item.line_total / 100.0) if item.line_total else 0,
            "category": item.category or self._infer_category(item),
            "status": item.status,
            "menu_id": item.menu_item.external_id if item.menu_item else None,
        }
        if hasattr(item.menu_item, 'category') and item.menu_item.category:
            return item.menu_item.category
        return "kitchen"
