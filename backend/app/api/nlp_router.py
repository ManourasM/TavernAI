"""NLP training sample capture and export API."""

from datetime import datetime
from io import StringIO
import csv
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import NLPTrainingSample
from app.db.dependencies import require_admin
from app.storage import Storage, SQLAlchemyStorage


router = APIRouter(prefix="/api/nlp", tags=["nlp"])


# Import get_storage at module level to avoid circular imports at import time
# but make it available for endpoint dependency injection

def get_storage_dependency() -> Storage:
    """Get storage from main app - lazy import to avoid circular dependency."""
    from app.main import get_storage
    return get_storage()


class CaptureSampleRequest(BaseModel):
    """Request body for capturing a training sample."""
    raw_text: str
    predicted_item_id: Optional[int] = None
    corrected_item_id: Optional[int] = None
    user_id: Optional[int] = None


class SampleResponse(BaseModel):
    """Response model for training samples."""
    id: int
    raw_text: str
    predicted_item_id: Optional[int]
    corrected_item_id: Optional[int]
    user_id: Optional[int]
    created_at: str


class SamplesListResponse(BaseModel):
    """Paginated response for training samples."""
    items: list[SampleResponse]
    total: int
    limit: int
    offset: int


# ---------- Helper Functions ----------

def _get_db_session(storage: Storage) -> Session:
    """Get a database session from SQLAlchemyStorage."""
    if not isinstance(storage, SQLAlchemyStorage):
        raise HTTPException(
            status_code=501,
            detail="NLP samples require SQLAlchemy storage backend"
        )
    return storage._get_session()


def _sample_to_response(sample: NLPTrainingSample) -> SampleResponse:
    """Convert ORM sample to response model."""
    return SampleResponse(
        id=sample.id,
        raw_text=sample.raw_text,
        predicted_item_id=sample.predicted_menu_item_id,
        corrected_item_id=sample.corrected_menu_item_id,
        user_id=sample.corrected_by_user_id,
        created_at=sample.created_at.isoformat()
    )


# ---------- Endpoints ----------

@router.post("/capture", response_model=SampleResponse, summary="Capture NLP training sample")
async def capture_sample(
    request: CaptureSampleRequest,
    storage: Storage = Depends(get_storage_dependency)
):
    """
    Capture a training sample for NLP improvements.
    
    Stores the raw text, predicted item, corrected item, and user ID.
    """
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is required")

    session = _get_db_session(storage)
    try:
        sample = NLPTrainingSample(
            raw_text=request.raw_text.strip(),
            predicted_menu_item_id=request.predicted_item_id,
            corrected_menu_item_id=request.corrected_item_id,
            corrected_by_user_id=request.user_id,
            created_at=datetime.utcnow()
        )
        session.add(sample)
        session.commit()
        session.refresh(sample)
        return _sample_to_response(sample)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to capture sample: {e}")
    finally:
        session.close()


@router.get("/samples", response_model=SamplesListResponse, summary="List NLP training samples")
async def list_samples(
    from_date: Optional[str] = Query(None, description="Filter by created_at >= from_date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter by created_at <= to_date (ISO format)"),
    user_id: Optional[int] = Query(None, description="Filter by user id"),
    predicted_item_id: Optional[int] = Query(None, description="Filter by predicted item id"),
    corrected_item_id: Optional[int] = Query(None, description="Filter by corrected item id"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    storage: Storage = Depends(get_storage_dependency),
    admin: dict = Depends(require_admin)
):
    """
    Admin-only list of training samples with filters.
    """
    session = _get_db_session(storage)
    try:
        query = session.query(NLPTrainingSample)

        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                query = query.filter(NLPTrainingSample.created_at >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format")

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                query = query.filter(NLPTrainingSample.created_at <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format")

        if user_id is not None:
            query = query.filter(NLPTrainingSample.corrected_by_user_id == user_id)

        if predicted_item_id is not None:
            query = query.filter(NLPTrainingSample.predicted_menu_item_id == predicted_item_id)

        if corrected_item_id is not None:
            query = query.filter(NLPTrainingSample.corrected_menu_item_id == corrected_item_id)

        total_count = query.count()

        samples = (
            query.order_by(NLPTrainingSample.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return SamplesListResponse(
            items=[_sample_to_response(s) for s in samples],
            total=total_count,
            limit=limit,
            offset=offset
        )
    finally:
        session.close()


@router.post("/export", summary="Export NLP training samples as CSV")
async def export_samples(
    from_date: Optional[str] = Query(None, description="Filter by created_at >= from_date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter by created_at <= to_date (ISO format)"),
    user_id: Optional[int] = Query(None, description="Filter by user id"),
    predicted_item_id: Optional[int] = Query(None, description="Filter by predicted item id"),
    corrected_item_id: Optional[int] = Query(None, description="Filter by corrected item id"),
    storage: Storage = Depends(get_storage_dependency),
    admin: dict = Depends(require_admin)
):
    """
    Admin-only export of training samples as CSV.
    """
    session = _get_db_session(storage)
    try:
        query = session.query(NLPTrainingSample)

        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                query = query.filter(NLPTrainingSample.created_at >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format")

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                query = query.filter(NLPTrainingSample.created_at <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format")

        if user_id is not None:
            query = query.filter(NLPTrainingSample.corrected_by_user_id == user_id)

        if predicted_item_id is not None:
            query = query.filter(NLPTrainingSample.predicted_menu_item_id == predicted_item_id)

        if corrected_item_id is not None:
            query = query.filter(NLPTrainingSample.corrected_menu_item_id == corrected_item_id)

        samples = query.order_by(NLPTrainingSample.created_at.desc()).all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id",
            "raw_text",
            "predicted_item_id",
            "corrected_item_id",
            "user_id",
            "created_at"
        ])
        for s in samples:
            writer.writerow([
                s.id,
                s.raw_text,
                s.predicted_menu_item_id,
                s.corrected_menu_item_id,
                s.corrected_by_user_id,
                s.created_at.isoformat()
            ])

        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nlp_samples.csv"}
        )
    finally:
        session.close()
