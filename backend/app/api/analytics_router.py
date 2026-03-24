"""Analytics API router — dashboard snapshot endpoint."""

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_sqlalchemy_session, require_admin
from app.db.models import User
from app.services.analytics_service import (
    build_low_rotation_items,
    build_orders_by_hour,
    build_revenue_per_day,
    build_revenue_per_workstation,
    build_summary,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ---------- Response models ----------

class TopItem(BaseModel):
    name: str
    qty: int
    revenue_cents: int


class SummaryResponse(BaseModel):
    today_revenue: float
    revenue_change_vs_previous_day: float
    orders_count: int
    average_ticket_size: float
    top_items_today: list[TopItem]
    busiest_workstation: str
    peak_hour: str


class RevenuePerDayPoint(BaseModel):
    date: str
    revenue: float


class RevenuePerWorkstationPoint(BaseModel):
    workstation: str
    revenue: float


class OrdersByHourPoint(BaseModel):
    hour: str
    orders_count: int


class LowRotationItemPoint(BaseModel):
    item_name: str
    qty_sold: int


def _parse_window(from_date: Optional[str], to_date: Optional[str]) -> tuple[datetime, datetime]:
    """Parse from/to query params into inclusive datetime bounds."""
    try:
        today = date.today()
        start_date = date.fromisoformat(from_date) if from_date else today
        end_date = date.fromisoformat(to_date) if to_date else today
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Dates must be in YYYY-MM-DD format")

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time(23, 59, 59, 999999))
    return start_dt, end_dt


# ---------- Endpoints ----------

@router.get("/summary", response_model=SummaryResponse, summary="Dashboard analytics snapshot")
async def get_summary(
    from_date: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD (defaults to today)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD (defaults to today)"),
    session: Session = Depends(get_sqlalchemy_session),
    _admin: User = Depends(require_admin),
):
    """Return a compact analytics snapshot for the given date window.

    Defaults to today when `from` and `to` are omitted.
    Both bounds are inclusive (full calendar day).
    """
    start_dt, end_dt = _parse_window(from_date, to_date)

    try:
        data = build_summary(session, start_dt, end_dt)
        return data
    finally:
        session.close()


@router.get(
    "/revenue-per-day",
    response_model=list[RevenuePerDayPoint],
    summary="Revenue grouped by day",
)
async def get_revenue_per_day(
    from_date: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD (defaults to today)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD (defaults to today)"),
    session: Session = Depends(get_sqlalchemy_session),
    _admin: User = Depends(require_admin),
):
    """Return chart-ready revenue per day rows for the given window."""
    start_dt, end_dt = _parse_window(from_date, to_date)
    try:
        return build_revenue_per_day(session, start_dt, end_dt)
    finally:
        session.close()


@router.get(
    "/revenue-per-workstation",
    response_model=list[RevenuePerWorkstationPoint],
    summary="Revenue grouped by workstation",
)
async def get_revenue_per_workstation(
    from_date: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD (defaults to today)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD (defaults to today)"),
    session: Session = Depends(get_sqlalchemy_session),
    _admin: User = Depends(require_admin),
):
    """Return chart-ready revenue per workstation rows for the given window."""
    start_dt, end_dt = _parse_window(from_date, to_date)
    try:
        return build_revenue_per_workstation(session, start_dt, end_dt)
    finally:
        session.close()


@router.get(
    "/orders-by-hour",
    response_model=list[OrdersByHourPoint],
    summary="Orders grouped by hour",
)
async def get_orders_by_hour(
    from_date: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD (defaults to today)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD (defaults to today)"),
    session: Session = Depends(get_sqlalchemy_session),
    _admin: User = Depends(require_admin),
):
    """Return 24-hour order counts for the selected date window."""
    start_dt, end_dt = _parse_window(from_date, to_date)
    try:
        return build_orders_by_hour(session, start_dt, end_dt)
    finally:
        session.close()


@router.get(
    "/low-rotation-items",
    response_model=list[LowRotationItemPoint],
    summary="Bottom 10 items by quantity sold",
)
async def get_low_rotation_items(
    from_date: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD (defaults to today)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD (defaults to today)"),
    session: Session = Depends(get_sqlalchemy_session),
    _admin: User = Depends(require_admin),
):
    """Return the lowest-rotation items for the selected window."""
    start_dt, end_dt = _parse_window(from_date, to_date)
    try:
        return build_low_rotation_items(session, start_dt, end_dt, limit=10)
    finally:
        session.close()
