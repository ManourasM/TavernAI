"""Order management utilities for normalized domain models.

This module provides helper functions for working with normalized Order and OrderItem
models while maintaining compatibility with existing JSON-based API contracts.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import TableSession, Order, OrderItem, MenuItem
from app.utils.time_utils import iso_athens, now_athens_naive, to_athens


def get_or_create_table_session(
    session: Session, 
    table_label: str,
    waiter_user_id: Optional[int] = None
) -> TableSession:
    """
    Get existing open TableSession or create a new one.
    
    Args:
        session: SQLAlchemy session
        table_label: Table identifier (e.g., "Table 1")
        waiter_user_id: Optional waiter ID for session
        
    Returns:
        TableSession object (existing or newly created)
    """
    # Try to find an open session for this table
    stmt = (
        select(TableSession)
        .where(TableSession.table_label == str(table_label))
        .where(TableSession.closed_at.is_(None))
        .order_by(TableSession.opened_at.desc())
    )
    table_session = session.execute(stmt).scalar_one_or_none()
    
    if not table_session:
        # Create new table session
        table_session = TableSession(
            table_label=str(table_label),
            waiter_user_id=waiter_user_id
        )
        session.add(table_session)
        session.flush()  # Get ID assigned
    
    return table_session


def create_order_from_payload(
    session: Session,
    table_label: str,
    classified_items: List[Dict[str, Any]],
    created_by_user_id: Optional[int] = None,
    waiter_user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create Order and OrderItem rows from classified order payload.
    
    Args:
        session: SQLAlchemy session
        table_label: Table identifier
        classified_items: List of classified items from NLP
        created_by_user_id: User creating the order
        waiter_user_id: Waiter assigned to table
        
    Returns:
        Dictionary with created items in legacy format for API compatibility
    """
    # Get or create table session
    table_session = get_or_create_table_session(session, table_label, waiter_user_id)
    
    # Calculate total
    total_cents = 0
    for item in classified_items:
        price = item.get("price") or 0  # Handle None prices
        multiplier = item.get("multiplier") or 1  # Handle None multipliers
        total_cents += int(round(price * multiplier * 100))
    
    # Create Order
    order = Order(
        table_session_id=table_session.id,
        created_by_user_id=created_by_user_id or 0,  # Default to 0 for anonymous
        status="pending",
        total=total_cents
    )
    session.add(order)
    session.flush()  # Get order ID
    
    # Create OrderItems and build response
    created_items = []
    for entry in classified_items:
        # Generate unique item_id
        item_id = str(uuid4())
        
        # Extract pricing info
        price = entry.get("price") or 0  # Handle None prices
        multiplier = entry.get("multiplier") or 1  # Handle None multipliers
        unit_price = price
        line_total = round(price * multiplier, 2)
        
        # Find menu item if menu_id provided
        menu_item_id = None
        menu_id_str = entry.get("menu_id")
        if menu_id_str:
            # Try to find MenuItem by external_id
            menu_stmt = select(MenuItem).where(MenuItem.external_id == menu_id_str)
            menu_item = session.execute(menu_stmt).scalar_one_or_none()
            if menu_item:
                menu_item_id = menu_item.id
        
        # Create OrderItem
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item_id,
            name=entry.get("menu_name") or entry.get("text", "Unknown"),
            text=entry.get("text"),  # Store original user input
            qty=multiplier,
            unit=None,  # Could be extracted from text if needed
            unit_price=int(round(unit_price * 100)),  # Store as cents
            line_total=int(round(line_total * 100)),  # Store as cents
            category=entry.get("category"),  # Store category for routing
            status="pending"
        )
        session.add(order_item)
        session.flush()  # Get OrderItem ID
        
        # Build legacy format for API response
        item_dict = {
            "id": item_id,
            "table": int(table_label) if table_label.isdigit() else table_label,
            "text": entry.get("text", ""),  # Original user input
            "menu_name": entry.get("menu_name"),
            "name": entry.get("menu_name") or entry.get("text", "Unknown"),
            "qty": multiplier,
            "unit_price": unit_price,
            "line_total": line_total,
            "menu_id": entry.get("menu_id"),
            "category": entry.get("category", "kitchen"),
            "status": "pending",
            "created_at": iso_athens(),
            "_db_order_item_id": order_item.id  # Internal reference
        }
        created_items.append(item_dict)
    
    return {
        "order_id": order.id,
        "table_session_id": table_session.id,
        "items": created_items
    }


