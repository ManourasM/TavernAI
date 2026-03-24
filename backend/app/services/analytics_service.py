"""Analytics aggregation service for TavernAI dashboard summary."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Order, OrderItem, Receipt, TableSession


def _revenue_for_window(session: Session, start: datetime, end: datetime) -> int:
    """Return total revenue in cents for closed orders within the given window.

    Uses Order.total when available, otherwise sums OrderItem.line_total.
    Only considers orders that belong to a closed TableSession.
    """
    result = (
        session.query(func.coalesce(func.sum(OrderItem.line_total), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711 — SQLAlchemy requires != None
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .scalar()
    )
    return int(result or 0)


def _orders_count(session: Session, start: datetime, end: datetime) -> int:
    """Return the number of distinct paid checkouts in the window.

    Legacy storage currently creates one Order row per submitted item, so raw
    Order.id counts inflate the apparent number of orders. For overview KPIs we
    want one count per closed table session that actually has non-cancelled
    items in the selected window.
    """
    result = (
        session.query(func.count(func.distinct(Order.table_session_id)))
        .select_from(Order)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .scalar()
    )
    return int(result or 0)


def _top_items(session: Session, start: datetime, end: datetime, limit: int = 5) -> list[dict]:
    """Return top items by total quantity sold within the window."""
    rows = (
        session.query(
            OrderItem.name,
            func.sum(OrderItem.qty).label("total_qty"),
            func.sum(OrderItem.line_total).label("total_revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.qty).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "name": row.name,
            "qty": int(row.total_qty or 0),
            "revenue_cents": int(row.total_revenue or 0),
        }
        for row in rows
    ]


def _busiest_workstation(session: Session, start: datetime, end: datetime) -> str:
    """Return the station slug/name with the most order items in the window."""
    row = (
        session.query(
            OrderItem.category,
            func.count(OrderItem.id).label("item_count"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
            OrderItem.category != None,  # noqa: E711
        )
        .group_by(OrderItem.category)
        .order_by(func.count(OrderItem.id).desc())
        .first()
    )
    return row.category if row else ""


def _peak_hour(session: Session, start: datetime, end: datetime) -> str:
    """Return the busiest hour of day as HH:00 string (based on order creation time)."""
    # SQLite-compatible hour extraction
    row = (
        session.query(
            func.strftime("%H", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
        )
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
        )
        .group_by(func.strftime("%H", Order.created_at))
        .order_by(func.count(Order.id).desc())
        .first()
    )
    if row and row.hour is not None:
        return f"{row.hour}:00"
    return ""


def build_summary(session: Session, start: datetime, end: datetime) -> dict[str, Any]:
    """Assemble the full analytics summary for the given time window.

    All monetary values are returned in euros (float, 2 dp) for frontend ease.
    Revenue change is a percentage float; 0.0 when previous window had no revenue.
    """
    today_revenue_cents = _revenue_for_window(session, start, end)

    # Previous window of equal length (same day width, shifted back)
    window_size = end - start
    prev_start = start - window_size - timedelta(seconds=1)
    prev_end = start - timedelta(seconds=1)
    prev_revenue_cents = _revenue_for_window(session, prev_start, prev_end)

    if prev_revenue_cents > 0:
        revenue_change = round(
            (today_revenue_cents - prev_revenue_cents) / prev_revenue_cents * 100, 2
        )
    else:
        revenue_change = 0.0

    count = _orders_count(session, start, end)
    avg_ticket_cents = (today_revenue_cents / count) if count > 0 else 0

    return {
        "today_revenue": round(today_revenue_cents / 100, 2),
        "revenue_change_vs_previous_day": revenue_change,
        "orders_count": count,
        "average_ticket_size": round(avg_ticket_cents / 100, 2),
        "top_items_today": _top_items(session, start, end),
        "busiest_workstation": _busiest_workstation(session, start, end),
        "peak_hour": _peak_hour(session, start, end),
    }


def build_revenue_per_day(session: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Return chart-ready revenue per day rows as [{date, revenue}]."""
    rows = (
        session.query(
            func.strftime("%Y-%m-%d", Order.created_at).label("date"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue_cents"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .group_by(func.strftime("%Y-%m-%d", Order.created_at))
        .order_by(func.strftime("%Y-%m-%d", Order.created_at).asc())
        .all()
    )

    return [
        {
            "date": row.date,
            "revenue": round(int(row.revenue_cents or 0) / 100, 2),
        }
        for row in rows
    ]


def build_revenue_per_workstation(
    session: Session, start: datetime, end: datetime
) -> list[dict[str, Any]]:
    """Return chart-ready revenue per workstation rows as [{workstation, revenue}]."""
    rows = (
        session.query(
            OrderItem.category.label("workstation"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue_cents"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .group_by(OrderItem.category)
        .order_by(func.coalesce(func.sum(OrderItem.line_total), 0).desc())
        .all()
    )

    return [
        {
            "workstation": row.workstation or "unknown",
            "revenue": round(int(row.revenue_cents or 0) / 100, 2),
        }
        for row in rows
    ]


def build_orders_by_hour(session: Session, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Return 24 rows ({hour, orders_count}) with zero-filled missing hours."""
    rows = (
        session.query(
            func.strftime("%H", Order.created_at).label("hour"),
            func.count(Order.id).label("orders_count"),
        )
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
        )
        .group_by(func.strftime("%H", Order.created_at))
        .all()
    )

    by_hour = {str(row.hour): int(row.orders_count or 0) for row in rows}
    return [
        {
            "hour": f"{hour:02d}:00",
            "orders_count": by_hour.get(f"{hour:02d}", 0),
        }
        for hour in range(24)
    ]


def build_low_rotation_items(
    session: Session, start: datetime, end: datetime, limit: int = 10
) -> list[dict[str, Any]]:
    """Return bottom-N items by quantity sold as [{item_name, qty_sold}]."""
    rows = (
        session.query(
            OrderItem.name.label("item_name"),
            func.sum(OrderItem.qty).label("qty_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(TableSession, Order.table_session_id == TableSession.id)
        .filter(
            TableSession.closed_at != None,  # noqa: E711
            Order.created_at >= start,
            Order.created_at <= end,
            OrderItem.status != "cancelled",
        )
        .group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.qty).asc(), OrderItem.name.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "item_name": row.item_name,
            "qty_sold": int(row.qty_sold or 0),
        }
        for row in rows
    ]
