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
from app.db.menu_access import get_latest_menu
from app.nlp import _normalize_text_basic, _normalize_rule_key
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
    predicted_item_id: Optional[str] = None
    corrected_item_id: Optional[str] = None
    user_id: Optional[int] = None


class SampleResponse(BaseModel):
    """Response model for training samples."""
    id: int
    raw_text: str
    predicted_item_id: Optional[str]
    corrected_item_id: Optional[str]
    user_id: Optional[int]
    created_at: str


class RuleResponse(BaseModel):
    """Response model for NLP override rules."""
    id: int
    raw_text: str
    corrected_item_id: Optional[str]
    corrected_item_name: Optional[str]
    created_at: str


class RuleUpdateRequest(BaseModel):
    """Request body for updating a rule."""
    raw_text: Optional[str] = None
    corrected_item_id: Optional[str] = None


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


def _build_menu_index(menu_dict):
    index = {}
    if not isinstance(menu_dict, dict):
        return index
    for top_cat, items in menu_dict.items():
        if not isinstance(items, (list, tuple)):
            continue
        for entry in items:
            if not isinstance(entry, dict):
                continue
            item_id = entry.get("id")
            if not item_id:
                continue
            index[str(item_id)] = {
                "id": str(item_id),
                "name": entry.get("name") or entry.get("title") or "",
                "price": entry.get("price"),
                "category": entry.get("category") or entry.get("station") or top_cat
            }
    return index


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
    predicted_item_id: Optional[str] = Query(None, description="Filter by predicted item id"),
    corrected_item_id: Optional[str] = Query(None, description="Filter by corrected item id"),
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
    predicted_item_id: Optional[str] = Query(None, description="Filter by predicted item id"),
    corrected_item_id: Optional[str] = Query(None, description="Filter by corrected item id"),
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


@router.get("/rules", response_model=list[RuleResponse], summary="List NLP override rules")
async def list_rules(
    limit: int = Query(200, ge=1, le=1000),
    storage: Storage = Depends(get_storage_dependency),
    admin: dict = Depends(require_admin)
):
    """
    Admin-only list of override rules (latest correction per normalized raw_text).
    """
    session = _get_db_session(storage)
    try:
        menu_dict = get_latest_menu(session)
        menu_index = _build_menu_index(menu_dict)

        samples = (
            session.query(NLPTrainingSample)
            .filter(NLPTrainingSample.corrected_menu_item_id.isnot(None))
            .order_by(NLPTrainingSample.created_at.desc())
            .limit(limit)
            .all()
        )

        rules_map = {}
        rules = []
        for s in samples:
            key = _normalize_rule_key(s.raw_text)
            if not key or key in rules_map:
                continue
            corrected_id = str(s.corrected_menu_item_id) if s.corrected_menu_item_id is not None else None
            corrected_item = menu_index.get(corrected_id) if corrected_id else None
            rules_map[key] = True
            rules.append(
                RuleResponse(
                    id=s.id,
                    raw_text=s.raw_text,
                    corrected_item_id=corrected_id,
                    corrected_item_name=corrected_item.get("name") if corrected_item else None,
                    created_at=s.created_at.isoformat()
                )
            )

        return rules
    finally:
        session.close()


@router.put("/rules/{rule_id}", response_model=RuleResponse, summary="Update NLP override rule")
async def update_rule(
    rule_id: int,
    request: RuleUpdateRequest,
    storage: Storage = Depends(get_storage_dependency),
    admin: dict = Depends(require_admin)
):
    session = _get_db_session(storage)
    try:
        sample = session.query(NLPTrainingSample).filter(NLPTrainingSample.id == rule_id).first()
        if not sample:
            raise HTTPException(status_code=404, detail="Rule not found")

        if request.raw_text is not None:
            if not request.raw_text.strip():
                raise HTTPException(status_code=400, detail="raw_text cannot be empty")
            sample.raw_text = request.raw_text.strip()

        if request.corrected_item_id is not None:
            menu_dict = get_latest_menu(session)
            menu_index = _build_menu_index(menu_dict)
            corrected_id = str(request.corrected_item_id) if request.corrected_item_id else ""
            if corrected_id and corrected_id not in menu_index:
                raise HTTPException(status_code=400, detail="corrected_item_id not found in menu")
            sample.corrected_menu_item_id = request.corrected_item_id

        session.commit()
        session.refresh(sample)

        menu_dict = get_latest_menu(session)
        menu_index = _build_menu_index(menu_dict)
        corrected_id = str(sample.corrected_menu_item_id) if sample.corrected_menu_item_id is not None else None
        corrected_item = menu_index.get(corrected_id) if corrected_id else None

        return RuleResponse(
            id=sample.id,
            raw_text=sample.raw_text,
            corrected_item_id=corrected_id,
            corrected_item_name=corrected_item.get("name") if corrected_item else None,
            created_at=sample.created_at.isoformat()
        )
    finally:
        session.close()


@router.delete("/rules/{rule_id}", summary="Delete NLP override rule")
async def delete_rule(
    rule_id: int,
    storage: Storage = Depends(get_storage_dependency),
    admin: dict = Depends(require_admin)
):
    session = _get_db_session(storage)
    try:
        sample = session.query(NLPTrainingSample).filter(NLPTrainingSample.id == rule_id).first()
        if not sample:
            raise HTTPException(status_code=404, detail="Rule not found")
        session.delete(sample)
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()