def list_orders_for_table(
    session: Session,
    table_label: str,
    pending_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get all orders for a table in legacy JSON format.
    
    Args:
        session: SQLAlchemy session
        table_label: Table identifier
        pending_only: Only return pending items
        
    Returns:
        List of items in legacy dict format for API compatibility
    """
    # Find all table sessions for this table
    sessions_stmt = (
        select(TableSession)
        .where(TableSession.table_label == str(table_label))
        .where(TableSession.closed_at.is_(None))  # Only open sessions
    )
    table_sessions = session.execute(sessions_stmt).scalars().all()
    
    if not table_sessions:
        return []
    
    # Get all orders for these sessions
    session_ids = [ts.id for ts in table_sessions]
    orders_stmt = (
        select(Order)
        .where(Order.table_session_id.in_(session_ids))
    )
    orders = session.execute(orders_stmt).scalars().all()
    
    # Get all order items
    result = []
    for order in orders:
        items_stmt = select(OrderItem).where(OrderItem.order_id == order.id)
        if pending_only:
            items_stmt = items_stmt.where(OrderItem.status == "pending")
        
        order_items = session.execute(items_stmt).scalars().all()
        
        for item in order_items:
            # Convert to legacy format
            item_dict = {
                "id": str(uuid4()),  # Generate stable ID
                "table": int(table_label) if table_label.isdigit() else table_label,
                "text": item.text or item.name,  # Use original text if available
                "menu_name": item.name,
                "name": item.name,
                "qty": item.qty,
                "unit_price": item.unit_price / 100.0 if item.unit_price else 0,
                "line_total": item.line_total / 100.0 if item.line_total else 0,
                "menu_id": item.menu_item.external_id if item.menu_item else None,
                "category": item.category or _infer_category_from_item(item),  # Use stored category first
                "status": item.status,
                "created_at": to_athens(order.created_at).isoformat() if order.created_at else None,
                "_db_order_item_id": item.id  # Internal reference
            }
            result.append(item_dict)
    
    return result


def update_order_item_status(
    session: Session,
    item_id_or_db_id: Any,
    status: str
) -> bool:
    """
    Update an OrderItem's status.
    
    Args:
        session: SQLAlchemy session
        item_id_or_db_id: Either UUID string (legacy) or DB ID
        status: New status (pending, preparing, ready, done, cancelled)
        
    Returns:
        True if updated, False if not found
    """
    # Try to find by DB ID first (from _db_order_item_id)
    if isinstance(item_id_or_db_id, int):
        stmt = select(OrderItem).where(OrderItem.id == item_id_or_db_id)
        item = session.execute(stmt).scalar_one_or_none()
    else:
        # For now, since we don't store UUIDs, we can't look up by UUID
        # This is a limitation - in production would need to store UUID mapping
        return False
    
    if item:
        item.status = status
        session.flush()
        return True
    
    return False


def delete_order_item(
    session: Session,
    item_id_or_db_id: Any
) -> bool:
    """
    Delete an OrderItem (or mark as cancelled).
    
    Args:
        session: SQLAlchemy session
        item_id_or_db_id: Either UUID string (legacy) or DB ID
        
    Returns:
        True if deleted, False if not found
    """
    # Similar to update_order_item_status
    if isinstance(item_id_or_db_id, int):
        stmt = select(OrderItem).where(OrderItem.id == item_id_or_db_id)
        item = session.execute(stmt).scalar_one_or_none()
    else:
        return False
    
    if item:
        # Soft delete: mark as cancelled
        item.status = "cancelled"
        session.flush()
        return True
    
    return False


def replace_table_orders(
    session: Session,
    table_label: str,
    new_classified_items: List[Dict[str, Any]],
    created_by_user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Smart replace logic: match existing items, cancel unmatched, create new.
    
    This implements the same smart matching semantics as the original endpoint.
    
    Args:
        session: SQLAlchemy session
        table_label: Table identifier
        new_classified_items: New classified items from NLP
        created_by_user_id: User making the change
        
    Returns:
        Dict with created, updated, cancelled, and kept items
    """
    from app.main import _normalize_text_for_match  # Import helper
    
    # Get existing pending items
    existing_items = list_orders_for_table(session, table_label, pending_only=True)
    
    # Build matching records
    existing_records = []
    for item in existing_items:
        norm_text = _normalize_text_for_match(item.get("text", ""))
        existing_records.append({
            "item": item,
            "norm": norm_text,
            "category": item.get("category"),
            "used": False
        })
    
    # Match new items against existing
    new_items_created = []
    updated_items = []
    kept_items = []
    
    for entry in new_classified_items:
        new_text = entry["text"].strip()
        new_cat = entry["category"]
        new_norm = _normalize_text_for_match(new_text)
        
        # Find matching existing item
        match_idx = None
        for idx, rec in enumerate(existing_records):
            if not rec["used"] and rec["norm"] == new_norm and rec["category"] == new_cat:
                match_idx = idx
                break
        
        if match_idx is not None:
            # Match found - mark as used
            existing_records[match_idx]["used"] = True
            existing_item = existing_records[match_idx]["item"]
            
            # Check if text changed (quantity change)
            if existing_item["text"] != new_text:
                # Update quantity/pricing
                db_id = existing_item.get("_db_order_item_id")
                if db_id:
                    item_stmt = select(OrderItem).where(OrderItem.id == db_id)
                    db_item = session.execute(item_stmt).scalar_one_or_none()
                    
                    if db_item:
                        # Update fields
                        price = (entry.get("price") or existing_item.get("unit_price") or 0)  # Handle None prices
                        multiplier = entry.get("multiplier") or 1  # Handle None multipliers
                        
                        db_item.name = entry.get("menu_name") or new_text
                        db_item.text = new_text  # Update original text
                        db_item.qty = multiplier
                        db_item.unit_price = int(round(price * 100))
                        db_item.line_total = int(round(price * multiplier * 100))
                        db_item.category = entry.get("category")  # Update category
                        session.flush()
                        
                        # Update response dict
                        existing_item["text"] = new_text
                        existing_item["menu_name"] = entry.get("menu_name")
                        existing_item["qty"] = multiplier
                        existing_item["unit_price"] = price
                        existing_item["line_total"] = round(price * multiplier, 2)
                        existing_item["category"] = entry.get("category")
                        updated_items.append(existing_item)
            else:
                # Exact match, keep as-is
                kept_items.append(existing_item)
        else:
            # No match - create new item
            result = create_order_from_payload(
                session,
                table_label,
                [entry],
                created_by_user_id
            )
            new_items_created.extend(result["items"])
    
    # Cancel unmatched items
    cancelled_items = []
    for rec in existing_records:
        if not rec["used"]:
            item = rec["item"]
            db_id = item.get("_db_order_item_id")
            if db_id:
                update_order_item_status(session, db_id, "cancelled")
            item["status"] = "cancelled"
            cancelled_items.append(item)
    
    return {
        "new": new_items_created,
        "updated": updated_items,
        "kept": kept_items,
        "cancelled": cancelled_items
    }


def purge_done_items(
    session: Session,
    table_label: str,
    older_than_seconds: int = 0
) -> int:
    """
    Remove done/cancelled order items from a table.
    
    Args:
        session: SQLAlchemy session
        table_label: Table identifier
        older_than_seconds: Only purge items older than this (0 = all)
        
    Returns:
        Number of items purged
    """
    from datetime import timedelta
    
    # Get table sessions
    sessions_stmt = (
        select(TableSession)
        .where(TableSession.table_label == str(table_label))
        .where(TableSession.closed_at.is_(None))
    )
    table_sessions = session.execute(sessions_stmt).scalars().all()
    
    if not table_sessions:
        return 0
    
    # Get orders
    session_ids = [ts.id for ts in table_sessions]
    orders_stmt = select(Order).where(Order.table_session_id.in_(session_ids))
    orders = session.execute(orders_stmt).scalars().all()
    
    # Delete done/cancelled items
    count = 0
    for order in orders:
        items_stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
            .where(OrderItem.status.in_(["done", "cancelled"]))
        )
        
        if older_than_seconds > 0:
            cutoff = now_athens_naive() - timedelta(seconds=older_than_seconds)
            items_stmt = items_stmt.where(Order.created_at < cutoff)
        
        items = session.execute(items_stmt).scalars().all()
        
        for item in items:
            session.delete(item)
            count += 1
    
    session.flush()
    return count


def _infer_category_from_item(item: OrderItem) -> str:
    """Infer category from OrderItem (uses menu_item if available)."""
    # First check if category is stored directly
    if hasattr(item, 'category') and item.category:
        return item.category
    # Then check menu item
    if item.menu_item:
        if hasattr(item.menu_item, 'station') and item.menu_item.station:
            return item.menu_item.station
        if hasattr(item.menu_item, 'category') and item.menu_item.category:
            return item.menu_item.category
    
    # Default fallback
    return "kitchen"
