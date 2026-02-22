"""
Receipts and order history API router.

Handles table closing, receipt generation, and history queries.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import TableSession, Order, OrderItem, Receipt
from app.storage import Storage, SQLAlchemyStorage


router = APIRouter(prefix="/api/orders", tags=["receipts", "history"])


# Import get_storage at module level to avoid circular imports at import time
# but make it available for endpoint dependency injection
def get_storage_dependency() -> Storage:
    """Get storage from main app - lazy import to avoid circular dependency."""
    from app.main import get_storage
    return get_storage()



# ---------- Request/Response Models ----------

class CloseTableRequest(BaseModel):
    """Request to close a table session."""
    table_label: str


class CloseTableResponse(BaseModel):
    """Response from closing a table."""
    status: str
    session_id: int
    receipt_id: int
    closed_at: str
    total: float


class ReceiptDetail(BaseModel):
    """Detailed receipt information."""
    id: int
    order_id: int
    table_label: str
    opened_at: str
    closed_at: str
    printed_at: Optional[str]
    content: str
    total: float


class HistoryItem(BaseModel):
    """Summary item for history list."""
    receipt_id: int
    order_id: int
    table_label: str
    closed_at: str
    total: float
    printed: bool


class HistoryResponse(BaseModel):
    """Paginated history response."""
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


# ---------- Helper Functions ----------

def _get_db_session(storage: Storage) -> Session:
    """Get a database session from SQLAlchemyStorage."""
    if not isinstance(storage, SQLAlchemyStorage):
        raise HTTPException(
            status_code=501,
            detail="Receipts require SQLAlchemy storage backend"
        )
    return storage._get_session()


def _generate_receipt_content(
    session: Session,
    table_session: TableSession,
    orders: list[Order]
) -> dict:
    """
    Generate receipt content as JSON blob.
    
    Returns a dictionary with:
    - table_label: str
    - opened_at: datetime
    - closed_at: datetime
    - items: list of {name, qty, unit, unit_price, line_total, status}
    - subtotal: float (all items)
    - total: float (same as subtotal, can add tax/tip later)
    """
    items = []
    subtotal_cents = 0
    
    for order in orders:
        for order_item in order.items:
            # Only include non-cancelled items in receipt
            if order_item.status != "cancelled":
                items.append({
                    "name": order_item.name,
                    "qty": order_item.qty,
                    "unit": order_item.unit,
                    "unit_price": order_item.unit_price / 100.0,  # cents to decimal
                    "line_total": order_item.line_total / 100.0,
                    "status": order_item.status
                })
                subtotal_cents += order_item.line_total
    
    receipt_data = {
        "table_label": table_session.table_label,
        "opened_at": table_session.opened_at.isoformat() if table_session.opened_at else None,
        "closed_at": table_session.closed_at.isoformat() if table_session.closed_at else None,
        "items": items,
        "subtotal": subtotal_cents / 100.0,
        "total": subtotal_cents / 100.0,  # Can add tax/service charge calculation here
        "currency": "EUR"
    }
    
    return receipt_data


# ---------- Endpoints ----------

@router.post("/close", response_model=CloseTableResponse, summary="Close a table session")
async def close_table_session(
    request: CloseTableRequest,
    storage: Storage = Depends(get_storage_dependency)
):
    """
    Close a table session and generate receipt.
    
    - Sets TableSession.closed_at to current time
    - Computes total from all OrderItems
    - Creates Receipt record with printable content
    - Returns receipt details
    """
    session = _get_db_session(storage)
    
    try:
        # Find open TableSession for this table_label
        table_session = (
            session.query(TableSession)
            .filter(
                TableSession.table_label == request.table_label,
                TableSession.closed_at.is_(None)
            )
            .first()
        )
        
        if not table_session:
            raise HTTPException(
                status_code=404,
                detail=f"No open session found for table '{request.table_label}'"
            )
        
        # Set closed_at timestamp
        table_session.closed_at = datetime.utcnow()
        
        # Get all orders for this session
        orders = (
            session.query(Order)
            .filter(Order.table_session_id == table_session.id)
            .all()
        )
        
        # Calculate total from all non-cancelled items
        total_cents = 0
        for order in orders:
            for item in order.items:
                if item.status != "cancelled":
                    total_cents += item.line_total
        
        # Update order totals
        for order in orders:
            order_total = sum(
                item.line_total for item in order.items
                if item.status != "cancelled"
            )
            order.total = order_total
        
        # Generate receipt content
        receipt_content = _generate_receipt_content(session, table_session, orders)
        
        # Create Receipt record (one receipt per session, linked to first order or create summary)
        # For simplicity, link to the first order in the session
        if orders:
            primary_order = orders[0]
            
            # Check if receipt already exists for this order
            existing_receipt = (
                session.query(Receipt)
                .filter(Receipt.order_id == primary_order.id)
                .first()
            )
            
            if existing_receipt:
                # Update existing receipt
                import json
                existing_receipt.content = json.dumps(receipt_content, ensure_ascii=False, indent=2)
                receipt = existing_receipt
            else:
                # Create new receipt
                import json
                receipt = Receipt(
                    order_id=primary_order.id,
                    content=json.dumps(receipt_content, ensure_ascii=False, indent=2),
                    printed_at=None
                )
                session.add(receipt)
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot close session: no orders found"
            )
        
        session.commit()
        
        return CloseTableResponse(
            status="closed",
            session_id=table_session.id,
            receipt_id=receipt.id,
            closed_at=table_session.closed_at.isoformat(),
            total=total_cents / 100.0
        )
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error closing table: {str(e)}")
    finally:
        session.close()


@router.get("/history", response_model=HistoryResponse, summary="Get order history")
async def get_order_history(
    from_date: Optional[str] = Query(None, description="Filter by closed_at >= from_date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter by closed_at <= to_date (ISO format)"),
    table: Optional[str] = Query(None, description="Filter by table label"),
    limit: int = Query(50, ge=1, le=500, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    storage: Storage = Depends(get_storage_dependency)
):
    """
    Get paginated list of closed table sessions with receipts.
    
    Filters:
    - from_date: ISO datetime string (e.g., "2026-02-01T00:00:00")
    - to_date: ISO datetime string
    - table: Table label (exact match)
    - limit: Results per page (1-500)
    - offset: Pagination offset
    """
    session = _get_db_session(storage)
    
    try:
        # Build query for closed TableSessions with Receipts
        query = (
            session.query(TableSession, Receipt, Order)
            .join(Order, Order.table_session_id == TableSession.id)
            .join(Receipt, Receipt.order_id == Order.id)
            .filter(TableSession.closed_at.isnot(None))
        )
        
        # Apply filters
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                query = query.filter(TableSession.closed_at >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format")
        
        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                query = query.filter(TableSession.closed_at <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format")
        
        if table:
            query = query.filter(TableSession.table_label == table)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply ordering and pagination
        query = query.order_by(TableSession.closed_at.desc())
        results = query.offset(offset).limit(limit).all()
        
        # Build response items
        items = []
        for table_session, receipt, order in results:
            # Calculate total from order
            total_cents = order.total if order.total else 0
            
            items.append(HistoryItem(
                receipt_id=receipt.id,
                order_id=order.id,
                table_label=table_session.table_label,
                closed_at=table_session.closed_at.isoformat(),
                total=total_cents / 100.0,
                printed=receipt.printed_at is not None
            ))
        
        return HistoryResponse(
            items=items,
            total=total_count,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")
    finally:
        session.close()


@router.get("/history/{receipt_id}", response_model=ReceiptDetail, summary="Get receipt details")
async def get_receipt_detail(
    receipt_id: int,
    storage: Storage = Depends(get_storage_dependency)
):
    """
    Get detailed receipt information including printable content.
    
    Returns full receipt data with line items and totals.
    """
    session = _get_db_session(storage)
    
    try:
        # Query receipt with joins
        result = (
            session.query(Receipt, Order, TableSession)
            .join(Order, Receipt.order_id == Order.id)
            .join(TableSession, Order.table_session_id == TableSession.id)
            .filter(Receipt.id == receipt_id)
            .first()
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Receipt {receipt_id} not found")
        
        receipt, order, table_session = result
        
        # Calculate total
        total_cents = order.total if order.total else 0
        
        return ReceiptDetail(
            id=receipt.id,
            order_id=order.id,
            table_label=table_session.table_label,
            opened_at=table_session.opened_at.isoformat(),
            closed_at=table_session.closed_at.isoformat() if table_session.closed_at else None,
            printed_at=receipt.printed_at.isoformat() if receipt.printed_at else None,
            content=receipt.content,
            total=total_cents / 100.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching receipt: {str(e)}")
    finally:
        session.close()


@router.post("/{order_id}/finalize_print", summary="Mark receipt as printed")
async def finalize_print_receipt(
    order_id: int,
    storage: Storage = Depends(get_storage_dependency)
):
    """
    Mark receipt as printed.
    
    Sets Receipt.printed_at to current timestamp.
    """
    session = _get_db_session(storage)
    
    try:
        # Find receipt for this order
        receipt = (
            session.query(Receipt)
            .filter(Receipt.order_id == order_id)
            .first()
        )
        
        if not receipt:
            raise HTTPException(
                status_code=404,
                detail=f"No receipt found for order {order_id}"
            )
        
        # Set printed_at timestamp
        receipt.printed_at = datetime.utcnow()
        session.commit()
        
        return {
            "status": "ok",
            "receipt_id": receipt.id,
            "printed_at": receipt.printed_at.isoformat()
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error marking receipt as printed: {str(e)}")
    finally:
        session.close()
