from fastapi import APIRouter
from pydantic import BaseModel
from app.nlp import classify_order

router = APIRouter()

class OrderRequest(BaseModel):
    order_text: str

@router.post("/")
def submit_order(order: OrderRequest):
    categorized = classify_order(order.order_text)
    return {"status": "received", "categorized": categorized}
